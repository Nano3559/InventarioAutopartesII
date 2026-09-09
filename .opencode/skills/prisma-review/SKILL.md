---
name: prisma-review
description: Use when reviewing Prisma schema, migrations, relations, indexes, transactions or data integrity in this repo. Trigger on schema.prisma, prisma/migrations, $transaction, stock concurrency, or before creating a migration. Audits without modifying the database.
---

# prisma-review

Audita cambios relacionados con Prisma y la base de datos sin modificar `schema.prisma` ni ejecutar operaciones destructivas.

## Checklist

* **Schema** — modelos, campos, tipos y `@map`/`@@map` coherentes con el dominio.
* **Relaciones** — `@relation`, referencias por id, integridad entre modelos (cascade/setNull/restrict).
* **Índices** — campos de filtro/orden con índices (itemCode, oemCode, factoryCode, fechas, `locationId`, `productId`); detectar `@@index` faltantes en búsquedas frecuentes.
* **Tipos** — `Int`/`Float`/`Decimal` (precios, costos, stock; nunca `Float` para dinero), `DateTime`, enums.
* **Decimal** — precisión/redondeo en montos y precios.
* **Nullability** — campos opcionales vs obligatorios; consecuencias en el resto del código.
* **Claves foráneas** — columnas FK y su relación con los filtros/joins usados.
* **onDelete / onUpdate** — política correcta según la lógica de negocio (no borrar stock de ubicaciones por accidente).
* **N+1** — queries con `include` dentro de bucles que cargan datos repetidamente.
* **Transacciones** — lecturas+escrituras de stock dentro de `$transaction`; bloqueo de filas (`SELECT ... FOR UPDATE`) en movimiento/salidas concurrentes.
* **Concurrencia** — resguardos ante dos operaciones simultáneas sobre el mismo inventario.
* **Riesgo de pérdida de datos** — migraciones que borren columnas/tablas o cambien precisión.
* **Migraciones** — revisar el historial de `backend/prisma/migrations/` y el impacto de cualquier migración propuesta antes de crearla.

## Prohibiciones

* NO ejecutar `prisma migrate reset`, `prisma db push` destructivo, `DROP`, `TRUNCATE` ni eliminación de datos.
* NO modificar `schema.prisma` automáticamente: reporta y espera autorización.
* NO reescribir ni borrar migraciones existentes.
* NO proponer cambios de base de datos sin explicar primero el impacto y el plan de migración.

## Formato de salida

Por hallazgo:

```text
- Severidad: <crítica|alta|media|baja>
- Archivo: ...
- Ubicación: ...
- Problema: ...
- Riesgo: ...
- Recomendación: ...
```

Entregar al final: resumen, archivos consultados y (si aplica) bosquejo de migración sin ejecutarla.