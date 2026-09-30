import { Router, Response } from "express";
import { PrismaClient, RequestStatus } from "@prisma/client";
import { authenticate, authorize, requireTiendaLocation } from "../../shared/middlewares/auth";
import { AuthRequest } from "../../shared/types";
import { parseId, parsePositiveInt } from "../../shared/middlewares/validate";
import { isPrismaClientError } from "../../shared/utils/errors";
import { parsePagination } from "../../shared/utils/pagination";
import { notificarInventarioSolicitud } from "../../shared/utils/notificarInventario";
import { nextDayAt8, REQUEST_STATUS_ACTIVOS } from "../../utils/replenish";

const router = Router();
const prisma = new PrismaClient();

router.use(authenticate);
router.use(requireTiendaLocation);

// Se exporta para que los tests puedan verificar el invariante
// VALID_STATUSES === REQUEST_STATUS_ACTIVOS + estados terminales (si se agrega un
// estado nuevo y se olvida la lista de activos, el índice parcial quedaría obsoleto).
export const VALID_STATUSES: RequestStatus[] = [
  "PENDIENTE", "RECIBIDO_POR_INVENTARIO", "PREPARANDO",
  "ENTREGADO", "RECIBIDO_POR_TIENDA", "CANCELADO",
];

const VALID_TRANSITIONS: Record<string, RequestStatus[]> = {
  PENDIENTE: ["RECIBIDO_POR_INVENTARIO", "CANCELADO"],
  RECIBIDO_POR_INVENTARIO: ["PREPARANDO", "CANCELADO"],
  PREPARANDO: ["ENTREGADO", "CANCELADO"],
  ENTREGADO: ["RECIBIDO_POR_TIENDA"],
  RECIBIDO_POR_TIENDA: [],
  CANCELADO: [],
};

const INVENTARIO_STATUSES: RequestStatus[] = ["RECIBIDO_POR_INVENTARIO", "PREPARANDO", "ENTREGADO"];

// GET / — Listar solicitudes con filtros + historial
router.get("/", async (req: AuthRequest, res: Response) => {
  try {
    const { status, locationId, page = "1", limit = "20" } = req.query;

    const where: any = {};
    if (status && typeof status === "string") where.status = status as RequestStatus;
    if (locationId && typeof locationId === "string") where.locationId = Number(locationId);

    if (req.user?.role === "TIENDA") {
      where.locationId = req.user.locationId;
    }

    const { page: pg, limit: take, skip } = parsePagination(page, limit, 100);

    const [requests, total] = await Promise.all([
      prisma.productRequest.findMany({
        where,
        include: {
          product: { select: { id: true, name: true, itemCode: true, brand: true, model: true } },
          location: { select: { id: true, name: true, type: true } },
          requestedBy: { select: { id: true, name: true, email: true } },
          history: { orderBy: { createdAt: "asc" } },
        },
        skip,
        take,
        orderBy: { date: "desc" },
      }),
      prisma.productRequest.count({ where }),
    ]);

    res.json({
      requests,
      pagination: { total, page: pg, limit: take, pages: Math.ceil(total / take) },
    });
  } catch (error) {
    console.error("Error al listar solicitudes:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /:id — Detalle de solicitud con historial
router.get("/:id", async (req: AuthRequest, res: Response) => {
  try {
    const id = parseId(req.params.id);
    const request = await prisma.productRequest.findUnique({
      where: { id },
      include: {
        product: { select: { id: true, name: true, itemCode: true, brand: true, model: true } },
        location: { select: { id: true, name: true, type: true } },
        requestedBy: { select: { id: true, name: true, email: true } },
        history: {
          include: { request: false },
          orderBy: { createdAt: "asc" },
        },
      },
    });

    if (!request) return res.status(404).json({ message: "Solicitud no encontrada" });
    if (req.user?.role === "TIENDA" && req.user.locationId && request.locationId !== req.user.locationId) {
      return res.status(403).json({ message: "No tiene acceso a esta solicitud" });
    }
    res.json(request);
  } catch (error: any) {
    if (error.message === "ID inválido") return res.status(400).json({ message: error.message });
    console.error("Error al obtener solicitud:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// POST — Crear solicitud (tienda pide a almacén)
router.post("/", async (req: AuthRequest, res: Response) => {
  try {
    const productId = parsePositiveInt(req.body.productId, "Producto");
    const quantity = parsePositiveInt(req.body.quantity, "Cantidad");
    const note = req.body.note || null;

    if (quantity <= 0) return res.status(400).json({ message: "La cantidad debe ser mayor a 0" });

    // El solicitante y su rol salen del token, no del body
    const requestedById = req.user!.userId;
    const requesterRole = req.user!.role;

    let locationId: number;
    if (requesterRole === "TIENDA") {
      if (!req.user!.locationId) {
        return res.status(400).json({ message: "Usuario TIENDA sin ubicación asignada" });
      }
      locationId = req.user!.locationId;
    } else {
      locationId = parsePositiveInt(req.body.locationId, "Ubicación");
    }

    const [product, location] = await Promise.all([
      prisma.product.findUnique({ where: { id: productId } }),
      prisma.location.findUnique({ where: { id: locationId } }),
    ]);

    if (!product) return res.status(404).json({ message: "Producto no encontrado" });
    if (!location) return res.status(404).json({ message: "Ubicación no encontrada" });

    // Una sola solicitud ABIERTA por producto y ubicación (mismo criterio que
    // aplica el job automático). Se comprueba aquí para dar un 409 con mensaje
    // claro en vez de depender del índice único parcial, que respondería 500.
    const yaAbierta = await prisma.productRequest.findFirst({
      where: { productId, locationId, status: { in: REQUEST_STATUS_ACTIVOS } },
      select: { id: true, status: true },
    });
    if (yaAbierta) {
      return res.status(409).json({
        message: `Ya existe una solicitud abierta (#${yaAbierta.id}, estado ${yaAbierta.status}) para este producto en esta ubicación. Cancelá esa solicitud o esperá a que se cierre para poder pedir de nuevo.`,
      });
    }

    const request = await prisma.productRequest.create({
      data: {
        productId,
        quantity,
        locationId,
        requestedById,
        note,
        // Sin expectedDate el job (expectedDate <= now) nunca activaba la
        // solicitud: quedaba PENDIENTE sin llegar a RECIBIDO_POR_INVENTARIO.
        expectedDate: nextDayAt8(),
        history: {
          create: {
            newStatus: "PENDIENTE",
            userId: requestedById,
            userRole: requesterRole,
          },
        },
      },
      include: {
        product: { select: { name: true, itemCode: true } },
        location: { select: { name: true } },
        history: true,
      },
    });

    // E5/E7: avisar a INVENTARIO en el momento de crear la solicitud.
    await notificarInventarioSolicitud(prisma, {
      requestId: request.id,
      productName: request.product?.name ?? `Producto #${productId}`,
      locationName: request.location?.name ?? `Ubicación #${locationId}`,
      quantity,
      origen: "Solicitud manual",
    });

    res.status(201).json(request);
  } catch (error: any) {
    // Carrera con otra creación simultánea: el índice único parcial
    // (ProductRequest_solicitud_abierta_unica) rechaza la segunda fila. Se traduce a
    // 409 en vez de dejar un 500 opaco.
    if (error?.code === "P2002") {
      return res.status(409).json({
        message:
          "Ya existe una solicitud abierta para este producto en esta ubicación. Cancelá esa solicitud o esperá a que se cierre para poder pedir de nuevo.",
      });
    }
    if (typeof error?.message === "string" && !isPrismaClientError(error)) {
      return res.status(400).json({ message: error.message });
    }
    console.error("Error al crear solicitud:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// PUT /:id — Cambiar estado de solicitud con historial
router.put("/:id", async (req: AuthRequest, res: Response) => {
  try {
    const id = parseId(req.params.id);
    const { status } = req.body;

    if (!status) return res.status(400).json({ message: "Campo obligatorio: status" });
    if (!VALID_STATUSES.includes(status)) {
      return res.status(400).json({ message: `Estado inválido. Valores válidos: ${VALID_STATUSES.join(", ")}` });
    }

    const existing = await prisma.productRequest.findUnique({ where: { id } });
    if (!existing) return res.status(404).json({ message: "Solicitud no encontrada" });

    const allowedTransitions = VALID_TRANSITIONS[existing.status] || [];
    if (!allowedTransitions.includes(status)) {
      return res.status(400).json({
        message: `No se puede cambiar de "${existing.status}" a "${status}"`,
      });
    }

    const role = req.user?.role || "";
    if (INVENTARIO_STATUSES.includes(status) && role !== "ADMIN" && role !== "INVENTARIO") {
      return res.status(403).json({ message: "Solo INVENTARIO o ADMIN pueden realizar esta acción" });
    }
    if (status === "RECIBIDO_POR_TIENDA" && role !== "ADMIN" && role !== "TIENDA") {
      return res.status(403).json({ message: "Solo TIENDA o ADMIN pueden confirmar recepción" });
    }
    if (role === "TIENDA" && existing.locationId !== req.user?.locationId) {
      return res.status(403).json({ message: "No puede modificar solicitudes de otra tienda" });
    }

    const STATUS_LABELS: Record<string, string> = {
      PENDIENTE: "Pendiente",
      RECIBIDO_POR_INVENTARIO: "Recibido por Inventario",
      PREPARANDO: "Preparando",
      ENTREGADO: "Entregado",
      RECIBIDO_POR_TIENDA: "Recibido por Tienda",
      CANCELADO: "Cancelado",
    };

    // Transición ATÓMICA: se relee el estado DENTRO de la transacción y el update se
    // condiciona a ese estado (updateMany). Antes se validaba contra una lectura
    //Outside de la transacción y el update solo condicionaba por id, de modo que dos
    // peticiones concurrentes (p. ej. INVENTARIO avanzando y TIENDA cancelando) pasaban
    // ambas la validación y la última en commit pisaba a la otra: una solicitud ya
    // cancelada podía "resucitar" y el RequestHistory quedaba con transiciones
    // imposibles. Si el estado cambió entre la lectura y el update, count === 0 y se
    // responde 409 en vez de escribir una transición que no aplica.
    const updated = await prisma.$transaction(async (tx) => {
      const actual = await tx.productRequest.findUnique({ where: { id }, select: { status: true } });
      if (!actual) return { conflicto: "AUSENTE" as const };
      if (actual.status !== existing.status) return { conflicto: "CAMBIO" as const, status: actual.status };

      const cambios = await tx.productRequest.updateMany({
        where: { id, status: existing.status },
        data: { status },
      });
      if (cambios.count !== 1) return { conflicto: "CAMBIO" as const, status: actual.status };

      await tx.requestHistory.create({
        data: {
          requestId: id,
          previousStatus: existing.status,
          newStatus: status,
          userId: req.user?.userId || 0,
          userRole: role,
        },
      });

      return {
        conflicto: "NINGUNO" as const,
        dato: await tx.productRequest.findUniqueOrThrow({
          where: { id },
          include: {
            product: { select: { name: true, itemCode: true } },
            location: { select: { name: true } },
            requestedBy: { select: { name: true } },
          },
        }),
      };
    });

    if (updated.conflicto === "AUSENTE") return res.status(404).json({ message: "Solicitud no encontrada" });
    if (updated.conflicto === "CAMBIO") {
      return res.status(409).json({
        message: `La solicitud cambió a "${updated.status}" mientras se procesaba tu petición. Recargá la lista e intentá de nuevo.`,
      });
    }
    const request = updated.dato;

    // Notify the requester about status change
    if (existing.requestedById) {
      await prisma.notification.create({
        data: {
          userId: existing.requestedById,
          title: `Solicitud #${id} - ${STATUS_LABELS[status] || status}`,
          message: `La solicitud del producto "${request.product?.name}" fue cambiada a "${STATUS_LABELS[status] || status}" por ${request.requestedBy?.name || "Sistema"}.`,
          type: status === "CANCELADO" ? "WARNING" : "INFO",
          linkUrl: "/panel/solicitudes",
        },
      });
    }

    res.json(request);
  } catch (error: any) {
    if (error.message === "ID inválido") return res.status(400).json({ message: error.message });
    // Carrera con otra apertura simultánea del mismo producto/ubicación: el índice
    // parcial ProductRequest_solicitud_abierta_unica rechaza el update al reabrir una
    // solicitud. Es un conflicto de negocio, no un fallo del servidor.
    if (error?.code === "P2002") {
      return res.status(409).json({ message: "Ya existe una solicitud abierta para este producto en esta ubicación" });
    }
    console.error("Error al actualizar solicitud:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// DELETE /:id — Cancelar solicitud
router.delete("/:id", async (req: AuthRequest, res: Response) => {
  try {
    const id = parseId(req.params.id);
    const existing = await prisma.productRequest.findUnique({ where: { id } });
    if (!existing) return res.status(404).json({ message: "Solicitud no encontrada" });

    if (existing.status === "RECIBIDO_POR_TIENDA" || existing.status === "CANCELADO") {
      return res.status(400).json({ message: "No se puede cancelar una solicitud ya recibida o cancelada" });
    }

    // Solo ADMIN/INVENTARIO o la tienda propietaria pueden cancelar
    const delRole = req.user?.role || "";
    if (delRole !== "ADMIN" && delRole !== "INVENTARIO") {
      if (delRole !== "TIENDA" || existing.locationId !== req.user?.locationId) {
        return res.status(403).json({ message: "No tiene permisos para cancelar esta solicitud" });
      }
    }

    // Cancelación ATÓMICA: igual que en PUT, el update se condiciona al estado leído
    // para que un PUT concurrente (p. ej. la tienda confirma recepción mientras se
    // cancela) no pueda ser sobrescrito ni dejar un previousStatus falso en el historial.
    const resultado = await prisma.$transaction(async (tx) => {
      const actual = await tx.productRequest.findUnique({ where: { id }, select: { status: true } });
      if (!actual) return { conflicto: "AUSENTE" as const };
      if (actual.status === "RECIBIDO_POR_TIENDA" || actual.status === "CANCELADO") {
        return { conflicto: "CERRADA" as const, status: actual.status };
      }
      if (actual.status !== existing.status) return { conflicto: "CAMBIO" as const, status: actual.status };

      const cambios = await tx.productRequest.updateMany({
        where: { id, status: existing.status },
        data: { status: "CANCELADO" },
      });
      if (cambios.count !== 1) return { conflicto: "CAMBIO" as const, status: actual.status };

      await tx.requestHistory.create({
        data: {
          requestId: id,
          previousStatus: existing.status,
          newStatus: "CANCELADO",
          userId: req.user?.userId || 0,
          userRole: req.user?.role || "ADMIN",
        },
      });
      return { conflicto: "NINGUNO" as const };
    });

    if (resultado.conflicto === "AUSENTE") return res.status(404).json({ message: "Solicitud no encontrada" });
    if (resultado.conflicto === "CERRADA") {
      return res.status(400).json({ message: "No se puede cancelar una solicitud ya recibida o cancelada" });
    }
    if (resultado.conflicto === "CAMBIO") {
      return res.status(409).json({
        message: `La solicitud cambió a "${resultado.status}" mientras se procesaba tu petición. Recargá la lista e intentá de nuevo.`,
      });
    }

    // Notify the requester about cancellation
    if (existing.requestedById) {
      await prisma.notification.create({
        data: {
          userId: existing.requestedById,
          title: `Solicitud #${id} - Cancelada`,
          message: `La solicitud fue cancelada por ${req.user?.role || "Sistema"}.`,
          type: "WARNING",
          linkUrl: "/panel/solicitudes",
        },
      });
    }

    res.json({ message: "Solicitud cancelada" });
  } catch (error: any) {
    if (error.message === "ID inválido") return res.status(400).json({ message: error.message });
    console.error("Error al cancelar solicitud:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
