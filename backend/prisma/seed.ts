import { PrismaClient } from "@prisma/client";
import bcrypt from "bcryptjs";
import { seedData } from "./seed-data";

const prisma = new PrismaClient();

async function main() {
  console.log("Sembrando datos iniciales...");

  // Roles
  const adminRole = await prisma.roleModel.upsert({
    where: { name: "ADMIN" },
    update: {},
    create: { name: "ADMIN", permissions: ["*"] },
  });

  const tiendaRole = await prisma.roleModel.upsert({
    where: { name: "TIENDA" },
    update: {
      permissions: ["ventas", "inventario", "solicitudes", "devoluciones"],
      columnConfig: {
        inventario: ["ID", "Fabricante", "Producto", "Marca", "Modelo", "Año", "Detalles", "Cód. OEM", "Cód. Fábrica", "Imagen", "Precio 1", "Precio 2", "Stock", "Acciones"],
        ventas: ["ID", "Fecha", "Cliente", "Tienda", "Vendedor", "Total", "Estado", "Acciones"],
        __categorias: ["Frenos", "Motor", "Eléctrico"],
      },
    },
    create: {
      name: "TIENDA",
      permissions: ["ventas", "inventario", "solicitudes", "devoluciones"],
      columnConfig: {
        inventario: ["ID", "Fabricante", "Producto", "Marca", "Modelo", "Año", "Detalles", "Cód. OEM", "Cód. Fábrica", "Imagen", "Precio 1", "Precio 2", "Stock", "Acciones"],
        ventas: ["ID", "Fecha", "Cliente", "Tienda", "Vendedor", "Total", "Estado", "Acciones"],
        __categorias: ["Frenos", "Motor", "Eléctrico"],
      },
    },
  });

  const inventarioRole = await prisma.roleModel.upsert({
    where: { name: "INVENTARIO" },
    update: {},
    create: { name: "INVENTARIO", permissions: ["movimientos", "inventario", "solicitudes"] },
  });

  console.log("Roles creados:", { adminRole: adminRole.id, tiendaRole: tiendaRole.id, inventarioRole: inventarioRole.id });

  // Ubicaciones: 4 almacenes + 3 tiendas
  const ubicaciones = [
    { name: "Almacén 1", type: "ALMACEN" as const, address: "Zona Industrial" },
    { name: "Almacén 2", type: "ALMACEN" as const, address: "Zona Sur" },
    { name: "Almacén 3", type: "ALMACEN" as const, address: "Zona Norte" },
    { name: "Almacén 4", type: "ALMACEN" as const, address: "Zona Este" },
    { name: "Tienda 1", type: "TIENDA" as const, address: "Av. Principal" },
    { name: "Tienda 2", type: "TIENDA" as const, address: "Av. Ballivián" },
    { name: "Tienda 3", type: "TIENDA" as const, address: "Av. Blanco Galindo" },
  ];

  const ubicacionesCreadas = [];
  for (const u of ubicaciones) {
    const ubicacion = await prisma.location.upsert({
      where: { id: ubicaciones.indexOf(u) + 1 },
      update: {},
      create: u,
    });
    ubicacionesCreadas.push(ubicacion);
  }

  console.log("Ubicaciones creadas:", ubicacionesCreadas.length);

  // Categorías iniciales
  const categorias = ["Frenos", "Motor", "Suspensión", "Eléctrico", "Carrocería", "Transmisión", "Filtros"];
  for (const cat of categorias) {
    await prisma.category.upsert({
      where: { id: categorias.indexOf(cat) + 1 },
      update: {},
      create: { name: cat },
    });
  }

  console.log("Categorías creadas:", categorias.length);

  // Usuario admin
  const hashedPassword = await bcrypt.hash("admin123", 10);
  const adminUser = await prisma.user.upsert({
    where: { email: "admin@inventario.com" },
    update: {},
    create: {
      name: "Administrador",
      email: "admin@inventario.com",
      password: hashedPassword,
      roleId: adminRole.id,
      locationId: null,
    },
  });

  console.log("Usuario admin creado:", adminUser.email);

  // Usuarios de tienda
  const tiendaPassword = await bcrypt.hash("tienda123", 10);
  const tiendaUsers = [
    { name: "Vendedor Tienda 1", email: "tienda1@inventario.com", locationId: ubicacionesCreadas[4].id },
    { name: "Vendedor Tienda 2", email: "tienda2@inventario.com", locationId: ubicacionesCreadas[5].id },
    { name: "Vendedor Tienda 3", email: "tienda3@inventario.com", locationId: ubicacionesCreadas[6].id },
  ];

  for (const tu of tiendaUsers) {
    await prisma.user.upsert({
      where: { email: tu.email },
      update: {},
      create: {
        name: tu.name,
        email: tu.email,
        password: tiendaPassword,
        roleId: tiendaRole.id,
        locationId: tu.locationId,
      },
    });
  }

  console.log("Usuarios de tienda creados:", tiendaUsers.length);

  // Usuario de inventario
  const inventarioPassword = await bcrypt.hash("inventario123", 10);
  await prisma.user.upsert({
    where: { email: "inventario@inventario.com" },
    update: {},
    create: {
      name: "Encargado Inventario",
      email: "inventario@inventario.com",
      password: inventarioPassword,
      roleId: inventarioRole.id,
      locationId: ubicacionesCreadas[0].id,
    },
  });

  console.log("Usuario de inventario creado");

  // Usuario de tienda adicional (Fernando) — rol TIENDA con categorías limitadas
  const vendedorPassword = await bcrypt.hash("vendedor123", 10);
  await prisma.user.upsert({
    where: { email: "fernando@inventario.com" },
    update: { roleId: tiendaRole.id, locationId: ubicacionesCreadas[4].id, password: vendedorPassword },
    create: {
      name: "Fernando Vendedor",
      email: "fernando@inventario.com",
      password: vendedorPassword,
      roleId: tiendaRole.id,
      locationId: ubicacionesCreadas[4].id,
    },
  });

  console.log("Usuario TIENDA (Fernando) creado");

  await seedData(prisma);

  console.log("\n=== Datos iniciales sembrados correctamente ===");
  console.log("Credenciales de acceso:");
  console.log("  Admin:       admin@inventario.com / admin123");
  console.log("  Tienda 1:    tienda1@inventario.com / tienda123");
  console.log("  Tienda 2:    tienda2@inventario.com / tienda123");
  console.log("  Tienda 3:    tienda3@inventario.com / tienda123");
  console.log("  Inventario:  inventario@inventario.com / inventario123");
  console.log("  Fernando:    fernando@inventario.com / vendedor123 (rol TIENDA, Tienda 1)");
}

main()
  .catch((e) => {
    console.error("Error al sembrar datos:", e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
