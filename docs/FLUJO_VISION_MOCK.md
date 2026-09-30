# FLUJO_VISION_MOCK — Pruebas end-to-end con el mock de IA

Sistema: RepuestoPro. Objetivo: verificar el flujo visual (cámara → backend → categoría → catálogo → stock → selección) **sin depender del modelo real de IA**. WB-10 del `PLAN_IMPLEMENTACION_IA_VISION.md`.

## 1. Modo mock (backend)

La resolución del modo es **explícita** y vive en `backend/src/modules/vision/vision.config.ts`
(`resolverVisionMode`). La regla es: el mock nunca se activa *en silencio* en producción.

| `VISION_MODE` | `VISION_IA_URL` | `NODE_ENV` | Modo resuelto | ¿Requiere IA? |
| ------------- | --------------- | ---------- | ------------- | ------------- |
| (sin definir)  | no              | dev/test   | `mock`        | no |
| (sin definir)  | sí              | cualquiera | `http`        | no (la URL está definida) |
| `remote`       | no              | **prod**   | `http`        | **sí → 503** |
| `http`         | no              | cualquiera | `http`        | **sí → 503** |
| `mock`         | —               | dev/test   | `mock`        | no |

- `remote` es alias de `http`.
- En **producción**, si el modo resuelto es `http` y falta `VISION_IA_URL`, el provider **no**
  devuelve detecciones simuladas: lanza `VisionErrores.servicioNoDisponible()` y la API responde
  **503 `VISION_NO_DISPONIBLE`**. Es un fallo explícito, no un resultado falso.
- `VISION_MODE=mock` explícito en producción es una opt-in deliberada del operador (queda
  registrada en el log de arranque); no se activa por ausencia de configuración.
- En dev/test sin URL se registra un warning de arranque indicando que las detecciones son
  simuladas:

  ```text
  VISIÓN: modo MOCK activo (detecciones simuladas, no provienen del modelo).
  Configure VISION_MODE=http y VISION_IA_URL para usar el modelo real.
  ```

- El modo `http` envía el secreto al servicio IA en el header `X-Vision-Key`, leído de
  `VISION_IA_KEY` (mismo nombre en backend y en `ia-service`). Si el servicio IA no tiene el
  mismo valor configurado, responde 401 y el backend traduce el error.

### Escenarios por header `x-vision-mock-scenario`

Solo aplican en modo `mock`.

| Header / ausencia | Respuesta | Equivalente real |
| ----------------- | --------- | ---------------- |
| `default` | 200, detección `Frenos` confianza 0.94 + boundingBox, 3 candidatos | Detección válida |
| `baja_confianza` | 422 `VISION_BAJA_CONFIANZA` | Imagen poco clara |
| `ninguna` | 422 `VISION_NO_CLASIFICADA` | No se detecta pieza |
| `categoria_desconocida` | 200, candidatos `[]` + nota | Clase desconocida |
| `error` | 503 `VISION_NO_DISPONIBLE` | IA caída |
| `timeout` | 504 `VISION_TIMEOUT` | IA lenta (el mock respeta el timeout real de 8 s) |

## 2. Pasos del flujo E2E (documentados)

1. **Captura** — `CameraCapture` (web, `getUserMedia`) entrega un `File`. Sin permisos de cámara, el estado muestra "no disponible/denegado".
2. **Llamada** — `detectarVisionPublica(file, { vehiculo })` → `POST /api/vision/public/detectar` (multipart, MIME `jpeg|png|webp`, máx 5 MB).
3. **Detección** — backend clasifica (mock: según escenario) y mapea la categoría.
4. **Catálogo** — productos de la categoría rankeados por score (mock: verificación de compatibilidad + orden).
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

## 3. Pruebas automatizadas (WB-10)

Backend (mock activo, independiente del modelo). **Requisito**: `DATABASE_URL` debe apuntar a la
base local de prueba; el helper `assertLocalTestUrl` aborta la suite si detecta una URL remota
(Neon) para no ejecutar pruebas destructivas contra producción.

```bash
cd backend
$env:DATABASE_URL = (Get-Content "$env:TEMP\opencode\pgtest\dburl.txt" -Raw).Trim()
npm test                  # unitarios
npm run test:integration  # itest: público 400/422/429/503/504/200, interno 401/403/200, MIME inválido, >5 MB
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
| `npm test` | **76 / 76** unitarios |
| `npm run test:integration` | **55 / 55**, estable en **3 corridas consecutivas** |
| `npm run test:all` | 76 unit + 55 integración, todo en verde |
| `npm run test:coverage` | 84.61% líneas, 89.83% ramas, 90.83% funciones |
| `npm run build` | sin errores |

Frontend (mock en el cliente vía `vi.mock`):

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
| `src/services/__tests__/visionApi.test.ts` | FormData multipart, campos vehículo, escenario mock, mapeo de errores 422/429/503/504, error de red |

Cifras frontend verificadas: **105 / 105** tests en 11 archivos; `tsc -b` y `build` sin errores.
El build emite el warning de Vite por un chunk > 500 kB (pendiente de code-splitting) y la
suite emite avisos `act(...)` de React en `PublicProductsPage` / `LoginPage` / `MemoryRouter`
(ruido de tests asíncronos, no afectan el resultado).

## 4. Probar a mano

1. Iniciar backend en modo mock y frontend dev.
2. Abrir la página pública → "Buscar por cámara".
3. Permitir la cámara (o negarla para ver el estado denegado).
4. Capturar una foto: debe abrirse `VisionResultsPanel` con candidatos `Frenos`.
5. Cambiar `x-vision-mock-scenario` (DevTools / prueba de API) para verificar 422/503/504 y las tarjetas de error del panel.