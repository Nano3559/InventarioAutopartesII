import { Response, NextFunction } from "express";
import jwt from "jsonwebtoken";
import { PrismaClient } from "@prisma/client";
import { config } from "../../config";
import { AuthRequest, AuthPayload } from "../types";

const prisma = new PrismaClient();

// Caché en memoria (single-instancia) de permisos por rol.
// Evita re-leer roleModel por cada request que usa authorizeModule.
// La invalidación ocurre cuando se actualizan permisos (ver permissions.routes).
interface CachedRole {
  name: string;
  permissions: string[];
  cachedAt: number;
}
const rolePermissionCache = new Map<number, CachedRole>();

// TTL de la caché: red de seguridad si los permisos cambian por una vía que no
// pase por permissions.routes (migración, script, otra instancia si se escala).
const ROLE_CACHE_TTL_MS = 60_000;

export function invalidateRoleCache(roleId: number) {
  rolePermissionCache.delete(roleId);
}

export function clearRoleCache() {
  rolePermissionCache.clear();
}

async function getCachedRole(roleId: number): Promise<CachedRole | null> {
  const cached = rolePermissionCache.get(roleId);
  if (cached && Date.now() - cached.cachedAt < ROLE_CACHE_TTL_MS) return cached;
  if (cached) rolePermissionCache.delete(roleId);

  const role = await prisma.roleModel.findUnique({
    where: { id: roleId },
    select: { name: true, permissions: true },
  });
  if (!role) return null;

  const entry = { name: role.name, permissions: role.permissions || [], cachedAt: Date.now() };
  rolePermissionCache.set(roleId, entry);
  return entry;
}

export const authenticate = (req: AuthRequest, res: Response, next: NextFunction) => {
  const authHeader = req.headers.authorization;

  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    return res.status(401).json({ message: "Token no proporcionado" });
  }

  const token = authHeader.split(" ")[1];

  try {
    const decoded = jwt.verify(token, config.jwtSecret, { algorithms: ["HS256"] }) as AuthPayload;
    req.user = decoded;
    next();
  } catch {
    return res.status(401).json({ message: "Token inválido o expirado" });
  }
};

export const optionalAuth = (req: AuthRequest, _res: Response, next: NextFunction) => {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith("Bearer ")) return next();
  try {
    const token = authHeader.split(" ")[1];
    req.user = jwt.verify(token, config.jwtSecret, { algorithms: ["HS256"] }) as AuthPayload;
  } catch { /* ignore invalid token */ }
  next();
};

export const authorize = (...roles: string[]) => {
  return (req: AuthRequest, res: Response, next: NextFunction) => {
    if (!req.user) {
      return res.status(401).json({ message: "No autenticado" });
    }

    if (!roles.includes(req.user.role)) {
      return res.status(403).json({ message: "No tiene permisos para esta acción" });
    }

    next();
  };
};

export const authorizeModule = (module: string) => {
  return async (req: AuthRequest, res: Response, next: NextFunction) => {
    if (!req.user) {
      return res.status(401).json({ message: "No autenticado" });
    }

    // ADMIN always has access
    if (req.user.role === "ADMIN") return next();

    try {
      const user = await prisma.user.findUnique({
        where: { id: req.user.userId },
        select: { roleId: true },
      });

      if (!user) return res.status(401).json({ message: "Usuario no encontrado" });

      const cached = await getCachedRole(user.roleId);

      if (!cached) return res.status(401).json({ message: "Usuario no encontrado" });

      if (cached.name === "ADMIN") return next();

      if (!cached.permissions.includes(module)) {
        return res.status(403).json({ message: `No tiene acceso al módulo: ${module}` });
      }

      next();
    } catch {
      return res.status(500).json({ message: "Error al verificar permisos" });
    }
  };
};

/**
 * Exige que los usuarios TIENDA tengan una ubicación asignada. Los usuarios
 * de otros roles pasan sin restricción. Devuelve 403 si un TIENDA no tiene
 * locationId (no puede operar sobre datos de ubicación sin estar asignado a una).
 */
export const requireTiendaLocation = (req: AuthRequest, res: Response, next: NextFunction) => {
  if (req.user?.role === "TIENDA" && !req.user.locationId) {
    return res.status(403).json({ message: "Usuario TIENDA sin ubicación asignada" });
  }
  next();
};

/**
 * Bloquea por completo el acceso de usuarios TIENDA a una ruta/recurso.
 * Util para endpoints administrativos globales (proveedores, costos, etc.).
 */
export const blockTienda = (req: AuthRequest, res: Response, next: NextFunction) => {
  if (req.user?.role === "TIENDA") {
    return res.status(403).json({ message: "Acción no permitida para usuario TIENDA" });
  }
  next();
};
