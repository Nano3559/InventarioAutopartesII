import { Router, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { authenticate } from "../../shared/middlewares/auth";
import { AuthRequest } from "../../shared/types";

const router = Router();
const prisma = new PrismaClient();

router.use(authenticate);

// GET / — Obtener notificaciones del usuario
router.get("/", async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) return res.status(401).json({ message: "No autenticado" });

    const { unreadOnly } = req.query;
    const where: any = { userId: req.user.userId };
    if (unreadOnly === "true") where.read = false;

    const [notifications, unreadCount] = await Promise.all([
      prisma.notification.findMany({
        where,
        orderBy: { createdAt: "desc" },
        take: 50,
      }),
      prisma.notification.count({
        where: { userId: req.user.userId, read: false },
      }),
    ]);

    res.json({ notifications, unreadCount });
  } catch (error) {
    console.error("Error al obtener notificaciones:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// PUT /:id/read — Marcar como leída
router.put("/:id/read", async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) return res.status(401).json({ message: "No autenticado" });
    const id = Number(req.params.id);
    if (isNaN(id)) return res.status(400).json({ message: "ID inválido" });

    const notification = await prisma.notification.findUnique({ where: { id } });
    if (!notification) return res.status(404).json({ message: "Notificación no encontrada" });
    if (notification.userId !== req.user.userId) return res.status(403).json({ message: "No autorizado" });

    const updated = await prisma.notification.update({
      where: { id },
      data: { read: true },
    });

    res.json(updated);
  } catch (error) {
    console.error("Error al marcar notificación:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// PUT /read-all — Marcar todas como leídas
router.put("/read-all", async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) return res.status(401).json({ message: "No autenticado" });

    await prisma.notification.updateMany({
      where: { userId: req.user.userId, read: false },
      data: { read: true },
    });

    res.json({ message: "Todas las notificaciones marcadas como leídas" });
  } catch (error) {
    console.error("Error al marcar notificaciones:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
