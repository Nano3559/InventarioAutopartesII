import { Router, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { authenticate } from "../../shared/middlewares/auth";
import { AuthRequest } from "../../shared/types";

const router = Router();
const prisma = new PrismaClient();

router.use(authenticate);

// GET / — Listar ventas con filtros
router.get("/", async (req: AuthRequest, res: Response) => {
  try {
    const { type, locationId, startDate, endDate, page = "1", limit = "20" } = req.query;

    const where: any = {};
    if (type && typeof type === "string") where.type = type;
    if (locationId && typeof locationId === "string") where.locationId = Number(locationId);
    if (startDate || endDate) {
      where.saleDate = {};
      if (startDate && typeof startDate === "string") where.saleDate.gte = new Date(startDate);
      if (endDate && typeof endDate === "string") {
        const end = new Date(endDate);
        end.setHours(23, 59, 59, 999);
        where.saleDate.lte = end;
      }
    }

    const skip = (Number(page) - 1) * Number(limit);
    const take = Number(limit);

    const [sales, total] = await Promise.all([
      prisma.sale.findMany({
        where,
        include: {
          user: { select: { id: true, name: true } },
          location: { select: { id: true, name: true } },
          customer: true,
          items: { include: { product: { select: { id: true, name: true, itemCode: true } } } },
          payments: true,
        },
        orderBy: { saleDate: "desc" },
        skip,
        take,
      }),
      prisma.sale.count({ where }),
    ]);

    res.json({
      sales: sales.map((s) => ({
        ...s,
        total: Number(s.total),
        items: s.items.map((i) => ({ ...i, unitPrice: Number(i.unitPrice), subtotal: Number(i.subtotal) })),
        payments: s.payments.map((p) => ({ ...p, amount: Number(p.amount) })),
      })),
      pagination: { total, page: Number(page), limit: take, pages: Math.ceil(total / take) },
    });
  } catch (error) {
    console.error("Error al listar ventas:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /:id — Detalle de venta
router.get("/:id", async (req: AuthRequest, res: Response) => {
  try {
    const sale = await prisma.sale.findUnique({
      where: { id: Number(req.params.id) },
      include: {
        user: { select: { id: true, name: true } },
        location: { select: { id: true, name: true } },
        customer: true,
        items: { include: { product: true } },
        payments: true,
        returns: true,
      },
    });

    if (!sale) {
      return res.status(404).json({ message: "Venta no encontrada" });
    }

    res.json({
      ...sale,
      total: Number(sale.total),
      items: sale.items.map((i) => ({ ...i, unitPrice: Number(i.unitPrice), subtotal: Number(i.subtotal) })),
      payments: sale.payments.map((p) => ({ ...p, amount: Number(p.amount) })),
      returns: sale.returns.map((r) => ({ ...r, amount: Number(r.amount) })),
    });
  } catch (error) {
    console.error("Error al obtener venta:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// POST — Crear venta con items, pagos y facturación
router.post("/", async (req: AuthRequest, res: Response) => {
  try {
    const { items, payments, customerId, customerData, requiereFactura, locationId } = req.body;

    if (!items || !Array.isArray(items) || items.length === 0) {
      return res.status(400).json({ message: "Debe agregar al menos un producto" });
    }

    if (!payments || !Array.isArray(payments) || payments.length === 0) {
      return res.status(400).json({ message: "Debe registrar al menos un pago" });
    }

    const user = req.user!;
    let userLocationId = user.locationId || locationId ? Number(locationId) : null;

    if (!userLocationId) {
      const tienda = await prisma.location.findFirst({ where: { type: "TIENDA" } });
      userLocationId = tienda?.id || 5;
    }

    const validMethods = ["EFECTIVO", "QR", "TRANSFERENCIA", "CREDITO"];
    for (const p of payments) {
      if (!validMethods.includes(p.method)) {
        return res.status(400).json({ message: `Método de pago inválido: ${p.method}` });
      }
    }

    let finalCustomerId = customerId || null;

    if (customerData && !finalCustomerId) {
      const { name, nit, phone } = customerData;
      if (name) {
        let customer;
        if (nit) {
          customer = await prisma.customer.findFirst({ where: { nit } });
        }
        if (!customer) {
          customer = await prisma.customer.create({
            data: { name, nit: nit || null, phone: phone || null },
          });
        }
        finalCustomerId = customer.id;
      }
    }

    const result = await prisma.$transaction(async (tx) => {
      const stockUpdates: { productId: number; quantity: number }[] = [];

      for (const item of items) {
        const product = await tx.product.findUnique({ where: { id: item.productId } });
        if (!product) {
          throw new Error(`Producto con ID ${item.productId} no encontrado`);
        }

        const inventory = await tx.inventory.findUnique({
          where: { productId_locationId: { productId: item.productId, locationId: userLocationId } },
        });

        const currentStock = inventory?.stock || 0;
        if (currentStock < item.quantity) {
          throw new Error(`Stock insuficiente para "${product.name}". Disponible: ${currentStock}, solicitado: ${item.quantity}`);
        }

        stockUpdates.push({ productId: item.productId, quantity: item.quantity });
      }

      let totalSale = 0;
      const saleItemsData = items.map((item: any) => {
        const subtotal = item.quantity * item.unitPrice;
        totalSale += subtotal;
        return {
          productId: item.productId,
          quantity: item.quantity,
          unitPrice: item.unitPrice,
          subtotal,
        };
      });

      const totalPaid = payments.reduce((sum: number, p: any) => sum + Number(p.amount), 0);
      if (Math.abs(totalPaid - totalSale) > 0.01) {
        throw new Error(`El total pagado (Bs. ${totalPaid}) no coincide con el total de la venta (Bs. ${totalSale})`);
      }

      const sale = await tx.sale.create({
        data: {
          total: totalSale,
          type: "NORMAL",
          userId: user.userId,
          locationId: userLocationId,
          customerId: finalCustomerId,
          items: { create: saleItemsData },
          payments: {
            create: payments.map((p: any) => ({
              method: p.method,
              amount: Number(p.amount),
            })),
          },
        },
        include: { items: true, payments: true },
      });

      for (const update of stockUpdates) {
        const inv = await tx.inventory.findUnique({
          where: { productId_locationId: { productId: update.productId, locationId: userLocationId } },
        });

        if (inv) {
          const newStock = inv.stock - update.quantity;
          await tx.inventory.update({
            where: { id: inv.id },
            data: { stock: newStock },
          });

          if (newStock === 0) {
            const almacenId = userLocationId <= 4 ? null : 1;
            if (almacenId) {
              await tx.productRequest.create({
                data: {
                  productId: update.productId,
                  quantity: Math.max(update.quantity, 5),
                  requestedById: user.userId,
                  locationId: userLocationId,
                  status: "PENDIENTE",
                },
              });
            }
          }
        }
      }

      return {
        ...sale,
        total: Number(sale.total),
        items: sale.items.map((i) => ({ ...i, unitPrice: Number(i.unitPrice), subtotal: Number(i.subtotal) })),
        payments: sale.payments.map((p) => ({ ...p, amount: Number(p.amount) })),
      };
    });

    res.status(201).json(result);
  } catch (error: any) {
    console.error("Error al crear venta:", error);
    res.status(400).json({ message: error.message || "Error interno del servidor" });
  }
});

export default router;
