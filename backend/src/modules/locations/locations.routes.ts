import { Router, Request, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { authenticate } from "../../shared/middlewares/auth";

const router = Router();
const prisma = new PrismaClient();

router.use(authenticate);

// GET / — Listar ubicaciones
router.get("/", async (_req: Request, res: Response) => {
  try {
    const locations = await prisma.location.findMany({
      orderBy: { name: "asc" },
    });
    res.json({ locations });
  } catch (error) {
    console.error("Error al listar ubicaciones:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
