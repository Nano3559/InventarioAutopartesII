# AUDITORÍA DE IMPLEMENTACIÓN — IA Y VISIÓN POR COMPUTADORA

Sistema: RepuestoPro (inventario y ventas de autopartes).
Base para: `PLAN_IMPLEMENTACION_IA_VISION.md` (FASE 0: plan + auditoría).
Tipo de auditoría: **solo lectura**. No se ejecutaron migraciones, instalaciones, deploys ni modificaciones de código ni de base de datos.

> **Nota de estado (vigente):** esta auditoría describe el punto de partida, cuando
> el proveedor de visión simulado (`MockVisionProvider`, `VISION_MODE`) formaba
> parte del diseño. **Hoy no existe en el runtime**: el único proveedor es
> `HttpVisionProvider` (HTTP real contra `ia-service`) y, sin `VISION_IA_URL`, la
> API responde `503 VISION_NO_DISPONIBLE`. Las menciones a "mock" en las secciones
> siguientes son históricas. Ver `docs/FLUJO_VISION_IA.md`.

---

## 1. Resumen ejecutivo

El repositorio es sólido como base de integración (arquitectura modular, seguridad, validaciones, tests, transacciones con bloqueo), pero **no contiene ningún componente de visión por computadora** implementado:

- Existe búsqueda por imagen **funcional vía OCR** (tesseract.js en Node) tanto pública como interna.
- **No existe modelo de detección/clasificación de piezas, no existe servicio de IA, no existe dataset de imágenes de producto.**
- La cámara **web no está implementada** (solo `<input type="file">`); la cámara móvil tampoco se usa (solo galería con `expo-image-picker`).
- La compatibilidad por vehículo **es parcial**: no hay entidad `Vehicle`; marca/modelo/año viven como cadenas libres en `Product` con utilidades de rangos de año.
- Stock por sucursal **existe internamente** (`Inventory` por `Location`) pero **no se expone** en endpoints públicos (por seguridad).

**Clasificación del proyecto para el módulo de visión: `LISTO CON CAMBIOS PREVIOS`.** Las FASE 1 (cámara + contrato + mocks) y FASE 2 (servicio IA con mock) son viables de inmediato; las FASE 3–6 (dataset, entrenamiento, compatibilidad, fuentes externas) requieren trabajo previo de datos antes de poder ejecutarse con resultados reales.

---

## 2. Alcance y metodología

Se auditaron los tres subproyectos (backend, frontend, mobile), la base de datos, la infraestructura y la documentación existente, con evidencia por archivo. Se aplicaron las reglas:

- Todo hallazgo cita archivo/módulo como evidencia.
- Lo que no fue verificable se marca **`NO VERIFICADO`**.
- No se dedujeron versiones: se leyeron los `package.json`.
- No se ejecutaron deploys, migraciones ni instalaciones.

---

## 3. Inventario del repositorio

```text
backend/     API Express + Prisma + PostgreSQL (TypeScript)
frontend/    SPA React + Vite + TailwindCSS
mobile/      App Expo (React Native)
docs/        Documentación (incl. el plan y esta auditoría)
docker-compose.yml   (PostgreSQL 16 local)
AGENTS.md, README.md, PLAN_TRABAJO_ERIKA_ROSS.md
```

Evidencia: estructura raíz, `docs/STACK_*.md`.

---

## 4. Stack backend (verificado en `backend/package.json`)

- TypeScript `^5.5.4`, Express `^4.21.0`, Prisma `^5.19.0` + `@prisma/client`.
- `bcryptjs` (contraseñas), `jsonwebtoken` `^9.0.2` (JWT HS256).
- `helmet` `^8.3.0`, `cors` `^2.8.5`, `express-rate-limit` `^8.7.0`.
- `express-validator` `^7.2.0` (validación), `multer` `^1.4.5-lts.1` (uploads).
- `tesseract.js` `^7.0.0` + `@tesseract.js-data/eng` `^1.0.0` (OCR ya integrado).
- `xlsx` `^0.18.5` (importaciones Excel), `node-cron` `^4.6.0` (job de reabastecimiento).
- Pruebas: Node `node:test` vía `tsx` (`test`, `test:integration`, `test:all`, `test:coverage`).

20 módulos en `backend/src/modules/` (auth, users, products, inventory, locations, sales, wholesale, movements, payments, returns, requests, costs, suppliers, prices, reports, customers, dashboard, permissions, notifications, public) + capas `shared/` (middlewares, utils, types) y `config/`.

---

## 5. Stack frontend (verificado en `frontend/package.json`)

- React `^18.3.1`, Vite `^5.4.2`, TypeScript `^5.5.4`, TailwindCSS `^3.4.10`.
- `react-router-dom` `^6.26.1`, `zustand` `^4.5.5`, `axios` `^1.7.5`.
- `react-hot-toast`, `lucide-react`, `recharts`, `xlsx`, `html2canvas`/`jspdf`.
- Pruebas: Vitest `^2.1.9` + Testing Library; build `tsc -b && vite build`.

Rutas (ver `frontend/src/App.tsx`): flujo público (`/`, `/contacto`, `/productos`, `/productos/:id`) sin token; panel protegido `/panel` con `RoleRoute` por módulo. **No existe ninguna ruta/página de captura de cámara.**

---

## 6. Stack mobile (verificado en `mobile/package.json`)

- Expo `~51.0.0`, React Native `0.74.5`, React `18.2.0`.
- `expo-camera` `~15.0.0`, `expo-image-picker` `~15.0.0`, `expo-file-system` `~17.0.0`.
- `@react-navigation/native` + `native-stack`, `axios`, AsyncStorage.
- Sin scripts de test/typecheck (solo `start`/`android`/`ios`/`web`).

Pantallas: `LoginScreen`, `HomeScreen`, `InventoryScreen`, `SalesScreen`, `ScannerScreen` (`mobile/src/navigation/AppNavigator.tsx`).

---

## 7. Infraestructura y despliegue

- PostgreSQL local: `docker-compose.yml` (`postgres:16-alpine`, puerto 5432).
- Backend Dockerfile: `node:20`, `npm install`, `prisma generate`, `npm run build`, boot `prisma migrate deploy && node dist/server.js` (backend/deploy confirmado).
- Fallo: `docker-compose.yml` **no despliega el backend**, solo la BD local.
- Vercel: ahora **existe** `frontend/vercel.json` (`buildCommand: npm run build`, `outputDirectory: dist`, framework `vite`, rewrites SPA). Root directory esperado: `frontend/`.
- API de producción declarada (no verificable en runtime): `VITE_API_URL=https://inventarioautopartesii-production-cacf.up.railway.app/api` (`frontend/.env.production`).
- `docs/STACK_INFRASTRUCTURE.md` (sección "Vercel") dice *"no hay `vercel.json`"* — **desactualizado**: el archivo ya existe. Hallazgo documental.
- CI/CD: **no hay** `.github/workflows` en el repositorio; despliegue manual/documentado. `NO VERIFICADO` si existen pipelines fuera del repo.

---

## 8. Modelo de datos (Prisma) — `backend/prisma/schema.prisma`

20 modelos y 5 enums verificado. Relevantes para IA:

- `Product`: `itemCode` (único), `manufacturer`, `name`, `brand`, `model`, `year` (String), `detail`, `detalles` (calidad), `oemCode`, `factoryCode`, **`image String?` (URL)**, `price1`, `price2`, `wholesalePrice`, `cost`, `categoryId` (nullable).
- `Category`: tabla plana `name` + `products[]`. Sin jerarquía.
- `Inventory`: `productId`, `locationId`, `stock`, `minStock`, `@@unique([productId, locationId])`, `@@index([locationId])`.
- `Location`: `name`, `type` (`ALMACEN` | `TIENDA`), `address`.
- `Movement`, `ProductRequest`, `RequestHistory`, `Sale`, `SaleItem`, `Payment`, `Return`, `Customer`, `Supplier`, `Cost`, `Importer`, `ProductImporter`, `RoleModel`, `User`, `AuditLog`, `Notification`.
- Enums: `Role`, `LocationType`, `SaleType`, `PaymentMethod`, `RequestStatus`.

**No existe entidad `Vehicle`, ni tabla de compatibilidad (marca/modelo/año ↔ producto), ni almacenamiento binario de imágenes.** Las imágenes de producto son cadenas URL.

---

## 9. Catálogo de productos

- CRUD completo (solo ADMIN): `backend/src/modules/products/products.routes.ts` (`POST /`, `PUT /:id`, `DELETE /:id`).
- Listado con filtros (`search`, `brand`, `manufacturer`, `model`, `year`, `oemCode`, `factoryCode`, `categoryId`, `locationId`) y paginación saneada (`parsePagination`). Filtro de categorías por rol TIENDA vía `columnConfig.__categorias`.
- Catálogo público en `public.routes.ts`: `GET /products`, `GET /products/:id`, filtros progresivos `brand → model → year` (`/filters`, `/filters/models`, `/filters/years`), `GET /importers`.
- Disponibilidad pública: agregada y tipificada (`Disponible` / `Pocas unidades` / `Consultar disponibilidad`) según umbrales (`>10`, `>0`) — **nunca expone stock exacto ni por sucursal** (ver `serializeProductoPublico` en `searchImage.service.ts`).
- Semilla de datos: ~65 productos reales con marca/modelo/año de rango en `backend/prisma/seed-data.ts` (Toyota Hilux, Nissan Frontier, Mazda CX-5, Ford Ranger, Honda Civic, Hyundai Tucson, etc.). Categorías: Frenos, Motor, Suspensión, Eléctrico, Filtros, Carrocería, Transmisión.

**Conclusión:** el catálogo es utilizable para Opción 1 (imagen → categoría → productos); los datos de marca/modelo/año existen pero son texto libre.

---

## 10. Compatibilidad por vehículo

- Filtros existentes por `brand` / `model` / `year` con lógica de rangos de año (`backend/src/utils/yearRanges.ts`: formatos `"13-15"`, `"13"`, `"13-"`, combinaciones `/`; `yearRangesOverlap` para intersección).
- **Faltantes para compatibilidad robusta:** entidad `Vehicle`, relación vehículo↔producto, validación de catálogos de marcas/modelos (valores son cadenas libres), y fuentes externas de compatibilidad.
- Personalización: `oemCode` y `factoryCode` permiten emparejamiento por referencia del fabricante (muy valioso para visión de etiquetas/códigos).

**Estado: `PARCIAL / NO LISTO` para Opción 2 sin trabajo previo de normalización de datos (WB-6).**

---

## 11. Búsqueda por imagen actual (OCR) — `backend/src/modules/products/searchImage.service.ts`

- Endpoints:
  - Público: `POST /api/public/search-image` (`public.routes.ts`), con `ocrPublicLimiter` (5/15 min/IP) → `imageUpload` → OCR. Serializa con `serializeProductoPublico` (sin `price2`, `wholesalePrice`, `cost`, `totalStock`, `locations`).
  - Interno: `POST /api/products/search-image` (`products.routes.ts`), `authenticate` → `ocrAuthenticatedLimiter` (20/15 min/usuario) → `imageUpload` → OCR. Respuesta con `serializeProductoInterno` (incluye `price2`, `totalStock`, `locations`).
- `imageUpload`: multer memoria, máx 5 MB, 1 archivo, solo MIME `image/jpeg|png|webp`.
- OCR: worker Tesseract reutilizable con `@tesseract.js-data/eng` local (sin descargas por request), cola de serialización, límite de 50 productos y ranking por coincidencias en `name/brand/model/itemCode/oemCode/factoryCode/detail`, tope 20 resultados.
- Consumidores:
  - Web público: `frontend/src/pages/PublicProductsPage.tsx` (input file → `/public/search-image`).
  - Móvil autenticado: `mobile/src/screens/ScannerScreen.tsx` (galería → `/products/search-image`). Exige login.

**Activo reutilizable:** OCR de texto en imagen (leer etiquetas/códigos). **No realiza detección de objetos ni clasificación de piezas por forma.**

---

## 12. Inventario y stock por sucursal

- Modelo `Inventory` por `(productId, locationId)` (stock + minStock) — fuente de verdad.
- Endpoint interno `GET /api/inventory/product/:productId` devuelve `stockTotal` + detalle por `Location` (`inventory.routes.ts`).
- `GET /api/products/:id` devuelve `stockByLocation` (**exige token**; ADMIN/INVENTARIO con vista global, TIENDA solo su propia tienda, rol desconocido sin ubicación → 403). Antes era `optionalAuth` y sin token entregaba el stock global; el catálogo anónimo es `/api/public/*`.
- Reporte `GET /api/reports/inventory` agrupa por ubicación con estados AGOTADO/BAJO/OK.
- Movimientos: `Transaction` con `SELECT ... FOR UPDATE` y `upsert` de destino; solo `ALMACEN → TIENDA` (`movements.routes.ts`).
- **El catálogo público NO expone stock por sucursal** (decisión de seguridad documentada en AGENTS.md y en las serializaciones). El endpoint público de visión mantiene el campo `disponibilidadPorSucursal` **por compatibilidad de contrato pero siempre vacío**, para no filtrar `locationId`, `nombre` ni `tipo` de las sedes a un visitante anónimo; el desglose por sede y el stock exacto quedan solo en el endpoint interno autenticado. Para el flujo de "recojo en sucursal" (WB-7/WB-8) el selector de entrega sigue funcionando porque se alimenta de `entrega.sucursales`, que solo lista sedes, no existencias.

**Estado: `LISTO` internamente; el contrato público de disponibilidad es el nivel agregado. Cualquier detalle público por sede requiere un contrato nuevo aprobado.**

---

## 13. Ventas, mayoristas, devoluciones, solicitudes

- Ventas: `sales.routes.ts` — venta normal (tipo `NORMAL`), transacción con bloqueo pesimista, deduplicación de ítems, validación de pagos (total = subtotal de items), auto-generación de solicitud de reabastecimiento al llegar a 0, nota de venta HTML imprimible.
- Mayoristas: `wholesale.routes.ts` — venta tipo `MAYOR`; **aquí** se usan campos de entrega: `paraQuien`, `lugarEntrega`, `datosFactura`, `formaPago`.
- Devoluciones: `returns.routes.ts` (módulo existe; flujo documentado).
- Solicitudes: `requests.routes.ts` + `RequestHistory` (traslados almacén→tienda).
- Pagos: métodos `EFECTIVO|QR|TRANSFERENCIA|CREDITO`.

**Relevancia IA:** el e-commerce "recojo/delivery" público **no existe** (la venta es punto de venta con usuario autenticado). WB-8 deberá construirse sobre el modelo de venta sin romper la transacción actual.

---

## 14. Flujo recojo/delivery actual

- No existe carrito/checkout/cotización pública.
- No existe tabla/estado de delivery.
- Existen solo campos de texto de entrega para venta MAYOR (`Sale.paraQuien`, `lugarEntrega`, `datosFactura`, `formaPago`).
- Disponibilidad por sucursal solo interna (ver sección 12).

**Estado: `NO LISTO` — requiere diseño e integración nueva (WB-8) manteniendo la invariante de la transacción de venta.**

---

## 15. Autenticación, roles y permisos — `backend/src/shared/middlewares/auth.ts`

- `authenticate`/`optionalAuth`: JWT HS256; payload `userId/email/role/locationId`.
- `authorize(...roles)` para rutas estáticas; `authorizeModule(module)` con caché `rolePermissionCache` (TTL 60 s) e invalidación manual en `permissions.routes`.
- `requireTiendaLocation` (TIENDA sin ubicación → 403) y `blockTienda`.
- `config/index.ts`: JWT_SECRET fail-fast (>=16 chars, rechaza `secret-key`/`secret`).
- Roles del seed: `ADMIN` (usa `*`), `TIENDA` (permisos `ventas/inventario/solicitudes/devoluciones` + categorías restringidas), `INVENTARIO` (`movimientos/inventario/solicitudes`).

**Relevancia IA:** los nuevos endpoints de visión autenticados deberán decidir si se protegen con `authorize("ADMIN","TIENDA","INVENTARIO")` o un módulo `authorizeModule("vision")`. El rol de caché permite invalidar cambios de permisos.

---

## 16. Validación de entradas — `backend/src/shared/middlewares/validate.ts`

- `validate` (express-validator) + helpers `parseId`, `parsePositiveInt`, `parsePositiveDecimal`, `parseString`.
- `parsePagination` (`shared/utils/pagination.ts`) sane al fin de página/limit (nunca NaN/negativos).
- Uso real parcial (mix): algunos módulos (movements) usan los helpers; otros usan validación manual inline. Para el contrato DTO de visión se recomienda fijar una sola estrategia (TC-1).

---

## 17. Manejo de errores — `backend/src/shared/middlewares/errorHandler.ts`

Central y exhaustivo: `LIMIT_FILE_SIZE`, `LIMIT_UNEXPECTED_FILE`, `INVALID_FILE_TYPE`, JSON inválido, JWT inválido/expirado, y Prisma `P2025/P2002/P2003/P2014` → códigos HTTP correctos. El resto → 500 genérico (no filtra información). `isPrismaClientError` (`shared/utils/errors.ts`) usado en ventas/movimientos para ocultar errores internos.

---

## 18. Rate limiting — `backend/src/shared/middlewares/rateLimit.ts`

- `generalLimiter`: 300 req / 15 min / IP (aplica a toda la API tras `/health`).
- `loginLimiter`: 10 / 15 min / IP.
- `ocrPublicLimiter`: 5 / 15 min / IP (endpoint público OCR).
- `ocrAuthenticatedLimiter`: 20 / 15 min / usuario (vía `req.user.userId`).

**Relevancia IA:** para visión (más costosa que OCR) habrá que definir límites nuevos (público ~5/15 min/IP, autenticado ~20/15; ajustables). Puede reutilizarse el patrón del keyGenerator.

---

## 19. CORS y Helmet — `backend/src/app.ts`

- `helmet()` activo.
- `cors` con `origin: [config.frontendUrl, config.mobileUrl]`, `credentials: true` (origen restringido).
- `trust proxy` = 1 solo en producción (corrige `req.ip` tras proxy en Railway).
- Log de cada request: `method`, `path` (sin query string), `status`, `ms`, `ip` — buena práctica de no filtrar parámetros sensibles en logs (`app.ts:46–55`).
- Health check `GET /api/health`.

**Relevancia IA:** el servicio de visión, si se implementa como microservicio, debe ser **interno** (llamado solo por backend o por red privada), no público, y quedar fuera del CORS del frontend.

---

## 20. Logs y trazabilidad

- Logger JSON en `shared/utils/logger.ts` (stdout/stderr) reutilizable para el servicio IA.
- `AuditLog` (modelo) registra cambios con `oldValue/newValue` (ya usado en inventario) → base para trazabilidad de "compatibilidad consultada/fuente".
- `Notification` (modelo) existe → útil para "disponibilidad / resultado de búsqueda por imagen" sin cambios de schema.

---

## 21. Pruebas backend (actuales)

- Scripts: `test` (unit `*.test.ts`), `test:integration` (`*.itest.ts` con `--test-force-exit`), `test:all`, `test:coverage` (`backend/package.json`).
- En sesiones previas verificadas: 28 unit + 23 integración (51 total), cobertura líneas ~79.5 %, ramas ~87.3 % (documentado en `docs/TESTING_BACKEND.md`). **No se re-ejecutó en esta auditoría (solo lectura)**.

**Base existente para TC-3 (pruebas de integración backend con mock de visión).**

---

## 22. Pruebas frontend (actuales)

- Vitest configurado; existe `frontend/src/pages/__tests__/PublicProductsPage.searchImage.test.tsx` (cubre el flujo actual de búsqueda por imagen).
- En sesiones previas verificadas: 69/69 tests Vitest pasan; `tsc -b` y `npm run build` salen 0. **No se re-ejecutó en esta auditoría (solo lectura).**

**Base para WB-3 (cliente HTTP de visión) y WB-10 (E2E con mock).** No hay tests de cámara porque no existe componente.

---

## 23. Cámara web (frontend) — estado

- **No existe** `navigator.mediaDevices.getUserMedia()` en el código frontend (se verificó por búsqueda: sin coincidencias).
- El único input de imagen actual es `<input type="file" accept="image/jpeg,image/png,image/webp">` en `PublicProductsPage.tsx:343–358`, con validación de MIME y 5 MB en el cliente.
- Frontend corre sobre Vite (dev en localhost / prod en Vercel HTTPS). `navigator.mediaDevices` requiere contexto seguro: **HTTPS** en prod (OK con Vercel) y `localhost` en dev (OK) — la exigencia de contexto seguro se cumple, pero **falta el componente de captura (WB-2)**.

---

## 24. Cámara móvil (Expo) — estado

- `expo-camera` está instalado (`mobile/package.json`) **pero no se usa**: `ScannerScreen.tsx` usa `expo-image-picker.launchImageLibraryAsync` (galería) y sube por `FormData` a `/products/search-image` (endpoint autenticado).
- No hay captura en vivo con `CameraView` ni modo continuo.
- Mobile exige sesión (solo usuarios autenticados); el flujo público de búsqueda por imagen está **solo en web**.

**Estado: `NO LISTO` para captura con cámara real; `LISTA` la mecánica de subida multipart (MIME/tamaño/nombre de archivo) que se reutilizará (WB-2/WB-4).**

---

## 25. Imágenes de producto y dataset — hallazgo crítico

- `Product.image` es **URL string opcional** (`schema.prisma:73`).
- **No existe endpoint de subida o gestión de imágenes de producto** (solo se asigna un string en `POST/PUT /products`; los archivos se suben solo para *búsqueda* por imagen, no para el catálogo).
- El backend **no sirve archivos estáticos** de imágenes (no hay `express.static` en `app.ts`).
- Semilla: `backend/prisma/seed-data.ts` **no define `image`** en ningún producto; el script `backend/prisma/enrich-data.ts` fija `image: null` (línea 39).
- La UI usa placeholder SVG por categoría (`frontend/src/components/public/ProductImage.tsx`) cuando no hay imagen.

**Consecuencia: no hay dataset de fotos de piezas en el sistema → la FASE 3 del plan (CV-1…CV-3: inventariar/capturar/etiquetar) parte de cero y requiere captura colaborativa.** Este es el bloqueador de mayor impacto para el modelo YOLO.

---

## 26. Estado de las fases del plan (0–10)

| Fase | Estado | Observación |
| ---- | ------ | ----------- |
| FASE 0 (plan + auditoría) | ✅ Lista | Plan y auditoría publicados (este documento). |
| FASE 1 (cámara + contrato + mocks) | 🟡 Lista para iniciar | Reusar `imageUpload`, `validate`, `errorHandler`, rate limiting; crear `CameraCapture` web + DTO + mocks. |
| FASE 2 (servicio IA mínimo) | 🟡 Lista para iniciar con mock | Falta servicio Python/mock + proxy backend. |
| FASE 3 (dataset/entrenamiento) | 🔴 No lista | Sin imágenes de producto (sección 25). |
| FASE 4 (imagen→categoría→catálogo) | 🟡 Parcial | Catálogo/filtros listos; falta detección. |
| FASE 5 (vehículo + compatibilidad) | 🔴 No lista | Falta normalizar datos y (para Opción 2) fuentes externas. |
| FASE 6 (fuentes externas) | 🔴 No lista | No existe `CompatibilityProvider`. |
| FASE 7 (stock por sucursal) | 🟡 Parcial | Listo internamente; falta contrato público seguro. |
| FASE 8 (recojo/delivery) | 🔴 No lista | No existe flujo público de venta/elección de sucursal. |
| FASE 9 (pruebas/hardening) | 🟡 Por construir | Infraestructura de tests lista; hay que agregar casos de visión. |
| FASE 10 (facial) | 🔴 Solo arquitectura | Por diseño, posterior. |

---

## 27. Requisitos previos antes de implementar (cambios previos)

1. **Dataset de imágenes de producto** (captura/import + política de almacenamiento y URLs). Bloquea CV-3/entrenamiento.
2. **Normalización/completado de datos de vehículo** (marcas, modelos, años, OEM de forma consistente; opcional entidad/envío de compatibilidad). Bloquea Opción 2 robusta (WB-6).
3. **Contrato DTO + mocks de visión** consensuado entre P1/P2 (TC-1/TC-2) y estrategia única de validación de inputs.
4. **Componente de cámara web** (`CameraCapture`, getUserMedia + HTTPS) y decisión de cámara móvil (captura vs galería) (WB-2).
5. **Contrato público seguro de disponibilidad por sucursal** (sin filtrar stock exacto) y diseño del flujo recojo/delivery (WB-7/WB-8).
6. **Proxy backend → servicio IA** con retry/timeout/fallback-mock y rate limits dedicados a visión (WB-4/TC-3/TC-4/TC-5).

---

## 28. Matriz de hallazgos

Severidad: CRÍTICO / ALTO / MEDIO / BAJO / INFORMATIVO.

| # | Severidad | Hallazgo | Evidencia | Impacto en IA |
| - | --------- | -------- | --------- | ------------- |
| H1 | CRÍTICO | No existe dataset de imágenes de producto (sin subida, sin static, seeds sin `image`). | `schema.prisma:73`, `products.routes.ts` (image como string), `seed-data.ts`, `enrich-data.ts:39`, `ProductImage.tsx` | Bloquea entrenamiento YOLO (CV-3) y evaluaciones reales. |
| H2 | ALTO | No existe servicio/módulo de visión; la búsqueda actual es solo OCR+texto. | `searchImage.service.ts`, `products.routes.ts`, `public.routes.ts` | Todo el reconocimiento de categorías es trabajo nuevo (CV-2…CV-6). |
| H3 | ALTO | Compatibilidad por vehículo solo en cadenas libres de `Product`; sin entidad ni fuentes externas. | `schema.prisma` (Product), `yearRanges.ts` | Opción 2 limitada hasta normalizar datos (WB-6) y conectar fuentes (TC-6). |
| H4 | ALTO | Cámara web no implementada (solo `<input type="file">`). | `PublicProductsPage.tsx:343–358`; búsqueda `getUserMedia` = 0 | WB-2 es 100 % trabajo nuevo. |
| H5 | ALTO | Cámara móvil sin captura en vivo (`expo-camera` instalado pero sin usar). | `mobile/package.json`, `ScannerScreen.tsx:51–69` | El flujo móvil de visión debe definir captura real (o validar galería como MVP). |
| H6 | ALTO | Stock por sucursal no expuesto públicamente (por seguridad) → recojo/delivery sin base pública. | `serializeProductoPublico`, `public.routes.ts:98–127`, `inventory.routes.ts` | WB-7/WB-8 requieren contrato seguro de disponibilidad. |
| H7 | ALTO | Rate limiting para visión no definido; hoy solo OCR/auth. | `rateLimit.ts` | Riesgo de abuso en endpoint de visión; definir límites dedicados. |
| H8 | MEDIO | Validación heterogénea entre módulos (mix express-validator/helpers). | `validate.ts`, `movements.routes.ts`, `products.routes.ts` | Centralizar la estrategia para el DTO de visión (TC-1). |
| H9 | MEDIO | Punto único OCR en Node (cola global) puede disputar CPU con un futuro servicio. | `searchImage.service.ts` (`ocrQueue`) | Considerar servicio separado para visión para evitar latencia. |
| H10 | MEDIO | Docs desactualizadas: `STACK_INFRASTRUCTURE.md` dice "no hay `vercel.json`" y ya existe. | `docs/STACK_INFRASTRUCTURE.md:35`, `frontend/vercel.json` | Documental; corregir para no confundirse en deploys. |
| H11 | MEDIO | Categorías sin jerarquía y `categoryId` nullable en `Product`. | `schema.prisma` (Category/Product), seed | Mapeo categoría→productos utilizable pero sin taxonomía. |
| H12 | BAJO | CORS restringido a frontend/mobile (`origin` fijo) — adecuado; el servicio IA debe ser interno. | `app.ts:39–42` | Confirma que la IA debe llamarse backend→IA, no público. |
| H13 | BAJO | `AuditLog` y `Notification` disponibles para trazabilidad/notificaciones de visión. | `schema.prisma` | Reutilizables sin migración. |
| H14 | INFORMATIVO | No hay CI/CD en el repo; despliegue manual. `NO VERIFICADO` si hay pipelines externos. | `.github` ausente | Para FASE 9 conviene añadir CI de pruebas (opcional). |
| H15 | INFORMATIVO | Frontend build prod apunta a Railway; Vercel sirve el SPA con rewrites. | `frontend/.env.production`, `frontend/vercel.json` | Flujo demo funcionando sobre HTTPS (requisito de cámara). |

---

## 29. Matriz de preparación

Clasificación: `LISTO` (se usa tal cual) / `LISTO CON CAMBIOS PREVIOS` (ajustes antes de usar) / `NO LISTO` (falta construir).

| Área | Clasificación | Evidencia | Nota |
| ---- | ------------- | --------- | ---- |
| Cámara web (frontend) | NO LISTO | sin `getUserMedia` | Requiere `CameraCapture` (WB-2). |
| API / backend (contrato, validación, upload, errores, rate limit) | LISTO CON CAMBIOS PREVIOS | `validate.ts`, `upload.ts`, `errorHandler.ts`, `rateLimit.ts`, `app.ts` | Reutilizar `imageUpload`, agregar límites de visión y proxy IA. |
| Producto (catálogo/búsqueda) | LISTO | `products.routes`, `public.routes` | Opción 1 lista para integrar categoría→catálogo. |
| Vehículo / compatibilidad | NO LISTO para Opción 2 | `schema.prisma` (sin Vehicle), `yearRanges.ts` | Requiere normalizar datos + fuentes externas (WB-6/TC-6). |
| Inventario / stock por sucursal | LISTO (interno) / NO LISTO (público) | `inventory.routes`, `reports.routes`, `public.routes` | Endpoint público seguro de disponibilidad por decidir (WB-7). |
| Imágenes / dataset | NO LISTO | `schema.prisma:73`, seeds, `ProductImage.tsx` | Fase de dataset (CV-1…CV-3) parte de cero. |
| Servicio IA (modelo/inferencia) | NO LISTO | no existe | Construir con mock primero (CV-6/WB-4/TC-2). |
| Búsqueda externa (CompatibilidadProvider) | NO LISTO | no existe | Diseñar TC-6; sin APIs registradas. |
| Reconocimiento facial | NO LISTO (solo arquitectura futura) | `auth.ts`, `schema.prisma` | Auth JWT/roles son la base reutilizable; cifrado/embeddings por diseñar (CV-9). |

---

## 30. Arquitectura objetivo recomendada y conclusiones

### Arquitectura objetivo recomendada

```text
                    FRONTEND (web HTTPS / mobile Expo)
                              │
                     CameraCapture (getUserMedia) / expo-camera
                              │  FormData imagen
                              ▼
                    BACKEND (Node/Express) — orquestador
                              │
      ┌───────────────────────┴────────────────────┐
      │                                            │
      ▼                                            ▼
  Módulo visión (proxy, validación,            Catálogo / Inventario /
  rate limit, retry/timeout/mock)              disponibilidad por sucursal
      │                                            │
      ▼                                            │
  Servicio IA (interno, no público)                │
  FastAPI + OpenCV + YOLO (o mock)                 │
      │   /vision/detect, /vision/classify          │
      └──────────────► Rankear candidatos ◄─────────┘
                            │
                  ┌─────────┴──────────┐
                  ▼                    ▼
          Motor de compatibilidad   (tesseract.js OCR ya en Node,
          (catálogo + fuentes       para lecturas de etiquetas/
           externas trazables)      códigos OEM si aplica)
                  ▼
          Stock por sucursal → recogida / delivery
```

Reglas clave del diseño recomendado:

1. **Un único orquestador: el backend Node actual.** No exponer el servicio de IA al público; Proxy+timeout+retry+fallback-mock (WB-4).
2. **Modo "mock-first"**: P1 y P2 pueden avanzar en paralelo contra mocks deterministas (TC-2) sin bloquearse (clave anti-bloqueo del plan).
3. **Reutilización máxima**: `imageUpload` (MIME/tamaño), `validate`, `errorHandler`, `rateLimit` (patrón), `parsePagination`, logger JSON, `AuditLog`/`Notification`.
4. **Seguridad**: endpoints internos con JWT+rol (o módulo `vision` vía `authorizeModule`); público con límite dedicado; eliminar imagen temporal tras procesar; no exponer stock exacto público.
5. **Compatibilidad honesta**: sin inventar; toda recomendación trazable a catálogo interno o fuente externa (regla del plan y del AGENTS.md). Hoy solo hay catálogo interno → Opción 1 primera; Opción 2 como evolución.
6. **Fases**: mantener orden 1→9 del plan; FASE 3+ depende de completar dataset y normalización de vehículo.

### Conclusiones

- **Puntos fuertes heredados:** modularidad (20 módulos), seguridad (JWT, helmet, CORS, rate limit, fail-fast), robustez transaccional (FOR UPDATE), validación y errores centralizados, tests unitarios/integración, OCR ya funcional, catálogo con filtros y rangos de año, stock por sucursal interno.
- **Bloqueadores reales (en orden):** (1) dataset de imágenes inexistente → entrenamiento YOLO; (2) datos de vehículo sin normalizar → Opción 2; (3) cámara web/móvil sin implementar; (4) disponibilidad/stock público y recojo-delivery sin contrato/flujo; (5) no hay servicio de IA ni fuentes externas (esperado, es lo que se va a construir).
- **Verifiabilidad:** todo lo anterior se corroboró en código; lo que no es verificable en el repositorio (estado runtime de Railway/Vercel, credenciales, despliegues) se marcó `NO VERIFICADO`.

---

*Documento de auditoría (FASE 0). Fin de la fase: no se implementó ninguna funcionalidad. Siguiente paso del plan: FASE 1.*

---

## Anexo A. Estado de implementación posterior a la FASE 0 (WB-1…WB-10, TC-1…TC-6)

Estado al 2026-09-21. El texto anterior es la auditoría base (solo lectura); este anexo registra el avance real posterior:

- **WB-4 / TC-1 / TC-2 / TC-4 / TC-5 (backend visión):** módulo completo en `backend/src/modules/vision/` (contrato, normalize, config `VISION_MODE` con resolución explícita, categorías/aliases, disponibilidad por umbral, compatibilidad por marca/modelo/año, provider mock/http con `AbortSignal.timeout(8000)`, service con serialización pública vs interna) y endpoint `POST /api/vision/detectar` (interno, TIENDA ve solo su sucursal) + endpoints públicos. Rate limits dedicados en `shared/middlewares/rateLimit.ts`. Tests: **76 unit + 55 integración** (incluye 40 unit + 15 itest de visión, con cobertura de rate limit 429) en verde, `tsc` y `npm run build` limpios.
- **WB-2 / WB-9 (frontend visión):** `CameraCapture` (getUserMedia + canvas → File) y `VisionResultsPanel` (resultados, vehículo, entrega recoger/delivery) creados; `PublicProductsPage` integrado con el botón "Buscar por cámara" y ambos modales. **92 tests Vitest** en verde (69 previos + 23 nuevos de visión: 4 cámara + 8 panel + 4 página + 7 visionApi), `tsc -b` y `npm run build` limpios.
- **WB-10 (E2E con IA):** ver `docs/FLUJO_VISION_IA.md`. Suite de prueba completa: cámara → endpoint público → categoría → catálogo → disponibilidad → selección. El proveedor simulado del runtime se eliminó: las pruebas hablan por HTTP real con un `ia-service` de test (`src/testing/fakeIaServer.ts`) y fijan por código los escenarios `default` / `ninguna` / `baja_confianza` / `categoria_desconocida` / `caida` / `timeout`.
- **Pendientes (fuera del alcance de Ross):** dataset e imágenes (CV-1…CV-4), entrenamiento del modelo real y umbral oficial (CV-5/CV-6/hito H2), facial (CV-9/FASE 10). El flujo productivo necesita conectar `VISION_IA_URL` al servicio real una vez exista (Erika). Ya no aplica `VISION_MODE=http`: el proveedor es siempre HTTP real.

---

# ANEXO — ESTADO POST-IMPLEMENTACIÓN ROSS

> Auditoría de cierre 2026-09-21. Verifica cada criterio del plan contra el código real (no solo contra tests).
> Convención de estados: `COMPLETA` / `PARCIAL` / `BLOQUEADA EXTERNA` / `PENDIENTE`. Los hallazgos H1–H15 se clasifican como `RESUELTO` / `MITIGADO` / `PENDIENTE ERIKA` / `PENDIENTE DATOS` / `PENDIENTE EXTERNO` / `FUERA DE ALCANCE ROSS`.

## A. Estado WB (trabajo de Ross)

| ID | Criterio del plan | Evidencia actual | Estado | Falta |
| -- | ----------------- | ---------------- | ------ | ----- |
| WB-1 | Relevamiento de arquitectura con inventario de endpoints/modelos por archivo. | `docs/AUDITORIA_IMPLEMENTACION_IA_VISION.md` (secciones 1–31), `docs/STACK_*.md`. | **COMPLETA** | — |
| WB-2 | Cámara web (getUserMedia HTTPS, fotograma único, permisos, responsive). | `frontend/src/components/camera/CameraCapture.tsx` + 4 tests. | **COMPLETA** | — |
| WB-3 | Cliente HTTP frontend (multipart, errores, cancelación, DTO). | `frontend/src/services/visionApi.ts`, `frontend/src/types/vision.ts` + 7 tests directos. | **COMPLETA** | — |
| WB-4 | Endpoints backend adaptadores (validación, proxy IA, timeout, fallback mock). | `backend/src/modules/vision/vision.routes.ts`, `vision.provider.ts`, `vision.config.ts` + 15 itest (400/401/403/422/429/503/504/200, >5 MB). | **COMPLETA** | Retry automático del provider HTTP (el flujo es foto puntual; el timeout de 8 s acota la ventana). |
| WB-5 | Imagen → categoría → lista de productos del catálogo. | `vision.service.ts` `generarRespuestaVision` + `categoryMapping.ts` (identidad + aliases, sin inventar). | **COMPLETA** | — |
| WB-6 | Compatibilidad por vehículo con ranking baseline. | `compatibility.ts` (`yearRanges`, score marca/modelo/año, `verificada` solo con evidencia), `base_datos_interna`. | **COMPLETA** (baseline) | Opción 2 completa requiere normalizar datos de vehículo y fuentes externas (H3/PENDIENTE DATOS). |
| WB-7 | Stock por sucursal (público seguro, interno exacto). | `availability.ts` + serialización pública/interna en `vision.service.ts`; itest ADMIN vs TIENDA. | **COMPLETA** | — |
| WB-8 | Flujo recogida/delivery (solo integración). | `VisionResultsPanel.tsx` (modalidad + sucursales con stock + cantidad/entrega), `entrega` en la respuesta, borrador público→venta (`saleDraft.ts`) prellenado en `SalesPage` y campos opcionales `paraQuien/lugarEntrega/datosFactura/formaPago` persistidos en `POST /api/sales` (R6.17/R6.18 + tests frontend). | **COMPLETA** | — (decisión: la venta sigue siendo punto de venta autenticado; no se creó e-commerce público, ver AUDITORÍA 13–14). |
| WB-9 | UX de resultados (carga/vacío/error, no inventar compatibilidad). | `VisionResultsPanel.tsx` + 8 tests. | **COMPLETA** | — |
| WB-10 | Pruebas E2E del servicio IA por HTTP real. | `docs/FLUJO_VISION_IA.md` + suites (backend 110 unit + 130 itest, frontend 110) en verde. | **COMPLETA** | — |

## B. Estado TC (trabajo compartido)

| ID | Criterio del plan | Evidencia actual | Estado | Falta |
| -- | ----------------- | ---------------- | ------ | ----- |
| TC-1 | Contrato de detección (DTO) con una sola fuente de verdad y validación. | `backend/src/modules/vision/contract.ts` (runtime validation → 503), tipos espejo `frontend/src/types/vision.ts`. | **COMPLETA** | — |
| TC-2 | Dobles deterministas del servicio IA. | Implementado como `MockVisionProvider` + `VISION_MODE`, **luego eliminado del runtime**. Hoy solo existe el doble HTTP de test `src/testing/fakeIaServer.ts`. | **SUPERADA** | El proveedor real es único (`HttpVisionProvider`); sin `VISION_IA_URL` responde 503. |
| TC-3 | Pruebas de integración backend contra el servicio IA. | `vision.routes.itest.ts`, hoy contra un `ia-service` HTTP de test. | **COMPLETA** | — |
| TC-4 | Manejo de errores uniforme con códigos. | `vision.errors.ts` (400/422/503/504 + codigo), frontend `CODIGOS_POR_STATUS`. | **COMPLETA** | — |
| TC-5 | Seguridad transversal de imágenes. | `imageUpload` reutilizado (MIME/5MB/1 archivo, memoria sin archivos temporales), `authenticate`+`requireTiendaLocation`, limiters dedicados. | **COMPLETA** | — |
| TC-6 | Abstracción de fuentes externas con trazabilidad. | `CompatibilityProvider`/`BaseDatosInternaProvider`/factory + interfaz `ProveedorExternoCompatibilidad` (fuente, fecha, confianza, timeout, cache, fallback); interno trazable (`base_datos_interna`). | **COMPLETA** | Integraciones reales `APIFabricante`/`APIDistribuidor`/`BúsquedaWebControlada` — no existen APIs externas registradas (H3/PENDIENTE EXTERNO). |

## C. Estado hallazgos H1–H15

| # | Sever. | Hallazgo | Estado inicial | Estado actual | Evidencia | Responsable |
| - | ------ | -------- | ------------- | ------------- | --------- | ----------- |
| H1 | CRÍTICO | No existe dataset de imágenes de producto. | CRÍTICO | **PENDIENTE DATOS** | Sin subida de imágenes de producto, seeds sin `image`, sin `express.static` (sin cambios). | Erika/Datos |
| H2 | ALTO | No existe servicio/módulo de visión; hoy solo OCR+texto. | ALTO | **MITIGADO** — módulo de visión completo con proxy HTTP y `ia-service` real implementado (71 tests), auth por secreto (`X-Vision-Key`) y **fallback silencioso a mock eliminado** (sin URL en modo remoto responde 503). Pendiente: red privada y umbral oficial (CV-8). | Ross (integración) |
| H3 | ALTO | Compatibilidad solo en cadenas libres; sin entidad ni fuentes externas. | ALTO | **MITIGADO** — baseline `base_datos_interna` funcional y trazable; Opción 2 completa pendiente de datos normalizados y APIs reales. | Ross (baseline) + Datos/Externo |
| H4 | ALTO | Cámara web no implementada (solo `<input type=file>`). | ALTO | **RESUELTO** — `CameraCapture` con `getUserMedia` + canvas → File + estados de permiso. | Ross |
| H5 | ALTO | Cámara móvil sin captura en vivo (Expo). | ALTO | **PENDIENTE ERIKA** | Mobile sin modificar (responsabilidad de Erika). | Erika |
| H6 | ALTO | Stock por sucursal no expuesto públicamente. | ALTO | **RESUELTO** — contrato público seguro por umbral: el público recibe solo el nivel agregado y `disponibilidadPorSucursal` **vacío** (sin `locationId`/`nombre`/`tipo` de sede); el desglose por sede y el stock exacto quedan en el endpoint interno autenticado. `availability.ts` + `vision.service.ts` + itest que afirma la ausencia de identificadores de sede. | Ross |
| H7 | ALTO | Rate limiting de visión no definido. | ALTO | **RESUELTO** — `visionPublicLimiter` 5/15 min/IP y `visionAuthenticatedLimiter` 20/15 min/usuario + test 429. | Ross |
| H8 | MEDIO | Validación heterogénea entre módulos. | MEDIO | **MITIGADO** (visión) — el DTO de visión centraliza con `parseString`/`validate` + validación runtime del contrato; el resto de módulos queda fuera del alcance de Ross. | Ross (visión) |
| H9 | MEDIO | OCR de un solo punto disputa CPU con futuro servicio IA. | MEDIO | **MITIGADO** — la visión usa provider independiente (mock/http), no comparte el worker ni la cola OCR. | Ross |
| H10 | MEDIO | Docs desactualizadas: "no hay `vercel.json`". | MEDIO | **RESUELTO** — `docs/STACK_INFRASTRUCTURE.md` corregido (fila Vercel con `vercel.json`). | Ross |
| H11 | MEDIO | Categorías sin jerarquía y `categoryId` nullable. | MEDIO | **PENDIENTE DATOS** — sin cambios de schema (no autorizado); `categoryMapping` ya excluye productos sin categoría y no inventa equivalencias. | Datos/Erika |
| H12 | BAJO | CORS restringido; el servicio IA debe ser interno. | BAJO | **RESUELTO** — el backend orquesta backend→IA (nunca pública); CORS sin cambios (correcto). | Ross |
| H13 | BAJO | `AuditLog`/`Notification` disponibles para trazabilidad. | BAJO | **MITIGADO** — trazabilidad de compatibilidad en la propia respuesta (`fuente`, `consultadoEn`, `metodologia`) en `compatibility.ts`; `AuditLog` no utilizado (sin necesidad demostrada). | Ross |
| H14 | INFORMATIVO | No hay CI/CD en el repo. | INFORMATIVO | **PENDIENTE EXTERNO** — fuera del alcance de Ross; no se crearon pipelines. | Externo |
| H15 | INFORMATIVO | Frontend prod en Railway/Vercel HTTPS (requisito cámara). | INFORMATIVO | **RESUELTO** — `vercel.json` + `.env.production`; contexto seguro (HTTPS/localhost) cubierto para `getUserMedia`. | Ross |

## D. Errores encontrados y corregidos en esta ronda de auditoría

1. **Typo en escenario mock** `categoria_desconocida`: "Intrumento raro XXYZ" → "Instrumento desconocido XXYZ" (`vision.provider.ts`).
2. **`console.error` en `vision.routes.ts`** reemplazado por `logger.error` centralizado (consistencia con el resto del backend; sin exponer stack en logs).
3. **Falta de cobertura del límite de rate (H7)**: agregado test `público: alcanzado el límite de 5/15 min por IP → 429` en `vision.routes.itest.ts` (itest pasa 15/15).
4. **`visionApi.ts` sin tests directos (WB-3)**: nueva suite `frontend/src/services/__tests__/visionApi.test.ts` (7 tests: multipart, vehículo, escenario mock, mapeo de errores 422/429/503/504, red) — antes el cliente solo se cubría vía mocks de componente.
5. Corrección de aserción en test de red de `visionApi` (el diseño previsto devuelve el mensaje genérico "Error al buscar por visión.", no "Intenta nuevamente").

## E. Resultados finales de pruebas (re-ejecutados en esta auditoría)

- Backend: `npx tsc --noEmit` ✅ · `npm test` 58/58 ✅ · `npm run test:integration` 38/38 ✅ (incl. 15 de visión) · `npm run build` ✅.
- Frontend: `npx tsc -b` ✅ · `npx vitest run` 92/92 ✅ (4 cámara + 8 panel + 4 página + 7 visionApi + 69 previos) · `npm run build` ✅.
- Gerente: sin cambios de Prisma ni esquema; no aplica `prisma migrate`.

*Fin del anexo. Documento de auditoría (FASE 0) mantiene su contenido histórico; este anexo registra el estado post-implementación de Ross.*

---

## ANEXO B — ESTADO POST-INTEGRACIÓN (2026-09-28)

Redacción: Ross. Rama `ross`, HEAD `d385377` (tras merges de Erika PR #40/#41/#42), árbol limpio antes de esta ronda; Git se mantiene de solo lectura (OpenCode no commitea).

### B.1 Servicio IA real (ia-service) — verificado

* `ia-service` (FastAPI + Python) implementa `/vision/health` y `/vision/detect` con el **contrato idéntico** al del backend (`backend/src/modules/vision/contract.ts`): `{detecciones:[{categoria,confianza,boundingBox}], consultadoEn}`.
* Schemas Pydantic (`schemas/vision.py`) validan tipos/SB y límites del `boundingBox` (0..1, `x+width<=1`, `y+height<=1`), imagen obligatoria y máximo de archivo.
* El backend envía a la IA el **MIME real** del archivo (`vision.provider.ts`), reflejando el tipo real, no `image/jpeg` fijo.
* Modo HTTP del backend activo **solo si existe `VISION_IA_URL`**. El fallthrough silencioso a mock **quedó eliminado** en esta ronda: `vision.config.ts` (`resolverVisionMode`) decide de forma explícita y, en producción sin URL, el provider responde **503 `VISION_NO_DISPONIBLE`** en vez de entregar detecciones simuladas. Timeout 8 s, `confianzaMinima` 0.55.
* Autenticación backend → IA añadida: header **`X-Vision-Key`**, variable **`VISION_IA_KEY`** (mismo nombre en backend e `ia-service`, prefijo `VISION_`). `/vision/health` queda abierto para sondas; `/vision/detect` y `/vision/classify` exigen el secreto (`secrets.compare_digest`, comparación en tiempo constante). 5 pruebas nuevas en `ia-service/tests/test_auth.py`.
* `categoryMapping.ts` cubre las 8 clases del modelo YOLO: `brake_pad`, `brake_rotor`, `brake_caliper` → Frenos; `alternator` → Eléctrico; `oil_filter`, `air_filter` → Filtros; `radiator` → Motor; `headlight` → Carrocería.

### B.2 Dataset y entrenamiento

* En Git **solo hay manifests CSV** (`ia-service/datasets/`: `dataset_manifest.csv`, `review_manifest.csv`, `annotation_batch_manifest.csv`). Las imágenes (`raw/`, `processed/`, `annotations/`) **no están versionadas** (`.gitignore` excluye `ia-service/datasets/*` salvo esos tres CSV). Única excepción para artefactos: el checkpoint `ia-service/models/repuestopro_yolo11n_v3_webcam_robust.pt` (5 471 507 bytes).
* `dataset_manifest.csv` = **1344 imágenes** en 8 clases: alternator 200, brake_pad 198, brake_rotor 186, brake_caliper 184, radiator 179, oil_filter 179, headlight 169, air_filter 49. Fuentes: `gpiosenka/car-parts-40-classes` v3 (1295) y `khaledchawa/car-engine-bay-pictures` v2 (49).
* `annotation_batch_manifest.csv` = **749 filas**: **700 en `PENDING`** con `has_ground_truth=false` y `label_path` vacío; solo **49 `ANNOTATED`**, todas de `air_filter`. `review_manifest.csv` = 80 filas `APPROVED`, pero con `review_label_path` vacío salvo las 10 de `air_filter`.
  → **Existe ground truth real para 1 de las 8 clases.** La versión anterior de este anexo decía "0 anotaciones, 100% sin anotación", lo cual era incorrecto.
* Desbalanceo conocido: `air_filter` con ~49 ejemplos vs. ~179–200 en el resto. ~93% del batch de anotación sigue pendiente (**PENDIENTE DATOS/ERIKA**).
* **Corrección de métrica (importante).** El `mAP50 = 0.489` de CV-5 corresponde al **baseline v1** (P 0.514 / R 0.490 / mAP50-95 0.326, 68 imágenes y 86 boxes en TEST; solo 4 clases presentes), **no al modelo desplegado**. El checkpoint en servicio es **V3** (`CV4_MODELO_V3_WEBCAM_ROBUST.md`): **val mAP50 0.741** (91 imágenes, 8 clases) y **test mAP50 0.775** (85 imágenes, **solo 3 clases**: alternator, radiator, headlight).
* **Por qué FASE 3 sigue PARCIAL notwithstanding el mAP:** (a) V3 se evaluó en test sobre 3 clases; (b) `brake_pad`/`brake_rotor`/`brake_caliper` no tienen GT auditado, así que nunca se pudieron medir; (c) `air_filter` tiene **0 filas de entrenamiento** en V3 y aun así reporta mAP50 0.590 (val) / 0.778 (test), combinación que exige verificación — la documentación admite fotos multiclase (`air_filter + alternator + radiator`), lo que puede contaminar la métrica; (d) `processed/` no está en el repo, por lo que **las métricas de V3 no son reproducibles desde este repositorio**.
* CV-7 validó el **E2E real** backend ↔ FastAPI ↔ PostgreSQL. **CV-8 (umbral oficial de confianza) sigue PENDIENTE** (documentado en CV-7 §11). CV-9 (facial) no implementado por diseño.

### B.3 Correcciones aplicadas en esta ronda (post-integración)

| ID | Sever. | Hallazgo | Corrección |
| -- | ------ | -------- | ---------- |
| P0-7 | CRÍTICO | `POST /api/sales` y `/api/wholesale` tomaban `unitPrice` del cliente (carrito/API podía alterar el precio) | El **servidor fija el precio** desde BD: NORMAL usa `product.price2` (minorista, con fallback a `price1` si no hay minorista definido); MAYOR usa `product.wholesalePrice ?? price1`; `unitPrice` del cliente se ignora; `throw` si `<=0`. `saleItems.ts` se conserva como validación de entrada (defensa en profundidad). **Nota:** la semántica del catálogo es `price1` = mayorista y `price2` = minorista (`prices.routes.ts`, `InventoryPage.tsx`, seeds), por eso la venta al público cobra `price2`: usar `price1` hacía que el POS (que compra por defecto en tier minorista) pagara un importe distinto al que el servidor calculaba y toda venta terminaba en 400. |
| P1-2 | ALTO | `SalesPage.tsx` llamaba `GET /api/categories` (no existe) → filtro muerto con error silencioso | Ahora usa `GET /api/products/filters` (contrato real) + `toast.error` en fallo. |
| P2-1 | MEDIO | `PublicProductsPage` / `PublicProductDetailPage` sin `.catch` → errores de red mostraban "no hay productos / no encontrado" (engañoso) | Estado `errorBusqueda`/`error` con mensaje distinto en fallo; fechas en diplomas mantienen el estado vacío real. |
| P2-2 | MEDIO | Mobile: MIME solo por extensión del nombre de archivo; 401 limpiaba AsyncStorage pero no el estado React (sesión "fantasma") | `ScannerScreen`: MIME real desde `asset.mimeType` (fallback extensión). `api.ts`: `setOnUnauthorized` callback invocado tras 401; `AppNavigator` registra `() => setUser(null)` → navega a Login. |
| P0-lat-1 | ALTO (latente) | JWT en `localStorage` (frontend) y `AsyncStorage` (mobile) | Sin sinks XSS detectados hoy; documentado, se mantiene (riesgo controlado, no se rediseña ahora). |
| P1-3 | ALTO | Mobile `ScannerScreen` sigue en OCR legacy (`/products/search-image`) | **SIGUE ABIERTO → PENDIENTE ERIKA** (decisión: fixes mínimos seguros en esta ronda; migración a visión queda fuera). |
| P1-5 | ALTO | ia-service sin autenticación (solo red interna) | **PARCIALMENTE MITIGADO** — se añadió auth por secreto compartido (`X-Vision-Key` / `VISION_IA_KEY`) en `/vision/detect` y `/vision/classify`, con `compare_digest`; `/vision/health` sigue abierto a propósito para sondas. Pendiente el transporte: el servicio debe quedar en red privada y con TLS si sale de ella. |
| P1-6 | CRÍTICO | Una notificación a INVENTARIO fallida **dentro** de la transacción de venta la abortaba: la venta se respondía **500** aunque el producto y el stock fueran válidos | El helper `notificarInventarioSolicitud` **nunca propaga el error** (registra y devuelve 0) y, en ventas y mayorista, la notificación se emite **después del commit**. Una venta válida nunca se cae por un aviso. |
| P1-7 | ALTO | Los bordes de los reportes se calculaban en la zona horaria del **servidor** (`new Date("YYYY-MM-DD")` + `setHours`): con el servidor en UTC+X una venta de la noche del último día quedaba **fuera** del reporte de ese día, y en devoluciones el corte era la medianoche del `endDate` (se perdía el día final entero) | Nuevo helper `shared/utils/rangoFechas.ts` (`rangoFechasNegocio`) que convierte el día a intervalo de instantes UTC en la zona del negocio (`America/La_Paz`, la misma del job de reposición). Aplicado en ventas, devoluciones y reportes, con 8 tests unitarios y 3 de integración. |
| P1-8 | ALTO | `replenishJob` comprobaba la disponibilidad contra **un** almacén arbitrario (`findFirst`): si ese almacén no tenía stock pero otro sí, la reposición se descartaba | Suma el stock de **todos** los almacenes, igual que ventas y mayorista. Además el aviso a INVENTARIO se agrupa en `createMany` y va en `try/catch` para no abortar el resto del job. |
| P1-9 | ALTO | Reporte mensual: un producto **sin factura en el mes** se costeaba a 0, inflando la utilidad | Fallback al último costo conocido vigente al cierre del periodo (`allCosts`/`lastKnownCost`). Cubierto por test de integración. |
| P1-10 | ALTO | Reporte diario: ventas y devoluciones se truncaban silenciosamente (100 y 20 filas por defecto), de modo que los totales no cuadraban con el período elegido | Tope explícito de 1000 en ambos listados (parseo centralizado, sin paginación abierta) y filtros `startDate`/`endDate` en devoluciones, que antes no existían. El frontend ya envía el mismo rango a ventas y devoluciones. |
| P2-3 | MEDIO | La suite de integración era intermitente: los archivos `*.itest.ts` comparten una BD y el runner los ejecutaba **en paralelo**, generando `P2003` y fallos cruzados (incluida una venta que caía a 500) | `test:integration` y `test:all` usan `--test-concurrency=1`. Además el `cleanup` borra costos/historial por usuario y reintenta el borrado final de usuarios. **3 corridas consecutivas idénticas.** |
| P0-8 | CRÍTICO | El POS quedaría **inutilizable**: el servidor cobraba la venta al público con `price1` (mayorista) mientras el carrito cobra `price2` (minorista) por defecto, así que el importe pagado nunca coincidía con el total y **toda venta terminaba en 400** | La venta NORMAL cobra `price2` (minorista) con fallback a `price1` si el producto no tiene minorista definido. Verificado contra `prices.routes.ts`, `InventoryPage.tsx`, `SalesPage.tsx` y `seed-data.ts`, que coinciden en la semántica `price1`=mayorista / `price2`=minorista. `createProduct` de tests acepta `price1`/`price2` por separado y hay tests con `price1 != price2` (antes `price1 == price2` en todos los fixtures, por lo que la regresión era invisible). |
| P1-11 | ALTO | `secrets.compare_digest()` con `str` no ASCII lanza `TypeError` → el endpoint de visión respondía **500** en vez de 401 (DoS de información con una credencial basura) | La comparación se hace sobre bytes UTF-8, y la ausencia del header se rechaza por separado. Cubierto por tests que ejercitan la dependencia directamente (httpx no puede enviar headers no ASCII: los codifica en ASCII). |
| P1-12 | ALTO | `ia-service` quedaba **fail-open**: sin `VISION_IA_KEY` el servicio aceptaba inferencia de cualquiera, incluso declarándose en producción | `VISION_ENV=production` vuelve la autenticación **obligatoria**: sin secreto el servicio **falla cerrado** con 503 en `/vision/detect` y `/vision/classify` y lo reporta como ERROR al arrancar. En `development` se mantiene el modo abierto con advertencia (solo red interna). `/vision/health` sigue abierto a propósito para sondas. |
| P1-13 | ALTO | `GET /api/reports/monthly` **expone costos y utilidad a usuarios TIENDA**, aunque los costos están restringidos a ADMIN en el resto del sistema | **RESUELTO (backend + frontend)** — el backend limita `cost`/`utilidad`/`margen` a la allow-list `ROLES_CON_COSTOS` (ADMIN, INVENTARIO) en `sales`, `inventory`, `monthly` y `suppliers`, y acota el resto del reporte a la ubicación del usuario; el `ReportsPage` replica el mismo criterio con `puedeVerCostos = ["ADMIN","INVENTARIO"].includes(user.role)`, de modo que la UI no muestra `0.00` engañoso. El PDF mensual hereda el mismo `puedeVerCostos`. Verificado con `reports.itest.ts` y `ReportsPage.test.tsx`. |
| P1-14 | ALTO | El OCR legacy `POST /api/products/search-image` **no aísla por tienda**: un usuario TIENDA con cualquier credencial válida obtiene `totalStock` y `locations` con el stock exacto de **todas** las sucursales, incluidos los almacenes | **PENDIENTE — requiere cambio coordinado.** El aislamiento se aplica con `requireTiendaLocation` en las rutas, pero aplicarlo al router de productos afectaría también el listado de ADMIN. El arreglo correcto es acotarlo a esa ruta, lo que cambia el contrato que consumen mobile y el panel: requiere coordinar con Erika. |
| P2-4 | MEDIO | `?limit=2.7` (o cualquier decimal) llegaba a Prisma sin truncar y devolvía **500** en 11 listados; `?month=abc` construía `new Date(NaN, …)` y también daba 500 | Todos los listados usan `parsePagination` (entero + topes). `rangoMesNegocio` valida `YYYY-MM` y responde **400**; el contrato real del frontend (`year=YYYY&month=MM`) se conserva. Los límites de mes ahora se calculan en `America/La_Paz`. |
| P2-5 | MEDIO | `replenishJob` resucitaba solicitudes canceladas: leía el estado fuera de la transacción y escribía un historial con `previousStatus=PENDIENTE` falso; además la notificación iba dentro de la transacción (si fallaba, la activación se revertía para siempre) | La activación es un `updateMany` condicional por `status = PENDIENTE` **dentro** de la transacción (si no aplica, se omite), y la notificación se emite **después** del commit en `try/catch`. |
| P2-6 | MEDIO | `allCosts` del reporte mensual arrastraba **todo** el historial de `Cost` de la base, sin acotar | Se limita a los productos realmente vendidos en el periodo; si no hubo ventas no se consulta. |
| P2-7 | MEDIO | `/api/wholesale` (GET) seguía con el patrón de fecha antiguo (corte a medianoche del `endDate`, zona del servidor) | Migrado a `rangoFechasNegocio`, igual que ventas, devoluciones y reportes. |
| P2-8 | MEDIO | `cleanup` de tests no borraba `AuditLog` (FK a `User`) y, si fallaba a mitad, dejaba el pool de conexiones abierto affecting las suites siguientes | `AuditLog` se barre en cada intento del borrado de usuarios; el `cleanup` envuelve el trabajo en `try/finally` con `$disconnect`. |
| P2-9 | MEDIO | `vision.routes.itest.ts` importaba `@prisma/client` **antes** de `testing/helpers`: eso carga el `.env` (Neon remoto) y el guardián abortaba el archivo entero | `helpers` es ahora el primer import del proyecto, como exige su documentación. El guardián de URL local sigue activo (es la red de seguridad, no el bug). |
| P2-10 | MEDIO | El endpoint público de visión (`serializarPublico`) devolvía `disponibilidadPorSucursal` con `locationId`, `nombre` y `tipo` de cada sede, aunque el público no debe conocer la operación interna | **RESUELTO (backend) / PENDIENTE ERIKA (UI)** — el público recibe solo `disponibilidad` agregada y `disponibilidadPorSucursal` **vacío**; el itest afirma que ningún candidato público trae identificadores de sede. Efecto colateral aceptado: el bloque "sede: etiqueta" de `VisionResultsPanel` ya no se renderiza en el catálogo anónimo (guardado por `length > 0`, no rompe nada). Rediseñar ese detalle público requiere coordinar con Erika; el selector de entrega sigue funcionando con `entrega.sucursales`. |

### B.4 Re-ejecución de pruebas completa (post-integración)

Cifras vigentes, re-verificadas el **2026-09-29** con el código final de esta ronda.

* **Backend** — `npx tsc --noEmit` ✅ · `npm test` **99/99** ✅ · `npm run test:integration` **127/127** ✅ (1 corrida, no se tocó reposición/concurrencia) · `npm run test:all` **99 + 127 = 226/226** ✅ · `npm run test:coverage` **86.58 % líneas / 90.17 % ramas / 89.01 % funciones** ✅ · `npm run build` ✅.
  * Nota de reproducibilidad: los itests exigen `DATABASE_URL` local; `src/testing/helpers.ts` aborta la suite si la URL no es `127.0.0.1`/`localhost`, para no ejecutar pruebas destructivas contra Neon.
* **Frontend** — `npm test` (**vitest run**, ya no interactivo) **109/109** ✅ en 12 archivos · `npx tsc -b` ✅ · `npm run build` ✅ (chunk >500 kB preexistente). Quedan avisos `act(...)` de React (`PublicProductsPage`, `LoginPage`, `MemoryRouter`): ruido de estado asíncrono en tests, no afecta el resultado.
* **Mobile** — `npm run typecheck` ✅ · `npm test` **8/8** ✅ (se añadieron los scripts: la prueba del precio minorista `precioVenta` con el runner nativo de Node, sin añadir dependencias).
* **ia-service** — `pytest -q` **74 passed**, 1 warning conocido (`StarletteDeprecationWarning` de `httpx`/`TestClient`, ajeno al proyecto). Smoke real previo verificado: `/vision/health`, `/vision/detect` con checkpoint real (8 clases), MIME inválido y campo ausente.
* Mobile (flujo OCR legacy, documentado sin cambios): cámara/galería → validación de MIME (`jpeg|png|webp`) y 5 MB → `POST /api/products/search-image` (endpoint **autenticado**, contrato interno con `price1`/`price2`/`totalStock`/`locations`) → resultados. El interceptor de Axios adjunta `Authorization: Bearer`; un 401 limpia sesión y estado React (`setOnUnauthorized` → `setUser(null)` → Login). Nota: `expo-camera` está instalada pero `ScannerScreen` **solo** usa galería (`launchImageLibraryAsync`).

*Fin del Anexo B.*