import { Response, NextFunction } from "express";
import jwt from "jsonwebtoken";
import { PrismaClient } from "@prisma/client";
import { config } from "../../config";
import { AuthRequest, AuthPayload } from "../types";

const prisma = new PrismaClient();

export const authenticate = (req: AuthRequest, res: Response, next: NextFunction) => {
  const authHeader = req.headers.authorization;

  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    return res.status(401).json({ message: "Token no proporcionado" });
  }

  const token = authHeader.split(" ")[1];

  try {
    const decoded = jwt.verify(token, config.jwtSecret) as AuthPayload;
    req.user = decoded;
    next();
  } catch {
    return res.status(401).json({ message: "Token inválido o expirado" });
  }
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
        include: { role: true },
      });

      if (!user) return res.status(401).json({ message: "Usuario no encontrado" });

      const permissions = user.role.permissions || [];
      if (!permissions.includes(module)) {
        return res.status(403).json({ message: `No tiene acceso al módulo: ${module}` });
      }

      next();
    } catch {
      return res.status(500).json({ message: "Error al verificar permisos" });
    }
  };
};
