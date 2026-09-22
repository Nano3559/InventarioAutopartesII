# FLUJO_VISION_MOCK — Pruebas end-to-end con el mock de IA

Sistema: RepuestoPro. Objetivo: verificar el flujo visual (cámara → backend → categoría → catálogo → stock → selección) **sin depender del modelo real de IA**. WB-10 del `PLAN_IMPLEMENTACION_IA_VISION.md`.

## 1. Modo mock (backend)

El backend arranca en modo mock cuando `VISION_MODE` no es `http` (por defecto):

```bash
VISION_MODE=mock npm run dev   # en backend/.env o como variable de entorno
```

- Log al arranque: `VISIÓN: modo MOCK activo (detecciones simuladas)`.
- No se conecta a un servicio IA (`VISION_IA_URL` solo se usa en modo `http`).
- La imagen recibida no se analiza de verdad; el escenario lo decide un header opcional.

### Escenarios por header `x-vision-mock-scenario`

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
5. **Disponibilidad** — solo niveles (`DISPONIBLE`/`POCAS_UNIDADES`/`NO_DISPONIBLE`) y sucursales **TIENDA**; nunca stock exacto ni `price2` en el endpoint público.
6. **Selección** — `VisionResultsPanel` muestra candidatos, confianza, entrega ("Recoger en sucursal" / "Delivery") con sucursales disponibles.

## 3. Pruebas automatizadas (WB-10)

Backend (mock activo, independiente del modelo):

```bash
cd backend
$env:DATABASE_URL = (Get-Content "$env:TEMP\opencode\pgtest\dburl.txt" -Raw).Trim()
$env:JWT_SECRET = $null
npm run test          # unit (30 visión + resto de la suite)
npm run test:integration   # itest: público 400/422/429/503/504/200, interno 401/403/200, MIME inválido, >5 MB
npm run test:all
```

Suite completa verificada: **58 unit + 38 integración** en verde (incl. `vision.routes.itest.ts` con cobertura de rate limit 429); `tsc --noEmit` y `npm run build` sin errores.

Frontend (mock en el cliente vía `vi.mock`):

```bash
cd frontend
npx vitest run
npx tsc -b
npm run build
```

Archivos nuevos (WB-10):

| Archivo | Cubre |
| ------- | ----- |
| `src/components/camera/__tests__/CameraCapture.test.tsx` | cámara no disponible, permiso denegado, captura → `onCapture(File)`, cerrar |
| `src/components/vision/__tests__/VisionResultsPanel.test.tsx` | foto, carga, error, inputs vehículo, candidatos, entrega, Buscar/Cerrar |
| `src/pages/__tests__/PublicProductsPage.vision.test.tsx` | botón "Buscar por cámara", captura → `detectarVisionPublica`, resultados, error traducido, cerrar |
| `src/services/__tests__/visionApi.test.ts` | FormData multipart, campos vehículo, escenario mock, mapeo de errores 422/429/503/504, error de red |

Suite frontend verificada: **92 tests** en verde (69 previos + 23 de visión); `tsc -b` y `npm run build` sin errores.

## 4. Probar a mano

1. Iniciar backend en modo mock y frontend dev.
2. Abrir la página pública → "Buscar por cámara".
3. Permitir la cámara (o negarla para ver el estado denegado).
4. Capturar una foto: debe abrirse `VisionResultsPanel` con candidatos `Frenos`.
5. Cambiar `x-vision-mock-scenario` (DevTools / prueba de API) para verificar 422/503/504 y las tarjetas de error del panel.