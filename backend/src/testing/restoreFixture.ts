/** Fixture ficticio de restauración. seed rechaza conexiones que no sean locales. */
import { seed, createProduct } from "./seed";
import { startTestServer, postJson, loginAndGetToken } from "./helpers";
import { randomUUID } from "crypto";

async function main() {
  const ctx = await seed(`restore-${Date.now()}`);
  const server = await startTestServer();
  try {
    const token = await loginAndGetToken(server.baseUrl, ctx.users.admin.email, ctx.users.admin.password);
    const product = await createProduct(ctx, { stockAlmacen: 20, stockTienda: 20 });
    const response = await postJson(server.baseUrl, "/api/sales", { operationId: randomUUID(), locationId: ctx.locationIds.tienda,
      items: [{ productId: product.id, quantity: 2 }], payments: [{ method: "EFECTIVO", amount: 150 }, { method: "CREDITO", amount: 50 }],
      customerData: { name: "Cliente ficticio de restauración" } }, token);
    if (response.status !== 201) throw new Error("Venta fixture rechazada");
    const sale: any = await response.json();
    const ret = await postJson(server.baseUrl, "/api/returns", { operationId: randomUUID(), saleId: sale.id, productId: product.id,
      quantity: 1, amount: 100, method: "EFECTIVO", reason: "Prueba local de restauración" }, token);
    if (ret.status !== 201) throw new Error("Devolución fixture rechazada");
    const move = await postJson(server.baseUrl, "/api/movements", { operationId: randomUUID(), productId: product.id,
      fromLocationId: ctx.locationIds.almacen, toLocationId: ctx.locationIds.tienda, quantity: 2 }, token);
    if (move.status !== 201) throw new Error("Traslado fixture rechazado");
    await ctx.prisma.productRequest.create({ data: { productId: product.id, locationId: ctx.locationIds.tienda,
      quantity: 1, requestedById: ctx.users.tienda.userId, status: "PENDIENTE" } });
    console.log("Fixture ficticio local creado. No contiene datos productivos");
  } finally { await server.close(); await ctx.prisma.$disconnect(); }
}
main().then(() => process.exit(0)).catch(() => { console.error("Falló fixture local de restauración"); process.exit(1); });
