# AUDITORÍA DE IMPLEMENTACIÓN — IA Y VISIÓN POR COMPUTADORA

Sistema: RepuestoPro (inventario y ventas de autopartes).
Base para: `PLAN_IMPLEMENTACION_IA_VISION.md` (FASE 0: plan + auditoría).
Tipo de auditoría: **solo lectura**. No se ejecutaron migraciones, instalaciones, deploys ni modificaciones de código ni de base de datos.

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
- `GET /api/products/:id` devuelve `stockByLocation` (solo ADMIN/roles internos; TIENDA ve únicamente su propia tienda).
- Reporte `GET /api/reports/inventory` agrupa por ubicación con estados AGOTADO/BAJO/OK.
- Movimientos: `Transaction` con `SELECT ... FOR UPDATE` y `upsert` de destino; solo `ALMACEN → TIENDA` (`movements.routes.ts`).
- **El catálogo público NO expone stock por sucursal** (decisión de seguridad documentada en AGENTS.md y en las serializaciones). Para el flujo de "recojo en sucursal" (WB-7/WB-8) hará falta definir un contrato público seguro (p. ej. disponibilidad por umbral o por tienda, sin stock exacto).

**Estado: `LISTO` internamente; `NO LISTO` para consumo público sin contrato nuevo de disponibilidad.**

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