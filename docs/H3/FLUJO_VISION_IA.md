# FLUJO_VISION_IA — Búsqueda por visión con el modelo real

Sistema: RepuestoPro. Objetivo: documentar el flujo visual (cámara → backend → `ia-service` → categoría → catálogo → stock → selección) y las pruebas que lo cubren **contra el modelo real de IA**.

> Histórico: este flujo antes se verificaba con un proveedor simulado en el runtime, activado por `VISION_MODE=mock` y por el header `x-vision-mock-scenario`. Ambos se eliminaron. No existe ninguna ruta en el runtime que entregue detecciones inventadas: si la IA no está disponible, la API responde 503.

## 1. Proveedor de visión (backend)

La configuración vive en `backend/src/modules/vision/vision.config.ts` (`resolverVisionModo`) y
solo hay un proveedor: `HttpVisionProvider`
(`backend/src/modules/vision/vision.provider.ts`), que llama a `ia-service` por HTTP real.

| `VISION_IA_URL` | `NODE_ENV` | ¿Requiere IA? | Comportamiento |
| --------------- | ---------- | ------------- | -------------- |
| sí              | cualquiera | no            | Modelo real (`POST <VISION_IA_URL>/vision/detect`) |
| no              | cualquiera | **sí**        | **503 `VISION_NO_DISPONIBLE`** |

- No hay variable `VISION_MODE`. El modo siempre es `http`.
- Sin `VISION_IA_URL` el endpoint falla cerrado con **503 `VISION_NO_DISPONIBLE`**, tanto en producción
  como en desarrollo: es un fallo explícito, nunca un resultado falso.
- El cliente no puede pedir una detección simulada: no existe header de escenario.
- El proveedor envía el secreto al servicio IA en el header `X-Vision-Key`, leído de
  `VISION_IA_KEY` (mismo nombre en backend y en `ia-service`). Si el servicio IA no tiene el
  mismo valor configurado, responde 401 y el backend traduce el error a **503 controlado**.

### Equivalencia entre escenarios de test y fallos reales

Las pruebas ya no inventan detecciones: levantan un `ia-service` de prueba real
(`backend/src/testing/fakeIaServer.ts`, un servidor HTTP local en `127.0.0.1`) y configuran su
comportamiento por código desde el test. Así se ejercita el mismo `fetch`, multipart y
`X-Vision-Key` que en producción.

| Escenario del doble | Respuesta de la API | Equivalente real |
| ------------------- | ------------------- | ---------------- |
| `default` | 200, detección `Frenos` confianza 0.94 + boundingBox, 3 candidatos | Detección válida |
| `baja_confianza` | 422 `VISION_BAJA_CONFIANZA` | Imagen poco clara |
| `ninguna` | 422 `VISION_NO_CLASIFICADA` | No se detecta pieza |
| `categoria_desconocida` | 200, candidatos `[]` + nota | Clase desconocida |
| `caida` | 503 `VISION_NO_DISPONIBLE` | IA caída |
| clave `X-Vision-Key` incorrecta | 503 `VISION_NO_DISPONIBLE` | Secreto desincronizado |
| `timeout` | 504 `VISION_TIMEOUT` | IA lenta (se respeta `VISION_TIMEOUT_MS`, 8 s por defecto) |
| `invalida` | 503 `VISION_RESPUESTA_INVALIDA` | Contrato roto en la respuesta |

## 2. Pasos del flujo E2E (documentados)

1. **Captura** — `CameraCapture` (web, `getUserMedia`) entrega un `File`. Sin permisos de cámara, el estado muestra "no disponible/denegado".
2. **Llamada** — `detectarVisionPublica(file, { vehiculo })` → `POST /api/vision/public/detectar` (multipart, MIME `jpeg|png|webp`, máx 5 MB).
3. **Detección** — el backend llama a `ia-service` (YOLO) y mapea la categoría detectada al catálogo.
4. **Catálogo** — productos de la categoría rankeados por score (verificación de compatibilidad + orden).
5. **Disponibilidad** — el endpoint público devuelve **solo el nivel agregado**
   (`DISPONIBLE`/`POCAS_UNIDADES`/`NO_DISPONIBLE`) calculado sobre el stock total: nunca
   stock exacto, nunca `price2` y **nunca el desglose por sede** (`disponibilidadPorSucursal`
   viaja vacío, porque cada entrada lleva `locationId`, `nombre` y `tipo` de la sede, que son
   datos internos de la operación). El desglose por ubicación y el stock exacto quedan
   reservados al endpoint interno autenticado.
6. **Selección** — `VisionResultsPanel` muestra candidatos, confianza, entrega ("Recoger en
   sucursal" / "Delivery"). Como el público ya no recibe el desglose por sede, los chips
   "sede: etiqueta" no se renderizan en el catálogo anónimo (el bloque está guardado por
   `length > 0`); las sedes siguen apareciendo en el selector de entrega, que usa
   `entrega.sucursales`. Rediseñar ese detalle público es un ítem de coordinación con Erika.

## 3. Arranque local

`backend` y `ia-service` se levantan juntos con `npm run dev` desde `backend/` (delega en
`dev.ps1`): abre `ia-service` (FastAPI + YOLO11n) en el puerto 8000 y arranca el backend Node.
Sin `VISION_IA_URL` en `backend/.env` el arranque avisa y la visión responde 503.

## 4. Pruebas automatizadas

Backend. **Requisito**: `DATABASE_URL` debe apuntar a la base local de prueba; el helper
`assertLocalTestUrl` aborta la suite si detecta una URL remota (Neon) para no ejecutar pruebas
destructivas contra producción.

```bash
cd backend
$env:DATABASE_URL = (Get-Content "$env:TEMP\opencode\pgtest\dburl.txt" -Raw).Trim()
npm test                  # unitarios
npm run test:integration  # itest: público 400/422/503/504/200, interno 401/403/200, MIME inválido, >5 MB
npm run test:all
npm run test:coverage
```

Los itests corren con `--test-concurrency=1`: comparten una única base PostgreSQL y el runner de
Node los ejecutaba en paralelo, lo que producía interferencias entre archivos (un `cleanup` de un
archivo borraba usuarios que otro estaba usando para insertar notificaciones).

Cifras verificadas en la última corrida completa:

| Comando | Resultado |
| ------- | --------- |
| `npx tsc --noEmit` | sin errores |
| `npm test` | **110 / 110** unitarios |
| `npm run test:integration` | **130 / 130** |
| `npm run build` | sin errores |

Frontend (los dobles de red se inyectan en el test con `vi.mock` sobre `services/api`; no hay
proveedor simulado en el cliente):

```bash
cd frontend
npm test          # vitest run (no interactivo)
npx tsc -b
npm run build
```

Archivos de pruebas de visión (frontend):

| Archivo | Cubre |
| ------- | ----- |
| `src/components/camera/__tests__/CameraCapture.test.tsx` | cámara no disponible, permiso denegado, captura → `onCapture(File)`, cerrar |
| `src/components/vision/__tests__/VisionResultsPanel.test.tsx` | foto, carga, error, inputs vehículo, candidatos, entrega, Buscar/Cerrar |
| `src/pages/__tests__/PublicProductsPage.vision.test.tsx` | botón "Buscar por cámara", captura → `detectarVisionPublica`, resultados, error traducido, cerrar |
| `src/services/__tests__/visionApi.test.ts` | FormData multipart, campos vehículo, ausencia de header de escenario, mapeo de errores 422/503/504, error de red |

Cifras frontend verificadas: **110 / 110** tests en 12 archivos; `tsc -b` y `build` sin errores.
El build emite el warning de Vite por un chunk > 500 kB (pendiente de code-splitting) y la
suite emite avisos `act(...)` de React en `PublicProductsPage` / `LoginPage` / `MemoryRouter`
(ruido de tests asíncronos, no afectan el resultado).

Archivos de pruebas de visión (backend):

| Archivo | Cubre |
| ------- | ----- |
| `src/modules/vision/__tests__/vision.config.test.ts` | el modo siempre es `http`; sin URL falla cerrado también en desarrollo |
| `src/modules/vision/__tests__/vision.provider.test.ts` | `HttpVisionProvider` contra un `ia-service` real: multipart, `X-Vision-Key`, 503 por IA caída / 401 / sin URL / puerto cerrado / contrato inválido, 504 por timeout |
| `src/modules/vision/__tests__/vision.routes.itest.ts` | público 400/422/503/504/200 con serialización segura, aislamiento por sucursal, ausencia de limiter propio |
| `src/testing/fakeIaServer.ts` | doble de `ia-service` solo de test (no lo importa la aplicación) |

## 5. Probar a mano

1. Arrancar con `npm run dev` desde `backend/` (levanta `ia-service` real).
2. Abrir la página pública → "Buscar por cámara".
3. Permitir la cámara (o negarla para ver el estado denegado).
4. Capturar una foto: debe abrirse `VisionResultsPanel` con candidatos `Frenos` y la etiqueta
   `ia-service (modelo real)`.
5. Para verificar 422/503/504, detener `ia-service` (503) o subir una imagen sin pieza (422).

## 6. E2E contra el modelo real (evidencia)

Ejecutado con `ia-service` real (YOLO11n, CPU, checkpoint
`repuestopro_yolo11n_v3_webcam_robust.pt`) en `127.0.0.1:8000` y el backend compilado
(`dist/server.js`) con `VISION_IA_URL` y `VISION_IA_KEY` correctos. Los casos de fallo se
validaron con instancias aisladas del mismo build (puertos 3101-3105), cada una con una
configuración distinta.

| Caso | Configuración | Resultado observado |
| ---- | ------------- | ------------------- |
| Detección real (15 imágenes) | IA real, `VISION_TIMEOUT_MS=8000` | **4 × HTTP 200** con `proveedor=http` (filtro de aceite 0.9446, caliper 0.6804, caliper 0.6441, pastilla de freno 0.6594) y **11 × HTTP 422** por resultado real del modelo (`VISION_BAJA_CONFIANZA` / `VISION_NO_CLASIFICADA`), nunca una detección inventada |
| MIME inválido | `text/plain` | **400** `Tipo de archivo no permitido` |
| Archivo > 5 MB | 5 MB + 10 B | **400** `El archivo excede el tamaño máximo permitido` |
| Clave incorrecta | `VISION_IA_KEY` distinta a la de `ia-service` | **503** `VISION_NO_DISPONIBLE` (el 401 upstream se traduce) |
| IA caída | `VISION_IA_URL` a puerto cerrado | **503** `VISION_NO_DISPONIBLE` |
| Sin IA configurada | sin `VISION_IA_URL` | **503** `VISION_NO_DISPONIBLE` en 105 ms (fail-closed) |
| Timeout | IA que no responde, `VISION_TIMEOUT_MS=500` | **504** `VISION_TIMEOUT` a los 553 ms |
| Compatibilidad | misma imagen con y sin vehículo | Detección **idéntica** (`filtro de aceite`, 0.9446, 8 candidatos); el vehículo solo actúa sobre catálogo/compatibilidad, confirmando que YOLO no decide compatibilidad |

Latencia de inferencia observada en CPU: 3.5-5.6 s por petición, dentro del timeout de 8 s. La
primera inferencia tras el arranque puede acercarse al límite (por eso `VISION_WARMUP=true` en
`ia-service`); si se supera el timeout, la API responde 504 y se puede reintentar.

Nota de entorno: al ejecutar esta prueba había un proceso antiguo del backend (`index.js`) ocupando
el puerto 3000 y respondiendo `401` en rutas públicas. Hay que verificar que el puerto 3000 lo
toma el build actual (`netstat -ano | findstr :3000`) antes de concluir que la visión está rota.