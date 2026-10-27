# Plan de saneamiento de RepuestoPro antes de H4

## SEGUNDA AUDITORÍA. Alcance y decisión comercial vigente

La segunda revisión del 27 de octubre de 2026 parte del código saneado, sin repetir la implementación anterior. La nueva decisión comercial sustituye los dos niveles normales por POR MENOR y POR MAYOR. Las secciones del primer saneamiento se conservan como registro fechado. Su política de PRICE1 y PRICE2 ya no es la política vigente de esta ronda. H4 permanece pausado.

| Campo | Uso encontrado antes de esta ronda | Dónde se utiliza | Significado comprobado | Necesidad | Semántica final |
|---|---|---|---|---|---|
| price1 | Catálogo público, venta normal por defecto, sugerencia de costo con margen bajo | Products, vision, SalesPage, precios, Excel, móvil y fixtures | Precio público efectivo. Algunos textos antiguos todavía lo llaman mayorista | CAMPO A CONSERVAR | Fuente autorizada de POR MENOR |
| price2 | Segundo nivel normal, selección automática desde visión, sugerencia con margen alto | SalesPage, SalesScreen, precios, inventario, importaciones y pruebas | Segundo importe sin una necesidad comercial actual aprobada | LEGACY, pendiente de revisión antes de migración física | Se conserva en la base, sin seleccionar nuevas ventas ni condicionar la política económica |
| wholesalePrice | Precio explícito del endpoint mayorista, configurable y nullable | Wholesale, productos, precios, Excel y política compartida | Precio de venta por mayor, sin fallback | CAMPO A CONSERVAR | Única fuente de POR MAYOR en ambos flujos |

La inspección encontró además selección automática de price2 al llegar desde visión, etiquetas contradictorias en Precios e InventoryScreen móvil, notas mayoristas sujetas al permiso del módulo normal y datos completos de Product en detalles de venta y devolución. Se corrigió la exposición de costos. La importación de facturas permitía registrar de nuevo todas las filas, con ingreso repetido de stock. Ahora usa proveedor y huella del archivo, con bloqueo transaccional, sin agregar columnas ni cambiar Neon. El resultado, sus límites y las matrices vigentes están al final, bajo SEGUNDA AUDITORÍA. Resultados.

La consulta productiva fue una transacción de solo lectura. Confirmó 247 ventas, 21 desde almacén, 200 diferencias con la ubicación actual del vendedor, 15 grupos de detalles repetidos, tres productos sin categoría, cero valores en quality y cero nulos en AuditLog.userId y targetType. Ningún dato se reparó automáticamente. La revisión local incluyó pruebas de comportamiento, contratos, migraciones y pantallas. El resultado definitivo se registra en la sección de resultados de esta ronda.

Fecha de inicio y verificación final: 27 de octubre de 2026. Estado: correcciones locales validadas. Cierre integral condicionado a los pendientes documentados.

## Objetivo y fuentes

El saneamiento busca corregir contradicciones entre ventas, inventario, precios, devoluciones, reportes y permisos antes de iniciar el experimento predictivo. La solicitud del equipo autoriza las correcciones por fases. Se conservan Express, Prisma y los clientes actuales. No se implementará H4, no se generará su dataset ni se entrenarán modelos.

Las fuentes son Ejercicio 1.pdf, la auditoría `AUDITORIA_MODELO_PREDICTIVO_H4.md` y los archivos actuales del proyecto. Los documentos recibidos en Downloads sirven como antecedentes. Cuando difieren de la solicitud actual, prevalece esta última. Este archivo y `H4_MODELO_PREDICTIVO_PROPUESTA_DETALLADA.md` son las versiones oficiales dentro del proyecto.

## Problemas y reglas que se deben unificar

La auditoría encontró una selección de precios en la interfaz que el servidor ignoraba, ajustes de inventario expuestos a concurrencia, devoluciones que tomaban solo la primera línea de un producto, reportes limitados a una página y diferencias en fechas y permisos. También encontró registros demo sin procedencia individual certificable y diferencias entre Prisma y Neon.

`price1` significa primer nivel de venta normal. `price2` significa segundo nivel de venta normal. Ninguno significa automáticamente precio mayorista. El cliente comunica `PRICE1` o `PRICE2`, mientras el servidor consulta el precio y calcula subtotal y total. Un importe arbitrario del cliente nunca determina el cobro.

`wholesalePrice` es exclusivo de venta por mayor. Debe estar configurado, ser positivo y no superar ninguno de los dos precios normales. Si existe `Product.cost`, los tres precios deben ser iguales o superiores a ese costo. Una configuración contradictoria se rechaza o se informa. Nunca se cambian precios productivos automáticamente. Un precio menor para el cliente no significa mayor margen unitario para el negocio.

La venta normal sale exclusivamente de una `Location` de tipo `TIENDA`. El usuario TIENDA opera en su ubicación. ADMIN elige expresamente una tienda. Una venta mayorista puede salir de una TIENDA o ALMACEN elegido expresamente por ADMIN, porque el proyecto ya registra mayoristas desde almacenes. TIENDA conserva su alcance propio. No se elige silenciosamente la primera ubicación.

La venta bruta, la devolución y el cobro son conceptos diferentes. CREDITO registra una obligación pendiente, no dinero cobrado. `Sale.userId` identifica al responsable autenticado. `Sale.seller` es una etiqueta adicional. Los estados de ProductRequest no son estados de Sale.

## Fases y seguimiento

| Fase | Trabajo | Estado al cierre |
|---|---|---|
| 1 | Precios, ventas, pagos, ubicación y clientes | Corregida y probada |
| 2 | Ajustes de inventario y concurrencia | Corregida y probada |
| 3 | Devoluciones sobre líneas repetidas y concurrencia | Corregida y probada |
| 4 | Solicitudes, movimientos y reposición reactiva | Corregida y probada |
| 5 | Costos, fórmulas y edición de precios | Corregida y probada |
| 6 | Reportes completos y dashboard | Corregida y probada |
| 7 | Fechas de negocio America/La_Paz | Corregida y probada |
| 8 | Permisos de API y clientes | Corregida y probada |
| 9 | Protección de generadores demo y procedencia | Corregida y probada |
| 10 | Prisma, migraciones y diferencias físicas | Verificada localmente, producción pendiente |
| 11 | Reglas compartidas con beneficio funcional | Corregida y probada |
| 12 | Límites y validación numérica | Corregida y probada |
| 13 | Regresión de búsqueda mediante imagen | Verificada sin cambiar H3 |
| 14 | Matriz funcional del ejercicio | Completa, con cinco cumplimientos parciales |
| 15 | Pruebas finales y decisión de cierre | 529 pruebas aprobadas, decisión documentada |

Después de cada fase se registrarán el problema, su causa, el comportamiento anterior, la corrección, el comportamiento actual, los archivos, las pruebas y el resultado. Una fase no se considera terminada por haber editado archivos. Los nuevos hallazgos se registrarán antes de corregirlos.

## Registro de cambios por fase

### Fase 1. Precios y ventas

El problema era que la interfaz elegía un precio y la API imponía otro. La causa era una interpretación contradictoria de price1 y price2. Ahora el cliente envía PRICE1 o PRICE2 y el servidor resuelve el importe desde Product. Los importes legacy se ignoran. Por compatibilidad, una petición antigua sin nivel usa PRICE1 de forma documentada, nunca un precio inferido del cliente. Los clientes actualizados siempre envían el nivel. La venta mayorista exige wholesalePrice y no recurre a price1.

Se eliminaron las ubicaciones elegidas silenciosamente. ADMIN selecciona el origen y una venta normal no puede salir de ALMACEN. La edición de producto y precio rechaza valores bajo costo o un mayorista superior a los normales. La aplicación masiva de precios es transaccional. Los importadores se revisarán en la fase 5. El crédito asignado inicialmente ya no se cuenta como dinero cobrado en el resumen de pagos ni en la nota del servidor. Un cobro posterior reduce el saldo pendiente.

Archivos principales: sales.routes.ts, wholesale.routes.ts, products.routes.ts, prices.routes.ts, payments.routes.ts, saleItems.ts y los nuevos helpers pricing.ts y saleLocation.ts. Clientes afectados: SalesPage, WholesalePage, InventoryPage, PricesPage y SalesScreen móvil con su utilidad de precios. Se actualizaron los tests de la política anterior y se añadieron pruebas del nuevo contrato.

Pruebas: 27 de integración local de ventas y precios, cinco nuevas de saneamiento, cinco unitarias de reglas, 15 de interfaz de ventas y tres del cliente móvil. Todas aprobaron. Typecheck backend y frontend aprobados. El primer intento de Vitest dentro del sandbox quedó bloqueado al iniciar workers y se interrumpió. La ejecución con un worker fuera del sandbox aprobó. No se escribió en Neon. Resultado: fase coherente para continuar.

Hallazgos nuevos registrados antes de corregir: los cobros de crédito se bloqueaban porque se contaba CREDITO como pago recibido. El importador de facturas usa almacenamiento en disco pero intenta leer buffer, un defecto que se corregirá en la fase 5. Los ajustes absolutos requieren una precondición de stock para no sobrescribir una lectura desactualizada, además de una transacción.

## Pruebas y restricciones

Las pruebas de integración se ejecutarán únicamente en una base local dedicada. No se ejecutarán seeds, limpiezas, migraciones ni DDL sobre Neon. Las consultas productivas, si son necesarias, serán SELECT dentro de una transacción de solo lectura. No se borrarán ni etiquetarán arbitrariamente los 247 registros observados en la auditoría anterior.

Se ejecutaron pruebas unitarias, de integración local, comprobaciones de tipos y compilaciones locales. Cada resultado distingue pruebas aprobadas, fallidas y omitidas. No se usaron comandos Git. La lista final de archivos se contrastó con el registro de edición y las fechas de modificación. El inventario temporal inicial de huellas no estuvo disponible al cierre, por lo que no se afirma una comparación completa contra ese archivo ni contra el historial Git.

## Matriz de cumplimiento contra Ejercicio 1.pdf

La fase 14 contiene la matriz completa de 19 requisitos con evidencia, corrección y pendiente. CUMPLE se refiere a los flujos locales comprobados, sin equivaler a certificación productiva o a una prueba manual exhaustiva de cada pantalla.

## Pendientes y criterio de preparación para H4

El historial actual no se puede declarar comercial real. Los scripts demo no deben seguir escribiendo sobre producción. Las diferencias físicas de Neon deberán quedar resueltas mediante otro procedimiento aprobado o registradas con su riesgo, sin aplicar cambios productivos en esta tarea.

RepuestoPro podrá considerarse preparado para comenzar el experimento académico H4 cuando las reglas de precios sean únicas, los clientes respeten el cálculo del servidor, el stock y las devoluciones sean coherentes, los reportes estén completos, las fechas y permisos estén alineados y las pruebas relevantes tengan resultados verificables. La matriz debe justificar todos los incumplimientos. Estar preparado para un experimento sintético no significa disponer de datos reales suficientes para un modelo comercial.

## Estado final

Las correcciones locales están verificadas mediante 529 pruebas aprobadas y compilaciones. RepuestoPro aún no se declara completamente listo para H4: quedan precios y permisos productivos por revisar, diferencias de esquema con una cadena pendiente de comprobar sobre una copia de Neon y verificaciones visuales sin realizar. No se implementó H4. El equipo debe revisar y aceptar este cierre condicionado antes del siguiente paso. No se realizó deploy ni se usaron comandos Git.

### Fase 2. Inventario y concurrencia

El ajuste leía un stock y escribía después un valor absoluto sin proteger la lectura. Además, el log era una operación independiente. Ahora bloquea la fila, comprueba expectedStock y guarda cambio y AuditLog dentro de la misma transacción. La interfaz conserva el valor leído. Si una venta lo cambia, el ajuste devuelve 409 y solicita recargar. No se sobreescribe silenciosamente una venta concurrente.

Archivos: inventory.routes.ts, InventoryPage.tsx, inventory.routes.itest.ts y saneamiento.itest.ts. Pruebas locales: 25 aprobadas, incluidas las de lectura y permisos existentes y una regresión de venta entre lectura y ajuste. Se comprobó el valor anterior y posterior del log. Resultado: fase coherente. Movimientos y solicitudes se validarán en su fase específica.

### Fase 3. Devoluciones

El problema era validar contra la primera línea de un producto aunque hubiera varias. Ahora se suman cantidades y valor histórico dentro de la transacción. Sale se bloquea antes de sus líneas para coordinar devoluciones y cobros. La suma de devoluciones se relee bajo bloqueo. Para líneas a precios distintos se devuelve el valor proporcional histórico del producto, redondeando el acumulado y restando lo ya reembolsado. Así una devolución total conserva el valor vendido. No se toman precios actuales del catálogo.

ReturnsPage agrupa por productId y calcula el mismo importe acumulado. El servidor valida ese importe y sigue siendo la autoridad. Se conserva la devolución parcial y el reintegro en Sale.locationId. Archivos: returns.routes.ts, ReturnsPage.tsx y returns.itest.ts. Pruebas locales: cinco aprobadas, incluidas líneas duplicadas a precios distintos, devolución parcial y total, exceso y dos devoluciones concurrentes. Resultado: fase coherente. No se alteraron las devoluciones productivas existentes.

### Fase 4. Solicitudes y movimientos

Se confirmó que cambiar una solicitud a ENTREGADO no realizaba un movimiento. Ahora entregar exige seleccionar el almacén, descuenta su inventario, ingresa la misma cantidad al destino y registra Movement dentro de la transacción del estado e historial. Confirmar recepción no vuelve a ingresar unidades. No se puede cancelar una entrega cuyo inventario ya fue trasladado. Se conserva la convención del sistema de registrar el traslado completo al entregar, no un stock en tránsito que el schema no representa.

moveStock.ts concentra el traslado y bloquea filas en orden estable. La ruta de movimientos permite las ubicaciones que muestra su interfaz, siempre distintas. Si se vincula una solicitud, comprueba producto, cantidad, destino y estado PREPARANDO. RequestsPage permite escoger el almacén. Se corrigió además la lectura de la respuesta de ubicaciones en MovementsPage.

Pruebas: 21 locales aprobadas en movimientos y solicitudes. Incluyen entrega y recepción sin doble ingreso, concurrencia de movimientos, solicitudes duplicadas y reposición automática. Archivos: moveStock.ts, movements.routes.ts, requests.routes.ts, RequestsPage.tsx, MovementsPage.tsx y movements.itest.ts. La reposición sigue siendo reactiva, basada en stock y reglas actuales. No utiliza predicción ni H4. Resultado: fase coherente.

### Fase 5. Costos y precios

La fórmula de costo se confirma como costo unitario USD por tipo de cambio por uno más gastos sobre cien. landedCost aplica esa regla en servidor y redondea al final. La interfaz envía el costo USD original. El costo vigente del producto se sincroniza con el registro más reciente. Crear, editar o eliminar un costo registra auditoría dentro de la misma transacción. Una nueva configuración bajo costo se rechaza y se revierte, sin modificar precios existentes automáticamente.

El importador de factura se corrigió para leer el archivo guardado en disco. Ahora conserva cada factura como historia, en lugar de sobrescribir una previa del mismo proveedor y producto. Se puede indicar una ubicación de ingreso. Si se indica, la cantidad incrementa su inventario y se registra el ingreso. Si no se indica, solo se registra el costo. Editar un costo no vuelve a ingresar stock. La política de precios también cubre el importador mayorista. La pantalla diferencia precios normales sugeridos, actuales y por mayor.

Archivos: costing.ts, costs.routes.ts, wholesale.routes.ts, CostsPage.tsx y PricesPage.tsx. Pruebas: tres integraciones locales nuevas aprobadas, con fórmula del servidor, rollback por costo contradictorio y factura Excel con ingreso de cantidades. Typecheck backend aprobado. Resultado: fase coherente. Pendiente registrado: el schema no tiene una clave única de factura para evitar toda reimportación manual duplicada. No se afirma idempotencia comercial de importaciones distintas.

### Fase 6. Reportes

El diario dependía de una sola página de ventas y devoluciones, y agrupaba por nombres. Se creó el endpoint real GET /api/reports/daily, que agrega en PostgreSQL todo el intervalo solicitado. Los grupos conservan productId y locationId aunque dos entidades tengan el mismo nombre. Las devoluciones se agrupan por su propia fecha. La respuesta diferencia ventas brutas, devoluciones y neto. El diario consume esta agregación. El listado del reporte de ventas recupera todas sus páginas para no exportar solo la primera.

Archivos: dailyReport.ts, reports.routes.ts y ReportsPage.tsx. Pruebas: diez integraciones locales aprobadas, incluida una con 1.005 ventas y productos de igual nombre. En la primera ejecución esa prueba detectó una conversión de fecha dependiente de la zona SQL. Se corrigió convirtiendo los parámetros a UTC antes de compararlos y se repitió satisfactoriamente. Typecheck frontend aprobado. Dashboard y presentación de fechas se completarán en la fase 7. Resultado: fase coherente.

### Fase 7. Fechas

El dashboard usaba la zona del servidor y varias pantallas la zona del navegador. Ahora los límites del dashboard y movimientos usan America/La_Paz. El mes por defecto de reportes también utiliza esa zona. La nota de venta del servidor la fija expresamente. Se centralizó la presentación de fechas y horas en businessDate.ts para las pantallas relacionadas. Una clave de calendario como 2026-02-01 se muestra como ese día, sin retroceder por interpretarla como medianoche UTC.

Archivos: rangoFechas.ts, dashboard.routes.ts, movements.routes.ts, reports.routes.ts, sales.routes.ts, businessDate.ts y pantallas de ventas, mayoristas, devoluciones, solicitudes, movimientos, costos, reportes y dashboard. Pruebas: 12 unitarias backend y seis frontend aprobadas, además de la frontera de mes en la agregación diaria ya probada. Typecheck backend y frontend aprobados. Resultado: fase coherente.

### Fase 8. Permisos

La API de ventas, mayoristas, devoluciones, solicitudes, inventario, costos, precios y reportes exige ahora su permiso de módulo, además de las restricciones de rol y ubicación que ya existían. Los cobros aceptan permiso de ventas o ventas-mayor. Se conserva el alias productos para inventario. Se mantuvo primero el rechazo por rol donde ya existía, para conservar su contrato. Las pruebas detectaron esa precedencia y se ajustó el orden de middleware.

Sidebar se alinea con los roles de RoleRoute. Si falla la carga de permisos, un cliente no administrador ya no obtiene permisos inventados. El móvil consulta los permisos y filtra sus pantallas y botones. Los roles de prueba y los defaults demo incluyen mayoristas y reportes para TIENDA, reportes para INVENTARIO. Esto no modifica los permisos ya guardados en Neon. Un administrador deberá revisarlos mediante el panel antes de desplegar estos cambios.

Pruebas: 14 integraciones locales de autenticación, módulos, cache y saneamiento aprobadas. La prueba nueva comprueba que retirar ventas bloquea la API aunque el token siga válido. No se alteraron JWT, Helmet o rate limiting. Archivos: routers afectados, auth.ts, testing/seed.ts, prisma/seed.ts, authStore, Sidebar, AppNavigator y HomeScreen móvil. Resultado: fase coherente en local. La revisión de permisos productivos queda registrada como paso previo al despliegue.

### Fase 9. Datos demo

seed.ts, seedData y enrich-data exigen ahora ALLOW_DEMO_DATA=1, entorno distinto de production, host loopback y nombre de base terminado en _demo. El control ocurre antes de generar operaciones. Una URL remota o una base local operativa se rechaza. Se retiró la impresión de credenciales demo en los logs. No se ejecutaron esos generadores.

Archivos: demoSafety.ts, demoSafety.test.ts y los tres scripts Prisma citados. Dos pruebas unitarias de bloqueo y permiso local aprobaron. Los tests de integración usan sus fixtures independientes en una base de pruebas, no estos generadores. Los 247 registros observados en Neon no se borraron ni se etiquetaron. Su origen sigue sin certificarse individualmente y no son historial comercial real para H4. Resultado: prevención de nuevas mezclas implementada. La procedencia histórica continúa como limitación explícita.

### Fase 10. Prisma y Neon

Las ocho migraciones existentes se aplicaron correctamente en una base local nueva. La migración 20260929_reconcile_production_schema ya contiene la corrección forward-only de AuditLog.userId, AuditLog.targetType y el default de Notification.type. No hace falta cambiar schema.prisma ni inventar otra migración que repita esa corrección. No se modificó ni reescribió ninguna migración.

La lectura de Neon confirma que AuditLog.userId y targetType permiten NULL, aunque Prisma los exige. Actualmente hay cero filas nulas en ambas columnas. Notification.type conserva el default info, frente a INFO del esquema. Product.quality sigue siendo una columna legacy documentada. detail y detalles existen en ambos lados y tienen usos distintos en importaciones y pantallas, por lo que no se fusionan sin un plan de compatibilidad.

El historial productivo tiene cuatro migraciones terminadas hasta add_movement_request_id y un intento anterior de esa migración revertido. Las cuatro migraciones posteriores de septiembre aún no constan terminadas. No se aplicó DDL ni se usó migrate resolve sobre producción. Antes de una aplicación futura se necesita respaldo, revisión de cambios manuales e índices existentes y ensayo sobre una copia local de su estructura. La cadena completa funciona desde una base local limpia, pero eso no garantiza que se pueda aplicar sin conflictos a una base modificada manualmente. Su aprobación y ejecución quedan fuera de esta tarea.

La consulta de precios encontró los siguientes casos que requieren decisión del responsable. No se cambiaron.

| Product.id | itemCode | Precio 1 | Precio 2 | Por mayor | Costo | Observación |
|---|---|---:|---:|---:|---:|---|
| 59 | 212-11D2 | 100 | 90 | Sin configurar | 58,20 | Mayorista bloqueado hasta configurar |
| 60 | 212-1548 | 50 | 40 | Sin configurar | 12,60 | Mayorista bloqueado hasta configurar |
| 61 | 215-1968 | 80 | 70 | Sin configurar | 26,30 | Mayorista bloqueado hasta configurar |
| 62 | 648519 | 500 | 400 | 390 | 490 | Precio 2 y mayorista bajo costo |

Ningún mayorista configurado supera ambos límites normales consultados. El producto 62 puede venderse en Precio 1 por 500, pero Precio 2 y mayorista se rechazan con la nueva política. Los permisos productivos de TIENDA siguen sin ventas-mayor ni reportes, y los de INVENTARIO sin reportes. No se actualizan silenciosamente. Antes de un despliegue un administrador debe decidir y asignar esos permisos con el panel existente.

Resultado: diferencias documentadas, corrección existente probada en local y ninguna modificación productiva. El despliegue permanece pendiente de revisión. Esta situación no debe confundirse con una base productiva ya saneada.

### Fase 11. Reglas compartidas

Se comparten resolución de precio, política de costo, validación de pagos y líneas, ubicación de venta e incremento de inventario. La validación de entrada de ambas ventas usa express-validator y validate. Compras, devoluciones y movimientos reutilizan el incremento bloqueado con límite de stock, para impedir que una entrada concurrente eluda la verificación. Se conservan los bloques transaccionales propios de cada operación y la reposición posterior al commit. No se extrajeron componentes por estética.

Archivos nuevos compartidos: pricing.ts, saleLocation.ts, costing.ts, moveStock.ts, stock.ts y saleValidation.ts. Las pruebas de las fases anteriores cubren su comportamiento. Se repetirán tras estos ajustes antes de cerrar la fase.

La comparación de metadatos también muestra RoleModel.permissions nullable en PostgreSQL. Es una lista Prisma y la migración original la crea como TEXT[] sin NOT NULL. No se confunde con las dos columnas escalares de auditoría pendientes. No se cambia esa representación en esta tarea.

Las 19 integraciones locales repetidas tras las extracciones compartidas aprobaron. La fase 11 queda validada. Nuevo hallazgo registrado antes de corregir en fase 12: la importación general de productos asignaba stock cero cuando faltaba la columna y actualizaba precios sin la política común. Se corregirá con transacción por fila, validación de configuración y precondición de stock esperado para ajustes.

### Fase 12. Validaciones numéricas

Se rechazan NaN, Infinity, booleanos usados como números, cantidades fraccionarias, negativos y valores fuera del rango entero de PostgreSQL. Los importes y totales tienen un límite explícito de mil millones y los precios de venta se expresan en centavos. Se comprueba también la suma de cantidades repetidas y el incremento acumulado de stock. Los márgenes explícitos inválidos ya no se sustituyen silenciosamente por defaults.

La importación general de productos valida la configuración y usa una transacción por fila. No altera inventario cuando falta la columna Stock. Un ajuste existente requiere Stock esperado. Se corrigieron también las etiquetas antiguas de ProductDetailPage y los comentarios de fixtures y permisos para que no llamen mayorista a price1. La pantalla de precios muestra sugerencias del servidor entre +20 % y +80 % sobre costo.

Archivos: validate.ts, numeric.test.ts, products.routes.ts, importProducts.itest.ts, prices.routes.ts, PricesPage.tsx, ProductDetailPage.tsx y helpers compartidos ya registrados. Pruebas: siete unitarias específicas y dos integraciones del importador, todas aprobadas. La suite unitaria backend completa anterior aprobó 153 pruebas. Se repetirá completa al cierre con las nuevas pruebas numéricas. Resultado: fase coherente.

### Hallazgos de la revisión final antes de corregir

La navegación directa a una pantalla protegida podía volver al dashboard antes de recuperar la sesión y sus permisos. Se corregirá la hidratación de sesión para conservar la ruta mientras se consultan permisos. La nota HTML del servidor y la impresión mayorista insertaban texto de clientes y productos sin escapar. Se corregirá la salida HTML y se reutilizará la nota del servidor. Estos hallazgos no requieren cambiar JWT ni la arquitectura.

La suite completa inicial de integración ejecutó 151 pruebas y encontró tres fallos de mensajes tras introducir express-validator. Se conservaron los mensajes del contrato anterior y la repetición de las 27 pruebas de ventas aprobó. El typecheck móvil detectó un paréntesis adicional en el selector de precio, que se corrigió y volvió a comprobar. No se ocultan esos fallos iniciales.

La revisión de clientes identificó otra lectura seguida de creación por NIT en ambas ventas. Dos ventas simultáneas podían intentar crear el mismo cliente. Se sustituirá por una resolución compartida con upsert de la clave única. También se aclararán las etiquetas de importes asignados y crédito en el formulario de cobro, para no llamar dinero pagado al crédito pendiente.

### Fase 13. Búsqueda mediante imagen

No se modificaron YOLO, ia-service, el proveedor de visión ni sus contratos. La suite completa local de integración aprobó 151 pruebas, incluidas búsqueda pública, límites de archivos, permisos, compatibilidad y respuestas del proveedor. Las pruebas de integración de visión usan el doble HTTP local existente para respuestas controladas. No prueban la calidad visual del modelo YOLO sobre fotografías reales. El catálogo público se mantiene sin token y con sus datos sensibles protegidos. Las 214 pruebas frontend completas también aprobaron antes de las últimas regresiones de sesión y contrato, que se repetirán al cierre.

La revisión con navegador usó exclusivamente frontend y backend de prueba en loopback. Se confirmó una venta normal con Precio 2 de 150 Bs. y su respuesta persistida, además de la selección explícita de almacén y precio mayorista de 80 Bs. Son fixtures locales, no ventas comerciales ni dataset de H4. La recarga directa conserva ahora la pantalla protegida. Los avisos de doble createRoot durante edición en caliente de main.tsx se corrigieron conservando la raíz de React en desarrollo. Se revisará una carga limpia para distinguir esos avisos de errores de operación.

### Resultado de las correcciones finales

La sesión se recupera antes de renderizar las rutas y RoleRoute espera la carga de permisos. Una carga limpia del navegador conservó /panel/ventas-mayor y registró cero errores de consola. El HTML de notas escapa texto libre y la impresión mayorista reutiliza esa salida. saleCustomer concentra la resolución de clientes y utiliza upsert por NIT. Una prueba concurrente confirmó que ambas ventas conservan el mismo cliente. El formulario distingue importes asignados, crédito pendiente y dinero sin asignar. Las regresiones correspondientes están incluidas en las suites finales.

### Fase 14. Matriz funcional contra Ejercicio 1.pdf

| Requisito | Estado | Evidencia | Corrección realizada | Pendiente |
|---|---|---|---|---|
| Inventario | CUMPLE | inventory.routes.itest y saneamiento.itest | Ajuste con expectedStock, bloqueo y auditoría atómica | Ninguno en el flujo local probado |
| Venta normal | CUMPLE | sales.itest, precioServidor.itest, saneamiento.itest y 17 pruebas SalesPage | PRICE1/PRICE2 del catálogo, tienda explícita y stock transaccional | Venta Precio 2 confirmada también con navegador local |
| Devoluciones | CUMPLE | Cinco integraciones de returns | Cantidades agrupadas, valor histórico proporcional y bloqueo | La procedencia histórica productiva sigue sin certificarse |
| Solicitudes | CUMPLE | Pruebas de notificaciones, duplicados y entrega | Estados reales, almacén explícito e historial con movimiento | No existe stock en tránsito en el modelo actual |
| Movimientos | CUMPLE | Cuatro integraciones de movements | Origen y destino distintos, bloqueos ordenados y vínculo validado | Ninguno en los escenarios locales probados |
| Costos | CUMPLE | Tres integraciones de costs con factura Excel | Fórmula del servidor, costo vigente e ingreso opcional transaccional | Sin clave única de factura no se garantiza idempotencia entre reimportaciones |
| Precios | CUMPLE PARCIAL | Política común y regresiones de ventas, productos y costos | Semántica única, centavos y rechazo bajo costo | Producto 62 y tres mayoristas ausentes requieren decisión productiva |
| Venta por mayor | CUMPLE | precioServidor.itest, saneamiento.itest y formulario local | wholesalePrice exclusivo, origen explícito, sin fallback | Navegador comprobó cotización, no una segunda confirmación manual |
| Clientes | CUMPLE | Caso concurrente de mismo NIT en saneamiento.itest | Resolución compartida por identificador o datos y upsert | No se fusionaron clientes históricos |
| Pagos | CUMPLE | Venta, cobro de crédito, rollback y límites en integración | CREDITO excluido de recaudación y saldo coherente | No es conciliación bancaria ni certificación contable |
| Nota de venta | CUMPLE PARCIAL | Escape HTML unitario y nota con crédito en integración | Texto escapado, precios aceptados y fecha de negocio | Falta revisión de impresión física y PDF generado en dispositivos |
| Dashboard | CUMPLE | Integraciones de reportes y typecheck | Límites de negocio y etiqueta ventas brutas | No representa cobros de caja como ingreso financiero |
| Reportes | CUMPLE | Diez integraciones, una con 1.005 ventas y nombres repetidos | Agregación diaria completa y recorrido de páginas | Verificar rendimiento con volumen productivo antes de desplegar |
| Reposición automática | CUMPLE | replenishDuplicados.itest, notificaciones y movimientos | Se conserva la regla reactiva y la entrega mueve stock una sola vez | No es reposición predictiva de H4 |
| Búsqueda mediante imagen | CUMPLE PARCIAL | Integraciones vision y searchImageRoutes | Contratos públicos, permisos y límites preservados | Sin evaluación de YOLO con fotos reales ni servicio remoto real |
| Responsive | CUMPLE PARCIAL | Interfaz de escritorio revisada a 1280 por 720 y tipos móviles | Se conservaron estilos y navegación, permisos y precios móviles | Sin matriz visual de tamaños ni ejecución Expo en dispositivo |
| Roles | CUMPLE | authPermissions, productsScope e inventory.routes | Roles y alcance de tienda preservados | No se cambiaron JWT ni roles productivos |
| Permisos | CUMPLE PARCIAL | Pruebas API de revocación y frontend de carga | Guards por módulo y clientes sin permisos inventados | TIENDA e INVENTARIO requieren revisión de asignaciones en Neon |
| Flujo conectado | CUMPLE | Suites integradas y venta confirmada desde navegador contra API local | Venta, inventario, devolución, solicitud, entrega y reporte conectados | No se declara una sesión manual única de extremo a extremo para todos los módulos |

Resultado: 14 CUMPLE, cinco CUMPLE PARCIAL, cero NO CUMPLE y cero NO APLICA. Los cinco parciales conservan pendientes concretos. Esta matriz no declara resueltas las diferencias productivas.

### Fase 15. Verificación final

| Comprobación | Ejecutados | Aprobados | Fallidos finales | Omitidos dentro de la suite |
|---|---:|---:|---:|---:|
| Unitarios backend | 156 | 156 | 0 | 0 |
| Integración backend, PostgreSQL local | 153 | 153 | 0 | 0 |
| Frontend, 24 archivos de pruebas | 217 | 217 | 0 | 0 |
| Utilidad de precios móvil | 3 | 3 | 0 | 0 |
| Total de pruebas automatizadas | 529 | 529 | 0 | 0 |

Comandos ejecutados desde cada paquete, con sus dependencias ya instaladas:

```text
backend: node --import tsx --test "src/**/*.test.ts"
backend: node --import tsx --test --test-force-exit --test-concurrency=1 "src/**/*.itest.ts"
backend: node node_modules/typescript/bin/tsc
frontend: node node_modules/vitest/vitest.mjs run --maxWorkers=1 --minWorkers=1
frontend: node node_modules/typescript/bin/tsc --noEmit
frontend: node node_modules/vite/bin/vite.js build
mobile: node --experimental-strip-types --test "src/**/*.test.ts"
mobile: node node_modules/typescript/bin/tsc --noEmit
backend: node node_modules/prisma/build/index.js validate
backend: node node_modules/prisma/build/index.js migrate deploy
backend: node node_modules/prisma/build/index.js migrate status
```

Prisma deploy y status se ejecutaron exclusivamente con DATABASE_URL apuntando a `127.0.0.1:55439/repuestopro_preh4_test`. Se aplicaron las ocho migraciones ya existentes en una base vacía de pruebas. validate aprobó. La cadena local quedó actualizada. Las integraciones utilizaron esa misma base local con fixtures aislados. No se ejecutaron sobre Neon.

Las compilaciones backend y frontend y los tres controles de tipos aprobaron. En la ejecución inicial de integración hubo tres fallos por mensajes de validación, corregidos y repetidos. También se corrigieron una conversión SQL de fecha y un error de sintaxis móvil detectados durante las fases. El resultado final es cero fallos, sin ocultar los fallos intermedios.

Warnings conservados: React Router informa futuras opciones de v7. JSDOM informa que no implementa una navegación de documento en la prueba del interceptor 401, aunque su aserción aprueba. Node advierte del tipo de módulo móvil no declarado. Vite advierte de un chunk principal de 1.939,72 kB, 545,34 kB gzip, superior a 500 kB. Ninguno bloqueó las comprobaciones. Dividir bundles queda como mejora de rendimiento, fuera de este saneamiento funcional.

No se ejecutaron pruebas visuales en dispositivos móviles, impresión física ni renderizado PDF de notas. El navegador disponible no expuso un control de tamaños de viewport y no se inició Expo. La visión se verificó con el doble HTTP local de las integraciones, no con fotografías y un proveedor real. No se ejecutaron pruebas de carga de producción, migraciones productivas ni generadores demo. Estas omisiones no son pruebas aprobadas y explican los cumplimientos parciales.

La revisión manual utilizó servidores temporales en 127.0.0.1, confirmó Precio 2 por 150 Bs. y verificó el formulario mayorista a 80 Bs. La captura `preh4-venta-local.png` quedó como evidencia fuera del código, en el directorio de visualizaciones de esta conversación. La carga limpia de mayoristas no registró errores de consola. Se cerraron las pestañas y los dos servidores, se retiraron los fixtures smoke y se detuvo PostgreSQL temporal. Sus archivos locales se conservan, sin eliminar directorios ajenos.

### Decisión y pendientes para el equipo

El saneamiento de código autorizado se entrega verificado en local. El cierre integral queda condicionado. No se comienza H4 ni se presenta el proyecto productivo como saneado.

Antes del siguiente paso, el equipo debe decidir los precios de los productos 59 a 62, revisar permisos de TIENDA e INVENTARIO y aceptar o resolver las diferencias físicas de Neon. Para las cuatro migraciones posteriores no registradas debe revisar el estado físico e índices en una copia, ensayar la cadena existente y preparar respaldo y aprobación antes de cualquier aplicación productiva. No corresponde crear una migración adicional ni marcar migraciones como aplicadas para ocultar diferencias.

También quedan la comprobación visual móvil, impresión y calidad de visión real. La reimportación de una factura requiere control operativo mientras no se apruebe una identidad de factura. Los 247 registros actuales conservan su procedencia no certificada y no constituyen por sí solos ventas comerciales utilizables para H4. La propuesta académica explica cómo trabajar después con datos sintéticos explícitos, sin generarlos ahora.

No se cambiaron schema.prisma, migraciones ni datos productivos. Los únicos archivos bajo prisma modificados son los tres scripts demo de protección. Se generaron artefactos locales de compilación en backend/dist y frontend/dist, además de logs y la base temporal de pruebas. No se cambiaron dependencias ni archivos .env, no se realizó deploy y no se usó Git.

### Archivos nuevos y modificados en esta tarea

Se registran 71 archivos fuente, de prueba y documentación: 21 nuevos y 50 existentes modificados. La auditoría anterior no se modificó. El detalle se basa en las ediciones de esta tarea y sus fechas, sin comandos Git.

Archivos nuevos:

```text
backend/src/modules/costs/__tests__/costs.itest.ts
backend/src/modules/products/__tests__/importProducts.itest.ts
backend/src/modules/reports/dailyReport.ts
backend/src/modules/sales/__tests__/saneamiento.itest.ts
backend/src/shared/middlewares/__tests__/numeric.test.ts
backend/src/shared/middlewares/saleValidation.ts
backend/src/shared/utils/__tests__/demoSafety.test.ts
backend/src/shared/utils/__tests__/html.test.ts
backend/src/shared/utils/costing.ts
backend/src/shared/utils/demoSafety.ts
backend/src/shared/utils/html.ts
backend/src/shared/utils/moveStock.ts
backend/src/shared/utils/pricing.ts
backend/src/shared/utils/saleCustomer.ts
backend/src/shared/utils/saleLocation.ts
backend/src/shared/utils/stock.ts
docs/H4_MODELO_PREDICTIVO_PROPUESTA_DETALLADA.md
docs/PLAN_SANEAMIENTO_REPUESTOPRO_PRE_H4.md
frontend/src/components/RoleRoute.test.tsx
frontend/src/utils/businessDate.test.ts
frontend/src/utils/businessDate.ts
```

Archivos existentes modificados:

```text
backend/prisma/enrich-data.ts
backend/prisma/seed-data.ts
backend/prisma/seed.ts
backend/src/modules/costs/costs.routes.ts
backend/src/modules/dashboard/dashboard.routes.ts
backend/src/modules/inventory/__tests__/inventory.routes.itest.ts
backend/src/modules/inventory/inventory.routes.ts
backend/src/modules/movements/__tests__/movements.itest.ts
backend/src/modules/movements/movements.routes.ts
backend/src/modules/payments/payments.routes.ts
backend/src/modules/prices/prices.routes.ts
backend/src/modules/products/products.routes.ts
backend/src/modules/reports/__tests__/reports.itest.ts
backend/src/modules/reports/reports.routes.ts
backend/src/modules/requests/requests.routes.ts
backend/src/modules/returns/__tests__/returns.itest.ts
backend/src/modules/returns/returns.routes.ts
backend/src/modules/sales/__tests__/precioServidor.itest.ts
backend/src/modules/sales/sales.routes.ts
backend/src/modules/wholesale/wholesale.routes.ts
backend/src/shared/middlewares/auth.ts
backend/src/shared/middlewares/validate.ts
backend/src/shared/utils/rangoFechas.ts
backend/src/shared/utils/scope.ts
backend/src/testing/seed.ts
backend/src/utils/__tests__/saleItems.test.ts
backend/src/utils/saleItems.ts
frontend/src/components/RoleRoute.tsx
frontend/src/components/layout/Sidebar.tsx
frontend/src/main.tsx
frontend/src/pages/CostsPage.tsx
frontend/src/pages/DashboardPage.tsx
frontend/src/pages/InventoryPage.tsx
frontend/src/pages/MovementsPage.tsx
frontend/src/pages/PricesPage.tsx
frontend/src/pages/ProductDetailPage.tsx
frontend/src/pages/ReportsPage.tsx
frontend/src/pages/RequestsPage.tsx
frontend/src/pages/ReturnsPage.tsx
frontend/src/pages/SalesPage.tsx
frontend/src/pages/SettingsPage.tsx
frontend/src/pages/WholesalePage.tsx
frontend/src/pages/__tests__/SalesPage.test.tsx
frontend/src/stores/__tests__/authStore.test.ts
frontend/src/stores/authStore.ts
mobile/src/__tests__/precioVenta.test.ts
mobile/src/navigation/AppNavigator.tsx
mobile/src/screens/HomeScreen.tsx
mobile/src/screens/SalesScreen.tsx
mobile/src/utils/precioVenta.ts
```

## SEGUNDA AUDITORÍA. Resultados

Esta sección sustituye la decisión de cierre de la primera ronda. Se leyeron los tres documentos obligatorios, el schema, las ocho migraciones y las 18 páginas de Ejercicio 1.pdf. Se revisaron los consumidores actuales de precios en backend, frontend, móvil, importaciones, exportaciones, notas, pruebas y documentación. Las consultas a Neon se ejecutaron dentro de una transacción de solo lectura. El código se probó con bases PostgreSQL locales aisladas. Las cantidades productivas descritas siguen siendo una observación del 27 de octubre de 2026.

### Precios, contratos y productos pendientes

POR MENOR obtiene su importe de Product.price1. POR MAYOR obtiene su importe exclusivamente de Product.wholesalePrice. La elección viaja como items.priceMode con POR_MENOR o POR_MAYOR. El servidor obtiene el producto y calcula cantidades, subtotales, total y pagos. No toma un unitPrice enviado por el cliente. El modo por mayor exige además el permiso ventas-mayor en el flujo normal. La tienda normal no puede vender desde un almacén. El módulo mayorista conserva su origen explícito, que puede ser tienda o almacén según el rol.

price2 se conserva como LEGACY y PENDIENTE DE REVISIÓN PARA MIGRACIÓN. No elige ventas, no recibe el nombre de mayorista o minorista y no limita los precios comerciales. Los productos nuevos pueden conservar cero como valor técnico de ese campo requerido por Prisma. Ese cero no es un precio de venta. Los valores históricos permanecen intactos. Un cliente antiguo sin modo mantiene POR MENOR, y PRICE1 se acepta solo como alias de compatibilidad de ese modo. PRICE2 se rechaza con un mensaje de actualización. Los clientes actualizados siempre envían el modo canónico.

La venta normal puede contener ambos modos en productos distintos. Un mismo producto del carrito utiliza un solo modo. Si se intenta agregarlo con otro, se solicita cambiar el modo en su fila, sin aumentar silenciosamente su cantidad. La entrada desde visión prepara POR MENOR, sin seleccionar el antiguo price2. En móvil se usan los mismos campos y nombres. El módulo mayorista obliga POR MAYOR, aunque utilice una pantalla diferente. Sale.type conserva el canal NORMAL o MAYOR y no se usa como prueba del modo de cada línea.

La regla vigente es costo menor o igual a POR MAYOR menor o igual a POR MENOR cuando existe costo y el mayorista está configurado. Si no se configuró mayorista, solo puede utilizarse POR MENOR. No se introdujo una excepción para vender bajo costo ni una modificación automática de precios. Menor precio para el cliente no significa mayor margen para la empresa. El módulo Precios calcula sugerencias por separado, conserva la edición manual mayorista y aplica ambos precios solo mediante la acción explícita. La exportación incluye los dos valores actuales con encabezados Por menor y Por mayor. Las sugerencias se identifican como sugerencias.

El importador general admite nombres históricos de columnas, pero Precio mayoreo ahora corresponde al único mayorista. El importador mayorista reconoce los encabezados de la exportación. Para crear un producto nuevo exige un Por menor explícito, porque no puede deducirlo del precio mayorista. Los productos existentes conservan su minorista. Los importes inválidos se rechazan. No se amplía inventario desde una hoja de precios.

| Producto | Valores físicos observados | Regla y situación actual | Pantallas | Decisión necesaria |
|---|---|---|---|---|
| 59, 212-11D2, FAROL | price1 100, price2 90, wholesalePrice NULL, cost 58,20, sin categoría | POR MENOR válido. Falta configurar POR MAYOR | Inventario, detalle, Precios y selección de venta | Responsable fija mayorista entre 58,20 y 100 y confirma categoría |
| 60, 212-1548, GUIÑADOR | price1 50, price2 40, wholesalePrice NULL, cost 12,60, sin categoría | POR MENOR válido. Falta configurar POR MAYOR | Las mismas pantallas | Responsable fija mayorista entre 12,60 y 50 y confirma categoría |
| 61, 215-1968, STOP | price1 80, price2 70, wholesalePrice NULL, cost 26,30, sin categoría | POR MENOR válido. Falta configurar POR MAYOR | Las mismas pantallas | Responsable fija mayorista entre 26,30 y 80 y confirma categoría |
| 62, 648519, prueba30 | price1 500, price2 400, wholesalePrice 390, cost 490, categoría Filtros | POR MENOR válido. Mayorista 390 bajo costo. price2 ya no es precio activo | Las mismas pantallas | Revisar si es registro de prueba y fijar mayorista entre 490 y 500 si el producto sigue vigente |

Inventario y detalle permiten corregir ambos precios mediante sus formularios administrativos. Precios permite calcular y aplicar sugerencias. La API impide guardar una configuración que siga bajo costo, por lo que el producto 62 debe corregirse en una misma operación coherente. La barrera restante es la decisión comercial, no un cambio de schema. Ninguno de estos valores fue modificado en Neon.

### Facturas, inventario, entregas y devoluciones

Cost tiene supplierId, productId, date, costPrice e invoiceUrl. No tiene número único de factura, hash ni cantidad persistida de factura. Los 113 costos productivos observados tienen invoiceUrl nulo. Por ello no se puede reconstruir una identidad comercial histórica con esos campos. No se inventó supplierId más un número inexistente.

La importación Excel utiliza la pareja supplierId y SHA-256 de los bytes del archivo. SHA-256 es una huella que permite reconocer el mismo contenido binario. La comprobación, los costos, la actualización de Product.cost, el ingreso opcional de stock y el registro IMPORT_INVOICE en AuditLog ocurren en una transacción. Un bloqueo de PostgreSQL coordina reenvíos incluso entre procesos. El reenvío devuelve el resultado guardado sin repetir costos ni ingreso. Si se cambia ubicación, tipo de cambio, gastos o margen para ese mismo archivo, se devuelve 409 para revisar la operación previa. Una fila inválida revierte toda la factura.

Esta regla reconoce el mismo archivo, no demuestra que dos archivos regenerados correspondan a la misma factura comercial. Tampoco declara duplicado todo costo manual con el mismo adjunto, porque una factura puede incluir varios productos. Para esa identidad futura se necesitaría número de factura o documento de compra con líneas, una revisión de datos y una migración aprobada. El historial previo sin huellas no queda protegido retroactivamente. No se confunde esta limitación con la corrección segura del reintento de una importación nueva.

Se revisaron todas las escrituras de stock. El ajuste manual y el ajuste por importación de productos bloquean Inventory y exigen expectedStock. La creación de inventario parte de un producto nuevo o una fila en cero, no sustituye un stock existente sin protección. Ventas bloquean y descuentan la ubicación de Sale. Devoluciones bloquean Sale y sus líneas, agregan cantidades y valor histórico, comprueban lo ya devuelto e ingresan en Sale.locationId. Compras incrementan con bloqueo y límite entero. Movimientos descuentan origen y suman destino dentro de la misma transacción.

Un movimiento manual requiere operationId. La interfaz conserva esa identidad al reintentar y la renueva al iniciar otro movimiento. AuditLog conserva su huella y resultado bajo bloqueo. Reenviar la identidad con otros datos se rechaza. Una entrega vinculada a solicitud también está protegida por su estado. Entregar desde PREPARANDO registra un único Movement e historial y cambia a ENTREGADO. Recibir no incrementa otra vez. No se permite cancelar después de la entrega. Los reintentos y las devoluciones concurrentes tienen comprobaciones de comportamiento, además de la inspección de rutas alternativas.

### Reportes, fechas, permisos y sesión

El diario continúa agregando en backend todos los registros del intervalo. El reporte de ventas tiene orden estable por saleDate e id y entrega snapshotMaxId, un identificador máximo que fija qué ventas pertenecen al recorrido. Las páginas siguientes conservan ese corte y los filtros. El cliente usa el número inicial de páginas, comprueba un límite finito y rechaza IDs repetidos. No sigue un total que crece al registrar otras ventas. Si se supera el límite de recorrido se informa un error, sin exportación truncada.

Los filtros por producto, marca, modelo y proveedor autorizado suman solo las líneas coincidentes. No suman otros productos de la misma venta bajo el nombre de la marca filtrada. La respuesta identifica ese alcance con MATCHING_ITEMS. Sin esos filtros se conserva el total de la venta. El mensual respeta la ubicación elegida y el inventario filtra búsqueda, marca y modelo. Se corrigieron tarjetas que reutilizaban cifras de otra pestaña o mostraban unidades como dinero. El stock crítico sin consultar se muestra como dato no cargado, no como cero confirmado. TIENDA no consulta el directorio de proveedores para construir un filtro que no tiene autorizado.

Las fechas de eventos se conservan como instantes UTC y los días comerciales usan America/La_Paz. Se comprobó 23:59:59.999 del último día de septiembre frente a 00:00 del primer día de octubre, equivalentes a 03:59:59.999 y 04:00 UTC. Reportes y notas mantienen ese criterio. El móvil no presenta actualmente una pantalla de historial con fechas comerciales. Envía operaciones para que el servidor registre la fecha, sin fabricar una fecha local. La recepción y los pagos conservan sus fechas de evento, sin sustituirlas por la fecha de la venta.

La API verifica permisos además de RoleRoute. El modo mayorista del punto de venta exige ventas-mayor. Historial y nota del canal MAYOR funcionan con ese permiso, sin exigir abrir ventas normales. El detalle comprueba el permiso del canal real y la ubicación. Los detalles de ventas y devoluciones dejaron de exponer Product.cost. Clientes exige un rol de venta y su permiso. Dashboard rechaza TIENDA sin ubicación y no usa inventarios ajenos para calcular sus productos sin stock. Los roles configurables con permiso explícito de movimientos conservan el contrato ya existente, sin reemplazarlo por una lista fija que rompería su caché.

La sesión espera permisos antes de resolver una ruta protegida. Un 401 limpia usuario y token y no devuelve permisos de ADMIN por fallback. Una respuesta tardía no recupera una sesión ya cerrada. Se verificaron sesión cargando, sesión vencida, usuario sin permiso y recuperación directa de una ruta. El token sigue siendo verificado por la API.

| Rol | Módulo | Lectura | Creación | Edición | Eliminación | Datos sensibles |
|---|---|---|---|---|---|---|
| ADMIN | Productos, categorías y ubicaciones | Global | Sí | Sí | Según endpoint y dependencias | Configuración interna |
| TIENDA | Productos e inventario | Catálogo y stock propio | No | No | No | Sin costo ni stock ajeno |
| INVENTARIO | Productos e inventario | Global con permiso | No alta de producto | Ajuste de stock con expectedStock | No producto | Costos autorizados por política |
| ADMIN | Inventario | Global | Mediante producto o ingreso | Ajuste protegido | Sin ruta de borrado directo | Configuración interna |
| ADMIN | Ventas y mayoristas | Global | Sí | Sin ruta | Sin ruta | Cliente, importes y nota |
| TIENDA | Ventas y mayoristas | Propia con permiso del canal | Propia con permiso | Sin ruta | Sin ruta | Cliente y venta, sin Product.cost |
| INVENTARIO | Ventas, mayoristas, pagos y devoluciones | No en esos endpoints | No | No | No | Acceso a agregados solo por reportes |
| ADMIN, TIENDA | Pagos | Global o propia según rol | Cobro de saldo | Sin ruta | Sin ruta | Importes y crédito |
| ADMIN, TIENDA | Devoluciones | Global o propia según rol y permiso | Sí, sobre venta autorizada | Sin ruta | Sin ruta | Valor vendido, sin costo de compra |
| ADMIN, INVENTARIO | Movimientos | Con permiso movimientos | Con permiso, identidad y stock | Sin ruta | Sin ruta | Origen, destino y responsable |
| TIENDA | Movimientos | Denegado con permisos actuales | Denegado con permisos actuales | Sin ruta | Sin ruta | No hereda permiso por la UI |
| ADMIN, INVENTARIO | Solicitudes | Global con permiso | Sí | Preparación y entrega | Cancelación antes de entregar | Historial operativo |
| TIENDA | Solicitudes | Propias con permiso | Propias | Recepción o cancelación permitida | Cancelación lógica, no borrado | Sin modificar destino ajeno |
| ADMIN | Costos y precios | Sí | Costos e importación | Costos, precios y aplicación | Costos según endpoint | Costos y márgenes |
| TIENDA, INVENTARIO | Costos y precios administrativos | No | No | No | No | No acceso a esos endpoints |
| ADMIN, INVENTARIO | Reportes | Global con permiso | No aplica | No aplica | No aplica | Costos según allow-list |
| TIENDA | Reportes | Solo ubicación propia con permiso | No aplica | No aplica | No aplica | Sin costo, utilidad ni sondeo por proveedor |
| ADMIN, TIENDA | Clientes | Con permiso de venta | Sí | Sí | Sin ruta | Directorio comercial, no Product.cost |
| INVENTARIO | Clientes | No | No | No | Sin ruta | No necesita datos de clientes |

La matriz describe las rutas existentes, no inventa operaciones CRUD. Los permisos productivos no se reasignaron. TIENDA sigue sin ventas-mayor ni reportes e INVENTARIO sin reportes según la lectura previa. Un administrador debe decidir sus asignaciones antes del despliegue. El código permite esa administración y la API rechaza la falta de permiso.

### DATOS HISTÓRICOS QUE NO PUEDEN REPARARSE AUTOMÁTICAMENTE

| Caso observado | Duda o inconsistencia | Impacto | Decisión humana necesaria |
|---|---|---|---|
| 247 Sale entre 08/03/2026 y 13/10/2026 | Sin procedencia real o demo certificada | No certifica historia comercial para H4 | Contrastar con documentos de venta y responsables |
| 21 ventas asociadas a ALMACEN | No deben mezclarse sin explicar el canal de venta | Pronóstico por tienda y trazabilidad | Confirmar operaciones mayoristas y el origen de las demás, sin cambiarlas a una tienda arbitraria |
| 15 grupos saleId/productId repetidos | No hay evidencia para distinguir líneas legítimas de duplicados | Una eliminación automática alteraría cantidades y reembolsos | Contrastar con notas. La nueva lógica agrupa cantidades sin borrar líneas |
| 200 diferencias entre ubicación actual del usuario y Sale.locationId | El usuario pudo cambiar de asignación. No prueba por sí solo que la venta esté mal | No reconstruir ubicación histórica con User.locationId | Confirmar asignaciones históricas. Conservar Sale.locationId mientras no exista evidencia |
| Productos 59, 60 y 61 sin categoryId | FAROL, GUIÑADOR y STOP no tienen categoría confirmada | Filtros y posibles variables futuras incompletas | Revisar catálogo. Eléctrico podría ser candidato, pero no se asigna por inferencia |
| Datos de vehículo de 59 y 60 | MAZDA con TACOMA e HYUNDAI con TUNDRA requieren comprobación | Compatibilidad y filtros pueden ser incorrectos | Verificar fabricante del vehículo, aplicación y códigos con el proveedor |
| Producto 62 con nombre prueba30 | Nombre, marca, modelo y fabricante sugieren una prueba, sin certificación | No usar como ejemplo comercial real | Responsable decide su vigencia. No se elimina |
| 113 Cost sin invoiceUrl | No existe evidencia de identidad de factura en esos registros | No se deduplican con certeza | Revisar documentos antes de una consolidación histórica |

brand, model y year representan aplicación del vehículo. manufacturer describe el fabricante del repuesto. oemCode y factoryCode son códigos distintos y no se intercambian automáticamente. year admite rangos como 05-11 o 22-, no equivale al año de una venta. Los campos requeridos de Prisma no certifican que su contenido comercial sea correcto.

detail se usa en formularios, búsqueda y exportación de descripción. detalles procede de quality en la cadena de migraciones y de columnas Calidad o Detalles en importaciones. El catálogo público también lo usa como filtro separado. No son intercambiables sin revisar la intención de ese filtro y sus valores. Neon no tiene productos con ambos campos no nulos, pero eso no certifica equivalencia semántica. Se hizo consistente la preferencia de la tabla de inventario con el campo que edita su formulario. La migración futura debe clasificar descripción frente a calidad, resolver colisiones en una copia, actualizar consumidores y solo después retirar el campo redundante aprobado. No se duplica ni se borra información productiva para aparentar una unificación.

Product.quality existe físicamente, con cero valores en 62 productos. No pertenece al schema ni a las respuestas actuales. El código solo acepta quality como encabezado histórico de Excel y lo dirige a detalles, sin consultar esa columna física. quality queda como columna LEGACY candidata a eliminación futura, previa copia y aprobación. No se utiliza para H4.

### Prisma, auditoría y migraciones

Neon conserva AuditLog.userId y targetType nullable, sin filas nulas observadas. Prisma los exige. Notification.type sigue con default info, frente a INFO. La última migración rechaza los nulos antes de aplicar NOT NULL. Una prueba local agregó nulos dentro de transacciones de prueba, comprobó que ambos controles abortan y verificó que todo se revierte. No se inventan usuarios ni tipos de evento para llenar auditorías.

| Migración | Cambio | Riesgo | Prerrequisito | Prueba local | Estado en Neon | Recomendación |
|---|---|---|---|---|---|---|
| 20260819182416_init | Tablas, enums, claves e índices iniciales | Creación sobre objetos existentes | Base vacía para su ejecución original | Aplicó en base nueva | Terminada | Conservar historial |
| 20260820163545_add_quality_importers | quality, Importer y ProductImporter | Objetos ya existentes o claves no válidas | Estado posterior a init | Aplicó | Terminada | No repetir |
| 20260902130000_add_unique_nit | Índices únicos parciales de NIT | Falla con NIT repetidos no nulos | Revisar duplicados | Aplicó | Terminada | Conservar y comparar definiciones |
| 20260902_add_movement_request_id | requestId y FK opcional en Movement | Columna ya creada o valores sin solicitud | ProductRequest existente | Aplicó | Intento revertido y ejecución terminada | No confundir el intento revertido con pendiente |
| 20260909_close_schema_drift | Estados nuevos, quality a detalles, columnas, tablas y claves. Reemplaza índices NIT | Colisión porque Neon ya tiene detalles, AuditLog, RequestHistory y otros objetos. No es idempotente | Copia física e inventario de objetos e índices | Cadena limpia aprobada | No consta terminada | No ejecutar directamente. Diseñar reconciliación sobre copia. No usar resolve sin demostrar equivalencia |
| 20260909b_add_etapa8_indexes | Índices para inventario, ventas, pagos, devoluciones, movimientos y auditoría | Nombres existentes y bloqueos de creación | Comparar índices reales y volumen | Aplicó | No consta terminada | Revisar duplicados físicos y ensayo antes de aplicar |
| 20260928_request_abierta_unica | Índice único parcial de solicitudes activas | Falla si hay dos activas por producto y destino | Conteo de duplicados y decisión humana si existen | Aplicó y pruebas concurrentes aprobadas | No consta terminada | No borrar ni cerrar solicitudes automáticamente para forzarlo |
| 20260929_reconcile_production_schema | NOT NULL en auditoría, FK RESTRICT y default INFO | Aborta con nulos. FK puede fallar con usuarios huérfanos | Repetir conteos nulos, huérfanos y comparar FK | Aplicó. Se probó el rechazo por nulos | No consta terminada | Aplicar solo tras resolver las etapas anteriores en copia y obtener aprobación |

Ninguna de estas migraciones elimina columnas de Product. close_schema_drift renombra quality y reemplaza índices, por lo que no basta describirla como aditiva. La última elimina y recrea una restricción, no datos. El renombrado falla si detalles ya existe, aunque quality esté vacía. La cadena desde cero funciona, pero la última migración no permite saltar los conflictos de las anteriores. Los registros reales de Neon, sus índices y cambios manuales deben reconciliarse con respaldo y ensayo. No se creó ni modificó una migración en esta ronda.

### Cinco parciales y revisión visual

| Requisito previo | Causa del parcial | Corrección local y evidencia | Lo que falta | Reevaluación |
|---|---|---|---|---|
| Precios | Tres mayoristas sin configurar y producto 62 bajo costo, además de tres conceptos ambiguos | Dos modos canónicos, política económica, importación y exportación coherentes, regresiones y venta visual | Decisión comercial sobre datos productivos | CUMPLE en código, datos productivos pendientes |
| Permisos | Asignaciones productivas diferentes de los defaults locales | API comprobada, canales de notas e historial, costos protegidos, sesión vencida y caché | Administrador revisa asignaciones antes del despliegue | CUMPLE en código, configuración productiva pendiente |
| Nota e impresión/PDF | Solo había HTML validado | Se revisó confirmación visual, se generó PDF desde la app y se corrigieron páginas y contenido largo | No se pudo recuperar el archivo descargado del navegador para renderizarlo. Impresión física pendiente | CUMPLE PARCIAL |
| Responsive | Sin revisión visual de anchuras móviles | Se revisaron pantallas de escritorio y tablas con desplazamiento | El navegador no ofrece resize. Zoom no cambió el ancho. No se ejecutó dispositivo móvil | CUMPLE PARCIAL |
| Imagen | Solo contratos con proveedor de prueba | 77 pruebas del servicio, contratos backend, interfaz pública, borrador hacia venta e inferencia del checkpoint existente en CPU | No hay fotos en datasets y artifacts revisados. Falta smoke completo con fotografía real | CUMPLE PARCIAL |

Se revisaron visualmente login, dashboard, inventario, venta normal, formulario mayorista, devoluciones, movimientos, precios, reportes y el inicio público de búsqueda por imagen a 1280 por 720. La tabla de inventario utiliza desplazamiento horizontal para sus numerosas columnas, no se afirma que todas quepan sin desplazar. Se confirmó una venta local con POR MAYOR por 80 Bs. El carrito, pago y confirmación coincidieron. La captura segunda-modos-venta.png conserva la evidencia de POR MENOR por 100 y POR MAYOR por 80. Son fixtures de pruebas, no dataset H4.

La nota HTML escapa cliente, descripción y entrega. La salida normal también incluye los datos de entrega que ya almacenaba. Las capturas PDF de ambas ventas ahora comparten saveSalePdf, expanden el comprobante completo y reparten páginas A4. Los nombres largos pueden ajustarse y la confirmación permite desplazarse para alcanzar sus botones. Se agregó precio unitario al resumen normal. Una regresión comprueba que el final de un comprobante largo queda en una página adicional. No se equipara esta prueba con validación visual del PDF final o de una impresora.

En móvil se revisaron tipos, cálculo de importes, payload, permisos, inventario y selección de modos. InventoryScreen dejó de llamar mayorista a price1 y minorista a price2. No existen pantallas móviles equivalentes a todos los módulos web y no se declara paridad completa. Expo no se ejecutó en un dispositivo. No hay una fecha móvil visible que deba reinterpretarse como hora comercial.

El checkpoint de visión cargó en CPU y ejecutó inferencia sin entrenamiento. Una imagen negra de control produjo dos candidatos. Se corrigió la validación del servicio para devolver una lista vacía cuando todos los píxeles tienen el mismo color, antes de invocar el modelo. Las tres pruebas nuevas comprueban negro, blanco y color uniforme. Se conservaron las 74 pruebas previas. No se cambió el checkpoint, el entrenamiento ni la arquitectura de YOLO. La corrección no certifica precisión con imágenes reales.

### Matriz final contra Ejercicio 1.pdf

| Requisito | Estado | Evidencia actual | Pendiente |
|---|---|---|---|
| Inventario | CUMPLE | Ajuste protegido, importación, compras y pruebas de concurrencia | Datos históricos no se reparan automáticamente |
| Venta normal | CUMPLE | Modos canónicos, importes de servidor y venta visual confirmada | Ninguno de código identificado |
| Devoluciones | CUMPLE | Líneas legacy, valor histórico, devolución parcial, total y concurrente | Decisiones sobre historia dudosa |
| Solicitudes | CUMPLE | Estados, entrega, historial y recepción sin doble ingreso | Sin stock en tránsito, según modelo existente |
| Movimientos | CUMPLE | Reenvío con identidad, concurrencia, origen y destino | Conservar auditoría de identidades |
| Costos | CUMPLE | Fórmula, rollback e importación atómica sin repetición de archivo | Identidad comercial entre archivos distintos requiere diseño posterior |
| Precios | CUMPLE | Dos conceptos, fuentes únicas y regla económica | Configuración de productos 59 a 62 en producción |
| Venta por mayor | CUMPLE | Fuente compartida, origen, importación y nota | Configuración comercial pendiente |
| Clientes | CUMPLE | NIT concurrente y permisos de API | No fusionar historia sin evidencia |
| Pagos | CUMPLE | Asignación de crédito distinta del cobro y control de saldo | No es conciliación bancaria |
| Nota, impresión y PDF | CUMPLE PARCIAL | Escape, entrega, confirmación, descarga y paginación probada | Render del PDF descargado e impresión física |
| Dashboard | CUMPLE | Fecha comercial, alcance y agregados | Prueba de carga productiva fuera del alcance |
| Reportes | CUMPLE | Totales por líneas, más de 1.000 registros, snapshot y filtros | Volumen real antes de desplegar |
| Reposición automática | CUMPLE | Regla reactiva y unicidad de solicitud activa | No es predicción de H4 |
| Búsqueda por imagen | CUMPLE PARCIAL | Contratos, interfaz, servicio y checkpoint existente | Fotografías reales y recorrido manual completo |
| Responsive | CUMPLE PARCIAL | Escritorio revisado y tipos móviles aprobados | Pantallas estrechas y dispositivo Expo |
| Roles | CUMPLE | Reglas de los tres roles y rol configurable de prueba | Aprobación operativa de asignaciones |
| Permisos | CUMPLE | API, alcance, costos, modo comercial y sesión | Ajustar asignaciones productivas mediante panel |
| Flujo conectado | CUMPLE | Venta visual, stock, devoluciones, entrega y reportes en integración | No se afirma una sesión manual de todos los módulos |

Resultado de código: 16 CUMPLE, tres CUMPLE PARCIAL y cero NO CUMPLE. Se aplica la decisión de esta ronda de separar preparación de código de reconciliación productiva. Los parciales describen evidencia visual o real que falta, no se ocultan ni se convierten en pruebas aprobadas.

### Pruebas, warnings y cierre de la segunda ronda

| Suite final | Ejecutados | Aprobados | Fallidos | Omitidos dentro de la suite |
|---|---:|---:|---:|---:|
| Unitarios backend | 156 | 156 | 0 | 0 |
| Integración backend en base local | 165 | 165 | 0 | 0 |
| Frontend, 26 archivos | 224 | 224 | 0 | 0 |
| Precios móvil | 3 | 3 | 0 | 0 |
| Servicio de visión existente | 77 | 77 | 0 | 0 |
| Total | 625 | 625 | 0 | 0 |

Las primeras cuatro suites suman 548 pruebas, frente a las 529 de la ronda anterior. Las pruebas nuevas cubren modos, legacy, facturas repetidas, rollback, movimientos repetidos, costos ocultos, permisos, sesión vencida, respuestas tardías, límites de fecha, snapshots, filtros, columnas de exportación y PDF largo. Durante la edición se reemplazó accidentalmente el archivo de cuatro pruebas frontend de aislamiento de costos. La comparación con el log anterior detectó la reducción. Se recuperaron sus cuatro comprobaciones para ADMIN, INVENTARIO, TIENDA y sesión sin recuperar, además de la nueva regresión de tarjetas. No se dejó la reducción como un resultado aceptable ni se ocultó en el total.

La primera integración de 153 casos tuvo un fallo por el fixture sin operationId. La siguiente ejecución junto a la API visual agotó conexiones locales y falló también la prueba de caché por una restricción fija de roles que se había añadido. Se retiró esa restricción para conservar el contrato de roles configurables con permisos explícitos. Se detuvo la API visual y se usó una base local nueva. La última ejecución completa aprobó 165 casos. Estos fallos intermedios no son fallos finales ni evidencia contra Neon, donde no se ejecutaron tests.

Se ejecutaron los comandos unitarios, integración, Vitest, tipos y build descritos en la primera ronda. Además se ejecutó `.venv/Scripts/python.exe -m pytest tests -q` desde ia-service. La inferencia de control utilizó el checkpoint existente en CPU. No se ejecutó ningún script de entrenamiento. Backend y frontend compilaron. El móvil aprobó tsc --noEmit. Prisma validate y migrate status aprobaron. Las ocho migraciones existentes se probaron de nuevo en repuestopro_round2_migrations_test y repuestopro_round2_final_test, ambas en 127.0.0.1:55439. La suite final usó la segunda. Nunca se apuntó un test o una migración a Neon.

| Warning observado | Clasificación | Interpretación y acción |
|---|---|---|
| Bundle principal Vite cercano a 1,94 MB, unos 546 kB gzip | RELEVANTE | Compila, pero puede tardar en conexiones móviles. Evaluar división de cargas en una tarea de rendimiento, sin refactor general en este cierre |
| React Router anuncia opciones futuras de v7 | NO BLOQUEANTE | Se mantiene la versión actual y su comportamiento. No se migra el router para silenciar un aviso |
| Node informa MODULE_TYPELESS_PACKAGE_JSON en pruebas móviles | NO BLOQUEANTE | Node vuelve a interpretar el archivo de test como módulo. No se cambia el tipo de paquete de Expo por este aviso |
| JSDOM no implementa navegación completa en el test del interceptor 401 | IGNORABLE JUSTIFICADO | Limitación de ese entorno. Se comprueba limpieza de sesión y se hizo navegación real local |
| Starlette TestClient depreca su integración actual con httpx | NO BLOQUEANTE | Las 77 pruebas pasan. Revisar actualización compatible de dependencias en otra tarea |
| Logs de imagen corrupta, formato inesperado y proveedor simulado en casos negativos | IGNORABLE JUSTIFICADO | Son entradas que los tests deben rechazar. No demuestran un error de operación normal |

No se ejecutaron impresión física, render visual del PDF descargado, tamaños móviles reales ni Expo en dispositivo. Las herramientas de navegador disponibles no ofrecen control de viewport y el intento de zoom no modificó el ancho. No hubo un dispositivo móvil controlado en esta sesión. Tampoco hubo fotos de repuestos en las carpetas datasets y artifacts revisadas para completar el recorrido manual real de visión. Estas limitaciones justifican los tres parciales. No se presentan como tests aprobados ni como una evaluación de precisión del modelo.

Decisión final: CÓDIGO LISTO PARA H4, con los límites de verificación visual declarados. No quedan fallos funcionales locales conocidos en los flujos revisados que alteren ventas, cantidades, stock, fechas o ubicaciones. Los precios tienen dos fuentes explícitas, el legacy está identificado, los reintentos están protegidos, los reportes fueron contrastados y las suites están verdes. Esta decisión utiliza el criterio nuevo de no exigir cambios en Neon para preparar el código. No autoriza comenzar H4 automáticamente.

PRODUCCIÓN COMPLETAMENTE RECONCILIADA: NO. Faltan las decisiones comerciales de precios y categorías, revisión de asignaciones de permisos y reconciliación de estructura e historial de migraciones sobre una copia. Los registros históricos dudosos no se borran ni se convierten en datos reales certificados. Las capturas móviles, impresión y fotos reales deben completarse como evidencia operativa antes de afirmar cumplimiento visual total.

No se creó dataset H4, módulo predictivo, entrenamiento ni artefacto de modelo. No se cambiaron secretos, dependencias, schema.prisma o migraciones. No hubo escritura productiva, deploy ni comandos Git. Las diferencias de esta ronda se identifican por huellas SHA-256 del estado inicial y el registro de los dos archivos de visión revisados. Los artefactos de compilación y el entorno PostgreSQL son locales.

Se cerró la pestaña de revisión, se detuvieron los servidores temporales y se retiraron los fixtures visual2 de su base local. PostgreSQL de pruebas se detuvo al finalizar. Sus bases y archivos se conservan como entorno local, sin eliminar directorios del usuario.

### Archivos de la segunda ronda

Comparación contra las huellas iniciales: 38 archivos existentes modificados y 7 nuevos, sin archivos eliminados. Los dos archivos de ia-service se agregan al inventario por su registro de edición, porque esa carpeta no estaba incluida en las huellas iniciales. No se presenta un diff de Git.

Modificados:

```text
backend/src/modules/costs/costs.routes.ts
backend/src/modules/customers/customers.routes.ts
backend/src/modules/dashboard/dashboard.routes.ts
backend/src/modules/inventory/__tests__/inventory.routes.itest.ts
backend/src/modules/movements/__tests__/movements.itest.ts
backend/src/modules/movements/movements.routes.ts
backend/src/modules/prices/prices.routes.ts
backend/src/modules/products/products.routes.ts
backend/src/modules/reports/reports.routes.ts
backend/src/modules/returns/returns.routes.ts
backend/src/modules/sales/__tests__/precioServidor.itest.ts
backend/src/modules/sales/__tests__/saneamiento.itest.ts
backend/src/modules/sales/sales.routes.ts
backend/src/modules/wholesale/wholesale.routes.ts
backend/src/shared/middlewares/saleValidation.ts
backend/src/shared/utils/pricing.ts
backend/src/testing/seed.ts
backend/src/utils/__tests__/saleItems.test.ts
backend/src/utils/saleItems.ts
docs/H4_MODELO_PREDICTIVO_PROPUESTA_DETALLADA.md
docs/PLAN_SANEAMIENTO_REPUESTOPRO_PRE_H4.md
frontend/src/pages/InventoryPage.tsx
frontend/src/pages/MovementsPage.tsx
frontend/src/pages/PricesPage.tsx
frontend/src/pages/ProductDetailPage.tsx
frontend/src/pages/ReportsPage.tsx
frontend/src/pages/SalesPage.tsx
frontend/src/pages/WholesalePage.tsx
frontend/src/pages/__tests__/ReportsPage.test.tsx
frontend/src/pages/__tests__/SalesPage.test.tsx
frontend/src/services/api.ts
frontend/src/stores/__tests__/authStore.test.ts
frontend/src/stores/authStore.ts
ia-service/app/routers/vision.py
mobile/src/__tests__/precioVenta.test.ts
mobile/src/screens/InventoryScreen.tsx
mobile/src/screens/SalesScreen.tsx
mobile/src/utils/precioVenta.ts
```

Nuevos:

```text
backend/src/modules/sales/__tests__/segundaAuditoria.itest.ts
backend/src/shared/utils/idempotentMovement.ts
frontend/src/services/__tests__/reportPages.test.ts
frontend/src/services/reportPages.ts
frontend/src/utils/salePdf.test.ts
frontend/src/utils/salePdf.ts
ia-service/tests/test_uniform_image.py
```

## RECONCILIACIÓN PRISMA / NEON

Estado: no iniciada en Neon. La solicitud exige integrar primero los cambios remotos de Erika con el saneamiento local. La inspección del checkout no acredita esa integración. HEAD apunta a ross, con referencia 06dd8a1103e7eca83501a7522a635b8f21103503. La última operación del registro local corresponde al 6 de octubre de 2026, anterior a las dos rondas de saneamiento. Esto no descarta una integración manual, pero obliga a confirmar qué estado final debe validarse. No se ejecutó una fusión ni un comando Git.

La comprobación local de `node node_modules/prisma/build/index.js --version` confirmó Prisma CLI 5.22.0 y @prisma/client 5.22.0. package.json declara rangos ^5.19.0, que no sustituyen la versión instalada comprobada. La ayuda instalada admite migrate status, migrate deploy y migrate diff con from-schema-datasource, to-schema-datamodel, script, output y exit-code. Solo se consultaron versión y ayuda. No se ejecutó un diff conectado a una base.

Hay ocho migraciones locales. El orden efectivo, comparando los nombres, es el siguiente. Los prefijos no tienen todos una hora completa, por lo que no se inventan horas ni se confunde la ordenación de archivos del explorador con la aplicada por Prisma.

```text
20260819182416_init
20260820163545_add_quality_importers
20260902130000_add_unique_nit
20260902_add_movement_request_id
20260909_close_schema_drift
20260909b_add_etapa8_indexes
20260928_request_abierta_unica
20260929_reconcile_production_schema
```

La tabla de migraciones de la segunda auditoría conserva el inventario previo y sus riesgos. No se presenta como inspección nueva de producción. En particular, close_schema_drift renombra quality a detalles y crea objetos sin comprobar si ya existen. Su aplicación requiere contrastar cada efecto con el estado físico final, después de confirmar la integración. La comprobación de nulos de AuditLog y de restricciones también deberá repetirse, sin reutilizar conteos anteriores como si fueran actuales.

En esta solicitud no hubo conexión a producción, lectura nueva de _prisma_migrations, creación de rama de prueba, backfill, migrate resolve ni aplicación de migraciones. Tampoco se creó un punto de recuperación, porque todavía no corresponde modificar producción. No se ejecutaron suites sobre Neon. El estado productivo posterior no se ha evaluado y no se declara reconciliado. La pérdida de filas no se ha evaluado mediante conteos nuevos, aunque no se emitió ninguna operación que escriba en la base.

Pendiente inmediato: acreditar la integración remota y local antes de avanzar. Después se debe volver a inventariar el código final, inspeccionar producción en solo lectura y seguir la secuencia autorizada de rama aislada, validación, recuperación y revalidación previa a producción. No se guardaron URLs ni credenciales. No hubo migrate dev, db push, reset, commit, push, deploy de aplicación ni trabajo de H4.

### Integración Git previa a Neon

La instrucción posterior del equipo autorizó expresamente fetch y merge sin commit para resolver el bloqueo anterior. El 27 de octubre se registraron status, rama, ramas con seguimiento, remotos y los últimos 40 commits. La rama actual era ross y HEAD era 06dd8a1103e7eca83501a7522a635b8f21103503. Existían 55 archivos versionados modificados y 29 archivos nuevos, sin cambios staged. No se realizó pull, rebase, squash, reset ni force.

Antes del fetch se creó el respaldo externo completo git-reconcile-backup-20261027 dentro del directorio de visualizaciones de esta conversación, fuera del repositorio. Contiene el checkout y .git, 86.255 archivos y aproximadamente 2,6 GB. Robocopy informó cero errores. También se guardaron el diff completo binario, el diff staged vacío, HEAD, rama, estado y lista de archivos nuevos. Las huellas SHA-256 de 347 archivos versionados o nuevos coincidieron con la copia. No se utilizó stash.

Se ejecutó únicamente git fetch --all --prune antes de decidir la integración. La referencia de Erika es origin/erika en d3fc837b20cbfcf55138c6e52b5259ec44a9e74e. El PR 48, chore: actualizar gitignore, confirmó en consulta de solo lectura su autoría, rama erika, estado fusionado y merge 6102f417e56b51614f30efd87c87f62a520ed507. Ese merge es el tip de origin/main.

El merge-base con HEAD es el propio 06dd8a1103e7eca83501a7522a635b8f21103503. El único cambio de archivos pendiente de recuperar es .gitignore. Organiza sus reglas y agrega la exclusión de experimentos locales de ia-service, conservando la excepción del checkpoint oficial. No agrega funcionalidades nuevas de aplicación. Los otros commits ausentes de la historia local son los merges ya existentes de los PR 43 a 48, que se conservan al integrar origin/main. No se modificó ninguno de esos PR o commits.

No hubo archivos modificados por ambas partes. .gitignore es remoto solamente. Los 55 archivos versionados modificados y los 29 nuevos son locales solamente. La comparación exacta, commits y listas completas están en integration-analysis.json del respaldo. No hubo cambios remotos en schema.prisma, migraciones, package.json ni contratos de aplicación.

Se ejecutó git merge --no-commit --no-ff origin/main. Git preparó la integración automáticamente y se detuvo antes de crear commit. No aparecieron conflictos y no fue necesario resolver archivos, aplicar stash o sobrescribir fuentes. HEAD permanece en 06dd8a1. MERGE_HEAD contiene 6102f417e56b51614f30efd87c87f62a520ed507. El índice solo contiene el cambio remoto de .gitignore. El saneamiento permanece sin staging, junto con los archivos nuevos, para revisión del equipo.

Antes de actualizar este registro, las huellas comprobaron que 346 de los 347 archivos iniciales permanecían idénticos y que solo .gitignore había cambiado conforme al remoto. Esta actualización documental registra el cierre, sin sustituir código ni eliminar evidencia anterior. Se conservaron POR MENOR en Product.price1, POR MAYOR en Product.wholesalePrice, price2 legacy y todas las correcciones de las dos rondas.

| Validación del árbol integrado | Aprobados | Fallidos |
|---|---:|---:|
| Unitarias backend | 156 | 0 |
| Integraciones backend en base local nueva | 165 | 0 |
| Frontend | 224 | 0 |
| Pruebas móviles disponibles | 3 | 0 |
| Visión, sin entrenamiento | 77 | 0 |
| Total | 625 | 0 |

Se mantuvo el total anterior de 625, sin agregar ni retirar tests. Aprobaron typecheck backend, frontend y móvil, build frontend y Prisma validate. Las ocho migraciones existentes aplicaron desde cero en repuestopro_git_reconcile_test, exclusivamente en 127.0.0.1:55439. migrate status confirmó la base local actualizada. Se mantienen los warnings no bloqueantes ya documentados, incluido el tamaño del bundle. No se detectaron regresiones nuevas ni se modificaron pruebas para ocultar fallos.

El código integrado queda listo para revisar y comenzar después la reconciliación con Neon. La integración sigue preparada sin commit y pendiente de revisión humana. Esta tarea no autoriza conectarse a Neon. No hubo conexión productiva, migraciones en Neon, commit, push ni alteración de historia o Pull Requests. El PostgreSQL temporal se detuvo al cerrar las validaciones. El respaldo externo se conserva.
