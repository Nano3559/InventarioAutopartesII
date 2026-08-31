import { PrismaClient } from "@prisma/client";
import { productSeed, suppliersSeed, customersSeed, importersSeed } from "./seed-data";

const prisma = new PrismaClient();

// Multiplicador determinístico por ítem para que los ids no dependan del orden de inserción
const hash = (s: string) => {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return h;
};

async function main() {
  console.log("=== ENRIQUECIMIENTO DE DATOS DE PRODUCCIÓN (idempotente) ===");

  const cats = await prisma.category.findMany();
  const catNames = cats.map((c) => c.name);

  // 1. PRODUCTOS — crear los que falten (upsert por itemCode)
  console.log("\n1. Productos:");
  let createdProducts = 0;
  const allProducts: any[] = [];
  const existing = await prisma.product.findMany({ include: { category: true } });
  const existingByCode = new Map(existing.map((p) => [p.itemCode, p]));
  for (const p of productSeed) {
    const cat = cats.find((c) => c.name === p.cat);
    if (!existingByCode.has(p.itemCode)) {
      const prod = await prisma.product.create({
        data: {
          itemCode: p.itemCode,
          manufacturer: p.manufacturer,
          name: p.name,
          brand: p.brand,
          model: p.model,
          year: p.year,
          detail: p.detail,
          oemCode: p.oemCode,
          factoryCode: p.factoryCode,
          image: null,
          price1: p.price1,
          price2: p.price2,
          wholesalePrice: p.wholesalePrice,
          cost: p.cost,
          categoryId: cat?.id ?? null,
        },
      });
      allProducts.push(prod);
      createdProducts++;
    } else {
      allProducts.push(existingByCode.get(p.itemCode)!);
    }
  }
  console.log(`  - Existentes: ${existing.length}, creados nuevos: ${createdProducts}, total: ${allProducts.length}`);

  // 2. INVENTARIO — para los productos nuevos, stock en todas las ubicaciones
  const locs = await prisma.location.findMany();
  if (createdProducts > 0) {
    const newProducts = allProducts.filter((p) => !existingByCode.has(p.itemCode));
    const invData: any[] = [];
    for (const product of newProducts) {
      const baseStock = product.name.includes("Filtro") ? 200 : product.name.includes("Bujía") ? 100 : product.name.includes("Pastilla") ? 60 : 20;
      const seed = hash(product.itemCode);
      for (let i = 0; i < locs.length; i++) {
        const factor = [1, 0.3, 0.2, 0.15, 0.1, 0.05, 0.03][i];
        const stock = Math.floor(baseStock * factor) + (seed % 10);
        invData.push({ productId: product.id, locationId: locs[i].id, stock, minStock: Math.max(1, Math.floor(stock * 0.15)) });
      }
    }
    await prisma.inventory.createMany({ data: invData, skipDuplicates: true });
  }
  console.log(`  - Inventario actualizado (${(await prisma.inventory.count())} registros)`);

  // 3. COSTOS — 1-2 por producto usando proveedores existentes
  console.log("\n2. Costos:");
  const suppliers = await prisma.supplier.findMany();
  const suppliersByName = new Map(suppliers.map((s) => [s.name, s]));
  for (const sp of suppliersSeed) {
    if (!suppliersByName.has(sp.name)) {
      const ns = await prisma.supplier.create({ data: sp });
      suppliersByName.set(sp.name, ns);
    }
  }
  const activeSuppliers = [...suppliersByName.values()];
  let costCount = 0;
  const costsByProduct = await prisma.cost.groupBy({ by: ["productId"], _count: { id: true } });
  const costCountByProduct = new Map(costsByProduct.map((c) => [c.productId, c._count.id]));
  for (const product of allProducts) {
    const existingCosts = costCountByProduct.get(product.id) || 0;
    const needed = Math.max(0, 2 - existingCosts);
    for (let c = 0; c < needed; c++) {
      const supplier = activeSuppliers[hash(product.itemCode + c) % activeSuppliers.length];
      await prisma.cost.create({
        data: {
          productId: product.id,
          supplierId: supplier.id,
          exchangeRate: 6.9,
          costPrice: Number((Number(product.cost || product.price1) * (0.7 + 0.05 * c)).toFixed(2)),
          percentage: c === 0 ? 8 : 12,
          date: new Date(),
        },
      });
      costCount++;
    }
  }
  console.log(`  - Costos creados nuevos: ${costCount} (total: ${await prisma.cost.count()})`);

  // 4. IMPORTADORES + ProductImporter
  console.log("\n3. Importadores:");
  let importerCount = 0;
  const importers = await prisma.importer.findMany();
  const importersByName = new Map(importers.map((i) => [i.name, i]));
  for (const imp of importersSeed) {
    if (!importersByName.has(imp.name)) {
      const ni = await prisma.importer.create({ data: imp });
      importersByName.set(imp.name, ni);
      importerCount++;
    }
  }
  const activeImporters = [...importersByName.values()];
  const existingLinks = await prisma.productImporter.findMany({ select: { productId: true, importerId: true } });
  const linkSet = new Set(existingLinks.map((l) => `${l.productId}-${l.importerId}`));
  let linkCount = 0;
  for (const product of allProducts) {
    const numImporters = 1 + (hash(product.itemCode) % 2); // 1-2 por producto
    for (let i = 0; i < numImporters; i++) {
      const imp = activeImporters[(hash(product.itemCode) + i * 3) % activeImporters.length];
      const key = `${product.id}-${imp.id}`;
      if (!linkSet.has(key)) {
        await prisma.productImporter.create({ data: { productId: product.id, importerId: imp.id } });
        linkSet.add(key);
        linkCount++;
      }
    }
  }
  console.log(`  - Importadores: ${importerCount} nuevos (total: ${activeImporters.length}), relaciones nuevas: ${linkCount}`);

  // 5. DEVOLUCIONES — asegurar al menos 10
  console.log("\n4. Devoluciones:");
  const returnCount = await prisma.return.count();
  if (returnCount < 10) {
    const sales = await prisma.sale.findMany({
      where: { NOT: { items: { none: {} } } },
      include: { items: { take: 5 } },
      orderBy: { saleDate: "desc" },
      take: 60,
    });
    const methods = ["EFECTIVO", "QR", "TRANSFERENCIA"] as const;
    let created = 0;
    for (const sale of sales) {
      const has = await prisma.return.findFirst({ where: { saleId: sale.id } });
      if (has) continue;
      const item = sale.items[hash(String(sale.id)) % sale.items.length];
      const qty = Math.min(item.quantity, 1 + (hash(String(sale.id)) % 2));
      const amount = qty * Number(item.unitPrice);
      const date = new Date(sale.saleDate);
      date.setDate(date.getDate() + 1 + (hash(String(sale.id)) % 5));
      await prisma.return.create({
        data: {
          saleId: sale.id,
          productId: item.productId,
          reason: ["Producto defectuoso", "No era el correcto", "Cliente se arrepintió", "Daño en transporte", "Garantía"][hash(String(sale.id)) % 5],
          quantity: qty,
          amount: Number(amount.toFixed(2)),
          method: methods[hash(String(sale.id)) % methods.length],
          date,
        },
      });
      created++;
      if (returnCount + created >= 12) break;
    }
    console.log(`  - Devoluciones creadas: ${created} (total: ${await prisma.return.count()})`);
  } else {
    console.log(`  - Ya hay ${returnCount} devoluciones, no se agregan.`);
  }

  // 6. VENTAS — distribuir en varios meses (mayo, junio, julio 2026) si faltan
  console.log("\n5. Ventas distribuidas:");
  const existingSalesMonths = await prisma.$queryRawUnsafe(
    `SELECT DISTINCT to_char("saleDate",'YYYY-MM') as mes FROM "Sale" ORDER BY mes`
  ) as any[];
  const presentMonths = new Set(existingSalesMonths.map((m) => m.mes));
  console.log(`  - Meses con ventas actuales: ${existingSalesMonths.map((m) => m.mes).join(", ")}`);

  const users = await prisma.user.findMany({ where: { role: { name: "TIENDA" } } });
  const tiendaUsers = await prisma.user.findMany({ where: { role: { name: "TIENDA" } } });
  const customers = await prisma.customer.findMany();
  const tiendaLocs = (await prisma.location.findMany({ where: { type: "TIENDA" } }));
  const methods: Array<"EFECTIVO" | "QR" | "TRANSFERENCIA" | "CREDITO"> = ["EFECTIVO", "QR", "TRANSFERENCIA", "CREDITO"];

  const targetMonths = ["2026-05", "2026-04", "2026-06", "2026-03", "2026-09"];
  for (const month of targetMonths) {
    if (presentMonths.has(month)) {
      console.log(`  - ${month}: ya tiene ventas (omitido)`);
      continue;
    }
    const [yy, mm] = month.split("-").map(Number);
    const numSales = 8 + (hash(month) % 8); // 8-15 ventas
    for (let s = 0; s < numSales; s++) {
      const user = tiendaUsers[hash(month + "-" + s) % tiendaUsers.length];
      const loc = tiendaLocs[hash(month + "-l" + s) % tiendaLocs.length];
      const customer = customers[hash(month + "-c" + s) % customers.length];
      const numItems = 1 + (hash(month + "-i" + s) % 3);
      const itemsData: any[] = [];
      let total = 0;
      for (let it = 0; it < numItems; it++) {
        const prod = allProducts[hash(month + "-p" + s + "-" + it) % allProducts.length];
        const qty = 1 + (hash(month + "-q" + s + "-" + it) % 4);
        const price = Number(prod.price1);
        const sub = qty * price;
        total += sub;
        itemsData.push({ productId: prod.id, quantity: qty, unitPrice: price, subtotal: sub });
      }
      const saleDate = new Date(Date.UTC(yy, mm - 1, 1 + (hash(month + "-d" + s) % 28), 8 + (hash(month + "-h" + s) % 10), hash(month + "-m" + s) % 60));
      const sellerUser = user!;
      await prisma.sale.create({
        data: {
          saleDate,
          total,
          type: "NORMAL",
          userId: sellerUser.id,
          locationId: loc.id,
          customerId: customer.id,
          items: { create: itemsData },
          payments: { create: { method: methods[hash(month + "-pay" + s) % 4], amount: total, date: saleDate } },
        },
      });
    }
    console.log(`  - ${month}: ${numSales} ventas creadas`);
  }

  console.log("\n=== ENRIQUECIMIENTO COMPLETADO ===");
  const final = {
    products: await prisma.product.count(),
    costs: await prisma.cost.count(),
    importers: await prisma.importer.count(),
    productImporters: await prisma.productImporter.count(),
    returns: await prisma.return.count(),
    sales: await prisma.sale.count(),
    suppliers: await prisma.supplier.count(),
    customers: await prisma.customer.count(),
    inventories: await prisma.inventory.count(),
  };
  console.log(JSON.stringify(final, null, 2));
}

main()
  .catch((e) => {
    console.error("Error al enriquecer datos:", e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });