# Stack Backend

Documentación basada en el repositorio real (`backend/package.json`, `backend/tsconfig.json`, `backend/prisma`, `docker-compose.yml`). No se documentan tecnologías supuestas.

## Resumen

| Área             | Tecnología / versión                                   |
| ---------------- | ------------------------------------------------------ |
| Lenguaje         | TypeScript (`^5.5.4`, `module: commonjs`, target ES2020) |
| Runtime          | Node.js (no fija `engines`; se ejecuta con `ts-node-dev`, `tsx` y `node dist/server.js`) |
| Framework        | Express `^4.21.0` (`@types/express ^4.17.21`)          |
| ORM              | Prisma `^5.19.0` (cliente `@prisma/client` + CLI `prisma`) |
| Base de datos    | PostgreSQL (local en `docker-compose.yml`: imagen `postgres:16-alpine`) |
| Validación       | `express-validator ^7.2.0` (+ utilidad `src/utils/validate.ts` y middleware `src/shared/middlewares/validate.ts`) |
| Autenticación    | `bcryptjs ^2.4.3` (hash/contraseñas) + `jsonwebtoken ^9.0.2` (JWT) |
| Subida de archivos | `multer ^1.4.5-lts.1` (importación Excel; búsqueda por imagen) |
| OCR              | `tesseract.js ^7.0.0` + datos de idioma `@tesseract.js-data/eng ^1.0.0` |
| Excel            | `xlsx ^0.18.5` (importación masiva de productos)       |
| Tareas programadas | `node-cron ^4.6.0` (job de reposición en `src/jobs/replenishJob.ts`) |
| CORS             | `cors ^2.8.5` (`@types/cors ^2.8.17`)                  |
| Variables de entorno | `dotenv ^16.4.5`                                      |
| Testing          | Node test runner vía `tsx --test "src/**/*.test.ts"`   |
| Build            | `tsc` → `dist/`; arranque `node dist/server.js`        |

## Scripts principales

| Script                   | Comando                                                |
| ------------------------ | ------------------------------------------------------ |
| `dev`                    | `ts-node-dev --respawn --transpile-only src/server.ts` |
| `build`                  | `tsc`                                                  |
| `start`                  | `node dist/server.js`                                  |
| `prisma:generate`        | `prisma generate`                                      |
| `prisma:migrate`         | `prisma migrate dev`                                   |
| `prisma:seed`            | `ts-node prisma/seed.ts`                               |
| `test`                   | `tsx --test "src/**/*.test.ts"`                        |
| `test:watch`             | `tsx --test --watch "src/**/*.test.ts"`                |

El script de seed está declarado en `"prisma": { "seed": "ts-node prisma/seed.ts" }`.

## Arquitectura modular observada

Organización por módulos de dominio dentro de `src/modules/`, con capas compartidas:

```text
backend/
├── src/
│   ├── server.ts                 # arranque HTTP + jobs
│   ├── app.ts                    # construcción de Express (CORS, JSON, rutas, errorHandler)
│   ├── config/                   # configuración (env: PORT, JWT_SECRET, DATABASE_URL, URLs)
│   ├── modules/                  # un router por dominio
│   │   ├── auth/                 # register, login, /me
│   │   ├── users/
│   │   ├── products/             # catálogo, importación Excel, search-image
│   │   ├── inventory/
│   │   ├── locations/
│   │   ├── sales/
│   │   ├── wholesale/
│   │   ├── movements/
│   │   ├── payments/
│   │   ├── returns/
│   │   ├── requests/
│   │   ├── costs/
│   │   ├── suppliers/
│   │   ├── prices/
│   │   ├── reports/
│   │   ├── dashboard/
│   │   ├── customers/
│   │   ├── notifications/
│   │   ├── permissions/
│   │   └── public/               # catálogo público y búsqueda por imagen pública
│   ├── shared/
│   │   ├── middlewares/          # auth, validate, errorHandler, etc.
│   │   ├── types/                # AuthRequest, AuthPayload
│   │   └── utils/                # yearRanges, saleItems, validate
│   └── jobs/                     # replenishJob (node-cron)
└── prisma/
    ├── schema.prisma
    ├── migrations/
    ├── seed.ts
    ├── seed-data.ts
    └── enrich-data.ts
```

## Middlewares y seguridad actual

* `src/shared/middlewares/auth.ts`: `authenticate`, `optionalAuth`, `authorize`, `authorizeModule`, `requireTiendaLocation`, `blockTienda`.
* `src/shared/middlewares/errorHandler.ts`: mapa de errores Multer/Prisma/JWT a respuestas HTTP.
* `src/shared/middlewares/rateLimit.ts`: `generalLimiter` (300/15min/IP), `loginLimiter` (10/15min/IP), `ocrPublicLimiter` (5/15min/IP) y `ocrAuthenticatedLimiter` (20/15min/usuario).
* Helmet (headers de seguridad) aplicado en `app.ts` antes de CORS y rutas.
* CORS limitado a `FRONTEND_URL` y `MOBILE_URL` desde `config`.
* JWT: fallback eliminado (la app falla al iniciar si `JWT_SECRET` falta o es inseguro) y algoritmo forzado a `HS256` en firma y validación.

## Variables de entorno (definidas en `backend/.env.example`)

`DATABASE_URL`, `JWT_SECRET`, `PORT`, `FRONTEND_URL`, `MOBILE_URL`.