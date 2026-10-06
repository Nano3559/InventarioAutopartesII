# MODO ESCANEO INTELIGENTE

Documento de defensa. Describe cómo funciona el flujo de identificación de piezas por visión, qué decisiones se tomaron y cuáles son sus límites reales.

---

## 0. Qué es y qué no es

**Es** una capa de lógica encima del clasificador existente que hace tres cosas:

1. avisa antes de gastar una inferencia si la foto es mala;
2. ofrece una segunda foto para confirmar categorías en zona de confianza media;
3. explica por qué aparece cada producto en los resultados.

**No es**:

- un entrenamiento nuevo (no se tocó ningún modelo);
- una métrica nueva sobre el dataset (no hay dataset ni ground truth: ver `docs/AUDITORIA_IMPLEMENTACION_IA_VISION.md`);
- una probabilidad entrenada para la combinación de dos fotos (la combinación es una regla de texto);
- una simulación (todas las llamadas reales: frontend → backend → `ia-service` → YOLO11n).

---

## 1. Detección visual (YOLO)

**Qué hace:** identifica la pieza en la foto y devuelve clase, confianza y *bounding box*.

| Dato | Origen | Quién lo dice |
|---|---|---|
| `categoria` | etiqueta de YOLO | modelo |
| `confianza` | score de YOLO | modelo |
| `boundingBox` | caja en coordenadas normalizadas `0..1` | modelo |

- El modelo es `ia-service/models/repuestopro_yolo11n_v3_webcam_robust.pt` (YOLO11n, 8 clases), el único checkpoint disponible.
- El bounding box se dibuja en porcentajes sobre la foto real en `frontend/src/components/vision/DetectionBox.tsx`.
- **La confianza es exclusiva del modelo.** Nada fuera de YOLO la produce ni la modifica.

Si la confianza cae por debajo del umbral del backend, el endpoint responde `422 VISION_BAJA_CONFIANZA` y nunca llega a inventar una categoría.

---

## 2. OCR (Tesseract, evidencia de código)

**Qué hace:** lee el texto grabado en la etiqueta de la pieza (código OEM, de fábrica, de ítem).

- Implementado en `backend/src/shared/utils/ocr.ts`.
- **Worker único y compartido** entre búsqueda por imagen y búsqueda por visión: un solo modelo Tesseract en memoria, con cola.
- **Best effort:** `ocrExtract` nunca lanza. Si Tesseract falla, el resultado sigue siendo YOLO-only y no hay evidencia de texto.
- Se lanza **en paralelo** con la llamada a `ia-service`: mientras la red espera, Tesseract trabaja.

Normalización (todo comparado en forma canónica):

```
90915-YZZD2  ≡  90915YZZD2  ≡  90915 YZZD2
```

Se descartan palabras que no son códigos (`FILTRO`, `TOYOTA`, etc.) para evitar coincidencias falsas.

**Límite explícito:** el código identifica la pieza. **No** confirma que sea compatible con el vehículo del usuario.

---

## 3. Calidad de imagen (previa, sin IA)

**Qué hace:** mide indicadores deterministas *antes* de enviar la foto al modelo, y avisa si la foto probablemente va a dar un resultado malo.

**Ubicación:** frontend, con Canvas (`frontend/src/services/imageQuality.ts`). Se eligió por ser la opción más simple: sin dependencia nueva, sin costo de CPU en el servidor, sin viaje extra de red, y permite advertir *antes* de la inferencia.

### Indicadores

| Indicador | Cómo se calcula |
|---|---|
| Brillo | luminancia media, ponderación Rec. 709 (`0.2126R + 0.7152G + 0.0722B`) |
| Contraste | desviación estándar de la luminancia |
| Nitidez | varianza del Laplaciano (métrica clásica de desenfoque) |
| Resolución | dimensiones reales de la foto |
| Tamaño | peso en bytes del archivo |

Las métricas de píxeles se calculan sobre una copia reducida a `256 px` de lado. Eso tiene dos consecuencias buscadas:

1. los umbrales no dependen de la resolución de origen;
2. una foto que llega borrosa por haber sido reescalada se detecta como borrosa, que es justamente lo que va a ver el modelo.

### Regla de veredicto

```
mala     ← cualquiera de estas condiciones severas:
           brillo < 0.15          → "muy oscura"
           brillo > 0.93          → "demasiado clara"
           lado menor < 320 px    → "resolución baja"
           nitidez < 0.0004  Y  contraste < 0.05 → "borrosa"

regular  ← condiciones menores: brillo fuera de [0.28, 0.82],
           nitidez < 0.003, contraste < 0.05,
           lado menor < 640 px, archivo < 15 KB

buena    ← sin observaciones
```

Detalle importante de diseño: **una nitidez baja sola no vuelve la foto "mala"**. Solo se considera borrosa definitiva cuando además el contraste es bajo. Así se evita el falso positivo típico de una pieza nítida sobre fondo liso (poca varianza de Laplacian sin estar desenfocada).

### Comportamiento de la interfaz

- **buena / regular:** la búsqueda arranca sola, sin fricción. El veredicto queda visible en el panel.
- **mala:** aparece un aviso **antes** de buscar, con el motivo concreto y qué hacer. El usuario tiene **dos** salidas: `Buscar de todos modos` o `Tomar otra foto`. **No se bloquea nunca.**
- Si el navegador no puede decodificar la imagen (sin Canvas, decodificador colgado), `analizarCalidadImagen` devuelve `null` y el flujo continúa sin aviso, con techo de tiempo de 2.5 s.

Ejemplo de salida:

```json
{
  "brillo": 0.10,
  "contraste": 0.20,
  "nitidez": 0.0100,
  "resolucion": { "ancho": 800, "alto": 600, "megapixeles": 0.48 },
  "bytesArchivo": 307200,
  "estado": "mala",
  "problemas": ["La foto está muy oscura (brillo 10%)."],
  "recomendaciones": ["Buscá más luz o acercá la pieza a una fuente de luz."]
}
```

---

## 4. Segunda vista (confirmación multi-foto)

**Idea central:** cuando la confianza está en un nivel medio, una sola foto no alcanza para afirmar. Se pide una segunda y se comparan las **dos detecciones reales**.

### Cuándo se ofrece

| Confianza YOLO | Comportamiento |
|---|---|
| `≥ 0.80` | no se molesta al usuario |
| `0.55 … 0.80` | se ofrece: *"¿Querés confirmar con otra foto?"* |
| `< 0.55` | el backend ya responde 422, no llega a la UI |

El `0.80` es una decisión de producto, no una propiedad entrenada del modelo.

### Regla de combinación

La implementación está en `frontend/src/services/multiView.ts`.

| Situación | Veredicto | Etiqueta mostrada |
|---|---|---|
| 1 sola foto | sin confirmar | `No confirmado` |
| 2 fotos, misma categoría | coincidencia entre vistas | `Confirmado por 2 imágenes` |
| 2 fotos, categorías distintas | ambas posibilidades | `Resultados inconsistentes` |
| 2 fotos, una no clasifica | se conserva la otra, sin confirmar | `No confirmado` |

La comparación de categorías normaliza mayúsculas, tildes y separadores, y prioriza `categoriaMapeada` (el nombre del catálogo) sobre la etiqueta cruda de YOLO.

### Lo que NO hace

- **No** promedia confianzas. `confianzaYolo` del resultado es exactamente la confianza de una de las dos fotos, nunca un valor combinado.
- **No** calcula ninguna probabilidad nueva ni la presenta como entrenada.
- En caso inconsistente **no** elige una categoría por mayoría ni por score: muestra ambas y pide otra foto.

Así se mantiene el criterio del proyecto: un número solo se muestra si existe fuente real que lo produjo.

---

## 5. Ranking explicable (score de coincidencia)

### Dos números, dos fuentes, nunca confundidos

| Nombre | Quién lo produce | Significado |
|---|---|---|
| **Confianza del modelo** | YOLO | ¿qué tan seguro está de la clase? |
| **Score de coincidencia** | motor de catálogo | ¿cuántos códigos/atributos del catálogo coincidieron? |

En la interfaz aparecen en lugares distintos, con nombres distintos. No existe en ninguna parte del código un texto que diga "Confianza IA" sobre el score de catálogo.

### Pesos del motor de catálogo

| Campo | Peso |
|---|---|
| `oemCode` | 10 |
| `factoryCode` | 8 |
| `itemCode` | 6 |
| coincidencia parcial | 3 (mínimo 6 caracteres) |

Implementado en `backend/src/modules/vision/hybridEvidence.ts`.

### Orden de selección

```
1. compatibilidad verificada con el vehículo
2. evidencia de código (score de coincidencia)
3. puntaje de compatibilidad
```

**Regla dura:** la compatibilidad verificada siempre va primero. Un `oemCode` leído en la etiqueta **nunca** desplaza a un producto que sí fue verificado contra la marca/modelo/año que pidió el usuario. Esto es lo que impide prometer compatibilidad inventada.

Los pesos `10 / 8 / 6` son **provisionales**: son un orden por autoridad del campo, no valores calibrados. Calibrarlos exige ground truth, que no existe.

---

## 6. Compatibilidad

- La compatibilidad se evalúa con datos reales del catálogo (`backend/src/modules/vision/compatibility.ts`): marca, modelo y año, consultados al proveedor configurado.
- `compatibilidad.verificada = true` solo cuando el backend confirmó la relación contra el vehículo consultado.
- El frontend nunca la crea: solo la renderiza.

### Explicabilidad por candidato

Cada producto incluye la sección **"¿Por qué aparece este producto?"** (`frontend/src/services/explicabilidad.ts`), colapsada por defecto para no recargar la interfaz.

Solo emite líneas con evidencia real:

```
✓ Categoría visual coincide
✓ Código OEM exacto: 90915YZZD2
✓ Marca
✓ Disponible
⚠ Compatibilidad no verificada: no se comprobó contra tu vehículo
⚠ Solo coincide por categoría: no se leyó ningún código en la foto
⚠ Sin stock disponible en este momento
```

Regla de diseño: **una línea sin respaldo es peor que no tener línea.** Si el inventario dice `NO_DISPONIBLE`, jamás aparece "Disponible". Si no hubo evidencia de código, aparece explícitamente que la coincidencia fue solo por categoría.

---

## 6.1 Experiencia de usuario final (UX del escaneo)

Decisión de producto única para todo el modo: **nunca se imprime `n/d`**. Si un dato no se pudo producir, se dice explícitamente lo que sí se sabe o se omite.

### La calidad se mide en TODOS los paths

Causa raíz corregida: el flujo de **subir archivo** (`analizarImagen` en `PublicProductsPage.tsx`) no medía calidad — solo la cámara. Por eso una foto subida por archivo mostraba *"Calidad n/d"*. Hoy ambos caminos pasan por el mismo helper `analizarYBuscar(file, vehiculo)`, que:

1. resetea el aviso y la búsqueda pendiente anteriores (no se arrastra la métrica de otra foto);
2. mide con `analizarCalidadImagen`;
3. si el veredicto es `mala`, advierte **antes** de gastar la inferencia, sin bloquear (`Buscar igualmente` / `Tomar otra foto`).

El estado multi-vista (`haySegundaFoto`/`vistaPrimera`) queda intacto: la segunda foto sigue confirmando contra la primera.

### Jerarquía del panel

- **Desktop:** dos columnas (`lg:grid-cols-[42%_1fr]`). Izquierda la foto con su *bounding box*; derecha la identificación (Pieza identificada con Confianza del modelo, Categoría, Proveedor, OCR, Calidad y Vehículo opcional). **Mobile:** apilado, identificación primero.
- **Vehículo como bloque propio** debajo del resultado principal: "¿Para qué vehículo lo buscas?" con `marca + modelo + año`. El botón **"Verificar compatibilidad"** se habilita solo con los tres campos; mientras faltan, se muestra la ayuda: *"La foto identifica la pieza sin depender del vehículo, pero la compatibilidad solo se confirma si indicás marca, modelo y año."*
- **Mejores coincidencias:** Top 3 con la primera destacada y etiquetada **"Mejor coincidencia"**. El resto queda en `Ver otros N resultados` / `Mostrar menos`.
- **Footer sticky** que solo ofrece `Tomar otra foto` y `Cerrar`.

### Copy honesto de compatibilidad

| Situación | Chip por tarjeta | Global |
|---|---|---|
| verificada | `✓ Compatible` | conteo `X de N ...` |
| con vehículo, sin verificar | `⚠ No verificada` | idem |
| sin vehículo | `Vehículo no indicado` | **"Agrega tu vehículo para verificar compatibilidad."** |

Sin vehículo el aviso **no se repite por tarjeta** (sería ruido): la llamada a la acción es única y global (`explicabilidad.ts` solo emite el aviso por candidato cuando `hayVehiculo`).

### Score y evidencia

- El chip con evidencia de código dice **"Coincidencia por código"** (el número vive en el `title`, nunca se anuncia un score 0). `claseCoincide` → *"Coincidencia por tipo de pieza"*; si nada, *"Coincidencia por categoría"*.
- El tooltip separa las dos fuentes: *"Este score corresponde al motor de búsqueda del catálogo. No es la confianza del modelo de IA."*
- `ExplainCard` muestra 2 motivos a la vista y el resto tras `Ver evidencias (N)`.

### Detalles colapsables

- **OCR:** resumen `OCR · N código(s) detectado(s)` + `Ver códigos`, colapsado por defecto (el contenido sigue en el DOM para los tests).
- **Pipeline técnico:** `Ver detalles del análisis` (antes "Ver proceso de análisis") cierra la tira Foto → Control de calidad → YOLO → OCR → Catálogo → Compatibilidad → Disponibilidad. Sin medición de calidad el paso se rotula **"Control de calidad · no medido"**.

### Aterrizaje a la venta

El bloque autónomo "¿Cómo la recibís?" desapareció: Modalidad, Sucursal, Cantidad y (en delivery) Lugar/Entregar a viven dentro de **"Preparar venta"**, que aparece solo al seleccionar un candidato.

---

## 7. Limitaciones (decir esto en la defensa es parte de la defensa)

1. **No hay dataset ni ground truth.** En todo el historial Git de este repositorio solo existen tres CSV de metadatos de anotación, sin imágenes ni labels. No se pueden calcular confusion matrix, P/R ni mAP nuevos.
2. **Los umbrales de calidad no están calibrados** sobre el dataset; son heurísticas razonables con justificación física (luminancia, varianza del Laplaciano). Se pueden ajustar con datos reales cuando existan.
3. **Los pesos 10/8/6 del ranking no están calibrados**; son un orden por autoridad del campo.
4. **La confianza de dos fotos no se combina estadísticamente**, a propósito: sería presentar como probabilidad algo que nadie entrenó.
5. **Una foto de baja calidad no impide buscar**: la calidad es un consejo, no un requisito. Si el usuario lo decide, el modelo se ejecuta igual.
6. **El OCR identifica, no certifica compatibilidad.**
7. **La latencia:** el OCR en caliente suma en torno a `319 ms` (p50) en una foto de 120 KB, pero corre en paralelo con el clasificador, por lo que sobre el request completo el costo adicional medido fue de `0 ms`. Un solo worker compartido puede convertirse en cuello de botella bajo concurrencia alta. La calidad de imagen se mide en el navegador y no agrega latencia de red.
8. **El modelo sigue siendo V3.** No se modificó ni se reclama superioridad de ninguna versión V4, porque no hay con qué demostrarla.

---

## 8A. Disponibilidad por sucursal (recoger) en la UX compacta

**Fuente única y contrato público seguro.** Cada candidato lleva la disponibilidad por sucursal derivada del mismo origen que el flujo interno (`backend/src/modules/vision/availability.ts`), pero el endpoint público **no reabre** `disponibilidadPorSucursal` (sigue llegando `[]`). Se expone un DTO mínimo y específico:

```json
"disponibilidadPorSucursalPublica": [
  { "sucursalId": 101, "nombre": "Tienda 1", "nivel": "DISPONIBLE" }
]
```

- `nivel`: `DISPONIBLE` (>10 unidades) · `POCAS_UNIDADES` (>0) · `NO_DISPONIBLE` (0).
- **Solo** sucursales de tipo `TIENDA` son puntos de recogida; un almacén jamás aparece como opción de recoger.
- **El público nunca ve** el número exacto de unidades, `totalStock`, `locations`, inventarios internos ni campos financieros (`minStock`, costos, `price2`). El bucket es el máximo detalle.
- El contrato interno (`disponibilidadPorSucursal` + `stockPorSucursal`) no cambia y el serializador interno no emite el campo público.

**Comportamiento de la UI compacta** (`frontend/src/components/vision/DisponibilidadSucursales.tsx` + panel):

- Cada card muestra una sección **DISPONIBILIDAD** propia (hasta 3 sucursales, con glifo 🟢/🟡/⚪ y su estado). Si hay más de 3, un botón "Ver todas las sucursales (N)" expande; sin sucursales de recogida, "No disponible para recogida actualmente."
- El bloque "Preparar venta" solo aparece al pulsar **"Seleccionar para venta"** en la card. No vuelve el bloque largo global de rondas anteriores.
- En **recoger**, el selector lista solo sucursales válidas (nivel ≠ `NO_DISPONIBLE`) y auto-prefiere la primera; en **delivery** no hay selector de sucursal.
- La cantidad se ajusta con stepper (− +). El botón final es **"Continuar con venta"**. La UI de recogida evita la palabra "stock" (usa "disponible / sucursal"); la etiqueta de estado global que manda el backend (p. ej. "Sin stock") se muestra solo como estado del producto, nunca como cantidad.
- El `saleDraft` (localStorage `borrador_venta_vision`) conserva `itemCode`, `modalidad`, `sucursalId` y `sucursalNombre` exactamente como lo espera SalesPage (WB-8); delivery guarda `lugarEntrega`/`paraQuien` sin sucursal.

**Pruebas:** `frontend/src/components/vision/__tests__/VisionResultsPanel.disponibilidad.test.tsx` (3 sucursales, estados 🟢🟡⚪, nunca stock numérico, selector solo válidas, conserva sucursalId, delivery sin sucursal, independencia compatibilidad/disponibilidad, Top 3, expandir, caso vacío). En backend: `availability.test.ts` y `vision.routes.itest.ts` verifican el DTO mínimo, los buckets y que el almacén no sea punto de recogida.

---

## 8. Flujo completo (para la demo)

```
Foto capturada
   │
   ├─ Calidad de la imagen (Canvas, en paralelo, sin IA)
   │     ¿mala? → aviso antes de buscar → [Buscar de todos modos / Otra foto]
   │
   ├─ Envío al backend → ia-service (YOLO)  ─┐
   │                                          ├─ en paralelo
   ├─ OCR Tesseract (mismo worker compartido) ─┘
   │
   ├─ Validación de confianza (422 si es baja)
   ├─ Mapeo de categoría → catálogo
   ├─ Evidencia de código por candidato
   ├─ Ranking: verificado > código > compatibilidad
   ├─ Bounding box sobre la foto
   └─ Panel: evidencias, score de coincidencia, disponibilidad

Si la confianza quedó en zona media:
   Segunda foto → segunda inferencia real → regla de combinación →
   "Confirmado por 2 imágenes" | "Resultados inconsistentes" | "No confirmado"
```

La tira de chips superior (`PipelineStrip`) muestra este recorrido con valores reales de la foto que se acaba de analizar.

---

## 9. Qué mostrar en una demo de 2 minutos

| Tiempo | Qué hacer | Qué decir |
|---|---|---|
| 0:00–0:20 | Foto con buena iluminación | "El pipeline completo en una sola foto." |
| 0:20–0:45 | Señalar la tira de chips | "Foto → bounding box → YOLO con su confianza → OCR con los códigos leídos → calidad → candidatos → evidencias → stock." |
| 0:45–1:10 | Abrir "¿Por qué aparece este producto?" | "Cada línea tiene evidencia atrás. Si no hay evidencia, no aparece." |
| 1:10–1:30 | Señalar los dos números separados | "Confianza del modelo = YOLO. Score de coincidencia = motor de catálogo con pesos OEM 10, fábrica 8, item 6. Nunca los mezclamos." |
| 1:30–1:50 | Tomar una foto oscura o desenfocada | "Avisa antes de gastar la inferencia y no bloquea: el usuario decide." |
| 1:50–2:00 | Decir el límite | "No hay dataset, por eso no inventamos métricas ni probabilidad para la segunda foto." |

---

## 10. Archivos

| Archivo | Responsabilidad |
|---|---|
| `frontend/src/services/imageQuality.ts` | indicadores de calidad y veredicto |
| `frontend/src/services/multiView.ts` | regla de combinación de dos vistas |
| `frontend/src/services/explicabilidad.ts` | motivos por candidato |
| `frontend/src/components/vision/QualityBadge.tsx` | chip de calidad |
| `frontend/src/components/vision/MultiVistaPanel.tsx` | aviso de 2.ª foto y veredicto |
| `frontend/src/components/vision/ExplainCard.tsx` | "¿Por qué aparece este producto?" |
| `frontend/src/components/vision/PipelineStrip.tsx` | tira del recorrido |
| `frontend/src/components/vision/DetectionBox.tsx` | bounding box |
| `frontend/src/components/vision/DisponibilidadSucursales.tsx` | sección de disponibilidad por sucursal (pública) |
| `frontend/src/components/vision/VisionResultsPanel.tsx` | integración |
| `frontend/src/pages/PublicProductsPage.tsx` | flujo de captura, calidad y 2.ª foto |
| `backend/src/shared/utils/ocr.ts` | worker Tesseract compartido |
| `backend/src/modules/vision/availability.ts` | única fuente de disponibilidad, buckets y DTO público |
| `backend/src/modules/vision/hybridEvidence.ts` | pesos, evidencia y ranking |
| `backend/src/modules/vision/vision.service.ts` | orquestación del pipeline |

Tests: `frontend/src/services/__tests__/{imageQuality,multiView,explicabilidad}.test.ts` y `frontend/src/components/vision/__tests__/VisionResultsPanel.{escaneo,hibrido,ranking,ux,disponibilidad}.test.tsx` (más `frontend/src/pages/__tests__/PublicProductsPage.vision.test.tsx`).
