# V2-04B. Matriz de procedencia y condiciones de uso

Revisión del 11 de noviembre de 2026. Solo investigación y metadata. No se procesaron tablas, no se construyó curated ni se entrenó. La matriz completa y estructurada está en [source_provenance_matrix.json](source_provenance_matrix.json).

## Decisión por fuente

| Fuente | Licencia | Académico | Comercial | Redistribución | Paso a profiling |
|---|---|---|---|---|---|
| automotive_spare_parts_demand | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | BLOCKED_LICENSE |
| monash_car_parts | VERIFIED | VERIFIED | VERIFIED | VERIFIED | APPROVED_ACADEMIC_ONLY |
| uci_online_retail_ii | VERIFIED | VERIFIED | VERIFIED | VERIFIED | APPROVED_ACADEMIC_ONLY |
| m5_walmart | PARTIALLY_VERIFIED | UNKNOWN | UNKNOWN | UNKNOWN | BLOCKED_LICENSE |
| corporacion_favorita | VERIFIED | PARTIALLY_VERIFIED | RESTRICTED | RESTRICTED | BLOCKED_ACCESS_CONFIRMATION |

VERIFIED indica evidencia explícita sobre ese aspecto, con sus condiciones. PARTIALLY_VERIFIED indica aspectos pendientes. UNKNOWN no equivale a permiso. RESTRICTED indica límites, no necesariamente prohibición de todo uso. La verificación global es parcial en las cinco fuentes porque la ruta real de adquisición y la identidad binaria respecto al proveedor no quedaron certificadas. La licencia sí puede estar verificada por la publicación primaria.

## Identificación y papel de las fuentes

### fable.intermittent 0.3.0, paquete con auto, raf, pasta y tinyM5

**Proveedor y autores:** Proyecto fable.intermittent, empaquetador. El propietario original de Auto no está identificado con suficiente detalle. Autores o responsables de referencia: Stefano Damato, Lorenzo Zambon, Dario Azzimonti.

**Fuente primaria:** [fable.intermittent 0.3.0, paquete con auto, raf, pasta y tinyM5](https://github.com/StefanoDamato/fable.intermittent).

**Datos:** auto y raf mensuales, pasta diaria según proveedor, tinyM5 diaria Geografía: UNKNOWN. Moneda: UNKNOWN/no declarada.

**Variables:** series_id, index, value, promotion (pasta), item_id/store_id/date/sell_price (tinyM5).

**Licencia de datos:** UNKNOWN. **Cita recomendada:** Citar el paquete y la fuente original de cada subdataset. Para auto: Türkmen et al. (2021), DOI 10.1371/journal.pone.0259764.

**Papel conceptual:** DIRECT_DOMAIN_REFERENCE, DEMAND_PATTERN_REFERENCE. No implica transformación o calibración autorizada.

**Cobertura:** UNKNOWN para el conjunto completo. No se rellenó utilizando otro dataset o páginas secundarias.

**Límites de la revisión:**
- Los 121 archivos no son un único dataset. No se ejecutó código R ni se decodificaron RDA.
- LGPL >= 3 corresponde al software. No acredita licencia de Auto o RAF.
- El calendario de auto y raf se construye con fechas iniciales fijadas en data-raw/build_datasets.R. No se certifican como fechas originales de observación.
- Conflicto pasta: R/data.R declara CC BY 4.0, mientras Mendeley versión 1 declara CC BY-NC 3.0. Prevalece como evidencia la publicación primaria, sin relicenciar RAW.
- DIRECT_DOMAIN_REFERENCE es potencial únicamente para auto, no para RAF, pasta o tinyM5. Uso bloqueado hasta aclarar derechos del subdataset.

| Subdataset | Archivos de datos | Tamaño documental | Licencia de datos |
|---|---|---|---|
| auto | fable.intermittent-main/data-raw/Auto.csv, fable.intermittent-main/data/auto.rda | 3000 series, MONTHLY | UNKNOWN |
| raf | fable.intermittent-main/data-raw/RAF.csv, fable.intermittent-main/data/raf.rda | 5000 series, MONTHLY | UNKNOWN |
| pasta | fable.intermittent-main/data-raw/pasta.csv, fable.intermittent-main/data/pasta.rda | 118 series, DAILY, según Mendeley. El constructor usa una columna llamada week, sin demostrar agregación semanal. | CC BY-NC 3.0 |
| tinyM5 | fable.intermittent-main/data/tinyM5.rda | 280 series, DAILY | Subject to M5 Competition Rules |

Solo auto tiene papel automotriz directo potencial. RAF es aeronáutico. Pasta y tinyM5 son retail complementario. No se aprueba el paquete completo por contener un subdataset con licencia conocida.

### Car Parts Dataset (with Missing Values), versión 2

**Proveedor y autores:** Monash Time Series Forecasting Repository / Zenodo, extraído de expsmooth Autores o responsables de referencia: Rakshitha Godahewa, Christoph Bergmeir, Geoff Webb, Rob Hyndman, Pablo Montero-Manso.

**Fuente primaria:** [Car Parts Dataset (with Missing Values), versión 2](https://zenodo.org/records/4656022).

**Datos:** 2674 series mensuales, 51 periodos documentados. Cada serie representa ventas de repuestos, no una tienda RepuestoPro. Geografía: Empresa automotriz de Estados Unidos según sección 5.2 de Türkmen et al. (2021). No identifica países por registro.. Moneda: UNKNOWN/no declarada.

**Variables:** series_name, start_timestamp, monthly values, missing values.

**Licencia de datos:** CC BY 4.0. **Cita recomendada:** Godahewa, R., Bergmeir, C., Webb, G., Hyndman, R., & Montero-Manso, P. (2020). Car Parts Dataset (with Missing Values), versión 2. Zenodo. https://doi.org/10.5281/zenodo.4656022

**Papel conceptual:** DIRECT_DOMAIN_REFERENCE, DEMAND_PATTERN_REFERENCE. No implica transformación o calibración autorizada.

**Cobertura documental:** 1998-01 a 2002-03. No representa perfilado de filas.

**Límites de la revisión:**
- La licencia CC BY 4.0 consta explícitamente en la API y en la metadata HTML de Zenodo.
- El encabezado local coincide con descripción, frecuencia y periodo oficiales. No se descargó el ZIP para comparar bytes del TSF interno.
- La URL y fecha de adquisición real del archivo local siguen desconocidas. No confundir el MD5 del ZIP publicado con el SHA-256 del TSF extraído.
- Conservar atribución y licencia e indicar cambios futuros. No usar estas series como historia real de RepuestoPro.

### Online Retail II

**Proveedor y autores:** UCI Machine Learning Repository. Comercio electrónico británico no identificado por nombre Autores o responsables de referencia: Daqing Chen.

**Fuente primaria:** [Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii).

**Datos:** 1067371 registros documentados. Son líneas de transacción, no necesariamente facturas únicas. Geografía: Empresa del Reino Unido, clientes en varios países. Moneda: GBP.

**Variables:** InvoiceNo/Invoice, StockCode, Description, Quantity, InvoiceDate, UnitPrice/Price, CustomerID/Customer ID, Country.

**Licencia de datos:** CC BY 4.0. **Cita recomendada:** Chen, D. (2012). Online Retail II [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5CG6D

**Papel conceptual:** WHOLESALE_PATTERN_REFERENCE, CANCELLATION_REFERENCE, PRICE_PATTERN_REFERENCE, DEMAND_PATTERN_REFERENCE. No implica transformación o calibración autorizada.

**Cobertura documental:** 2009-12-01 a 2011-12-09. No representa perfilado de filas.

**Límites de la revisión:**
- No es de autopartes. Muchas personas compradoras son mayoristas según UCI, pero no se identifican todas las líneas mayoristas con una etiqueta.
- UCI define cancelación por prefijo c en InvoiceNo. No se calcularon cantidades negativas, anulaciones o distribución.
- La ficha informa faltantes, pero su API devuelve has_missing_values=no y variables vacías. Resolver esa contradicción en profiling, sin asumir limpieza.
- Los nombres Price y UnitPrice son variantes entre archivo y descripción, no se renombraron columnas.
- No se verificó equivalencia binaria con una descarga oficial. No publicar identificadores de clientes innecesarios. Mantener atribución y señalar transformaciones.

### M5 Forecasting - Accuracy

**Proveedor y autores:** Walmart / organizadores de M5 / Kaggle Autores o responsables de referencia: Spyros Makridakis, Evangelos Spiliotis, Vassilios Assimakopoulos.

**Fuente primaria:** [M5 Forecasting - Accuracy](https://www.kaggle.com/competitions/m5-forecasting-accuracy).

**Datos:** 3049 productos en 10 tiendas, 30490 series inferiores. Ventas diarias y precios semanales por producto y tienda. Geografía: Estados Unidos: California, Texas y Wisconsin. Moneda: USD.

**Variables:** item_id, store_id, state_id, d_1..d_1941, wm_yr_wk, sell_price, date, event_name/type, snap_CA/TX/WI.

**Licencia de datos:** Subject to Competition Rules, no licencia CC verificada. **Cita recomendada:** Walmart y M5 (2020), M5 Forecasting - Accuracy, Kaggle. Publicación asociada: Makridakis, Spiliotis y Assimakopoulos (2022), DOI 10.1016/j.ijforecast.2021.11.013.

**Papel conceptual:** PRICE_PATTERN_REFERENCE, STORE_PATTERN_REFERENCE, CALENDAR_REFERENCE, DEMAND_PATTERN_REFERENCE. No implica transformación o calibración autorizada.

**Cobertura documental:** 2011-01-29 a 2016-05-22. No representa perfilado de filas.

**Límites de la revisión:**
- No representa autopartes ni ventas en Bolivia. No convertir directamente sus IDs a Product.id.
- Los cinco nombres de archivo y los extremos d_1913/d_1941 concuerdan con la página oficial y las cabeceras locales.
- d_1941 corresponde al 22 de mayo de 2016 desde el inicio declarado. La guía también menciona 19 de junio de 2016, que incluye el horizonte posterior. No confundir calendario con etiquetas disponibles.
- La página Data declara Subject to Competition Rules. El texto específico de Rules no resultó legible y la respuesta HTML contiene un desafío de acceso. No se eludió.
- No extrapolar las reglas de Favorita ni interpretar una licencia de código de soluciones como permiso de datos. Falta comprobar uso académico, comercial y redistribución.

### Corporación Favorita Grocery Sales Forecasting (competición 2017)

**Proveedor y autores:** Corporación Favorita C.A. / Kaggle Autores o responsables de referencia: Corporación Favorita C.A..

**Fuente primaria:** [Corporación Favorita Grocery Sales Forecasting (competición 2017)](https://www.kaggle.com/competitions/favorita-grocery-sales-forecasting).

**Datos:** Diaria por producto y tienda. Transacciones por tienda y día, eventos y promociones. No confundir con la competición Store Sales de 2021 agregada por familia. Geografía: Ecuador. Moneda: UNKNOWN/no declarada.

**Variables:** date, store_nbr, item_nbr, unit_sales, onpromotion, transactions, family/class/perishable, city/state/type/cluster, holidays_events, oil.

**Licencia de datos:** Reglas específicas de Corporación Favorita Grocery Sales Forecasting, sección 7. No licencia CC verificada. **Cita recomendada:** Corporación Favorita C.A. (2017). Corporación Favorita Grocery Sales Forecasting. Kaggle. Cita recomendada, no obligación de atribución contractual certificada.

**Papel conceptual:** PROMOTION_REFERENCE, STORE_PATTERN_REFERENCE, CALENDAR_REFERENCE, DEMAND_PATTERN_REFERENCE. No implica transformación o calibración autorizada.

**Cobertura:** UNKNOWN para el conjunto completo. No se rellenó utilizando otro dataset o páginas secundarias.

**Límites de la revisión:**
- Las reglas 7.A contemplan investigación y educación después de aceptarlas. 7.B restringe compartir los datos con personas no participantes o que no aceptaron las reglas.
- No se aceptaron términos por el usuario ni se comprobó su aceptación previa. Mantener bloqueado el acceso analítico hasta acreditar el cumplimiento de esas condiciones.
- Los ocho archivos coinciden por nombre con la competición de 2017. No se extrajeron 7Z ni se verificaron los bytes contra el proveedor.
- No se certificó aquí el rango exacto de train mediante una página primaria legible o el archivo. Se mantiene temporal_coverage=null en lugar de copiar fechas de blogs o de la competición de 2021.
- La descripción de Data no estuvo legible directamente. Se identificaron variables con documentación de la competición reproducida en una entrada de datos de Kaggle, utilizada solo como corroboración secundaria.
- Las devoluciones pueden aparecer como unit_sales negativas y hay cantidades fraccionarias según esa documentación. Revisarlo posteriormente, sin trasladar esas reglas a ventas brutas de RepuestoPro.
- oil no es tipo de cambio Bs/USD ni precio unitario del producto. No inferir moneda de las columnas solo por el país.

## SHA-256 y snapshot_id

No hay que hacer coincidir hashes de objetos distintos. files[].sha256 identifica los bytes originales. inventory_sha256 identifica el JSON canónico del inventario ordenado de ruta relativa, tamaño y hash por archivo. snapshot_id es sha256- más los primeros 24 caracteres hexadecimales de inventory_sha256. No depende de la licencia o descripción actualizada.

| Fuente | Hash del archivo único | Hash del inventario | snapshot_id |
|---|---|---|---|
| monash_car_parts | 818470cd0a65679b38b48a20e4d916d11fbd2ccbf7f5f9d8d97093dd6c784600 | d69d3412b9c45248f1c9c44154b50bb6bd9f58e6a6132957b839f8d493b1fd0e | sha256-d69d3412b9c45248f1c9c441 |
| uci_online_retail_ii | bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980 | 4dc26799b20addb7559df7e26ac855c20d780def99542912433b6f553d3e18f4 | sha256-4dc26799b20addb7559df7e2 |

No se modificó ningún identificador para aparentar coincidencia. Tampoco se comparó el MD5 del ZIP publicado por Zenodo con el SHA-256 de su TSF local, porque corresponden a objetos distintos.

## Límites y siguiente paso

Monash y UCI pueden pasar a V2-04C para perfilado académico local con atribución y conservación de licencia. No se ejecutó ese paso. Automotive y M5 solo deben continuar con aclaración documental de derechos. Favorita requiere acreditar acceso conforme a reglas y aceptación previa por quienes accedan. No publicar sus RAW ni asumir que disponer del archivo equivale a cumplir condiciones.

No se descartó definitivamente ninguna fuente. Las fuentes bloqueadas no se analizan ni calibran mientras se aclaran sus permisos. Ninguna de estas cinco fuentes aporta por sí sola una historia acreditada de tipo de cambio Bs/USD o tiempos de importación de RepuestoPro. Tampoco demuestra elasticidad causal de precios de autopartes.

## Evidencia primaria

- [metadata.license.id, creators, description, doi](https://zenodo.org/api/records/4656022): CC BY 4.0 explícita para Car Parts con faltantes. Metadata guardada en tmp/provenance-20261111-01/monash_zenodo_api.txt.
- [Rights y metadata HTML de licencia](https://zenodo.org/records/4656022): CC BY 4.0 corroborada en HTML, aunque el lector web inicialmente no mostró el texto de licencia.
- [Dataset Information, Additional Variable Information, Citation, License](https://archive.ics.uci.edu/dataset/502/online+retail+ii): CC BY 4.0, Daqing Chen, GBP, cancelación por prefijo c y periodo 2009-12-01 a 2011-12-09.
- [Freedoms and terms](https://creativecommons.org/licenses/by/4.0/): Permite compartir y adaptar, también comercialmente, manteniendo crédito, enlace de licencia e indicación de cambios.
- [Licence y descripción de versión 1](https://data.mendeley.com/datasets/njdkntcpc9/1): CC BY NC 3.0 para pasta, contradice CC BY 4.0 en documentación del paquete R.
- [General Competition Rules, 7.A y 7.B](https://www.kaggle.com/competitions/favorita-grocery-sales-forecasting/rules): Contenido primario indexado: investigación y educación tras aceptar reglas, restricciones de acceso y redistribución. No se aceptaron términos ni se certificó aceptación previa.
- [Files, Size y License](https://www.kaggle.com/c/m5-forecasting-accuracy/data): Cinco CSV, 450.47 MB, Subject to Competition Rules. Nombres y cabeceras locales consistentes, sin comparación binaria con descarga remota.
- [Acceso directo](https://www.kaggle.com/competitions/m5-forecasting-accuracy/rules): Sin contenido de reglas legible. HTML capturado contiene desafío de acceso. No se utilizó una copia secundaria ni se extrapolaron reglas de otra competición.
- [auto, raf, pasta, tinyM5](https://raw.githubusercontent.com/StefanoDamato/fable.intermittent/main/R/data.R): Documentación del empaquetador. Se contrastó con copia local y fuentes originales, sin ejecutar R.
- [5.2 Real data y Data Availability](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0259764): Distingue Auto, Car Parts, RAF y M5 como datos reales. La licencia del artículo no demuestra derechos de cada archivo de terceros.
- [The dataset, páginas 3 a 5](https://storage.googleapis.com/kaggle-forum-message-attachments/772349/15032/M5-Competitors-Guide-Final-10-March-2020.pdf): Jerarquía, tiendas, productos, unidades, calendario y precios. No se usó como sustituto de cláusulas de licencia.

## Publicaciones asociadas

- automotive_spare_parts_demand: [Forecasting intermittent and sparse time series: A unified probabilistic framework via deep renewal processes](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0259764), 2021. Auto y RAF, antecedentes. No licencia de datos.
- monash_car_parts: [Monash Time Series Forecasting Archive](https://arxiv.org/abs/2105.06643), 2021. Publicación del repositorio. El DOI del dataset es distinto.
- m5_walmart: [M5 accuracy competition: Results, findings, and conclusions](https://doi.org/10.1016/j.ijforecast.2021.11.013), 2022. Artículo de resultados, no DOI del dataset ni licencia.

Para UCI Online Retail II y Favorita no se identificó aquí un paper específico de esa edición. No confundir Online Retail II con Online Retail de un solo año. Favorita no recibe CANCELLATION_REFERENCE solo por tener devoluciones negativas.
