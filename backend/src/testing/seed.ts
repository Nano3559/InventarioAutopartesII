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
  resolveTestEnv();
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
  unitPrice: number;
}

export interface ProductSeedOptions {
  unitPrice?: number;
  stockAlmacen?: number;
  stockTienda?: number;
}

export async function createProduct(ctx: SeedContext, opts: ProductSeedOptions = {}): Promise<TestProduct> {
  productCounter += 1;
  const unitPrice = opts.unitPrice ?? 100;
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
      price1: unitPrice,
      price2: unitPrice,
      wholesalePrice: Math.round(unitPrice * 0.8 * 100) / 100,
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

  return { id: product.id, itemCode, unitPrice };
}

export async function cleanup(ctx: SeedContext): Promise<void> {
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
  await prisma.movement.deleteMany({
    where: { OR: [{ userId: { in: userIds } }, { productId: { in: productIds } }] },
  });
  await prisma.productRequest.deleteMany({
    where: { OR: [{ requestedById: { in: userIds } }, { productId: { in: productIds } }] },
  });
  await prisma.saleItem.deleteMany({ where: { saleId: { in: saleIds } } });
  await prisma.payment.deleteMany({ where: { saleId: { in: saleIds } } });
  await prisma.sale.deleteMany({ where: { id: { in: saleIds } } });
  await prisma.inventory.deleteMany({ where: { productId: { in: productIds } } });
  await prisma.product.deleteMany({ where: { id: { in: productIds } } });
  await prisma.customer.deleteMany({ where: { name: { contains: `Cliente ${ns}` } } });
  await prisma.user.deleteMany({ where: { email: { in: emails } } });
  // Barrido por ubicación del namespace: elimina CUALQUIER Inventory residual que
  // bloquee la eliminación de las ubicaciones (FK), incluido el que R6.16 (ventas)
  // crea transitoriamente en todos los ALMACEN para desacoplar del findFirst global
  // de reposición. Esas filas son transitorias (las borra el propio cleanup de ventas
  // de forma idempotente al barrer por productId) y nunca se re-leen, así que borrarlas
  // aquí es seguro e independiente del orden de ejecución entre archivos.
  await prisma.inventory.deleteMany({
    where: { locationId: { in: [ctx.locationIds.almacen, ctx.locationIds.tienda] } },
  });
  await prisma.location.deleteMany({ where: { name: { in: [`ALMACEN-${ns}`, `TIENDA-${ns}`] } } });
  await prisma.$disconnect();
}