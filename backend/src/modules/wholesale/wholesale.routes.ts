import { Router, Response } from "express";
import { PrismaClient } from "@prisma/client";
import multer from "multer";
import * as XLSX from "xlsx";
import { authenticate } from "../../shared/middlewares/auth";
import { AuthRequest } from "../../shared/types";

const router = Router();
const prisma = new PrismaClient();
const upload = multer({ storage: multer.memoryStorage() });

router.use(authenticate);

// POST — Crear venta mayorista
router.post("/", async (req: AuthRequest, res: Response) => {
  try {
    const { items, payments, customerId, customerData, locationId, clienteName, paraQuien, lugarEntrega, datosFactura, formaPago } = req.body;

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
        const unitPrice = item.unitPrice || item.wholesalePrice || 0;
        const subtotal = item.quantity * unitPrice;
        totalSale += subtotal;
        return {
          productId: item.productId,
          quantity: item.quantity,
          unitPrice,
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
          type: "MAYOR",
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
            const almacen = await tx.location.findFirst({ where: { type: "ALMACEN" } });
            if (almacen) {
              const existing = await tx.productRequest.findFirst({
                where: {
                  productId: update.productId,
                  locationId: userLocationId,
                  status: { in: ["PENDIENTE", "EN_PREPARACION", "ENVIADO"] },
                },
              });
              if (!existing) {
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
    console.error("Error al crear venta mayorista:", error);
    res.status(400).json({ message: error.message || "Error interno del servidor" });
  }
});

// POST /import — Importar productos desde Excel
router.post("/import", upload.single("file"), async (req: AuthRequest, res: Response) => {
  try {
    if (!req.file) {
      return res.status(400).json({ message: "Debe subir un archivo Excel" });
    }

    const workbook = XLSX.read(req.file.buffer, { type: "buffer" });
    const sheetName = workbook.SheetNames[0];
    const sheet = workbook.Sheets[sheetName];
    const rows = XLSX.utils.sheet_to_json(sheet);

    if (rows.length === 0) {
      return res.status(400).json({ message: "El archivo está vacío" });
    }

    const imported: any[] = [];
    const errors: string[] = [];

    for (let i = 0; i < rows.length; i++) {
      const row = rows[i] as any;
      const itemCode = row["Codigo fabrica"] || row["codigo fabrica"] || row["itemCode"] || "";
      const name = row["Descripcion"] || row["descripcion"] || row["Producto"] || row["producto"] || "";
      const brand = row["Marca"] || row["marca"] || "";
      const model = row["Modelo"] || row["modelo"] || "";
      const year = row["Anos"] || row["anos"] || row["Años"] || row["años"] || "";
      const detail = row["Detalle"] || row["detalle"] || "";
      const wholesalePrice = parseFloat(row["Precio mayor"] || row["precio mayor"] || row["wholesalePrice"] || "0");

      if (!itemCode || !name) {
        errors.push(`Fila ${i + 1}: Código y nombre son obligatorios`);
        continue;
      }

      try {
        let product = await prisma.product.findUnique({ where: { itemCode } });

        if (!product) {
          product = await prisma.product.create({
            data: {
              itemCode,
              name,
              brand: brand || "Sin marca",
              model: model || "Sin modelo",
              year: year || "",
              detail,
              manufacturer: "Importado",
              price1: wholesalePrice || 0,
              price2: wholesalePrice || 0,
              wholesalePrice: wholesalePrice || undefined,
            },
          });
        } else if (wholesalePrice > 0) {
          product = await prisma.product.update({
            where: { id: product.id },
            data: { wholesalePrice },
          });
        }

        imported.push({ id: product.id, itemCode: product.itemCode, name: product.name });
      } catch (err: any) {
        errors.push(`Fila ${i + 1}: ${err.message}`);
      }
    }

    res.json({
      imported: imported.length,
      errors: errors.length,
      details: { imported, errors },
    });
  } catch (error: any) {
    console.error("Error al importar Excel:", error);
    res.status(500).json({ message: error.message || "Error al procesar el archivo" });
  }
});

// GET / — Listar ventas mayoristas
router.get("/", async (req: AuthRequest, res: Response) => {
  try {
    const { startDate, endDate, locationId, page = "1", limit = "20" } = req.query;

    const where: any = { type: "MAYOR" };
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
    console.error("Error al listar ventas mayoristas:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
