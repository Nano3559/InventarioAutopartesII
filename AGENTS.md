# AGENTS.md — RepuestoPro / Inventario Autopartes II

Guía para asistentes de IA que trabajan en este repositorio.

## Propósito del proyecto

Sistema de gestión de inventario y ventas de autopartes (web + móvil) con roles de usuario, catálogo público, búsqueda por imagen (OCR), ventas, mayoristas, devoluciones, movimientos de stock, costos, precios, reportes y panel de administración.

## Estructura del repositorio

```text
backend/             API Express + TypeScript + Prisma + PostgreSQL
frontend/            SPA React + Vite + TailwindCSS
mobile/              App Expo (React Native)
docs/                Documentación del proyecto
PLAN_TRABAJO_ERIKA_ROSS.md   Plan oficial de tareas (leer antes de trabajar)
README.md            Documentación general
```

## Reglas Backend

* Stack: TypeScript, Express, Prisma, PostgreSQL. No se cambia de framework ni de ORM.
* Arquitectura modular: un router por dominio en `backend/src/modules/`; capas compartidas en `backend/src/shared/` (middlewares, types, utils).
* Usar middlewares centralizados: `authenticate`, `authorize`, `authorizeModule`.
* Respetar los contratos de respuesta existentes; la serialización protege datos sensibles (p. ej. el endpoint público de búsqueda por imagen jamás expone `price2`, `totalStock`, `locations` ni costos).
* Validar entradas con `express-validator` y la utilidad `validate`.
* Las actualizaciones de stock que involucran lectura + escritura deben protegerse dentro de la misma transacción (`$transaction` con bloqueo de fila cuando corresponda, como en movimientos).
* No se elimina funcionalidad existente ni se cambia arquitectura sin autorización.
* No modificar archivos fuera del alcance de la tarea asignada.

## Reglas Frontend

* Stack: React 18, TypeScript, Vite, TailwindCSS, React Router, Zustand, Axios.
* No romper el flujo anónimo del catálogo público.
* El token se envía vía interceptor de Axios; manejar errores con `toast.error(...)` o equivalente.
* Frontend es responsabilidad principal de Erika: no se modifica salvo que una tarea lo exija y se coordine.

## Reglas Mobile

* Stack: Expo (React Native), React Navigation, Axios, AsyncStorage, expo-camera/expo-image-picker.
* Mobile es responsabilidad principal de Erika: no se modifica salvo coordinación previa.
* El MIME real del archivo debe reflejar el tipo del archivo (no fijar siempre `image/jpeg`).

## Reglas Prisma y base de datos

* No modificar `backend/prisma/schema.prisma` sin revisar primero las migraciones existentes.
* No borrar ni reescribir migraciones existentes.
* Explicar cualquier migración antes de realizarla.
* No ejecutar `prisma migrate reset`, `db push` destructivo, `DROP`, `TRUNCATE` ni eliminación de datos sin autorización explícita.

## Reglas de seguridad

* No leer ni exponer secretos de forma innecesaria.
* No committear archivos `.env` reales.
* No mostrar el valor de `JWT_SECRET` ni de credenciales.
* No registrar contraseñas ni tokens en logs o documentación.
* No introducir dependencias innecesarias.

## Flujo de trabajo obligatorio

Toda tarea sigue:

```text
ANALIZAR → REPORTAR → APROBAR → IMPLEMENTAR → PROBAR → VALIDAR
```

* Analizar y reportar antes de implementar.
* Implementar solo lo aprobado.
* Probar (compilación, tests, build) y validar antes de dar por terminada una tarea.
* Mostrar al final: archivos modificados, archivos nuevos, `git status`, `git diff --stat` y resultados de pruebas.

## Git

> OpenCode no crea commits, pushes ni Pull Requests. Estos son realizados manualmente por Ross.

* No ejecutar `git add`, `git commit`, `git push`, `git merge`, `git rebase`, `git reset`, `git stash`, `git clean` ni crear Pull Requests.
* No usar force push.
* No rebase de historial publicado.
* No reset destructivo.
* No squash de commits existentes.
* No alterar el historial académico del proyecto.
* El flujo de ramas/PR está en `docs/GIT_CONVENTION.md`.

## Qué cosas NO modificar sin autorización

* `backend/prisma/schema.prisma` y migraciones.
* Contratos de API de endpoints existentes.
* Endpoints públicos que deben seguir accesibles sin token.
* Archivos de frontend/mobile (responsabilidad de Erika).
* Arquitectura general del proyecto.
* Cambios de seguridad globales (JWT, Helmet, rate limiting) sin seguir el plan de etapas.