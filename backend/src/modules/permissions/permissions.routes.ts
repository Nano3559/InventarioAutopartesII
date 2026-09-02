import { Router, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { authenticate, authorize } from "../../shared/middlewares/auth";
import { AuthRequest } from "../../shared/types";

const router = Router();
const prisma = new PrismaClient();

router.use(authenticate);

const AVAILABLE_MODULES = [
  "inventario", "ventas", "ventas-mayor", "devoluciones",
  "solicitudes", "movimientos", "costos", "precios", "reportes", "configuracion",
];

const DEFAULT_COLUMNS: Record<string, string[]> = {
  inventario: ["ID", "Fabricante", "Producto", "Marca", "Modelo", "Año", "Detalles", "Cód. OEM", "Cód. Fábrica", "Proveedor", "Imagen", "Precio 1", "Precio 2", "Stock", "Acciones"],
  ventas: ["ID", "Fecha", "Cliente", "Tienda", "Vendedor", "Total", "Estado", "Acciones"],
};

// GET /roles — Listar roles con permisos y columnas
router.get("/roles", async (_req: AuthRequest, res: Response) => {
  try {
    const roles = await prisma.roleModel.findMany({
      include: { _count: { select: { users: true } } },
      orderBy: { id: "asc" },
    });

    const result = roles.map((r) => ({
      id: r.id,
      name: r.name,
      permissions: r.permissions || [],
      columnConfig: r.columnConfig || {},
      userCount: r._count.users,
    }));

    res.json({ roles: result });
  } catch (error) {
    console.error("Error al listar roles:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /roles/modules — Módulos disponibles
router.get("/roles/modules", (_req: AuthRequest, res: Response) => {
  res.json({ modules: AVAILABLE_MODULES, defaultColumns: DEFAULT_COLUMNS });
});

// PUT /roles/:id/permissions — Actualizar permisos de módulos
router.put("/roles/:id/permissions", authorize("ADMIN"), async (req: AuthRequest, res: Response) => {
  try {
    const roleId = Number(req.params.id);
    const { permissions } = req.body;

    if (!Array.isArray(permissions)) {
      return res.status(400).json({ message: "permissions debe ser un array" });
    }

    const invalidModules = permissions.filter((p: string) => !AVAILABLE_MODULES.includes(p));
    if (invalidModules.length > 0) {
      return res.status(400).json({ message: `Módulos inválidos: ${invalidModules.join(", ")}` });
    }

    const role = await prisma.roleModel.findUnique({ where: { id: roleId } });
    if (!role) return res.status(404).json({ message: "Rol no encontrado" });

    const oldValue = { permissions: role.permissions };

    const updated = await prisma.roleModel.update({
      where: { id: roleId },
      data: { permissions },
    });

    if (req.user) {
      await prisma.auditLog.create({
        data: {
          userId: req.user.userId,
          action: "UPDATE_PERMISSIONS",
          targetType: "ROLE",
          targetId: roleId,
          oldValue,
          newValue: { permissions },
        },
      });
    }

    res.json({ id: updated.id, name: updated.name, permissions: updated.permissions });
  } catch (error) {
    console.error("Error al actualizar permisos:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// PUT /roles/:id/columns — Actualizar configuración de columnas
router.put("/roles/:id/columns", authorize("ADMIN"), async (req: AuthRequest, res: Response) => {
  try {
    const roleId = Number(req.params.id);
    const { columnConfig } = req.body;

    if (!columnConfig || typeof columnConfig !== "object") {
      return res.status(400).json({ message: "columnConfig debe ser un objeto" });
    }

    const role = await prisma.roleModel.findUnique({ where: { id: roleId } });
    if (!role) return res.status(404).json({ message: "Rol no encontrado" });

    const oldValue = { columnConfig: role.columnConfig };

    const updated = await prisma.roleModel.update({
      where: { id: roleId },
      data: { columnConfig },
    });

    if (req.user) {
      await prisma.auditLog.create({
        data: {
          userId: req.user.userId,
          action: "UPDATE_COLUMNS",
          targetType: "ROLE",
          targetId: roleId,
          oldValue,
          newValue: { columnConfig },
        },
      });
    }

    res.json({ id: updated.id, name: updated.name, columnConfig: updated.columnConfig });
  } catch (error) {
    console.error("Error al actualizar columnas:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /audit — Log de auditoría
router.get("/audit", authorize("ADMIN"), async (req: AuthRequest, res: Response) => {
  try {
    const { page = "1", limit = "20" } = req.query;
    const pg = Math.max(1, Number(page) || 1);
    const take = Math.min(100, Math.max(1, Number(limit) || 20));
    const skip = (pg - 1) * take;

    const [logs, total] = await Promise.all([
      prisma.auditLog.findMany({
        include: { user: { select: { id: true, name: true, email: true } } },
        orderBy: { createdAt: "desc" },
        skip,
        take,
      }),
      prisma.auditLog.count(),
    ]);

    res.json({
      logs,
      pagination: { total, page: pg, limit: take, pages: Math.ceil(total / take) },
    });
  } catch (error) {
    console.error("Error al obtener auditoría:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /permissions/me — Permisos del usuario actual
router.get("/permissions/me", async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) return res.status(401).json({ message: "No autenticado" });

    const user = await prisma.user.findUnique({
      where: { id: req.user.userId },
      include: { role: true },
    });

    if (!user) return res.status(404).json({ message: "Usuario no encontrado" });

    res.json({
      role: user.role.name,
      permissions: user.role.permissions || [],
      columnConfig: user.role.columnConfig || {},
    });
  } catch (error) {
    console.error("Error al obtener permisos:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
