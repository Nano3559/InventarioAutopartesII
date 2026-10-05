import { PrismaClient } from "@prisma/client";
import bcrypt from "bcryptjs";
import { resolveTestEnv } from "./helpers";

/**
 * Siembra datos de prueba aislados por namespace (ns): cada archivo *.itest.ts
 * usa su propio ns para no interferir con los demás (los archivos corren en
 * procesos separados). Los roles (ADMIN/TIENDA/INVENTARIO) son compartidos y
 * solo se leen, por lo que nunca se eliminan.
 */

const ROLE_PERMISSIONS: Record<string, string[]> = {
  ADMIN: ["*"],
  TIENDA: ["ventas", "inventario", "solicitudes", "devoluciones"],
  INVENTARIO: ["movimientos", "inventario", "solicitudes"],
};

const PASSWORD = "TestPassword123!";
const EMAIL_DOMAIN = "@itest.local";

export interface TestUser {
  email: string;
  password: string;
  userId: number;
  locationId: number | null;
}

export interface SeedContext {
  ns: string;
  prisma: PrismaClient;
  roleIds: { admin: number; tienda: number; inventario: number };
  locationIds: { almacen: number; tienda: number };
  users: { admin: TestUser; tienda: TestUser; inventario: TestUser };
}

export async function seed(ns: string): Promise<SeedContext> {
  // Idempotente: garantiza el entorno de test aunque algún futuro archivo importe
  // a seed.ts antes que helpers.ts.
  await resolveTestEnv();
  const prisma = new PrismaClient();

  const roleIds = {} as SeedContext["roleIds"];
  for (const name of Object.keys(ROLE_PERMISSIONS)) {
    const role = await prisma.roleModel.upsert({
      where: { name },
      update: { permissions: ROLE_PERMISSIONS[name] },
      create: { name, permissions: ROLE_PERMISSIONS[name] },
    });
    roleIds[name.toLowerCase() as keyof SeedContext["roleIds"]] = role.id;
  }

  const locationByName = async (name: string, type: "ALMACEN" | "TIENDA") => {
    const existing = await prisma.location.findFirst({ where: { name } });
    if (existing) return existing;
    return prisma.location.create({ data: { name, type, address: "Zona Test" } });
  };
  const almacen = await locationByName(`ALMACEN-${ns}`, "ALMACEN");
  const tienda = await locationByName(`TIENDA-${ns}`, "TIENDA");

  const hash = await bcrypt.hash(PASSWORD, 10);

  const admin = await prisma.user.upsert({
    where: { email: `admin.${ns}${EMAIL_DOMAIN}` },
    update: { password: hash, roleId: roleIds.admin },
    create: {
      name: `Admin ${ns}`,
      email: `admin.${ns}${EMAIL_DOMAIN}`,
      password: hash,
      roleId: roleIds.admin,
      locationId: null,
    },
  });
  const tiendaUser = await prisma.user.upsert({
    where: { email: `tienda.${ns}${EMAIL_DOMAIN}` },
    update: { password: hash, roleId: roleIds.tienda, locationId: tienda.id },
    create: {
      name: `Vendedor ${ns}`,
      email: `tienda.${ns}${EMAIL_DOMAIN}`,
      password: hash,
      roleId: roleIds.tienda,
      locationId: tienda.id,
    },
  });
  const inventario = await prisma.user.upsert({
    where: { email: `inventario.${ns}${EMAIL_DOMAIN}` },
    update: { password: hash, roleId: roleIds.inventario },
    create: {
      name: `Inventario ${ns}`,
      email: `inventario.${ns}${EMAIL_DOMAIN}`,
      password: hash,
      roleId: roleIds.inventario,
      locationId: null,
    },
  });

  return {
    ns,
    prisma,
    roleIds,
    locationIds: { almacen: almacen.id, tienda: tienda.id },
    users: {
      admin: { email: admin.email, password: PASSWORD, userId: admin.id, locationId: null },
      tienda: { email: tiendaUser.email, password: PASSWORD, userId: tiendaUser.id, locationId: tienda.id },
      inventario: { email: inventario.email, password: PASSWORD, userId: inventario.id, locationId: null },
    },
  };
}

let productCounter = 0;

export interface TestProduct {
  id: number;
  itemCode: string;
  name: string;
  unitPrice: number;
}

export interface ProductSeedOptions {
  unitPrice?: number;
  /** Precio mayorista. Por defecto 80% de unitPrice. null = sin precio mayorista (usa price1). */
  wholesalePrice?: number | null;
  /** Precio mayorista explicito (price1). Por defecto igual a unitPrice. */
  price1?: number;
  /** Precio minorista explicito (price2). Por defecto igual a unitPrice. */
  price2?: number;
  stockAlmacen?: number;
  stockTienda?: number;
}

export async function createProduct(ctx: SeedContext, opts: ProductSeedOptions = {}): Promise<TestProduct> {
  productCounter += 1;
  const unitPrice = opts.unitPrice ?? 100;
  const wholesalePrice = "wholesalePrice" in opts ? opts.wholesalePrice : Math.round(unitPrice * 0.8 * 100) / 100;
  const price1 = opts.price1 ?? unitPrice;
  const price2 = opts.price2 ?? unitPrice;
  const itemCode = `${ctx.ns.toUpperCase()}-ITEST-${productCounter}-${Date.now()}`;
  const product = await ctx.prisma.product.create({
    data: {
      itemCode,
      manufacturer: `TEST-${ctx.ns}`,
      name: `Producto de prueba ${ctx.ns} #${productCounter}`,
      brand: "TEST",
      model: "TEST",
      year: "2020",
      detail: "Producto para pruebas automatizadas",
      price1,
      price2,
      wholesalePrice: wholesalePrice as number | null,
      cost: 50,
    },
  });

  const inventories: { productId: number; locationId: number; stock: number; minStock: number }[] = [];
  if (opts.stockAlmacen !== undefined) {
    inventories.push({ productId: product.id, locationId: ctx.locationIds.almacen, stock: opts.stockAlmacen, minStock: 1 });
  }
  if (opts.stockTienda !== undefined) {
    inventories.push({ productId: product.id, locationId: ctx.locationIds.tienda, stock: opts.stockTienda, minStock: 1 });
  }
  if (inventories.length > 0) {
    await ctx.prisma.inventory.createMany({ data: inventories });
  }

  return { id: product.id, itemCode, name: product.name, unitPrice };
}

/** Proveedor de prueba. Necesario para registrar costos (Cost.supplierId es FK obligatoria). */
export async function createSupplier(ctx: SeedContext, name = `Proveedor ${ctx.ns}`): Promise<number> {
  const supplier = await ctx.prisma.supplier.create({
    data: { name, phone: "70000000" },
  });
  return supplier.id;
}

export async function cleanup(ctx: SeedContext): Promise<void> {
  // finally para que un fallo intermedio no deje el pool de conexiones abierto
  // (los archivos de prueba se ejecutan en el mismo proceso y las conexiones
  // filtradas hacen fallar las suites siguientes).
  try {
    await cleanupNamespace(ctx);
  } finally {
    await ctx.prisma.$disconnect();
  }
}

async function cleanupNamespace(ctx: SeedContext): Promise<void> {
  const { prisma, ns } = ctx;
  const emails = [`admin.${ns}${EMAIL_DOMAIN}`, `tienda.${ns}${EMAIL_DOMAIN}`, `inventario.${ns}${EMAIL_DOMAIN}`];
  const productIds = (await prisma.product.findMany({ where: { manufacturer: `TEST-${ns}` }, select: { id: true } })).map(
    (p) => p.id
  );
  const userIds = (await prisma.user.findMany({ where: { email: { in: emails } }, select: { id: true } })).map((u) => u.id);
  const saleIds = (await prisma.sale.findMany({ where: { userId: { in: userIds } }, select: { id: true } })).map(
    (s) => s.id
  );

  await prisma.return.deleteMany({
    where: { OR: [{ saleId: { in: saleIds } }, { productId: { in: productIds } }] },
  });
  // Las notificaciones del namespace (p. ej. la aviso a INVENTARIO al crear una
  // solicitud) referencian a los usuarios de prueba: sin borrarlas, el
  // deleteMany de User viola la FK.
  await prisma.notification.deleteMany({ where: { userId: { in: userIds } } });
  await prisma.movement.deleteMany({
    where: { OR: [{ userId: { in: userIds } }, { productId: { in: productIds } }] },
  });
  // RequestHistory referencia a ProductRequest: hay que borrar el historial
  // antes que las solicitudes o el deleteMany viola la FK.
  const requestIds = (
    await prisma.productRequest.findMany({
      where: { OR: [{ requestedById: { in: userIds } }, { productId: { in: productIds } }] },
      select: { id: true },
    })
  ).map((r) => r.id);
  if (requestIds.length > 0) {
    await prisma.requestHistory.deleteMany({ where: { requestId: { in: requestIds } } });
  }
  // RequestHistory.userId también referencia a User: puede apuntar a un usuario de
  // prueba desde una solicitud creada por otro actor, así que se barre por usuario.
  await prisma.requestHistory.deleteMany({ where: { userId: { in: userIds } } });
  await prisma.productRequest.deleteMany({
    where: { OR: [{ requestedById: { in: userIds } }, { productId: { in: productIds } }] },
  });
  await prisma.saleItem.deleteMany({ where: { saleId: { in: saleIds } } });
  await prisma.payment.deleteMany({ where: { saleId: { in: saleIds } } });
  await prisma.sale.deleteMany({ where: { id: { in: saleIds } } });
  // Cost referencia a Product: sin barrerlo, el deleteMany de Product viola la FK.
  await prisma.cost.deleteMany({ where: { productId: { in: productIds } } });
  await prisma.inventory.deleteMany({ where: { productId: { in: productIds } } });
  await prisma.product.deleteMany({ where: { id: { in: productIds } } });
  await prisma.customer.deleteMany({ where: { name: { contains: `Cliente ${ns}` } } });
  await prisma.supplier.deleteMany({ where: { name: { contains: `Proveedor ${ns}` } } });
  // El aviso a INVENTARIO notifica a TODOS los usuarios con ese rol, así que otro
  // archivo de pruebas puede insertar una notificación dirigida a estos mismos
  // usuarios mientras corre este cleanup. Por eso el borrado final reintenta
  // re-limpiando notificaciones: el deleteMany de User es idempotente y no se
  // depende del orden de ejecución entre archivos.
  for (let intento = 1; intento <= 5; intento++) {
    await prisma.notification.deleteMany({ where: { userId: { in: userIds } } });
    // AuditLog.userId es FK obligatoria a User (aunque la relación sea opcional):
    // cualquier auditoría de una acción sobre datos de prueba bloquea el borrado
    // del usuario. Se barre en cada intento por la misma razón que las
    // notificaciones: otro archivo puede insertar filas mientras corre el cleanup.
    await prisma.auditLog.deleteMany({ where: { userId: { in: userIds } } });
    try {
      await prisma.user.deleteMany({ where: { email: { in: emails } } });
      break;
    } catch (err: any) {
      const esConflictoDeLlaveForanea = err?.code === "P2003";
      if (!esConflictoDeLlaveForanea || intento === 5) throw err;
      await new Promise((resolve) => setTimeout(resolve, 150 * intento));
    }
  }
  // Barrido por ubicación del namespace: elimina CUALQUIER Inventory residual que
  // bloquee la eliminación de las ubicaciones (FK), incluido el que R6.16 (ventas)
  // crea transitoriamente en todos los ALMACEN para desacoplar del findFirst global
  // de reposición. Esas filas son transitorias (las borra el propio cleanup de ventas
  // de forma idempotente al barrer por productId) y nunca se re-leen, así que borrarlas
  // aquí es seguro e independiente del orden de ejecución entre archivos.
  await prisma.inventory.deleteMany({
    where: { locationId: { in: [ctx.locationIds.almacen, ctx.locationIds.tienda] } },
  });
  // El prefijo cubre también almacenes auxiliares del namespace (p. ej. ALMACEN-<ns>-2).
  await prisma.location.deleteMany({
    where: { OR: [{ name: { startsWith: `ALMACEN-${ns}` } }, { name: { startsWith: `TIENDA-${ns}` } }] },
  });
}