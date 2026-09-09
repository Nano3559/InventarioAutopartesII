# Stack de Infraestructura

Este documento distingue lo que es **comprobable en el repositorio** de lo que solo está **mencionado en la documentación del proyecto**. No se copian valores de `.env` ni credenciales.

## Arquitectura general (confirmada por el repositorio)

Monorepo con:

```text
backend/     API Express + Prisma + PostgreSQL
frontend/    SPA React + Vite
mobile/      Aplicación Expo (React Native)
docs/        Documentación
docker-compose.yml
```

## Infraestructura confirmada por archivos del repositorio

| Elemento                 | Evidencia                                             |
| ------------------------ | ----------------------------------------------------- |
| PostgreSQL local         | `docker-compose.yml`: servicio `db`, imagen `postgres:16-alpine`, puerto `5432`, volumen `pgdata`. |
| Prisma migrations        | `backend/prisma/migrations/` con historial desde `20260819182416_init` y varias migraciones posteriores (jul-2026/sep-2026) + ad-hoc (p. ej. `add_seller_columnPrefs.sql`). |
| Prisma generate/migrate/seed | Scripts en `backend/package.json` (`prisma:generate`, `prisma:migrate`, `prisma:seed`). |
| Build backend            | `tsc` → `dist/`; arranque `node dist/server.js`.      |
| Build frontend           | `tsc -b && vite build` (salida estática de Vite).      |
| Variables de entorno     | `backend/.env.example` (DATABASE_URL, JWT_SECRET, PORT, FRONTEND_URL, MOBILE_URL); `frontend/.env.example`; `mobile/.env.example`. Los archivos `.env` reales están en `.gitignore`. |
| Repositorio Git          | Ramas `main`, `ross`, `erika`; flujo PR descrito en `docs/GIT_CONVENTION.md`. |

## Servicios mencionados en la documentación pero NO verificables solo desde el código

| Servicio | Estado                                                   |
| -------- | -------------------------------------------------------- |
| Neon     | Mencionado en la documentación como hosting de PostgreSQL; no hay configuración Neon en el repositorio. |
| Railway  | Mencionado como hosting del backend (se indica definir `JWT_SECRET` real allá); no hay configuración Railway en el repositorio. |
| Vercel   | Mencionado como hosting del frontend; no hay `vercel.json`. |
| Docker en producción | Solo existe el `docker-compose.yml` para la base de datos local. |

Estos servicios deben tratarse como **supuestos documentales** hasta confirmarlos con configuración o URLs reales de deployment.

## Reglas de infraestructura

* No se exponen secretos ni se copian valores de `.env` en la documentación.
* No se eliminan ni se rescriben migraciones existentes.
* No se ejecutan `prisma migrate reset`, `db push` destructivos, `DROP` ni `TRUNCATE` sin autorización explícita.
* Cualquier cambio de infraestructura (nueva migración, hosting, variables de producción) se documenta antes de ejecutarse.