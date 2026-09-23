# CV-7 — Integración del servicio IA con RepuestoPro

Proyecto: RepuestoPro
Fecha: 2026-09-22
Alcance: integración real FastAPI (servicio de inferencia YOLO) ↔ backend Express ↔ frontend React, demostrada con E2E en host local. No se modifica el modelo, el dataset ni los thresholds.

## 1. Objetivo

Demostrar y documentar la integración funcional de extremo a extremo del módulo de visión:

```
Frontend (React) -> Backend Express -> HttpVisionProvider -> FastAPI -> YOLO -> Backend -> PostgreSQL -> Frontend
```

En CV-4..CV-6 se construyó y evaluó el modelo YOLO (`best.pt`, 8 clases) y se levantó el servicio de inferencia FastAPI. En CV-7 se validó que el backend real de RepuestoPro consume ese servicio real vía HTTP, procesa la detección, mapea a categorías de catálogo, consulta PostgreSQL y devuelve candidatos con disponibilidad y compatibilidad.

## 2. Arquitectura de integración

```
Cliente / Frontend
      |
      | POST /api/vision/public/detectar   (multipart: image [+ vehiculoMarca,Modelo,Anio])
      v
Backend Express  (backend/src/modules/vision)
      | vision.routes -> vision.service (generarRespuestaVision)
      | -> provider.detectar()            -> HttpVisionProvider (fetch)
      v
FastAPI (ia-service) POST /vision/detect
      | YOLO best.pt (YOLO11n, 8 clases)
      v
Backend: validarRespuestaVision (contrato) -> threshold confianza -> MAFEAR_CATEGORIA -> Prisma/PostgreSQL -> candidatos + compatibilidad + entrega
      |
      v
Frontend: VisionResultsPanel (detección, categoría, candidatos, disponibilidad, vehículo, entrega, llevar a venta)
```

El backend monta el módulo en `/api/vision` (`app.use("/api/vision", visionRoutes)` en `backend/src/app.ts`) y selecciona proveedor Mock o HTTP según configuración.

## 3. Contrato FastAPI ↔ backend

Request (desde `HttpVisionProvider`, `backend/src/modules/vision/vision.provider.ts`):

- `POST {VISION_IA_URL}/vision/detect`
- multipart/form-data; campo `image` (JPEG/PNG/WebP, máx 5 MB)
- El backend reenvía el MIME real del archivo (no fija `image/jpeg`).

Response de FastAPI (`ia-service/app/schemas/vision.py`):

```json
{
  "detecciones": [
    {
      "categoria": "filtro de aire",
      "confianza": 0.9703,
      "boundingBox": {"x": 0.347, "y": 0.124, "width": 0.288, "height": 0.237}
    }
  ],
  "consultadoEn": "2026-09-23T01:20:33.631Z"
}
```

- `boundingBox` normalizado a 0..1.
- El backend valida con `validarRespuestaVision` (`contract.ts`): `detecciones` debe ser array; `categoria` string no vacía ≤120; `confianza` número finito 0..1; `boundingBox` números finitos.
- Si `detecciones` es `[]` → el backend responde `422 VISION_NO_CLASIFICADA`.
- `consultadoEn` se propaga como string a la respuesta del backend.

## 4. Configuración

Variables de entorno leídas por `backend/src/modules/vision/vision.config.ts`:

| Variable | Default | Uso |
|---|---|---|
| `VISION_MODE` | `mock` | `mock` o `http`. Si `VISION_IA_URL` está definida, el modo pasa a `http` automáticamente. |
| `VISION_IA_URL` | vacío | Base URL del servicio IA, p.ej. `http://127.0.0.1:8000`. |
| `VISION_TIMEOUT_MS` | `8000` | Timeout del provider (mínimo 500). |
| `VISION_CONFIDENCE_MIN` | `0.55` | Umbral de negocio aplicado al candidato de mayor confianza. |

Diferenciación importante (dos umbrales distintos):

- `CONF_TECNICO_INFERENCIA = 0.25`: umbral técnico del servicio IA (FastAPI) que produce los candidatos visuales. Es config del servicio de IA, no del backend.
- `VISION_CONFIDENCE_MIN = 0.55`: umbral de negocio del backend aplicado a la detección de mayor confianza; por debajo → `422 VISION_BAJA_CONFIANZA`.

Nota: `0.55` es el valor actual del backend y NO se define aquí como política final. La política definitiva de baja confianza es objeto de CV-8.

En la prueba E2E las variables se inyectaron como temporales de sesión (entorno del proceso backend), sin modificar `.env`:

```
VISION_MODE=http
VISION_IA_URL=http://127.0.0.1:8000
VISION_TIMEOUT_MS=8000
VISION_CONFIDENCE_MIN=0.55
```

Por cómo se carga (`dotenv.config()` sin override en `backend/src/config/index.ts`), las variables del proceso tienen prioridad sobre `.env`.

## 5. Mapeo de categorías

Las 8 clases que emite YOLO se normalizan y mapean a categorías existentes del catálogo mediante `CATEGORY_MAP` (`backend/src/modules/vision/categoryMapping.ts`):

| Clase IA | Categoría catálogo |
|---|---|
| pastilla de freno | Frenos |
| disco de freno | Frenos |
| caliper | Frenos |
| alternador | Eléctrico |
| filtro de aceite | Filtros |
| filtro de aire | Filtros |
| radiador | Motor |
| faro | Carrocería |

El mapeo requiere que la categoría destino exista en la tabla `Category`. Si no existe, `categoriaCatalogo` es `null` y la búsqueda devuelve candidatos vacíos con nota aclaratoria (no es fallo de la IA).

## 6. Manejo de errores

Comportamiento existente del backend (`vision.errors.ts`, `vision.routes.ts`, `vision.service.ts`):

| Caso | Respuesta backend |
|---|---|
| Sin imagen en el multipart | 400 `VISION_IMAGEN_REQUERIDA` |
| MIME no permitido / archivo > 5 MB | 400 (multer: "Tipo de archivo no permitido" / "El archivo excede el tamaño máximo permitido") |
| Body del request inválido | 400 `VISION_REQUEST_INVALIDO` |
| Respuesta IA sin detecciones | 422 `VISION_NO_CLASIFICADA` |
| Confianza menor a `VISION_CONFIDENCE_MIN` | 422 `VISION_BAJA_CONFIANZA` |
| Límite de requests (público 5/15min/IP; interno 20/15min/usuario) | 429 `VISION_LIMITE_ALCANZADO` |
| IA no disponible (status 4xx/5xx, conexión rechazada) | 503 `VISION_NO_DISPONIBLE` |
| Timeout (fetch abortado o status 408/504) | 504 `VISION_TIMEOUT` |
| JSON inválido o contrato no valido | 503 `VISION_RESPUESTA_INVALIDA` |

El frontend traduce estos códigos a mensajes de usuario en `CODIGOS_POR_STATUS` / `MENSAJES` (`frontend/src/services/visionApi.ts`) y maneja también 401/403.

## 7. Prueba E2E backend

Evidencia real del Paso 2 (imagen de control `car_engine_bay__val__1028.jpg`, BD del proyecto, backend en host):

- FastAPI: `GET /vision/health` → 200, `modelLoaded=true`, `model=YOLO11n`, `device=cuda:0`, `classes=8`, `cargas=1`.
- Request 1 → HTTP 200 en ~387 ms: `proveedor=http`, detección **filtro de aire** @ **0.9703**, `categoriaCatalogo=Filtros`, 6 candidatos, compatibilidad consultada (0 verificadas / 6 sin verificar, sin vehículo), entrega recoger/delivery con 3 sucursales.
- Request 2 → HTTP 200 en ~77 ms, resultado idéntico, modelo sin recargar.
- Evidencia de que FastAPI recibió los requests: access log de uvicorn con 3 líneas `POST /vision/detect HTTP/1.1 200 OK` (1 directa + 2 originadas por el backend); respuesta del backend con `proveedor: http`.

Los valores mostrados (clase `filtro de aire`, confianza ~0.9703, categoría `Filtros`, 6 candidatos) corresponden a la imagen de control y a la BD usada en la prueba; no son resultados universales.

## 8. Prueba E2E frontend

Auditoría previa: el frontend ya consume la respuesta del backend (contrato campo a campo compatible en `types/vision.ts`), sin necesidad de cambios.

Flujo real ejecutado (Paso 3) con los 3 servicios levantados:

- Frontend Vite en `http://localhost:5173`; base URL del API: `VITE_API_URL || "http://localhost:3000/api"` (`services/api.ts`), sin proxy.
- Backend Express en `http://localhost:3000` con `VISION_MODE=http`; FastAPI en `http://127.0.0.1:8000`.
- Request A (sin vehículo) → HTTP 200 (~137 ms tras warmup): `proveedor=http`, filtro de aire 0.9703, `Filtros`, 6 candidatos, compatibilidad 0v/6nv.
- Request B (con `vehiculoMarca=Toyota`, `vehiculoModelo=Corolla`, `vehiculoAnio=2020-2024`) → HTTP 200 (~81 ms): misma detección (la IA no ve el vehículo), categoría igual, candidatos 6, compatibilidad pasa a **1v/5nv**; el primer candidato ("Filtro de Aire Deportivo") reporta coincidencias `marca,modelo,anio`. El vehículo solo afecta compatibilidad/catálogo, no la inferencia.
- Evidencia: access log de uvicorn registró los POST del backend; respuesta con `proveedor=http`; consumido por el mismo contrato tipado del frontend (test de Vitest `PublicProductsPage.vision.test.tsx` valida el render con datos de la misma forma).

Hallazgo observado durante la sesión (cold start): la primera inferencia tras arrancar FastAPI puede tardar >8 s (la petición dio 504 `VISION_TIMEOUT`); las siguientes se responden en <200 ms. Es un comportamiento de arranque del runtime de inferencia, no una falla del contrato; no se modificó el timeout.

Limitación de prueba de interfaz: la UI de visión es de captura por cámara (`getUserMedia` → JPEG), no permite seleccionar archivo desde galería para visión (la subida por archivo existe para la búsqueda por imagen Tesseract, una feature distinta). En esta prueba el flujo del frontend se validó con el payload y el contrato exactos que la UI dispara y con los tests del componente.

## 9. Separación de responsabilidades

- IA (FastAPI/YOLO): detección visual de la pieza (clase, confianza, bounding box). NO determina marca/modelo/año ni compatibilidad.
- Backend: umbral de negocio, mapeo a categorías, catálogo, disponibilidad, compatibilidad por vehículo y recomendaciones.
- Frontend: captura/upload de la imagen y presentación e interacción de resultados.

Explícito: **YOLO NO determina compatibilidad de vehículo**. La compatibilidad es del backend/catálogo, confirmado en la prueba (misma detección con y sin vehículo).

## 10. Mock vs HTTP

El modo mock se conserva y se usa para desarrollo y tests (rutas, límites, contratos) sin depender de la infraestructura IA:

- Backend en `VISION_MODE=mock` (default): `MockVisionProvider` devuelve escenarios (`default`, `ninguna`, `baja_confianza`, `categoria_desconocida`, `timeout`, `error`) vía header `x-vision-mock-scenario`.
- Backend en `VISION_MODE=http` (o con `VISION_IA_URL` definida): `HttpVisionProvider` llama a FastAPI real; el header de mock no interviene.

Integración real: `http`. Desarrollo/tests: `mock`.

## 11. Limitaciones

- El modelo conserva las limitaciones documentadas en CV-5 (dataset, cobertura por clase, condiciones de captura).
- El umbral de negocio final de baja confianza (`VISION_CONFIDENCE_MIN`) está pendiente de definición en CV-8.
- Docker build/run del servicio IA aún no validado; la prueba se realizó en host local (Windows), FastAPI y backend en `127.0.0.1`.
- Cold start: la primera inferencia tras arrancar el servicio puede superar `VISION_TIMEOUT_MS` (8 s); convendría warmup o ajuste de timeout en una etapa posterior.
- La disponibilidad de productos depende de la BD (PostgreSQL local); la compatibilidad depende de los datos del catálogo (marca/modelo/año) presentes.
- La interfaz web de visión es de captura por cámara; no ofrece selector de archivo/galleria para el flujo de visión (el upload de archivo existe para la búsqueda OCR).

## 12. Estado final CV-7

La integración quedó validada de inicio a fin con servicios reales (no mock):

- Frontend → Backend: OK (mismo contrato tipado, tests del componente verdes).
- Backend → FastAPI: OK (`HttpVisionProvider=proveedor http`, access log uvicorn).
- FastAPI → YOLO: OK (inferencia real, `cargas=1`).
- YOLO → Catálogo: OK (filtro de aire → Filtros, 6 candidatos).
- Respuesta → Frontend: OK.
- Test de la IA: `pytest` → 66 passed. Backend visión (unit): 30 passed. Frontend visión (vitest): 27 passed.

Cierre CV-7: integración validada; pendientes para etapas siguientes: política de baja confianza (CV-8), validación del contenedor Docker del servicio IA, y opcionalmente warmup del modelo o ajuste de cold start.