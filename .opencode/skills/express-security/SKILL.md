---
name: express-security
description: Use when auditing security of the Express/TypeScript backend: JWT, authentication, authorization, secrets, CORS, Helmet, rate limiting, uploads, validation, exposed data, and error handling. Reports findings by severity without applying changes.
---

# express-security

Revisa la seguridad del backend Express/TypeScript y reporta hallazgos por severidad. NO aplica cambios automáticamente.

## Checklist

* **Autenticación** — `authenticate`/`optionalAuth`: manejo de headers, tokens ausentes/malformados, expiración.
* **Autorización** — `authorize`, `authorizeModule`, roles ADMIN/TIENDA/INVENTARIO, rutas que deberían exigir rol y no lo hacen.
* **JWT** — algoritmo `HS256` explícito en `sign` y `algorithms` en `verify`; `JWT_SECRET` definido (sin fallback inseguro); expiración razonable.
* **Secretos** — secretos en `.env` no commiteados; ninguna credencial/valor de `JWT_SECRET` en docs, logs ni código versionado.
* **Validación** — `express-validator`/`validate` en entradas del usuario (body, params, query, archivos).
* **CORS** — orígenes permitidos (`config.frontendUrl`, `config.mobileUrl`), no `*`.
* **Helmet** — cabeceras de seguridad presentes (X-Content-Type-Options, X-Frame-Options, CSP, HSTS) y compatibles con el frontend/mobile.
* **Rate limiting** — límites para API general, login y OCR; claves correctas (IP y/o `req.user.userId`); no compartir límites entre usuarios.
* **Uploads** — Multer: tamaños máximos, MIME permitidos, archivos únicos, nombres, riesgo de abuso.
* **Exposición de datos** — endpoints públicos que filtren `price2`, `totalStock`, `locations`, costos o datos administrativos.
* **Errores** — no filtrar stack traces ni detalles internos; códigos HTTP coherentes (400/401/403/404/429/500).
* **Headers** — cabeceras sensibles (cache, referrer, server) en respuestas.
* **Abuso de endpoints costosos** — OCR y exportaciones grandes con límites independientes.
* **Logging sensible** — no registrar contraseñas, tokens ni secretos.

## Clasificación de hallazgos

* **Crítica** — vulnerabilidad explotable o fuga de datos sensibles.
* **Alta** — exposición que debe corregirse pronto (datos internos en rutas públicas, JWT sin algoritmo).
* **Media** — falta de mitigaciones estándar (Helmet, rate limiting) sin un vector directo demostrado.
* **Baja** — buenas prácticas opcionales o limpieza.

## Formato de salida

Por hallazgo:

```text
- Severidad: <crítica|alta|media|baja>
- Archivo: ...
- Zona/línea: ...
- Problema: ...
- Riesgo: ...
- Mitigación: ...
```

Al final: resumen ordenado por severidad y recomendaciones priorizadas.

## Reglas

* NO aplicar cambios automáticamente.
* Reportar y esperar aprobación antes de proponer correcciones.
* No exponer secretos ni valores de `JWT_SECRET` en los reportes.