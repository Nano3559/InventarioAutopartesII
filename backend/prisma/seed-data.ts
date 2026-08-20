import { PrismaClient } from "@prisma/client";

export async function seedData(prisma: PrismaClient) {
  console.log("=== Sembrando datos completos para dashboard ===");

  const admin = await prisma.user.findUnique({ where: { email: "admin@inventario.com" } });
  const tienda1 = await prisma.user.findUnique({ where: { email: "tienda1@inventario.com" } });
  const tienda2 = await prisma.user.findUnique({ where: { email: "tienda2@inventario.com" } });
  const tienda3 = await prisma.user.findUnique({ where: { email: "tienda3@inventario.com" } });

  if (!admin || !tienda1 || !tienda2 || !tienda3) {
    console.error("Faltan usuarios. Ejecuta el seed principal primero.");
    return;
  }

  const locs = await prisma.location.findMany();
  const alm1 = locs.find(l => l.name === "Almacén 1")!;
  const alm2 = locs.find(l => l.name === "Almacén 2")!;
  const alm3 = locs.find(l => l.name === "Almacén 3")!;
  const alm4 = locs.find(l => l.name === "Almacén 4")!;
  const ti1 = locs.find(l => l.name === "Tienda 1")!;
  const ti2 = locs.find(l => l.name === "Tienda 2")!;
  const ti3 = locs.find(l => l.name === "Tienda 3")!;

  const cats = await prisma.category.findMany();

  const products = [
    { itemCode: "FRN-001", manufacturer: "Brembo", name: "Pastillas de Freno Delanteras", brand: "Toyota", model: "Hilux", year: "2020-2024", detail: "Cerámica alta resistencia", oemCode: "04465-0C010", factoryCode: "BRM-HLX20", price1: 280, price2: 250, wholesalePrice: 200, cost: 140, categoryId: cats.find(c => c.name === "Frenos")?.id },
    { itemCode: "FRN-002", manufacturer: "TRW", name: "Disco de Freno Delantero", brand: "Toyota", model: "Hilux", year: "2020-2024", detail: "Ventilado 320mm", oemCode: "43512-0K030", factoryCode: "TRW-DHL32", price1: 350, price2: 320, wholesalePrice: 260, cost: 180, categoryId: cats.find(c => c.name === "Frenos")?.id },
    { itemCode: "FRN-003", manufacturer: "Akebono", name: "Pastillas de Freno Traseras", brand: "Nissan", model: "Frontier", year: "2021-2024", detail: "Semimetálica", oemCode: "4M580-4GA0B", factoryCode: "AKB-NFT21", price1: 220, price2: 195, wholesalePrice: 160, cost: 110, categoryId: cats.find(c => c.name === "Frenos")?.id },
    { itemCode: "MTR-001", manufacturer: "Denso", name: "Bujía de Encendido", brand: "Toyota", model: "Corolla", year: "2020-2024", detail: "Iridium FK20HR11", oemCode: "90919-01275", factoryCode: "DNS-FK20", price1: 65, price2: 55, wholesalePrice: 40, cost: 22, categoryId: cats.find(c => c.name === "Motor")?.id },
    { itemCode: "MTR-002", manufacturer: "NGK", name: "Bujía de Encendido", brand: "Mazda", model: "CX-5", year: "2021-2024", detail: "Laser Iridium", oemCode: "PYRA-11EG", factoryCode: "NGK-PYRA", price1: 72, price2: 60, wholesalePrice: 45, cost: 25, categoryId: cats.find(c => c.name === "Motor")?.id },
    { itemCode: "MTR-003", manufacturer: "Bosch", name: "Bobina de Encendido", brand: "Nissan", model: "Sentra", year: "2020-2024", detail: "Bobina pack 4 unidades", oemCode: "22433-3TA0A", factoryCode: "BSH-BN4S", price1: 420, price2: 380, wholesalePrice: 300, cost: 200, categoryId: cats.find(c => c.name === "Motor")?.id },
    { itemCode: "SUS-001", manufacturer: "Monroe", name: "Amortiguador Delantero", brand: "Toyota", model: "Prado", year: "2018-2024", detail: "Gas-Matic premium", oemCode: "48520-60461", factoryCode: "MON-DPR18", price1: 480, price2: 440, wholesalePrice: 350, cost: 220, categoryId: cats.find(c => c.name === "Suspensión")?.id },
    { itemCode: "SUS-002", manufacturer: "KYB", name: "Amortiguador Trasero", brand: "Mazda", model: "CX-5", year: "2020-2024", detail: "Excel-G", oemCode: "KV114-AD01A", factoryCode: "KYB-CX5T", price1: 320, price2: 290, wholesalePrice: 230, cost: 150, categoryId: cats.find(c => c.name === "Suspensión")?.id },
    { itemCode: "SUS-003", manufacturer: "Sachs", name: "Brazo de Suspensión Inferior", brand: "Toyota", model: "Corolla", year: "2020-2024", detail: "Con rótula", oemCode: "48068-02130", factoryCode: "SAC-BCR20", price1: 290, price2: 260, wholesalePrice: 200, cost: 130, categoryId: cats.find(c => c.name === "Suspensión")?.id },
    { itemCode: "FLT-001", manufacturer: "Mann", name: "Filtro de Aceite", brand: "Toyota", model: "Hilux", year: "2016-2024", detail: "W 811/80", oemCode: "04152-YZZA1", factoryCode: "MAN-W811", price1: 45, price2: 38, wholesalePrice: 28, cost: 15, categoryId: cats.find(c => c.name === "Filtros")?.id },
    { itemCode: "FLT-002", manufacturer: "Bosch", name: "Filtro de Aire", brand: "Nissan", model: "Frontier", year: "2021-2024", detail: "Panel filtrante", oemCode: "21010-4KA0A", factoryCode: "BSH-FA-NF", price1: 85, price2: 72, wholesalePrice: 55, cost: 30, categoryId: cats.find(c => c.name === "Filtros")?.id },
    { itemCode: "FLT-003", manufacturer: "Mahle", name: "Filtro de Combustible", brand: "Mazda", model: "CX-5", year: "2020-2024", detail: "Elemento carbón activado", oemCode: "PE01-13-270", factoryCode: "MAH-FCX5", price1: 95, price2: 82, wholesalePrice: 65, cost: 35, categoryId: cats.find(c => c.name === "Filtros")?.id },
    { itemCode: "ELC-001", manufacturer: "Valeo", name: "Alternador", brand: "Toyota", model: "Hilux", year: "2016-2024", detail: "14V 130A", oemCode: "27060-0C060", factoryCode: "VAL-AHL130", price1: 850, price2: 780, wholesalePrice: 650, cost: 400, categoryId: cats.find(c => c.name === "Eléctrico")?.id },
    { itemCode: "ELC-002", manufacturer: "Mitsubishi", name: "Marcha de Arranque", brand: "Nissan", model: "Sentra", year: "2020-2024", detail: "12V 1.0kW", oemCode: "23300-4MA0B", factoryCode: "MIT-MSN20", price1: 680, price2: 620, wholesalePrice: 500, cost: 320, categoryId: cats.find(c => c.name === "Eléctrico")?.id },
    { itemCode: "ELC-003", manufacturer: "Hella", name: "Foco Halógeno H7", brand: "Mazda", model: "CX-5", year: "2020-2024", detail: "Ultra Blue 55W par", oemCode: "9-999-033-550", factoryCode: "HEL-H7CX", price1: 120, price2: 105, wholesalePrice: 80, cost: 45, categoryId: cats.find(c => c.name === "Eléctrico")?.id },
    { itemCode: "CAR-001", manufacturer: "Steelcraft", name: "Parachoque Delantero", brand: "Toyota", model: "Hilux", year: "2020-2024", detail: "Completo con parrilla", oemCode: "52111-0C030", factoryCode: "STL-PH20", price1: 950, price2: 880, wholesalePrice: 700, cost: 450, categoryId: cats.find(c => c.name === "Carrocería")?.id },
    { itemCode: "CAR-002", manufacturer: "TYC", name: "Retrovisor Lateral Izquierdo", brand: "Nissan", model: "Frontier", year: "2021-2024", detail: "Con luz LED integrada", oemCode: "87810-4KA5A", factoryCode: "TYC-RFL-NF", price1: 380, price2: 340, wholesalePrice: 270, cost: 170, categoryId: cats.find(c => c.name === "Carrocería")?.id },
    { itemCode: "TRN-001", manufacturer: "Aisin", name: "Kit de Embrague", brand: "Toyota", model: "Corolla", year: "2020-2024", detail: "Disco + presión + rodamiento", oemCode: "31250-02280", factoryCode: "AIS-KEC20", price1: 1200, price2: 1100, wholesalePrice: 900, cost: 580, categoryId: cats.find(c => c.name === "Transmisión")?.id },
    { itemCode: "TRN-002", manufacturer: "Exedy", name: "Kit de Embrague", brand: "Mazda", model: "CX-5", year: "2021-2024", detail: "Disco + presión + desembrague", oemCode: "KD023-16-301", factoryCode: "EXD-KEC5", price1: 1100, price2: 1000, wholesalePrice: 820, cost: 520, categoryId: cats.find(c => c.name === "Transmisión")?.id },
  ];

  console.log("Creando productos...");
  const createdProducts = [];
  for (const p of products) {
    const product = await prisma.product.upsert({
      where: { itemCode: p.itemCode },
      update: {},
      create: {
        itemCode: p.itemCode,
        manufacturer: p.manufacturer,
        name: p.name,
        brand: p.brand,
        model: p.model,
        year: p.year,
        detail: p.detail,
        oemCode: p.oemCode,
        factoryCode: p.factoryCode,
        price1: p.price1,
        price2: p.price2,
        wholesalePrice: p.wholesalePrice,
        cost: p.cost,
        categoryId: p.categoryId ?? null,
      },
    });
    createdProducts.push(product);
  }
  console.log(`${createdProducts.length} productos creados`);

  console.log("Creando inventario por ubicación...");
  const stockData: Record<string, number[]> = {
    "FRN-001": [45, 12, 8, 0, 5, 3, 0],
    "FRN-002": [30, 8, 5, 2, 4, 2, 1],
    "FRN-003": [25, 10, 6, 0, 3, 2, 0],
    "MTR-001": [200, 50, 30, 40, 25, 15, 10],
    "MTR-002": [150, 40, 25, 30, 20, 12, 8],
    "MTR-003": [40, 6, 3, 2, 2, 1, 0],
    "SUS-001": [20, 5, 3, 2, 3, 2, 1],
    "SUS-002": [22, 6, 4, 3, 3, 2, 0],
    "SUS-003": [18, 4, 3, 2, 2, 1, 1],
    "FLT-001": [500, 120, 80, 100, 60, 40, 30],
    "FLT-002": [300, 80, 50, 60, 40, 25, 20],
    "FLT-003": [250, 70, 45, 55, 35, 22, 18],
    "ELC-001": [8, 2, 1, 1, 1, 0, 0],
    "ELC-002": [6, 2, 1, 1, 1, 0, 0],
    "ELC-003": [80, 20, 15, 18, 12, 8, 6],
    "CAR-001": [10, 2, 1, 1, 1, 0, 0],
    "CAR-002": [15, 4, 3, 2, 3, 2, 1],
    "TRN-001": [5, 1, 1, 0, 1, 0, 0],
    "TRN-002": [4, 1, 1, 0, 1, 0, 0],
  };

  const allLocs = [alm1, alm2, alm3, alm4, ti1, ti2, ti3];
  const inventoryEntries: Array<{ productId: number; locationId: number; stock: number; minStock: number }> = [];
  for (const product of createdProducts) {
    const stocks = stockData[product.itemCode] || [0, 0, 0, 0, 0, 0, 0];
    for (let i = 0; i < allLocs.length; i++) {
      inventoryEntries.push({ productId: product.id, locationId: allLocs[i].id, stock: stocks[i], minStock: 1 });
    }
  }
  await prisma.inventory.createMany({ data: inventoryEntries, skipDuplicates: true });
  console.log("Inventario creado para todas las ubicaciones");

  const suppliers = [
    { name: "Importaciones Automotrices Bolivia", nit: "1025478963", phone: "+591 4 4567890" },
    { name: "Distribuidora de Repuestos del Sur", nit: "1254789630", phone: "+591 4 5678901" },
    { name: "Repuestos Original S.R.L.", nit: "1547896302", phone: "+591 2 6789012" },
  ];
  await prisma.supplier.createMany({ data: suppliers, skipDuplicates: true });
  const createdSuppliers = await prisma.supplier.findMany();
  console.log(`${createdSuppliers.length} proveedores creados`);

  console.log("Creando ventas de los últimos 30 días...");
  const now = new Date();
  const saleRecords = [];

  const tiendaUsers = [tienda1, tienda2, tienda3];
  const tiendaLocs = [ti1, ti2, ti3];
  const methods: Array<"EFECTIVO" | "QR" | "TRANSFERENCIA" | "CREDITO"> = ["EFECTIVO", "QR", "TRANSFERENCIA", "CREDITO"];

  for (let day = 0; day < 30; day++) {
    const numSales = Math.floor(Math.random() * 4) + 2;
    for (let s = 0; s < numSales; s++) {
      const user = tiendaUsers[Math.floor(Math.random() * 3)];
      const loc = tiendaLocs[Math.floor(Math.random() * 3)];
      const numItems = Math.floor(Math.random() * 3) + 1;
      let total = 0;
      const itemsData = [];

      for (let it = 0; it < numItems; it++) {
        const prod = createdProducts[Math.floor(Math.random() * createdProducts.length)];
        const qty = Math.floor(Math.random() * 3) + 1;
        const price = Number(prod.price1);
        const sub = qty * price;
        total += sub;
        itemsData.push({ productId: prod.id, quantity: qty, unitPrice: price, subtotal: sub });
      }

      const saleDate = new Date(now);
      saleDate.setDate(saleDate.getDate() - day);
      saleDate.setHours(Math.floor(Math.random() * 10) + 8, Math.floor(Math.random() * 60));

      const paymentMethod = methods[Math.floor(Math.random() * methods.length)];

      const sale = await prisma.sale.create({
        data: {
          saleDate,
          total,
          type: "NORMAL",
          userId: user.id,
          locationId: loc.id,
          items: { create: itemsData },
          payments: { create: { method: paymentMethod, amount: total, date: saleDate } },
        },
      });
      saleRecords.push(sale);
    }
    process.stdout.write(`\r  Día ${day + 1}/30...`);
  }
  console.log(`\n${saleRecords.length} ventas normales creadas`);

  console.log("Creando ventas por mayor...");
  for (let day = 0; day < 15; day++) {
    const numSales = Math.floor(Math.random() * 2) + 1;
    for (let s = 0; s < numSales; s++) {
      const loc = day % 2 === 0 ? alm1 : alm2;
      const numItems = Math.floor(Math.random() * 4) + 2;
      let total = 0;
      const itemsData = [];

      for (let it = 0; it < numItems; it++) {
        const prod = createdProducts[Math.floor(Math.random() * createdProducts.length)];
        const qty = Math.floor(Math.random() * 8) + 5;
        const price = Number(prod.wholesalePrice || prod.price2);
        const sub = qty * price;
        total += sub;
        itemsData.push({ productId: prod.id, quantity: qty, unitPrice: price, subtotal: sub });
      }

      const saleDate = new Date(now);
      saleDate.setDate(saleDate.getDate() - day);
      saleDate.setHours(Math.floor(Math.random() * 8) + 9);

      await prisma.sale.create({
        data: {
          saleDate,
          total,
          type: "MAYOR",
          userId: admin.id,
          locationId: loc.id,
          items: { create: itemsData },
          payments: { create: { method: "TRANSFERENCIA", amount: total, date: saleDate } },
        },
      });
    }
    process.stdout.write(`\r  Día ${day + 1}/15...`);
  }
  console.log("\nVentas por mayor creadas");

  console.log("Creando movimientos...");
  const movementCount = 40;
  for (let i = 0; i < movementCount; i++) {
    const fromIdx = Math.floor(Math.random() * 4);
    let toIdx = Math.floor(Math.random() * 3) + 4;
    if (toIdx === fromIdx) toIdx = (toIdx + 1) % 7;
    const prod = createdProducts[Math.floor(Math.random() * createdProducts.length)];
    const qty = Math.floor(Math.random() * 10) + 1;
    const date = new Date(now);
    date.setDate(date.getDate() - Math.floor(Math.random() * 30));
    date.setHours(Math.floor(Math.random() * 8) + 10);

    await prisma.movement.create({
      data: {
        productId: prod.id,
        fromLocationId: allLocs[fromIdx].id,
        toLocationId: allLocs[toIdx].id,
        quantity: qty,
        userId: admin.id,
        date,
        observation: `Traslado de ${allLocs[fromIdx].name} a ${allLocs[toIdx].name}`,
      },
    });
  }
  console.log(`${movementCount} movimientos creados`);

  console.log("Creando solicitudes de producto...");
  const requestStatuses: Array<"PENDIENTE" | "EN_PREPARACION" | "ENVIADO" | "RECIBIDO" | "CANCELADO"> = ["PENDIENTE", "EN_PREPARACION", "ENVIADO", "RECIBIDO"];
  for (let i = 0; i < 12; i++) {
    const prod = createdProducts[Math.floor(Math.random() * createdProducts.length)];
    const tiendaUser = tiendaUsers[Math.floor(Math.random() * 3)];
    const tiendaLoc = tiendaLocs[Math.floor(Math.random() * 3)];
    const date = new Date(now);
    date.setDate(date.getDate() - Math.floor(Math.random() * 15));

    await prisma.productRequest.create({
      data: {
        productId: prod.id,
        quantity: Math.floor(Math.random() * 10) + 1,
        requestedById: tiendaUser.id,
        locationId: tiendaLoc.id,
        status: requestStatuses[Math.floor(Math.random() * requestStatuses.length)],
        date,
      },
    });
  }
  console.log("Solicitudes creadas");

  console.log("Creando clientes...");
  const customersData = [
    { name: "Juan Pérez", nit: "4567890", phone: "+591 71234567" },
    { name: "María López", nit: "6543210", phone: "+591 72345678" },
    { name: "Taller Mecánico El Racing", nit: "9876543", phone: "+591 4 7890123" },
    { name: "Distribuciones Santa Cruz S.A.", nit: "1234567", phone: "+591 3 4567890" },
    { name: "Transportes Bolívar", nit: "7654321", phone: "+591 7 3456789" },
  ];
  await prisma.customer.createMany({ data: customersData, skipDuplicates: true });
  const createdCustomers = await prisma.customer.findMany();
  console.log(`${createdCustomers.length} clientes creados`);

  console.log("Creando importadoras...");
  const importersData = [
    { name: "Importadora El Sol", phone: "+591 4 4561001", email: "contacto@elsol.com", city: "Cochabamba", description: "Especialistas en repuestos Toyota y Lexus" },
    { name: "Repuestos del Norte", phone: "+591 4 4561002", email: "ventas@repuestosnorte.com", city: "Cochabamba", description: "Repuestos Nissan y Mitsubishi de origen asiático" },
    { name: "AutoPartes Premium", phone: "+591 4 4561003", email: "info@autopartespremium.com", city: "Santa Cruz", description: "Piezas premium para vehículos japonenses y europeos" },
    { name: "Importadora Honda Bolivia", phone: "+591 4 4561004", email: "ventas@hondabolivia.com", city: "La Paz", description: "Representante oficial de repuestos Honda" },
    { name: "Mazda Parts Bolivia", phone: "+591 4 4561005", email: "contacto@madaparts.bo", city: "Cochabamba", description: "Repuestos originales y alternativos Mazda" },
    { name: "Repuestos Dongfeng", phone: "+591 4 4561006", email: "ventas@dongfeng.bo", city: "Santa Cruz", description: "Repuestos para vehículos chinos: Changan, BYD, Dongfeng" },
    { name: "Kia Hyundai Service", phone: "+591 4 4561007", email: "servicio@kiahyundai.bo", city: "La Paz", description: "Repuestos originales Kia e Hyundai coreanos" },
  ];
  const createdImporters = [];
  for (const imp of importersData) {
    const importer = await prisma.importer.create({ data: imp });
    createdImporters.push(importer);
  }
  console.log(`${createdImporters.length} importadoras creadas`);

  console.log("Asociando productos con importadoras y calidades...");
  const qualities = ["Taiwanesa", "Tailandesa", "China", "Japonesa", "Coreana", "Estadounidense"];
  const productImporterData: Array<{ productId: number; importerId: number }> = [];

  for (const product of createdProducts) {
    const qualityIdx = Math.floor(Math.random() * qualities.length);
    await prisma.product.update({
      where: { id: product.id },
      data: { quality: qualities[qualityIdx] },
    });

    const numImporters = Math.floor(Math.random() * 3) + 1;
    const shuffled = [...createdImporters].sort(() => Math.random() - 0.5);
    for (let i = 0; i < numImporters; i++) {
      productImporterData.push({ productId: product.id, importerId: shuffled[i].id });
    }
  }
  await prisma.productImporter.createMany({ data: productImporterData, skipDuplicates: true });
  console.log("Productos asociados con importadoras y calidades");

  console.log("\n=== Datos sembrados correctamente ===");
  console.log(`  - ${createdProducts.length} productos`);
  console.log(`  - ${saleRecords.length}+ ventas normales`);
  console.log(`  - ${movementCount} movimientos`);
  console.log(`  - 12 solicitudes`);
  console.log(`  - ${createdCustomers.length} clientes`);
}
