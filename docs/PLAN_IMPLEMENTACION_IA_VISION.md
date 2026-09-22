# PLAN DE IMPLEMENTACIÓN — IA Y VISIÓN POR COMPUTADORA

Sistema: RepuestoPro (inventario y ventas de autopartes).
Documento de planificación y división de tareas para **dos personas**.
Este documento es la **primera fase** del proyecto de IA. No implementa funcionalidades: planifica.

---

## 1. Objetivo general

Ampliar el sistema RepuestoPro con inteligencia artificial y visión por computadora para:

1. **Reconocimiento visual de partes de vehículos** (módulo principal, prioridad media/alta):
   - El usuario activa la cámara y muestra una pieza.
   - Un modelo de visión clasifica la pieza en una **categoría** (ej.: faro, retrovisor, parachoques).
   - El backend consulta el catálogo interno y devuelve productos candidatos.
   - **Opción 1:** solo búsqueda por imagen.
   - **Opción 2:** búsqueda por imagen + marca/modelo/año de vehículo, con motor de compatibilidad y, si hace falta, fuentes externas confiables.

2. **Reconocimiento facial para acceso** (las tareas de etapas 1). Prioridad **posterior** a lo anterior. Solo se planifica y audita la arquitectura; no se implementa en esta etapa.

Restricción transversal: la IA **no inventa compatibilidades**; toda recomendación debe poder trazarse a una fuente verificable (catálogo interno o fuente externa autorizada).

---

## 2. Arquitectura objetivo preliminar

```text
                         FRONTEND
                            │
                        Cámara Web
                            │
                            ▼
                         BACKEND
                            │
                ┌───────────┴────────────┐
                │                        │
                ▼                        ▼
        Catálogo / Inventario       Servicio IA
                │                        │
                │                  OpenCV + YOLO
                │                        │
                └───────────┬────────────┘
                            ▼
                  Motor de compatibilidad
                            │
                ┌───────────┴───────────┐
                ▼                       ▼
          Base de datos          Fuentes externas
                │
                ▼
        Stock por sucursal
                │
                ▼
        Recojo / Delivery
```

Las tecnologías base consideradas (a confirmar en la auditoría):

- **Python** como lenguaje del servicio de visión/IA.
- **YOLO** para detección/clasificación de piezas.
- **OpenCV** para preprocesamiento de imágenes.
- **FastAPI** como framework HTTP del servicio IA, si se confirma un servicio independiente.
- **OCR** (Tesseract) posteriormente, si hace falta leer etiquetas o códigos.
- **APIs/fuentes externas** para compatibilidad, solo si faltan datos internos.

Nota: el backend actual ya usa **tesseract.js** (`@tesseract.js-data/eng` + `tesseract.js`). Eso es un activo reutilizable para OCR directo desde Node si un día se decide no mover todo a Python.

---

## 3. Trabajo de Erika — IA / Computer Vision

### Responsabilidad global
Modelo de visión, dataset, entrenamiento, evaluación, servicio de inferencia, contrato de detección y reconocimiento facial futuro.

### 3.1 Tarea CV-1 — Auditoría de datos disponibles para el dataset
- **Subtareas:**
  1. Inventariar imágenes existentes de productos en el sistema (modelo `Product`, campos de imagen).
  2. Evaluar si sirven como dataset base (clases por categoría, variaciones).
  3. Definir qué imágenes nuevas deben capturarse.
- **Dependencias:** ninguna (paralela con la integración web).
- **Entregables:** informe de dataset; lista de categorías posibles con nº estimado de imágenes.
- **Criterios de aceptación:** documento que enumera categorías candidatas y cuántas imágenes existen/necesita cada una.

### 3.2 Tarea CV-2 — Definición de clases y MVP del dataset
- **Subtareas:**
  1. Seleccionar MVP de 5–10 categorías de piezas (ej.: faro, retrovisor, parachoques, radiador, filtro, guardabarros, parrilla, stop, amortiguador, espejo).
  2. Definir etiquetado (bounding boxes) y estándar de anotación (formato YOLO).
  3. Definir variaciones: iluminación, perspectiva, fondo, oclusión.
- **Dependencias:** CV-1.
- **Entregables:** especificación de clases; guía de etiquetado; plantilla de dataset.
- **Criterios de aceptación:** 5–10 clases definidas y validadas; guía de anotación aprobada por ambos.

### 3.3 Tarea CV-3 — Preparación y etiquetado del dataset
- **Subtareas:**
  1. Captura/recolección de imágenes por clase.
  2. Anotación (bounding boxes) con herramienta definida.
  3. Divisar train/val/test.
  4. Control de balanceo y duplicados.
- **Dependencias:** CV-2.
- **Entregables:** dataset anotado (carpetas organizadas), divisiones train/val/test.
- **Criterios de aceptación:** >= 100–200 imágenes por clase en MVP (objetivo inicial, ajustable); >= 80 % imágenes útiles tras revisión.

### 3.4 Tarea CV-4 — Entrenamiento del modelo YOLO
- **Subtareas:**
  1. Seleccionar variante YOLO acorde a CPU/GPU disponibles.
  2. Configurar hiperparámetros y aumentos (perspectiva, rotación, iluminación).
  3. Entrenar y guardar checkpoints.
- **Dependencias:** CV-3.
- **Entregables:** checkpoints del modelo; config de entrenamiento.
- **Criterios de aceptación:** mAP@0.5 >= 0.60–0.70 objetivo en validación (definir umbral final en CV-5).

### 3.5 Tarea CV-5 — Evaluación del modelo
- **Subtareas:** métricas (Precision, Recall, mAP, IoU); análisis de errores; ajuste de confidence threshold.
- **Dependencias:** CV-4.
- **Entregables:** reporte de métricas; umbral oficial de confianza por clase.
- **Criterios de aceptación:** umbral de confianza definido; detecciones falsas máximas aceptables especificadas.

### 3.6 Tarea CV-6 — Servicio de inferencia Python + OpenCV
- **Subtareas:**
  1. Crear servicio (FastAPI si se confirma) con endpoints `/vision/detect`, `/vision/classify`, `/vision/health`.
  2. Preprocesar con OpenCV (redimensionado, normalización).
  3. Cargar modelo YOLO y ejecutar inferencia.
  4. Formatear respuesta según contrato acordado (DTO de detección).
- **Dependencias:** CV-4/5 (puede empezar con modelo preentrenado/mock), contrato API (TC-3).
- **Entregables:** servicio Python ejecutable; Dockerfile del servicio; tests unitarios de la lógica.
- **Criterios de aceptación:** responde al contrato; latencia media por imagen medida y documentada; tolera imágenes inválidas sin crash.

### 3.7 Tarea CV-7 — Diseño del contrato IA ↔ Backend
- **Subtareas:** definir input (imagen) y output (detecciones + confianza + boundingBox); versión del contrato; manejo de errores y timeouts.
- **Dependencias:** TC-3 (trabajo compartido), CV-6.
- **Entregables:** esquema JSON validado; ejemplos mock (respuestas simuladas).
- **Criterios de aceptación:** backend y frontend pueden desarrollarse contra mocks idénticos al contrato real.

### 3.8 Tarea CV-8 — Tratamiento de detecciones incorrectas
- **Subtareas:** política de "baja confianza"; umbrales por categoría; mensajes de error al usuario (no mostrar resultados falsos).
- **Dependencias:** CV-5, CV-7.
- **Entregables:** documento de políticas + reglas implementadas en el servicio.
- **Criterios de aceptación:** detección con confianza < umbral devuelve estado "no clasificada" en lugar de inventar.

### 3.9 Tarea CV-9 — Reconocimiento facial (solo arquitectura, fase final)
- **Subtareas (análisis/arquitectura):**
  1. Estudiar embeddings faciales (ej. librerías tipo FaceNet/ArcFace a evaluar) y técnicas de liveness detection.
  2. Diseñar almacenamiento seguro de referencias biométricas (cifrado, sin guardar fotos innecesarias).
  3. Diseñar verificación (1:1) contra usuario autenticado conectado al rol, no solo detección.
  4. Anti-suplantación: liveness detection (parpadeo/profundidad), límites de intentos.
- **Dependencias:** TC-10 (validación seguridad), módulos de auth existentes.
- **Entregables:** documento de arquitectura facial; riesgos; propuesta de fallback a login tradicional.
- **Criterios de aceptación:** diseño revisado por Ross; plan de privacidad y consentimiento explícito definido. **No se implementa en esta etapa.**

---

## 4. Trabajo de Ross — Integración Web / Backend / Datos

### Responsabilidad global
Integración con el frontend y backend existentes, catálogo, compatibilidad, stock, stock por sucursal, proveedores externos y UX.

### 4.1 Tarea WB-1 — Relevamiento de arquitectura actual
**Estado: [x] COMPLETA** — Evidencia: `docs/AUDITORIA_IMPLEMENTACION_IA_VISION.md` (31 secciones: stacks, endpoints, modelos, seguridad, hallazgos y matrices) + `docs/STACK_*.md`. Inventario completo de endpoints y modelos citado por archivo.
- **Subtareas:** mapear frontend (React 18 + Vite + Tailwind + Zustand + Axios), backend (Express + TS + Prisma + PostgreSQL), mobile (Expo/React Native), imágenes, inventario por Location, auth (JWT + roles).
- **Dependencias:** ninguna.
- **Entregables:** nota técnica alineada a `STACK_*.md` existentes.
- **Criterios de aceptación:** inventario completo de endpoints y modelos con archivo/evidencia.

### 4.2 Tarea WB-2 — Acceso a cámara en el frontend (web)
**Estado: [x] COMPLETA** — `frontend/src/components/camera/CameraCapture.tsx`: fotograma único vía `canvas.toBlob` → `File` (no streaming continuo), previsualización, permisos, estados error/denegado/no disponible, responsive, cleanup del `MediaStream` (stop de tracks al capturar/cerrar/desmontar). Tests: `__tests__/CameraCapture.test.tsx` (4).
- **Subtareas:**
  1. Verificar `navigator.mediaDevices.getUserMedia()` en contexto HTTPS.
  2. Crear componente de captura de fotograma único (no streaming continuo).
  3. Previsualización, permisos, estados de error/denegado, responsive.
- **Dependencias:** ninguna (puede construirse contra mocks).
- **Entregables:** componente `CameraCapture` reutilizable; demo capturando un frame.
- **Criterios de aceptación:** captura funciona en desktop y móvil con al menos un navegador moderno cada uno; errores de permiso manejados.

### 4.3 Tarea WB-3 — Cliente HTTP frontend para visión
**Estado: [x] COMPLETA** — `frontend/src/services/visionApi.ts`: multer/multipart vía `FormData`, tipado `VisionAnalysis` (`src/types/vision.ts`), `AbortSignal` de cancelación, `timeout` 20 s, mapeo de errores por `codigo`/status (400/401/403/422/429/503/504). Tests directos: `src/services/__tests__/visionApi.test.ts` (7) + cobertura de flujo en `PublicProductsPage.vision.test.tsx`.
- **Subtareas:** función de subida de imagen al backend (form/multipart); manejo de progreso, errores y cancelación; tipado de la respuesta (DTO de detección).
- **Dependencias:** WB-2, TC-3 (contrato), mocks.
- **Entregables:** `visionApi` en frontend; tests (Vitest).
- **Criterios de aceptación:** envío de imagen + parseo de respuesta con mocks; errores de red/manejo de timeouts.

### 4.4 Tarea WB-4 — Endpoints backend de visión (adaptadores)
**Estado: [x] COMPLETA** — `backend/src/modules/vision/`: `vision.routes.ts` (público `/api/vision/public/detectar` con `visionPublicLimiter` → `imageUpload`; interno `/api/vision/detectar` con `authenticate` → `requireTiendaLocation` → `visionAuthenticatedLimiter`), proxy IA (`vision.provider.ts` mock/http con `AbortSignal.timeout` y `withVisionTimeout`), fallback mock por env sin URL, tipo de detección y contratos en `contract.ts`. Reutiliza `imageUpload` (MIME `jpeg|png|webp`, 5 MB, 1 archivo) y `parseString`. Image en memoria: no hay archivos temporales que limpiar. No aplica retry automático del provider http (el envío es de fotografía puntual y el timeout externo de 8 s acota la ventana). Tests de integración: `__tests__/vision.routes.itest.ts` (15: 400/401/403/422/429/503/504/200 público e interno, serialización segura, stock TIENDA vs ADMIN, >5 MB).
- **Subtareas:**
  1. Endpoint para subir imagen (Go reuse validación existente de MIME/tamaño, ej. `imageUpload` actual).
  2. Proxy hacia el servicio IA (retry, timeout, fallback mock).
  3. Sanitización de la imagen temporal y su eliminación posterior.
- **Dependencias:** TC-3, servicio IA (o mock).
- **Entregables:** rutas de visión en backend con validación y pruebas de integración.
- **Criterios de aceptación:** 400 en archivos inválidos, tamaño límite, autenticación/rate limit aplicados.

### 4.5 Tarea WB-5 — Integración con el catálogo interno por categoría
**Estado: [x] COMPLETA** — `vision.service.ts` (`generarRespuestaVision`): clase detectada → `mapearCategoria` (`categoryMapping.ts`, identidad + sinónimos, sin inventar) → productos `categoryId` (top 30 consultados, 12 devueltos) → respuesta con `price1`+disponibilidad por niveles. Flujo "imagen → categoría → lista de productos" verificado en itest (3 candidatos `Frenos`, excluye producto sin categoría).
- **Subtareas:** dado `categoria`, consultar productos (endpoint/servicio existente de búsqueda/filtros) y construir respuesta de candidatos (imagen, nombre, marca, compatibilidades, precio, stock).
- **Dependencias:** WB-4, revisión de endpoints de productos existentes.
- **Entregables:** flujo "imagen → categoría → lista de productos".
- **Criterios de aceptación:** para una detección ficticia de "faro", se recuperan todos los `Product` de esa categoría con stock disponibles.

### 4.6 Tarea WB-6 — Catálogo y compatibilidad por vehículo
**Estado: [x] COMPLETA (baseline)** — `compatibility.ts`: motor baseline de marca/modelo/año sobre las tablas existentes (`Product.brand/model/year` + `yearRanges` con rangos `"20-24"`), ranking por score, **no inventa**: sin vehículo o sin coincidencias suficiente → `verificada:false` con nota. `CompatibilityProvider` + `BaseDatosInternaProvider` + factory. Pendiente (dependencia): normalización/completado de datos de vehículo y fuentes externas para la Opción 2 completa (ver WB-6 del plan y hallazgo H3).
- **Subtareas:**
  1. Analizar si el modelo `Product` soporta marca/modelo/año/rango de años/OEM.
  2. Diseñar consulta "¿qué faros son compatibles con Toyota Hilux 2020?" usando las tablas existentes (Year, Marca, Modelo, Importer, etc.).
  3. Diseñar el motor de compatibilidad → Ranking de productos.
- **Dependencias:** WB-5.
- **Entregables:** especificación de la consulta de compatibilidad; ranking simple baseline (porcentaje de coincidencia de campos).
- **Criterios de aceptación:** consulta funcional contra datos reales; documentar qué campos faltan (los datos se completan en fase de datos).

### 4.7 Tarea WB-7 — Stock por sucursal
**Estado: [x] COMPLETA** — `availability.ts`: disponibilidad pública segura por umbral (`>10` DISPONIBLE, `>0` POCAS_UNIDADES, `0` NO_DISPONIBLE) nunca expone stock exacto; público devuelve sucursales **TIENDA** con nivel; interno devuelve stock exacto por `Location` (ADMIN global, TIENDA solo su sucursal `requireTiendaLocation`). Verificado en itest y en `availability.test.ts`.
- **Subtareas:** usar `Location` + `Inventory` + `Movement` para responder "Sucursal A: 3, Sucursal B: 0, Almacén: 5"; frontend muestra disponibilidad por ubicación.
- **Dependencias:** WB-5.
- **Entregables:** endpoint de disponibilidad por producto; vista de stock por sucursal en el frontend.
- **Criterios de aceptación:** para un producto, devuelve stock por cada Location con nombre y tipo.

### 4.8 Tarea WB-8 — Flujo de recogida / delivery (solo integración)
**Estado: [x] COMPLETA** — Selección en `VisionResultsPanel` (modalidad "Recoger en sucursal" / "Delivery", sucursal con stock, cantidad, "Entregar a"), respuesta `entrega` del backend y acople real al modelo de venta autenticado actual sin romper su transacción: el público anónimo guarda un **borrador de venta** (`frontend/src/services/saleDraft.ts`, localStorage `borrador_venta_vision`) y se completa el cobro en el punto de venta;
`SalesPage` relee precios/stock en el momento de vender, pre-llenan sucursal/«lugar de entrega»/«entregar a», y `POST /api/sales` persiste `paraQuien`/`lugarEntrega`/`datosFactura`/`formaPago` (opcionales, validados) en las columnas ya existentes. Se verifica en `R6.17`/`R6.18` (backend) y `saleDraft.test.ts`, `VisionResultsPanel.test.tsx`, `PublicProductsPage.vision.test.tsx`, `SalesPage.test.tsx` (frontend). No se creó e-commerce público nuevo (decisión: el flujo de venta sigue siendo punto de venta autenticado, ver AUDITORÍA 13–14).
- **Subtareas:** UI para seleccionar "Recoger en sucursal" vs "Delivery"; para recogida listar sucursales con stock y permitir elegir; delivery: mapear con la lógica existente (o documentar qué falta).
- **Dependencias:** WB-7.
- **Entregables:** componente de selección entregable; documento de acople con el modelo de venta actual.
- **Criterios de aceptación:** la elección de sucursal con stock llega a la cotización/venta sin romper el flujo existente.

### 4.9 Tarea WB-9 — UX de resultados
**Estado: [x] COMPLETA** — `frontend/src/components/vision/VisionResultsPanel.tsx`: categoría + confianza, lista de productos con precio/disponibilidad/compatibilidad y stock por sucursal, estados cargando/vacío/error, selector entregabilidad. **No muestra compatibilidad inventada**: solo la marca "verificada" cuando el backend lo confirma. Tests: `__tests__/VisionResultsPanel.test.tsx` (8).
- **Subtareas:** mostrar resultado de detección (categoría + confianza), lista de productos, tarjetas con los datos, estados cargando/vacío/error; no mostrar compatibilidad inventada.
- **Dependencias:** WB-6/WB-7.
- **Entregables:** pantalla de resultados de búsqueda visual integrada al flujo público.
- **Criterios de aceptación:** UX aprobada; resultado con baja confianza muestra aviso de no clasificación.

### 4.10 Tarea WB-10 — Pruebas de integración end-to-end
**Estado: [x] COMPLETA** — `docs/FLUJO_VISION_MOCK.md` documenta el flujo completo con mock (cámara → backend → categoría → catálogo → stock → selección) y los escenarios `x-vision-mock-scenario`. Verificado de punta a punta: backend **96 tests** (58 unit + 38 integración, incl. 30 unit + 15 itest de visión) y frontend **92 tests** (8 nuevas suites de visión) en verde; `tsc`/`build` limpios en ambos.
- **Subtareas:** flujo completo con mock del servicio IA: cámara → backend → categoría → catálogo → stock → selección.
- **Dependencias:** WB-9.
- **Entregables:** suite E2E básica del flujo visual.
- **Criterios de aceptación:** flujo verificado de punta a punta con el mock; pasos documentados.

---

## 5. Trabajo compartido

### 5.1 TC-1 — Definición del contrato de detección (DTO)
**Estado: [x] COMPLETA** — `backend/src/modules/vision/contract.ts`: `VisionDetection[]` (`categoria`, `confianza`, `boundingBox` opcional) + `esVisionDetection`/`esBoundingBoxValido` como fuente única de verdad; runtime validation `validarRespuestaVision` (respuesta del proveedor inválida → 503). Tipos TS espejo en `frontend/src/types/vision.ts`. La serialización pública jamás expone `price2`/stock exacto.
- **Subtareas:** definir tipo `VisionDetection[]` con `categoria`, `confianza`, `boundingBox` opcional; naming en español consistente con el proyecto (ej. `categoria`, `confianza`).
- **Entregables:** esquema JSON + tipos TS + validación (backend reutiliza express-validator / validate).
- **Criterios de aceptación:** una sola fuente de verdad para el contrato.

### 5.2 TC-2 — Mocks / stubs del servicio IA
**Estado: [x] COMPLETA** — `MockVisionProvider` (`vision.provider.ts`) devuelve detecciones deterministas; montable con `VISION_MODE=mock` (default) o automático si `VISION_MODE=http` sin `VISION_IA_URL` (fallback mock con log de error). Header `x-vision-mock-scenario`: `default|ninguna|baja_confianza|categoria_desconocida|timeout|error`. Ross desarrolló todo sin el modelo real (clave anti-bloqueo).
- **Subtareas:** crear un mock que devuelva detecciones deterministas; montable desde backend con variable de entorno.
- **Entregables:** stub JSON + servidor mock simple.
- **Criterios:** Ross puede desarrollar todo sin esperar el modelo.

### 5.3 TC-3 — Pruebas de integración backend
**Estado: [x] COMPLETA** — `backend/src/modules/vision/__tests__/vision.routes.itest.ts` (15 tests) con mock: 400 sin imagen/MIME inválido/vehículo largo, 401 anónimo/inválido, 403 TIENDA sin ubicación, 200 público seguro + interno ADMIN/TIENDA, 422 baja confianza/no clasificada, 429 límite de rate, 503 IA caída, 504 timeout, `>5 MB` rechazado. Suite completa sin depender del modelo real.
- **Subtareas:** tests `*.itest.ts` para endpoints de visión con mock; validación de payload; verificación de los requisitos de seguridad.
- **Criterios:** suite completa sin depender del modelo real.

### 5.4 TC-4 — Manejo de errores uniforme
**Estado: [x] COMPLETA** — `vision.errors.ts`: `VisionServiceError` con `status`/`codigo` y `VisionErrores` (400 `VISION_IMAGEN_REQUERIDA`/`VISION_REQUEST_INVALIDO`, 422 `VISION_NO_CLASIFICADA`/`VISION_BAJA_CONFIANZA`, 503 `VISION_NO_DISPONIBLE`/`VISION_RESPUESTA_INVALIDA`, 504 `VISION_TIMEOUT`). Manejados en `manejarVision`; el frontend conoce todos los códigos (`visionApi.ts` `CODIGOS_POR_STATUS`).
- **Subtareas:** estandarizar códigos de error (400 mala imagen, 422 no clasificada, 503 servicio IA no disponible, 504 timeout).
- **Criterios:** el frontend conoce todos los códigos.

### 5.5 TC-5 — Seguridad transversal de imágenes
**Estado: [x] COMPLETA** — Política común reutilizando `imageUpload` (MIME `jpeg|png|webp`, 5 MB, 1 archivo); imagen en memoria (sin archivos temporales en disco); endpoint interno protegido con `authenticate` + `requireTiendaLocation`; endpoints con rate limits dedicados `visionPublicLimiter` (5/15 min/IP) y `visionAuthenticatedLimiter` (20/15 min/usuario). Error centralizado en el `errorHandler` existente (`INVALID_FILE_TYPE`, `LIMIT_FILE_SIZE` → 400).
- **Subtareas:** política común de MIME/tamaño; limpieza temporal; protección del endpoint interno (JWT + rol) y límite de rate para el público.
- **Criterios:** revisión de seguridad aprobada por ambos.

### 5.6 TC-6 — Estrategia de fuentes externas (abstracción)
**Estado: [x] COMPLETA** — Abstracción implementada y verificada: `CompatibilityProvider`, `BaseDatosInternaProvider`, `CompatibilityProviderFactory` y la interfaz `ProveedorExternoCompatibilidad` (trazabilidad `fuente` + `fechaConsulta` + `confianza`, `timeoutMs`, `usaCache`, `fallback`) en `compatibility.ts`. El proveedor interno de catálogo funciona con trazabilidad (`fuente: base_datos_interna`, `consultadoEn`). **Pendiente externo (no técnico de esta tarea):** implementadores `APIFabricante`, `APIDistribuidor`, `BúsquedaWebControlada` → dependen de APIs/contratos externos reales que aún no existen (hallazgo H3; FASE 6). La abstracción quedó lista para registrarlos cuando existan.
- **Subtareas / análisis:** diseñar `CompatibilityProvider` con implementadores (BaseDatosInterna, APIFabricante, APIDistribuidor, BusquedaWebControlada); definir caching, timeouts, fallbacks, rate limits y trazabilidad (fuente + fecha de consulta + confianza).
- **Criterios:** todas las recomendaciones de compatibilidad con fuente verificable.

---

## 6. Orden recomendado de implementación

```text
FASE 0   Auditoría y arquitectura (este plan + docs/AUDITORIA_IMPLEMENTACION_IA_VISION.md)
FASE 1   Captura de cámara (frontend) + contrato DTO + mocks
FASE 2   Servicio IA mínimo (mock primero; luego Python/FastAPI + OpenCV + YOLO)
FASE 3   Reconocimiento de categoría (5–10 clases MVP)
FASE 4   Integración con catálogo (imagen → categoría → productos)
FASE 5   Vehículo + compatibilidad (marca/modelo/año)
FASE 6   Fuentes externas (proveedores de compatibilidad)
FASE 7   Stock por sucursal
FASE 8   Recojo / delivery
FASE 9   Pruebas y hardening
FASE 10  Reconocimiento facial (posterior)
```

Nota original: esta fase ya corresponde a FASE 0 (plan + auditoría), y no se implementará **ninguna** de las fases 1–10 aún.

**Actualización (2026-09-21, trabajo de Ross, modo mock):** se implementaron las FASE 1–9 del lado de integración **con mock del servicio IA** (cámara web, contrato DTO, mocks, endpoints backend con proxy/fallback-mock, categoría→catálogo, compatibilidad baseline, stock por sucursal seguro, UI recoger/delivery, UX de resultados y suite E2E). Lo que sigue dependiendo de Erika/datos: FASE 2 (servicio IA real Python/OpenCV/YOLO), FASE 3 (dataset y entrenamiento), FASE 6 (fuentes externas reales) y FASE 10 (facial, solo arquitectura). Ver estados `[x]`/`[~]` en WB-1…WB-10 y TC-1…TC-6.

---

## 7. Dependencias entre ambas personas

| Responsable | Depende de | Por qué |
| ----------- | ---------- | ------- |
| Erika (IA) | Ross (WB-1) | Conocimiento del modelo `Product` y del catálogo para decidir clases finales. |
| Erika | Ross/Erika (TC-1) | El contrato IA debe fijarse para que el servicio genere el output esperado. |
| Ross (Web) | Erika (TC-3/mock) | Endpoints backend reales dependen del servicio IA (o su mock). |
| Ross | Erika (CV-5) | El umbral de confianza oficial define UX de resultados. |
| Ambas | equipo | Aprobación conjunta del contrato y del flujo de integración. |

**Clave anti-bloqueo:** Ross nunca espera el modelo real: trabaja contra mocks deterministas desde la FASE 1.

---

## 8. Posibles puntos de bloqueo

1. **Dataset**: sin imágenes suficientes y etiquetadas no hay modelo bueno.
2. **Hardware de entrenamiento**: CPU sola limita tamaño de YOLO y tiempos.
3. **Datos de compatibilidad**: si el catálogo no tiene marca/modelo/año/rango/importadores suficientes, la Opción 2 queda limitada.
4. **Cámara en móvil/navegador**: permisos HTTPS y experiencia en dispositivos reales.
5. **Fuentes externas**: falta de APIs confiables o términos de uso de fabricantes.
6. **Privacidad/biometría**: reconocimiento facial introduce requisitos legales y de consentimiento.
7. **Recursos de despliegue**: un servicio Python adicional requiere infraestructura (Docker/CPU o GPU).

---

## 9. Definition of Done de cada fase

**FASE 0**: plan creado + auditoría publicada; nada implementado aún.
**FASE 1**: componente cámara captura frame; contrato DTO e mocks versionados; frontend envía imagen al backend (con mock).
**FASE 2**: servicio IA responde `/vision/health` y `/vision/detect` con mock (o modelo preliminar) bajo contrato; backend proxya correctamente.
**FASE 3**: MVP de 5–10 clases con mAP objetivo alcanzado en validación; umbral de confianza fijado.
**FASE 4**: imagen → categoría → lista de productos del catálogo; pruebas de integración pasando.
**FASE 5**: respuesta correcta a "¿qué faros para Toyota Hilux 2020?" usando datos internos; ranking implementado.
**FASE 6**: al menos una fuente externa integrada bajo `CompatibilityProvider` con trazabilidad; staging del fallback.
**FASE 7**: endpoint de stock por sucursal operativo y mostrado en UI.
**FASE 8**: selección recogida/delivery funcional integrado con el modelo de venta.
**FASE 9**: suite unitaria + integración + E2E completa; revisión de seguridad y rendimiento.
**FASE 10**: diseño facial aprobado; prototipo con verificación 1:1 + liveness en entorno controlado (requiere revisión previa de privacidad).

---

## 10. Riesgos técnicos

| Riesgo | Probabilidad | Impacto | Mitigación |
| ------ | ------------ | ------- | ---------- |
| Dataset pequeño | Alta | Alto | MVP con 5–10 clases y captura colaborativa; aumentos de datos. |
| Sobreajuste / clases desbalanceadas | Media | Alto | División train/val/test estricta; métricas por clase; aumentos. |
| Confusión entre clases parecidas (faro vs stop) | Media | Media | Ejemplos adversos; umbrales por clase; muestras de baja confianza. |
| YOLO pesado en CPU | Alta | Medio | Seleccionar variante nano/small; redimensionar input; fotografía puntual (no streaming). |
| Compatibilidad incompleta en BD | Alta | Alto | Priorizar opción 2 con fuentes externas; documentar campos faltantes. |
| Latencia de inferencia alta | Media | Medio | Limitar tamaño; cuantizar modelo; async/timeouts; prestar atención al envío de foto única. |
| Cámara en HTTP (no HTTPS) | Baja (dev) | Alto | Entornos de demo en HTTPS (Vercel) / localhost seguro. |
| Seguridad de imágenes maliciosas | Media | Alto | Repetir validaciones MIME/tamaño; eliminar archivos temporales; rate limiting (ya existente). |
| Privacidad facial | Media | Alto | Embeddings cifrados, sin almacenar fotos; consentimiento; liveness; fallback tradicional. |
| Dependencia de APIs externas | Media | Alto | Abstracción `CompatibilityProvider`; caché; fallback; trazabilidad. |

---
