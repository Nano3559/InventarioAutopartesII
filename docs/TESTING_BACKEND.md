# Testing Backend

Documento oficial de la suite de pruebas del backend de RepuestoPro / Inventario Autopartes II.
Los valores consignados corresponden al estado validado del repositorio el 2026-09-09 y fueron
re-verificados al momento de redactar este documento ejecutando los comandos descritos en la
Sección 4 (unit tests 28/28, tests de integración 23/23, `tsc` con salida 0 y cobertura 79.51 %
de líneas).

Esta suite es el equivalente backend del conjunto de pruebas frontend de la Etapa 7 (E7.1–E7.8)
registrado por Erika en `PLAN_TRABAJO_ERIKA_ROSS.md`. El repositorio no contiene un documento
independiente de testing frontend; el registro de Erika es la lista de tareas de la Etapa 7 y la
entrada del historial de avance (`E7.1–E7.4, E7.7–E7.8` → Vitest). Siguiendo la convención de
documentación en `docs/` (p. ej. `STACK_FRONTEND.md`, `STACK_BACKEND.md`), este documento se creó
como `docs/TESTING_BACKEND.md`.

---

## 1. Objetivo

La suite de pruebas del backend busca garantizar de forma reproducible y permanente que los
flujos críticos del sistema funcionan correctamente y no se rompen con los cambios posteriores
(regresión). En concreto, se implantó para:

* Verificar la autenticación (login válido e inválido) y la autorización por roles
  (ADMIN, TIENDA, INVENTARIO) y por módulos (`authorizeModule`).
* Proteger la integridad del stock frente a **concurrencia**: dos ventas o dos movimientos
  simultáneos nunca deben dejar el stock en negativo ni registrar operaciones de más.
* Comprobar el flujo de ventas (creación, múltiples pagos, descuento de stock, rollback
  por stock insuficiente) y de devoluciones (incremento de inventario y límite máximo).
* Validar la reposición automática de productos al agotarse el stock.
* Validar el flujo de búsqueda por imagen (OCR): accesibilidad de los endpoints público e
  interno, límites de subida (MIME y 5 MB) y la **serialización segura** de la respuesta
  pública, que nunca expone `price2`, `cost`, `wholesalePrice`, `totalStock` ni `locations`.
* Validar el funcionamiento de la caché de permisos (TTL e invalidación).

Los tests se ejecutan sobre una aplicación Express **real** (la misma `app.ts` de producción),
sobre una base de datos **PostgreSQL aislada local**, y nunca contra bases remotas como Neon o
Railway (la propia infraestructura de testing lo impide, ver Sección 14).

---

## 2. Resumen general

| Tipo | Cantidad | Resultado |
|---|---:|---|
| Unitarios | 28 | 28/28 PASS |
| Integración | 23 | 23/23 PASS |
| TOTAL | 51 | 51/51 PASS |

Complementos de calidad validados:

| Práctica | Herramienta | Resultado |
|---|---|---|
| Cobertura de líneas | Node.js (runner native `node:test`) | 79.51 % |
| Cobertura de ramas | Node.js (runner native `node:test`) | 87.30 % |
| Cobertura de funciones | Node.js (runner native `node:test`) | 89.25 % |
| Compilación TypeScript | `npx tsc --noEmit` | PASS (exit 0) |
| Build | `npm run build` (tsc) | PASS |
| Migraciones Prisma | `prisma migrate deploy` (BD aislada) | 6/6 PASS |
| Estado de migraciones | `prisma migrate status` (BD aislada) | up to date |

> La cobertura se mide sobre la suite unitaria (es el alcance del script `test:coverage`),
> no sobre los tests de integración.

---

## 3. Tecnologías y herramientas utilizadas

Solo herramientas realmente presentes en el proyecto (`backend/package.json` y código fuente):

| Herramienta | Uso |
|---|---|
| Node.js `24.16.0` | Runtime de ejecución; incluye el **runner nativo de pruebas `node:test`** (`node --test`) |
| TypeScript `^5.5.4` | Lenguaje del backend y de todos los archivos de prueba (`*.test.ts`, `*.itest.ts`) |
| `tsx` `^4.23.13` | Ejecutor de TypeScript usado para lanzar los tests sobre el código fuente |
| Prisma `^5.19.0` (prisma / @prisma/client) | ORM; los tests de integración usan `PrismaClient` real para seed, verificación y cleanup |
| PostgreSQL aislada | Base de datos local de pruebas (residente en el equipo, jamás Neon/Railway) |
| `express`/`multer` reales | Los tests de integración y de subida ejercitan la aplicación Express real |

Aclaraciones importantes para evitar malentendidos:

* **No se utiliza Jest, Vitest, Mocha, Supertest ni mochiglia alguna.** El runner es el módulo
  nativo de Node.js `node:test`, con `assert` estricto (`node:assert/strict`).
* La cobertura la genera el propio Node.js con la bandera experimental `--experimental-test-coverage`
  (no c8 ni nyc).
* El frontend sí usa Vitest; el backend usa su propio runner. Son suites independientes.

---

## 4. Comandos disponibles

| Comando | Qué hace | Notas |
|---|---|---|
| `npm test` | Ejecuta la suite **unitaria**: `tsx --test "src/**/*.test.ts"` | No requiere base de datos ni red |
| `npm run test:integration` | Ejecuta los **tests de integración**: `tsx --test --test-force-exit "src/**/*.itest.ts"` | Requiere PostgreSQL local de prueba; `--test-force-exit` cierra procesos HTTP/Prisma restantes de forma determinista |
| `npm run test:all` | Unit + integración en una sola corrida: `tsx --test "src/**/*.test.ts" && tsx --test --test-force-exit "src/**/*.itest.ts"` | Se separó en dos fases para evitar un flake de libuv en Windows al forzar `--test-force-exit` sobre los unitarios |
| `npm run test:coverage` | Ejecuta los unitarios con cobertura nativa de Node: `node --import tsx --test --experimental-test-coverage "src/**/*.test.ts"` | Reporta `line %`, `branch %` y `funcs %` |
| `npm run test:watch` | Ejecuta los unitarios en modo watch | Utilidad de desarrollo |
| `npx tsc --noEmit` | Verifica tipos de todo el backend sin emitir | Equivale a la compilación de `npm run build` |
| `npm run build` | Compila el backend (`tsc`) | Produce `dist/` |

---

## 5. Pruebas unitarias

**Resultado: 28/28 PASS.**

Los archivos unitarios reales y su contenido:

| Archivo | Módulo | Qué valida | Nº tests |
|---|---:|---|:---:|
| `src/utils/__tests__/yearRanges.test.ts` | `utils/yearRanges` | Parseo y expansión de rangos de años (`13-15` → 2013–2015), rangos abiertos (`10-`), múltiples rangos (`13-15/16-18`), normalización de años de 2 dígitos, `end < start`, `yearMatchesRanges` y `yearRangesOverlap` (solapados / disjuntos / multi) | 10 |
| `src/utils/__tests__/saleItems.test.ts` | `utils/saleItems` | `validateAndMergeItems`: ítems únicos, deduplicación de productos repetidos sumando cantidades, uso de `wholesalePrice` como precio cuando no hay `unitPrice`, y rechazo de cantidad no entera < 1, precio ≤ 0, `productId` inválido y lista vacía | 7 |
| `src/shared/middlewares/__tests__/validate.test.ts` | `shared/middlewares/validate` | `parseId` (solo enteros ≥ 1), `parsePositiveInt`, `parsePositiveDecimal` (acepta 0) y `parseString` (obligatorio / opcional) | 4 |
| `src/modules/products/__tests__/imageUpload.test.ts` | `products/searchImage` (middleware `imageUpload`) | Subida real con multer: acepta JPEG/PNG/WebP; rechaza MIME no permitido con 400; rechaza > 5 MB con 400; rechaza campo multipart inesperado; sin archivo no crea `req.file` | 5 |
| `src/modules/products/__tests__/searchImage.serialize.test.ts` | `products/searchImage` | Serialización de resultados: el endpoint público **nunca** expone `price2`, `wholesalePrice`, `cost`, `totalStock` ni `locations`; el interno expone `price2`/`totalStock`/`locations` pero tampoco `cost` ni `wholesalePrice` | 2 |

**Total unitarios = 10 + 7 + 4 + 5 + 2 = 28.**

---

## 6. Pruebas de integración

**Resultado: 23/23 PASS.**

Las pruebas de integración levantan la aplicación Express real en `127.0.0.1` con puerto efímero,
siembran datos en la PostgreSQL local de prueba, hacen peticiones HTTP reales (`fetch`) y limpian
los datos al finalizar.

| Archivo | Módulo | Escenarios | Nº tests |
|---|---:|---|:---:|
| `src/modules/auth/__tests__/authPermissions.itest.ts` | Auth y permisos | R6.1 login válido; R6.2 login inválido (401 password incorrecta, 401 usuario inexistente, 400 datos faltantes); R6.3 ADMIN (acceso movimientos y ventas); R6.4 TIENDA (403 en movimientos, 200 en ventas); R6.5 INVENTARIO (200 movimientos, 403 ventas) | 5 |
| `src/modules/sales/__tests__/sales.itest.ts` | Ventas e inventario | R6.6 crear venta 201 con total/ítems/pagos; R6.7 descuento de stock; R6.8 múltiples pagos + métodos/montos inválidos; R6.9 stock insuficiente (400 sin descuento); R6.10 ventas concurrentes (una gana, stock nunca negativo); R6.16 reposición automática (solicitud PENDIENTE cantidad 5) y caso sin stock de almacén (no crea solicitud) | 6 |
| `src/modules/movements/__tests__/movements.itest.ts` | Inventario / movimientos | R6.11 movimiento válido ALMACÉN→TIENDA (descuenta y acredita); R6.11 validaciones (origen == destino → 400; stock insuficiente → 400); R6.12 movimientos concurrentes (uno gana, origen nunca negativo) | 3 |
| `src/modules/returns/__tests__/returns.itest.ts` | Devoluciones | R6.13 devolución válida 201; R6.14 devoluciones inválidas (exceso de cantidad, método inválido, monto excesivo, sale inexistente → 404); R6.15 incremento de stock por devolución + bloqueo de doble devolución | 3 |
| `src/modules/products/__tests__/searchImageRoutes.itest.ts` | Search Image (rutas) | J3.1 `POST /api/public/search-image` funciona sin token (400, nunca 401); J3.2 `POST /api/products/search-image` exige token (401 anónimo e inválido); J3.3 archivo inválido → 400 antes de OCR; J3.8 límite de 5 MB en el flujo HTTP anónimo | 4 |
| `src/shared/middlewares/__tests__/permissionCache.itest.ts` | Caché de permisos (Etapa 8) | E8: permiso en caché permite acceso (200); cambio de permisos por fuera del flujo de invalidación sigue sirviendo el snapshot dentro del TTL; tras `invalidateRoleCache` la recarga desde BD devuelve 403 | 2 |

**Total integración = 5 + 6 + 3 + 3 + 4 + 2 = 23.**

---

## 7. Matriz R6.1–R6.16

Cumplimiento de la **Etapa 6 — Testing Backend** del plan de trabajo:

| ID | Prueba | Resultado | Evidencia / test relacionado |
|---|---|---|---|
| R6.1 | Login válido | PASS | `authPermissions.itest.ts` |
| R6.2 | Login inválido | PASS | `authPermissions.itest.ts` |
| R6.3 | Permisos ADMIN | PASS | `authPermissions.itest.ts` |
| R6.4 | Permisos TIENDA | PASS | `authPermissions.itest.ts` |
| R6.5 | Permisos INVENTARIO | PASS | `authPermissions.itest.ts` |
| R6.6 | Crear venta | PASS | `sales.itest.ts` |
| R6.7 | Descuento de stock | PASS | `sales.itest.ts` |
| R6.8 | Múltiples pagos | PASS | `sales.itest.ts` |
| R6.9 | Stock insuficiente | PASS | `sales.itest.ts` |
| R6.10 | Ventas concurrentes | PASS | `sales.itest.ts` |
| R6.11 | Movimiento de stock | PASS | `movements.itest.ts` |
| R6.12 | Movimiento concurrente | PASS | `movements.itest.ts` |
| R6.13 | Devolución válida | PASS | `returns.itest.ts` |
| R6.14 | Devolución superior a la cantidad vendida | PASS | `returns.itest.ts` |
| R6.15 | Incremento de stock por devolución | PASS | `returns.itest.ts` |
| R6.16 | Reposición automática | PASS | `sales.itest.ts` |

Etapa 6 cubierta: **16/16 requisitos con PASS automatizado.**

---

## 8. Autenticación y permisos

Cubierto por `authPermissions.itest.ts` (5 tests):

* **Login válido**: `POST /api/auth/login` con credenciales reales siembradas responde 200,
  devuelve `token` y el perfil con `email`, `role` y `locationId` correctos.
* **Login inválido**: password incorrecta → 401 con `Credenciales inválidas`; usuario inexistente
  → 401; datos faltantes → 400.
* **ADMIN** (rol con permisos `["*"]`): accede al módulo movimientos (200 y lista) y a ventas (200).
* **TIENDA** (roles con permisos ventas/inventario/solicitudes/devoluciones): bloqueado en
  movimientos con **403** y mensaje `No tiene acceso al módulo: movimientos`; accede a ventas (200).
* **INVENTARIO** (roles con permisos movimientos/inventario/solicitudes): accede a movimientos
  (200) y queda **403** en ventas con `No tiene permisos para esta acción`.

Estos tests validan tanto el middleware `authenticate` (generación/validación de JWT) como
`authorize` y `authorizeModule` (permisos por rol y por módulo).

---

## 9. Ventas e inventario

Cubierto por `sales.itest.ts` (6 tests):

* **Creación de venta** (R6.6): 201 con `type: "NORMAL"`, total calculado, ítem con cantidad y
  subtotal, y pago registrado.
* **Descuento de stock** (R6.7): tras vender 3 unidades de un producto con stock 8, el inventario
  de la tienda queda en 5.
* **Pagos múltiples** (R6.8): venta con `EFECTIVO 120 + QR 180` → 201 con sumatoria 300; método
  inválido (`BITCOIN`) → 400; monto negativo → 400.
* **Stock insuficiente** (R6.9): pedir 5 con stock 2 → 400 con mensaje `/Stock insuficiente/` y el
  stock permanece en 2 (**rollback**: no se descuenta ni se registra venta).
* **Concurrencia de ventas** (R6.10): ver Sección 10.
* **Reposición automática** (R6.16): al vender la última unidad (stock llega a 0) se crea una
  `ProductRequest` `PENDIENTE` de 5 unidades (máximo entre vendida y 5). Si el almacén no tiene
  stock del producto, **no** se crea la solicitud.

---

## 10. Concurrencia

La integridad del stock frente a peticiones simultáneas se prueba con operaciones reales lanzadas
en paralelo con `Promise.all` sobre la misma base de datos, dentro de la misma transacción con
bloqueos de fila (`SELECT … FOR UPDATE`) y orden de locks determinista.

### Ventas concurrentes (R6.10) — `sales.itest.ts`

Escenario real ejecutado:

```
Stock en tienda = 5
Operación A = vender 3
Operación B = vender 3
```

Resultado verificado:

* **una** operación gana (201) y **exactamente una** falla (400 `Stock insuficiente`);
* stock final = **2** (5 − 3);
* **nunca negativo**;
* en la BD solo existe **1** `SaleItem` para el producto (no hay ítems fantasma).

### Movimientos concurrentes (R6.12) — `movements.itest.ts`

Escenario real ejecutado:

```
Stock en origen (ALMACÉN) = 5
Operación A = mover 4 → TIENDA
Operación B = mover 4 → TIENDA
```

Resultado verificado:

* **un** movimiento gana (201) y **exactamente uno** falla (400 `Stock insuficiente en origen`);
* stock de origen = **1**, stock de destino = **4**;
* en la BD solo existe **1** registro de `Movement`.

La misma transacción que protege estas operaciones usa bloqueo de fila del inventario
(`$queryRaw SELECT … FOR UPDATE`) antes de la lectura-escritura, garantizando que dos procesos
concurrentes jamás sobrevendan ni dejen stock negativo. (Los movimientos a un destino sin
inventario previo se resuelven con un `upsert` atómico bajo la misma transacción.)

---

## 11. Devoluciones

Cubierto por `returns.itest.ts` (3 tests):

* **Devolución válida** (R6.13): tras vender 5, devolver 2 → 201 con `quantity`, `saleId`,
  `productId` y `reason`.
* **Devolución inválida** (R6.14): devolver 3 de una venta de 2 → 400
  `La cantidad a devolver (3) excede la vendida (2)`; método de pago inválido → 400; monto
  devuelto mayor al pagado → 400; venta inexistente → 404.
* **Incremento de inventario + doble devolución** (R6.15): con stock 5, se venden 3 (queda 2),
  se devuelven 2 (queda 4): el stock **aumenta** con la cantidad devuelta. Un segundo intento de
  devolver 2 sobre la misma venta → 400 (`Ya se devolvieron… Maximo adicional: 1`), y en la BD
  solo existe **1** registro de devolución (la operación es idempotente gracias al doble control:
  cantidad vendida − cantidad ya devuelta).

Concurrencia de doble devolución: el test R6.15 cubre el rechazo de devolver más de lo vendido en
secuencia; la segunda devolución se bloquea a nivel de lógica de negocio (límite máximo por venta),
evitando que el stock se infle.

---

## 12. Search Image

Cubierto por `imageUpload.test.ts` (unitario, 5), `searchImage.serialize.test.ts` (unitario, 2) y
`searchImageRoutes.itest.ts` (integración, 4).

| Aspecto | Test que lo cubre | Resultado |
|---|---|---|
| Endpoint público `POST /api/public/search-image` sin token | J3.1 (itest) | 400 `Debe subir una imagen`, **nunca 401** (anónimo permitido por contrato público) |
| Endpoint interno `POST /api/products/search-image` con token | J3.2 (itest) | Anónimo → 401 `Token no proporcionado`; token inválido → 401 `Token inválido o expirado` |
| MIME no permitido (público anónimo) | J3.3 (itest) | 400 `Tipo de archivo no permitido` antes de ejecutar OCR |
| MIME permitidos (JPEG/PNG/WebP) | unit Image Upload | Aceptados (200) |
| MIME no permitido (unit) | unit Image Upload | 400 |
| Límite 5 MB (flujo HTTP real anónimo) | J3.8 (itest) | 400 `El archivo excede el tamaño máximo permitido` |
| Límite 5 MB (unit) | unit Image Upload | 400 |
| Campo multipart inesperado | unit Image Upload | 400 |
| Serialización pública (no expone internos) | unit Serialization | Público sin `price2`, `cost`, `wholesalePrice`, `totalStock`, `locations` |
| Serialización interna | unit Serialization | Expone `price2`, `totalStock`, `locations`, pero **no** `cost` ni `wholesalePrice` |
| `score` y `availability` presentes | unit Serialization | `score` numérico e `availability` (`Disponible`) en la respuesta |

**Regla de seguridad firmemente establecida:** el endpoint **público** de búsqueda por imagen
jamás expone `price2`, `cost`, `wholesalePrice`, `totalStock` ni `locations`. Estos campos solo
existen en la vista interna autenticada (y ni siquiera ahí aparecen `cost` ni `wholesalePrice`).

> La validación OCR con una foto real tomada con cámara/Exposición (J3.9–J3.11) queda como
> validación manual de Ross sobre el móvil; los límites automáticos (MIME y 5 MB) ya están
> verificados punto a punto en el flujo HTTP.

---

## 13. Caché de permisos

Cubierto por `src/shared/middlewares/__tests__/permissionCache.itest.ts` (E8, 2 tests).

La prueba usa un **rol dedicado** por namespace (`TEST-CACHE-<ns>`) para no mutar los roles
compartidos (ADMIN/TIENDA/INVENTARIO) que otros tests de integración leen. Verifica:

* **Cache hit**: el rol con permiso `movimientos` entra a la caché → `GET /api/movements` = 200.
* **TTL / snapshot**: el permiso se retira **por fuera** del flujo de invalidación (escritura
  directa a BD, simula otra instancia o migración) → dentro del TTL la caché sigue sirviendo los
  permisos que conoce (aún 200).
* **Invalidación**: `invalidateRoleCache(roleId)` fuerza la recarga desde BD → la siguiente
  petición es 403 `No tiene acceso al módulo: movimientos`.
* Restaura el permiso al final para no dejar el rol mutado.

La caché es en memoria (por rol, TTL 60 s) y la invalidez se produce también en el endpoint de
actualización de permisos `PUT /api/permissions/roles/:id/permissions` (invalidación previa al
registro de auditoría).

---

## 14. PostgreSQL de testing

Las pruebas de integración utilizan una **PostgreSQL aislada local** y **jamás** Neon, Railway u
otra base remota de producción. Mecanismos implementados en `backend/src/testing/helpers.ts` y
`seed.ts`:

* **Protección anti-producción**: `assertLocalTestUrl()` valida que el host de `DATABASE_URL` sea
  estrictamente loopback (`127.0.0.1`, `localhost` o `::1`) y que el protocolo sea `postgresql:`
  o `postgres:`. Si la URL apunta a cualquier otro host, la ejecución **aborta** con un error claro.
  Es imposible correr los tests contra una base remota por accidente.
* **Aislamiento por namespace (`ns`)**: cada archivo `.itest.ts` siembra sus propios usuarios,
  ubicaciones y productos (`ALMACEN-<ns>`, `TIENDA-<ns>`, `admin.<ns>@itest.local`, …). Los roles
  compartidos (ADMIN/TIENDA/INVENTARIO) solo se leen, nunca se eliminan.
* **Seed idempotente**: `seed()` usa `upsert` y contraseñas encriptadas con `bcrypt`; `createProduct()`
  crea productos de prueba etiquetados por namespace.
* **Cleanup**: `cleanup()` elimina devoluciones, movimientos, solicitudes, ítems/pagos/ventas,
  inventarios, productos, clientes y usuarios del namespace, y **desconecta** el `PrismaClient`.
* **Cierre de conexiones**: `startTestServer()` abre la app en `127.0.0.1` con puerto efímero;
  `close()` cierra los sockets keep-alive (`closeAllConnections`) y el servidor para que el proceso
  termine de forma determinista.
* **Límite de conexiones**: `connection_limit=3` en la URL de test para no agotar `max_connections`
  del clúster local cuando varios archivos corren en paralelo.
* **Secreto de prueba**: `resolveTestEnv()` establece un `JWT_SECRET` de prueba (nunca el real) y
  valida que sea suficientemente largo y no un valor reservado.
* **URL de conexión**: se toma de `DATABASE_URL` (validada) o, si no existe, de un archivo local
  fuera del repositorio que contiene el valor de conexión del clúster de pruebas; en ningún caso se
  usa la base remota.

Este documento no consigna ni la URL ni credenciales de la base de prueba (secreto operativo).

---

## 15. Migraciones Prisma

La reconstrucción verificada del esquema se realizó sobre la **base de datos aislada de pruebas**:

```text
DB vacía (recreada localmente)
→ npx prisma migrate deploy
→ 6/6 migraciones aplicadas en orden:
    20260819182416_init
    20260820163545_add_quality_importers
    20260902130000_add_unique_nit
    20260902_add_movement_request_id
    20260909_close_schema_drift
    20260909b_add_etapa8_indexes
→ npx prisma generate
→ npx prisma migrate status  → "Database schema is up to date!"
→ npm run test:integration    → 23/23 PASS
```

Observaciones:

* No se modificó, borró ni reescribió ninguna migración histórica.
* Los índices de la Etapa 8 (`20260909b_add_etapa8_indexes`) son **aditivos** y fueron aplicados
  correctamente en la reconstrucción.
* Existe un **residual deliberado** en el enum `RequestStatus`: la migración `close_schema_drift`
  creó los nuevos estados (`RECIBIDO_POR_INVENTARIO`, `PREPARANDO`, `ENTREGADO`,
  `RECIBIDO_POR_TIENDA`, `CANCELADO`), pero las variantes legacy (`EN_PREPARACION`, `ENVIADO`,
  `RECIBIDO`) permanecen en la base. `prisma migrate diff` propone eliminarlas; se optó por
  **mantenerlas** para no ejecutar una migración destructiva. Por ello **no** se afirma un "drift
  cero" absoluto: el único diff residual es un cambio destructivo de enum que se descarta a propósito.
* La base remota desplegada actualmente no tiene aún aplicadas las migraciones
  `20260909_close_schema_drift` ni `20260909b_add_etapa8_indexes`; su aplicación en el entorno de
  despliegue queda pendiente para el proceso manual de Ross (fuera del alcance de documentación).
  Los tests siempre se ejecutan únicamente contra la base local aislada.

---

## 16. Cobertura

Medida por el runner nativo de Node.js (`--test --experimental-test-coverage`) sobre la suite
unitaria:

| Métrica | Resultado |
|---|---:|
| Lines | 79.51 % |
| Branches | 87.30 % |
| Functions | 89.25 % |

La herramienta (`node:test`) reporta estas tres métricas; no reporta `statements`. La cobertura
abarca los módulos ejercitados por los unitarios: `searchImage.service.ts` (71.97 % líneas),
`errorHandler.ts` (71.64 %), `validate.ts` (85.37 %), `logger.ts` (100 %), `saleItems.ts` (100 %) y
`yearRanges.ts` (85.59 %).

---

## 17. Estructura de archivos de testing

Árbol real del backend:

```text
backend/src/
├── modules/
│   ├── auth/
│   │   └── __tests__/
│   │       └── authPermissions.itest.ts            (5)
│   ├── movements/
│   │   └── __tests__/
│   │       └── movements.itest.ts                  (3)
│   ├── products/
│   │   └── __tests__/
│   │       ├── imageUpload.test.ts                 (5)
│   │       ├── searchImage.serialize.test.ts       (2)
│   │       └── searchImageRoutes.itest.ts          (4)
│   ├── returns/
│   │   └── __tests__/
│   │       └── returns.itest.ts                    (3)
│   └── sales/
│       └── __tests__/
│           └── sales.itest.ts                      (6)
├── shared/
│   └── middlewares/__tests__/
│       ├── validate.test.ts                        (4)
│       └── permissionCache.itest.ts                (2)
├── testing/                     (infraestructura compartida, sin `*.test.*`)
│   ├── helpers.ts              (servidor de test + seguridad anti-remota + login)
│   └── seed.ts                 (siembra/carga/limpieza por namespace)
└── utils/
    └── __tests__/
        ├── saleItems.test.ts                       (7)
        └── yearRanges.test.ts                      (10)
```

Recuento por convención de nombres: `*.test.ts` (unitarios) = **28**; `*.itest.ts` (integración)
= **23**; total = **51**.

---

## 18. Resultado final

| Práctica | Herramienta | Resultado |
|---|---|---|
| TypeScript | `npx tsc --noEmit` | PASS |
| Unit tests | `npm test` | 28/28 PASS |
| Integration tests | `npm run test:integration` | 23/23 PASS |
| Suite completa | `npm run test:all` | 51/51 PASS |
| Cobertura | `npm run test:coverage` | Lines 79.51 % / Branches 87.30 % / Funcs 89.25 % |
| Build | `npm run build` | PASS |
| Prisma | `prisma migrate deploy` + `migrate status` (BD aislada) | 6/6 · up to date |

---

## 19. Conclusión

El backend de RepuestoPro cuenta con una suite de pruebas permanente de **51 tests**, todos
aprobados. De ellos, **28 son unitarios** y **23 de integración**. Los tests unitarios garantizan
la corrección de las operaciones aisladas (rangos de años, normalización de ítems de venta,
validaciones de entrada, subida de imágenes y serialización segura de resultados). Los tests de
integración ejercitan la aplicación Express real contra una PostgreSQL aislada local y validan los
flujos principales: autenticación y permisos por rol/módulo, ventas con descuento de stock y
múltiples pagos, devoluciones con límite máximo, movimientos de inventario, búsqueda por imagen
(accesos, límites de subida y campos protegidos) y la caché de permisos.

Se comprobó de manera explícita la **concurrencia**: ventas y movimientos simultáneos mantienen el
stock positivo (una operación gana y la otra es rechazada, sin registros duplicados), lo que avala
el diseño transaccional con bloqueos de fila. La **integridad** de los datos quedó verificada con
reconstrucción limpia del esquema (6/6 migraciones, estado up to date, con el único residual
deliberado del enum `RequestStatus`). Con todo lo anterior, la **Etapa 6 (Testing Backend) queda
cubierta por completo** (matriz R6.1–R6.16 en PASS), el backend compila y buildea sin errores, y
la suite queda lista para prevenir regresiones en los siguientes cambios.

---

## Apéndice — Comparación informativa con el frontend

El repositorio no contiene un documento independiente de testing frontend; el registro de Erika en
`PLAN_TRABAJO_ERIKA_ROSS.md` (Etapa 7, entrada del historial) consigna 57 tests con Vitest. Para la
comparación se contaron los tests **reales** presentes actualmente en el código del frontend:

| Suite | Framework | Tests |
|---|---|---:|
| Frontend (Erika) | Vitest | 69 |
| Backend (Ross) | Node.js `node:test` (nativo) | 51 |

> La cifra 69 es la cantidad real encontrada en los archivos de test del frontend al momento de
> este documento (`LoginPage` 12, `PublicProductsPage` 10, `PublicProductsPage.searchImage` 11,
> `SalesPage` 12, `services/api` 8, `stores/authStore` 16 = 69); difiere de los 57 registrados en el
> historial del plan, lo que refleja la adición posterior de pruebas. Ambas suites son
> independientes y no comparten framework.