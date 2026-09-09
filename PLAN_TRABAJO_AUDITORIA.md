# PLAN DE TRABAJO — AUDITORÍA MAESTRA
## InventarioAutopartesII

**Fecha:** 2026-09-08
**Integrantes:** Erika (frontend/mobile/docs) | Ross (backend/seguridad/BD)

---

## ETAPA 1 — Seguridad y Críticos

### ROSS

| ID | Tarea | Prioridad | Archivos | Estado |
|----|-------|-----------|----------|--------|
| R1.1 | Eliminar fallback `"secret-key"` en config/index.ts — exigir JWT_SECRET | CRITICAL | `backend/src/config/index.ts` | PENDIENTE |
| R1.2 | Forzar `algorithms: ["HS256"]` en `jwt.verify()` | CRITICAL | `backend/src/shared/middlewares/auth.ts` | PENDIENTE |
| R1.3 | Instalar `helmet` y configurar en `app.ts` | CRITICAL | `backend/src/app.ts`, `package.json` | PENDIENTE |
| R1.4 | Instalar `express-rate-limit` y configurar rate limiting global + por ruta | CRITICAL | `backend/src/app.ts`, `package.json` | PENDIENTE |
| R1.5 | Agregar `authenticate` a `POST /products/search-image` | CRITICAL | `backend/src/modules/products/products.routes.ts` | PENDIENTE |
| R1.6 | Agregar `uploads/` a `backend/.gitignore` | CRITICAL | `backend/.gitignore` | PENDIENTE |
| R1.9 | Verificar RequestStatus enum en BD (¿se ejecutó ALTER TYPE?) | MEDIUM | `schema.prisma`, BD | PENDIENTE |
| R1.10 | Reorganizar migración huérfana `add_seller_columnPrefs.sql` | HIGH | `backend/prisma/migrations/` | PENDIENTE |

### ERIKA

| ID | Tarea | Prioridad | Archivos | Estado |
|----|-------|-----------|----------|--------|
| E1.1 | Completar `.gitignore` raíz (uploads, IDE, OS, Expo, certs, temp, .env.production) | CRITICAL | `.gitignore` | PENDIENTE |
| E1.8 | Eliminar credenciales de `TAREAS_ERIKA_Y_ROSS.md:290` | MEDIUM | `TAREAS_ERIKA_Y_ROSS.md` | PENDIENTE |

---

## ETAPA 2 — Concurrencia e Integridad

### ROSS

| ID | Tarea | Prioridad | Archivos | Estado |
|----|-------|-----------|----------|--------|
| R2.1 | Agregar SELECT FOR UPDATE en `sales.routes.ts` | HIGH | `backend/src/modules/sales/sales.routes.ts` | PENDIENTE |
| R2.2 | Agregar SELECT FOR UPDATE en `wholesale.routes.ts` | HIGH | `backend/src/modules/wholesale/wholesale.routes.ts` | PENDIENTE |
| R2.3 | Consolidar PrismaClient a singleton (todos routes.ts + replenishJob.ts) | HIGH | `backend/src/config/database.ts`, todos routes | PENDIENTE |
| R2.4 | Agregar graceful shutdown en `server.ts` | MEDIUM | `backend/src/server.ts` | PENDIENTE |
| R2.5 | Verificar lógica de precios en mobile (price1 vs price2) | MEDIUM | `mobile/src/screens/SalesScreen.tsx` | PENDIENTE |

---

## ETAPA 3 — Frontend: Calidad y Seguridad

### ERIKA

| ID | Tarea | Prioridad | Archivos | Estado |
|----|-------|-----------|----------|--------|
| E3.1 | Configurar ESLint en frontend | MEDIUM | `.eslintrc.js`, `package.json` | PENDIENTE |
| E3.2 | Configurar Prettier en frontend | MEDIUM | `.prettierrc`, `package.json` | PENDIENTE |
| E3.3 | Configurar ESLint en backend | MEDIUM | `backend/.eslintrc.js` | PENDIENTE |
| E3.4 | Agregar toast.error a ~15 catches silenciosos críticos | HIGH | InventoryPage, SalesPage, ReportsPage | PENDIENTE |
| E3.5 | Eliminar catches vacíos restantes | HIGH | Múltiples páginas | PENDIENTE |
| E3.6 | Tipar `any` types — InventoryPage(7), SettingsPage(6), PricesPage(5) | HIGH | `InventoryPage.tsx`, `SettingsPage.tsx`, `PricesPage.tsx` | PENDIENTE |
| E3.7 | Tipar `any` types — ReportsPage(4), WholesalePage(4), SalesPage(3) | HIGH | `ReportsPage.tsx`, `WholesalePage.tsx`, `SalesPage.tsx` | PENDIENTE |
| E3.8 | Verificar price1 vs price2 en SalesPage | MEDIUM | `SalesPage.tsx` | PENDIENTE |

---

## ETAPA 4 — Documentación

### ERIKA

| ID | Tarea | Prioridad | Archivos | Estado |
|----|-------|-----------|----------|--------|
| E4.1 | Crear `README.md` completo | HIGH | `README.md` | PENDIENTE |
| E4.2 | Crear `frontend/.env.example` | MEDIUM | `frontend/.env.example` | PENDIENTE |
| E4.3 | Crear `mobile/.env.example` | MEDIUM | `mobile/.env.example` | PENDIENTE |
| E4.4 | Mover archivos .md de raíz a `docs/` | LOW | raíz → `docs/` | PENDIENTE |
| E4.5 | Crear `docs/ARCHITECTURE.md` | LOW | `docs/ARCHITECTURE.md` | PENDIENTE |
| E4.6 | Crear `.editorconfig` | MEDIUM | `.editorconfig` | PENDIENTE |

### ROSS

| ID | Tarea | Prioridad | Archivos | Estado |
|----|-------|-----------|----------|--------|
| R4.1 | Crear `backend/.env.example` completo | MEDIUM | `backend/.env.example` | PENDIENTE |
| R4.2 | Eliminar `fix_*.sql` de backend root | HIGH | `backend/fix_*.sql` | PENDIENTE |

---

## ETAPA 5 — Testing Backend

### ROSS

| ID | Tarea | Prioridad | Archivos | Estado |
|----|-------|-----------|----------|--------|
| R5.1 | Test: POST /auth/login (válidas/inválidas) | MEDIUM | `auth.test.ts` | PENDIENTE |
| R5.2 | Test: POST /auth/register (ADMIN puede, otros no) | MEDIUM | `auth.test.ts` | PENDIENTE |
| R5.3 | Test: POST /sales con descuento de stock | HIGH | `sales.test.ts` | PENDIENTE |
| R5.4 | Test: POST /sales concurrente (sobreventa) | HIGH | `sales.test.ts` | PENDIENTE |
| R5.5 | Test: POST /returns (válida/excede cantidad) | MEDIUM | `returns.test.ts` | PENDIENTE |
| R5.6 | Test: POST /movements (transferencia) | MEDIUM | `movements.test.ts` | PENDIENTE |
| R5.7 | Test: /movements concurrencia (FOR UPDATE) | HIGH | `movements.test.ts` | PENDIENTE |
| R5.8 | Test: authorizeModule (permisos por rol) | MEDIUM | `auth.test.ts` | PENDIENTE |
| R5.9 | Test: errorHandler (códigos Prisma) | LOW | `errorHandler.test.ts` | PENDIENTE |
| R5.10 | Test: replenishJob (solicitudes automáticas) | LOW | `replenishJob.test.ts` | PENDIENTE |

---

## ETAPA 6 — Testing Frontend/Mobile

### ERIKA

| ID | Tarea | Prioridad | Archivos | Estado |
|----|-------|-----------|----------|--------|
| E6.1 | Configurar vitest en frontend | MEDIUM | `vitest.config.ts`, `package.json` | PENDIENTE |
| E6.2 | Test: LoginPage (render, login exitoso/fallido) | MEDIUM | `LoginPage.test.tsx` | PENDIENTE |
| E6.3 | Test: SalesPage (agregar item, calcular total) | MEDIUM | `SalesPage.test.tsx` | PENDIENTE |
| E6.4 | Test: api.ts interceptor (token, 401 redirect) | LOW | `api.test.ts` | PENDIENTE |
| E6.5 | Test: authStore (login, logout, loadFromStorage) | LOW | `authStore.test.ts` | PENDIENTE |

---

## ETAPA 7 — Calidad y Mobile

### ERIKA

| ID | Tarea | Prioridad | Archivos | Estado |
|----|-------|-----------|----------|--------|
| E7.1 | Eliminar 3 dependencias no usadas en mobile | LOW | `mobile/package.json` | PENDIENTE |
| E7.2 | Corregir MIME type hardcoded en ScannerScreen | LOW | `mobile/src/screens/ScannerScreen.tsx` | PENDIENTE |
| E7.3 | Agregar ErrorBoundary global en mobile | LOW | `mobile/App.tsx` | PENDIENTE |
| E7.4 | Tipar navigation con NativeStackNavigationProp | LOW | HomeScreen, ScannerScreen | PENDIENTE |
| E7.5 | Eliminar rol filtering duplicado en HomeScreen | LOW | `mobile/src/screens/HomeScreen.tsx` | PENDIENTE |
| E7.6 | Agregar image size validation en ScannerScreen | LOW | `mobile/src/screens/ScannerScreen.tsx` | PENDIENTE |
| E7.7 | Corregir cart price1 → price2 en SalesScreen | MEDIUM | `mobile/src/screens/SalesScreen.tsx` | PENDIENTE |
| E7.8 | Agregar paginación en InventoryScreen y SalesScreen | MEDIUM | `InventoryScreen.tsx`, `SalesScreen.tsx` | PENDIENTE |

### ROSS

| ID | Tarea | Prioridad | Archivos | Estado |
|----|-------|-----------|----------|--------|
| R7.1 | Eliminar campo `detalles` duplicado de Product | LOW | `schema.prisma` | PENDIENTE |
| R7.2 | Agregar @@index en foreign keys consultados | MEDIUM | `schema.prisma` | PENDIENTE |
| R7.3 | Configurar logging con winston/pino | HIGH | `package.json`, `errorHandler.ts` | PENDIENTE |
| R7.4 | Reducir Decimal precision a DECIMAL(10,2) | LOW | `schema.prisma` | PENDIENTE |
| R7.5 | Agregar ON DELETE CASCADE donde corresponda | LOW | `schema.prisma` | PENDIENTE |
| R7.6 | Corregir score hardcodeado en search-image | LOW | `products.routes.ts` | PENDIENTE |
| R7.7 | Eliminar date redundante en modelos con createdAt | LOW | `schema.prisma` | PENDIENTE |

---

## ETAPA 8 — OpenCode, Agentes, CI/CD

### ERIKA

| ID | Tarea | Prioridad | Archivos | Estado |
|----|-------|-----------|----------|--------|
| E8.1 | Crear `.github/workflows/ci.yml` (typecheck + tests + build) | HIGH | `.github/workflows/ci.yml` | PENDIENTE |
| E8.2 | Crear `opencode.json` | LOW | `opencode.json` | PENDIENTE |
| E8.3 | Crear agente `backend-reviewer` | LOW | `.opencode/agent/` | PENDIENTE |
| E8.4 | Crear agente `frontend-reviewer` | LOW | `.opencode/agent/` | PENDIENTE |

### ROSS

| ID | Tarea | Prioridad | Archivos | Estado |
|----|-------|-----------|----------|--------|
| R8.1 | Crear `AGENTS.md` con convenciones del proyecto | HIGH | `AGENTS.md` | PENDIENTE |

---

## ETAPA 9 — Revisión Final (JUNTOS)

| ID | Tarea | Prioridad | Estado |
|----|-------|-----------|--------|
| J9.1 | Verificar compilación limpia (backend + frontend + mobile) | HIGH | PENDIENTE |
| J9.2 | Ejecutar todos los tests y verificar que pasan | HIGH | PENDIENTE |
| J9.3 | Verificar migraciones sincronizadas con schema | HIGH | PENDIENTE |
| J9.4 | Verificar frontend en navegador (login → ventas → reportes → export) | HIGH | PENDIENTE |
| J9.5 | Verificar mobile conecta backend (login → inventario → ventas) | HIGH | PENDIENTE |
| J9.6 | Revisar PR y merge a main | HIGH | PENDIENTE |
| J9.7 | Verificar deployment en Vercel y Railway | HIGH | PENDIENTE |
| J9.8 | Revisar que no hay credenciales expuestas | CRITICAL | PENDIENTE |

---

## RESUMEN

| | Erika | Ross | Total |
|---|---|---|---|
| **CRITICAL** | 1 | 6 | 7 |
| **HIGH** | 7 | 7 | 14 |
| **MEDIUM** | 13 | 14 | 27 |
| **LOW** | 9 | 8 | 17 |
| **TOTAL** | 30 | 35 | **65** |
