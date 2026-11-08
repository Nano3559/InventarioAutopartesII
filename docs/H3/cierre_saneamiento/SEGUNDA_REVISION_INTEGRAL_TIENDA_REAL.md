# Segunda revisión integral de RepuestoPro para una tienda real

Fecha: 3 de noviembre de 2026. Estado: auditoría documental con comprobaciones locales. No se modificó la aplicación, el dataset, Prisma o Neon. No se entrenaron modelos.

Este documento conserva los hallazgos previos a las correcciones. Su estado posterior debe consultarse en [correcciones integrales para una tienda real](CORRECCIONES_INTEGRALES_TIENDA_REAL.md). Las afirmaciones de ausencia de cambios corresponden a la auditoría original, no a la ronda de implementación autorizada después.

## 1. Resultado ejecutivo y límites de la revisión

**No está acreditado que RepuestoPro esté listo para operar comercialmente sin supervisión.** Existen controles útiles de precios, permisos, concurrencia e inventario. Sin embargo, una tienda real necesita resolver reintentos de ventas y cobros, revocación de sesiones, diferencias entre stock físico y disponible, piezas devueltas dañadas, conciliación de dinero, continuidad y recuperación.

Este resultado no elimina el saneamiento previo ni significa que todas las funciones estén mal. Distingue coherencia del código de suficiencia del proceso comercial. El dataset H4 sigue siendo utilizable para un experimento académico acotado. No certifica demanda comercial, decisiones de compra o seguridad de la plataforma.

La revisión cubre el recorrido completo de compra, almacenamiento, traslado, venta, cobro, devolución, reporte y futura reposición, además de usuarios, fallas técnicas y operación humana. Se clasifican los hallazgos como confirmado por código, riesgo de negocio o pendiente de validación. Una ausencia de evidencia no se presenta como una falla demostrada. Lo que depende de infraestructura, personal, documentos comerciales o equipos físicos queda marcado como pendiente.

Se revisó el árbol actual en ross, basado en a9ff618, conservando las modificaciones locales anteriores. Se consultaron el [plan del equipo](../../GENERAL/PLAN_TRABAJO_ERIKA_ROSS.md), el [saneamiento](PLAN_SANEAMIENTO_REPUESTOPRO_PRE_H4.md), la [definición de datos H4](../../H4/historico/H4_FASE1_ESTRUCTURA_DATASET_Y_RIESGOS.md), el [informe de escenarios](../../H4/historico/H4_FALLAS_Y_ESCENARIOS_DATASET.md) y la [auditoría de cobertura](../../H4/historico/H4_AUDITORIA_COBERTURA_Y_PREPARACION_ENTRENAMIENTO.md). No se volvió a consultar producción.

## 2. Qué se conserva como avance comprobable

El backend obtiene los precios desde Product y conserva unitPrice en SaleItem. POR MENOR utiliza price1, POR MAYOR utiliza wholesalePrice y price2 queda como legacy. Valida cantidades, pagos y reglas económicas. La venta y el descuento de inventario se realizan dentro de una transacción con bloqueos de filas. Los ajustes manuales usan expectedStock y registran auditoría.

Las devoluciones bloquean la venta y sus líneas, suman lo vendido y lo ya devuelto, calculan el importe desde valores históricos y limitan cantidades. Los movimientos tienen operationId y protección contra reintentos. Las solicitudes protegen sus transiciones. Recibir una solicitud no incrementa el inventario otra vez. Los reportes diarios agregan en backend. La consulta paginada de reportes tiene límite finito, snapshot de IDs y detección de duplicados. Las fechas de negocio consideran America/La_Paz.

Existen protección de rutas, permisos de módulos, límites de solicitudes, validación de archivos, separación de respuestas públicas y privadas de visión, escape de HTML y pruebas de sesión y PDF. Estos controles son una base. Las pruebas locales no demuestran por sí solas funcionamiento bajo toda carga, frente a una interrupción de energía o con mercadería física.

## 3. Hallazgos que afectan dinero, autorización o stock

| ID | Prioridad | Evidencia y situación | Posible consecuencia en tienda real | Qué debe resolverse |
|---|---|---|---|---|
| R01 | CRÍTICA | Confirmado en shared/middlewares/auth.ts: authenticate acepta rol y locationId del JWT. authorize usa ese rol. authorizeModule deja pasar directamente un token ADMIN. auth.routes.ts emite tokens de 24 horas. users.routes.ts permite cambiar rol, ubicación y contraseña sin una versión de sesión | Un administrador degradado puede conservar privilegios del token anterior. Un vendedor reasignado puede conservar la ubicación anterior hasta renovar su sesión | Revocación o verificación efectiva del estado actual, con pruebas de cambio de rol, ubicación y contraseña. No confundirlo con la caché de permisos de 60 segundos |
| R02 | ALTA | No se encontró clave de idempotencia en creación de ventas normales o mayoristas, ni en Sale. Movimientos sí la tienen | Si el servidor confirma una venta y se pierde la respuesta, repetir puede registrar otra y descontar nuevamente stock | Identidad de operación, consulta del resultado y respuesta estable ante reintentos. Deshabilitar el botón no resuelve el corte de red |
| R03 | ALTA | payments.routes.ts bloquea Sale y limita saldo, pero no identifica un cobro repetido | Dos reintentos del mismo abono pueden registrarse si todavía queda saldo suficiente. El bloqueo evita sobrepago, no prueba que sean dos cobros diferentes | Idempotencia de cobros y conciliación contra comprobante externo |
| R04 | ALTA | returns.routes.ts llama siempre a incrementStock al registrar una devolución. Return no guarda una disposición de pieza vendible, dañada o en cuarentena | Una pieza rota, usada o pendiente de inspección vuelve al inventario que consulta la venta | Definir recepción de devolución, inspección y destino físico antes de habilitar venta. La regla actual está confirmada, no se constató una pieza dañada real |
| R05 | ALTA | requests.routes.ts ejecuta moveStock al pasar a ENTREGADO. moveStock incrementa Inventory del destino. RECIBIDO_POR_TIENDA no vuelve a incrementar | El stock lógico de la tienda incluye unidades que aún pueden estar viajando. Las ventas no distinguen ese stock de mercadería recibida | Separar tránsito y disponible o acordar una regla explícita que impida vender lo no recibido. Es una decisión adicional al saneamiento aprobado, no motivo para volver a duplicar ingresos |
| R06 | ALTA | Return.amount y method representan la devolución. El saldo de pagos se calcula como total menos cobros no crédito menos devoluciones. No hay un campo separado para aplicar a deuda frente a devolver dinero | En una venta a crédito parcial, reducir deuda y entregar dinero son operaciones diferentes. La fórmula no basta para demostrar ambos casos | Definir política y conciliación de devoluciones sobre crédito, reintegro efectivo y saldos a favor. Requiere decisión comercial y pruebas |
| R07 | ALTA | Sale.customerId es opcional y saleCustomer devuelve null sin datos. Crear pagos CREDITO no obliga a identificar al deudor | Crédito sin cliente identificable o sin condiciones de cobro | Exigir identificación y reglas de crédito si se permite en operación real, además de vencimiento, límites y responsables |
| R08 | ALTA | No se encontró una integración de confirmación bancaria ni una referencia de operación en Payment. QR y TRANSFERENCIA son métodos registrados por la aplicación | Una selección de método puede confundirse con dinero realmente recibido, incluso con una captura falsa o comprobante repetido | Definir verificación humana o integración autorizada, estado del cobro y referencia única. No afirmar que una selección confirma el banco |
| R09 | ALTA | Sale no tiene estado de anulación ni una entidad de reversión comercial específica | Un error de caja puede resolverse borrando o simulando una devolución, perdiendo su significado real | Definir cancelación antes de confirmar, anulación posterior y reversión autorizada con trazabilidad. No borrar historia |
| R10 | ALTA | El schema revisado no representa apertura/cierre de caja, arqueo ni retiros. CREDITO se separa de cobros, pero no hay una sesión de caja | Diferencias entre ventas, dinero físico, pagos externos, devoluciones y retiros al cambiar turno | Proceso de apertura, cierre, fondo inicial, diferencias, aprobación y conciliación por cajero y día |
| R11 | ALTA | app.ts registra peticiones sin query, pero errorHandler.ts usa req.originalUrl, message y stack | Un error puede volver a registrar búsquedas, parámetros o datos internos que el logger normal pretendía omitir | Redacción uniforme de logs, acceso restringido y retención. No se afirma haber observado una filtración real |
| R12 | ALTA | Cost admite invoiceUrl, pero no una identidad comercial completa de cabecera de factura. La importación protege el hash del archivo y su configuración | La misma factura modificada o presentada en otro archivo puede producir un nuevo ingreso. Archivo idéntico e identidad comercial no son equivalentes | Identificar comprobante, proveedor, documento, recepción y líneas. Conservar la protección por hash, sin inventar datos faltantes |
| R13 | MEDIA | reports.routes.ts aplica un costo por producto del periodo o el último conocido al cierre. No es un costo persistido por cada línea vendida | El resultado puede interpretarse como utilidad contable exacta pese a usar un criterio agregado | Mostrar método y límites del costo. Acordar valoración antes de usar el reporte para decisiones financieras |
| R14 | MEDIA | syncProductCost valida los precios de venta actuales contra el nuevo costo antes de actualizar | Una compra real cuyo costo subió puede rechazarse hasta ajustar precios. Mercadería física y registro podrían quedar desfasados | Proceso de recepción pendiente, revisión administrativa y actualización coherente. No modificar precios silenciosamente |

La revocación de sesiones debe validarse en el servidor. La [guía de seguridad REST de OWASP](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html) explica que un token puede seguir vigente después de terminar la sesión y requiere un mecanismo de invalidación acorde con el sistema. No se implementó ese cambio en esta revisión.

Para R06, un ejemplo muestra la decisión pendiente. Una venta de 100 con 40 cobrados tiene 60 pendientes. Una devolución por 20 puede reducir deuda, entregar dinero o combinar ambos efectos. Si se reduce deuda sin entregar dinero, quedan 40 pendientes. Si se reintegran los 20 cobrados, la conciliación debe considerar esa salida de dinero y no confundirla con el mismo ajuste de deuda. Es un ejemplo de consistencia aritmética, no una regla contable adoptada por el proyecto. No se probó un reintegro bancario o de caja real.

## 4. Disponibilidad, infraestructura y recuperación

| ID | Prioridad | Evidencia o límite | Riesgo operativo y comprobación necesaria |
|---|---|---|---|
| R15 | ALTA | /api/health devuelve ok sin consultar dependencias | No demuestra que la base permita vender. Separar proceso vivo de servicio listo para atender y probar dependencia caída |
| R16 | ALTA | No se acreditó una restauración de respaldo productivo. El respaldo Git anterior conserva código, no demuestra recuperación de ventas y archivos | Acordar pérdida máxima tolerable de datos y tiempo de recuperación. Restaurar una copia aislada y conciliar ventas, pagos, inventario y adjuntos |
| R17 | ALTA | Los archivos de facturas se guardan en backend/uploads. Esta revisión no confirmó almacenamiento persistente en el hosting | Un redeploy o cambio de instancia puede dejar referencias sin archivo si el almacenamiento es efímero. Verificar volumen, copia y restauración de adjuntos |
| R18 | MEDIA | generalLimiter permite 300 solicitudes por IP cada 15 minutos, con almacenamiento en memoria | Varios cajeros con la misma salida a Internet comparten el cupo. Cinco usuarios con 61 solicitudes ya sumarían 305. Probar carga y política por operación/usuario |
| R19 | MEDIA | La caché de permisos y los limitadores son locales al proceso | En varias instancias pueden aparecer decisiones o contadores temporalmente diferentes. La [documentación del limitador](https://express-rate-limit.mintlify.app/overview) confirma el alcance del MemoryStore |
| R20 | MEDIA | Se identificaron 22 módulos con su propio new PrismaClient, además de otros consumidores | Aumentar instancias puede multiplicar pools y conexiones. No se midió un agotamiento real. Revisar presupuesto y carga antes de escalar |
| R21 | MEDIA | server.ts no contiene manejo explícito de SIGTERM/SIGINT para drenar peticiones y cerrar conexiones | Un reinicio puede cortar la respuesta de una venta ya confirmada. Probar apagado controlado y reconciliación de resultados |
| R22 | MEDIA | La reposición posterior a la venta se crea después del commit. Un fallo se registra sin revertir la venta. Existe además un job periódico | La venta queda bien confirmada, pero una caída puede retrasar la reposición. Probar recuperación del job y alertas, sin afirmar pérdida definitiva del pedido |
| R23 | MEDIA | Axios web y móvil no fijan timeout general ni una política de resultado desconocido de venta | Un cajero puede esperar sin saber si se confirmó. Un timeout por sí solo no debe provocar un segundo registro |
| R24 | MEDIA | XLSX se procesa con un límite de tamaño de archivo, sin acreditar límites de filas, expansión y tiempo de procesamiento | Un archivo pequeño comprimido puede consumir mucha memoria o CPU. Probar tamaño lógico, múltiples importaciones y cancelación segura |
| R25 | MEDIA | La visión pública depende del limitador general. El servicio tiene límites de imagen, clave y protección de inferencia, pero no se midió capacidad de cola bajo carga | Varias fotos pueden competir por CPU/GPU y afectar otros usuarios. Probar concurrencia, espera máxima, errores y costo operacional |
| R26 | MEDIA | Bundle principal web de 1.940,99 kB, 545,95 kB gzip en el build actual | Validar tiempos con teléfonos y redes lentas. El build aprobado no prueba experiencia de usuario aceptable |
| R27 | PENDIENTE | Drift Prisma/Neon y migraciones productivas no se consultaron | No declarar producción reconciliada. Retomar el procedimiento específico de rama aislada y recuperación cuando se autorice |
| R28 | PENDIENTE | No se verificaron alertas, certificados, cuotas, políticas del proveedor ni accesos de soporte en producción | Confirmar responsables, monitoreo, renovaciones, presupuesto, escalamiento y rotación de accesos |
| R29 | ALTA | npm audit de producción reporta cinco paquetes afectados en backend y seis en frontend, con una alerta crítica por árbol | Revisar versiones, condiciones de explotación y actualización controlada antes de habilitar operación comercial. No ejecutar correcciones automáticas |
| R30 | MEDIA | La auditoría móvil devuelve ENOLOCK. No se encontró package-lock.json, yarn.lock ni pnpm-lock.yaml en mobile | Falta evidencia de resolución reproducible propia del móvil y de su auditoría de dependencias. No se creó un lockfile durante la revisión |

La recuperación debe incluir base de datos y archivos relacionados. La [documentación oficial de PostgreSQL](https://www.postgresql.org/docs/current/backup.html) distingue respaldos lógicos, físicos y recuperación mediante archivado. Esta revisión no presupone qué mecanismos están activos en Neon ni altera su configuración.

Se ejecutó npm audit --omit=dev --json sin audit fix, instalación o cambios de paquetes. La primera consulta quedó bloqueada por DNS del entorno restringido. La consulta autorizada al registro público terminó y produjo la siguiente evidencia. Los conteos corresponden a paquetes afectados dentro de cada árbol, no a vulnerabilidades únicas sumables entre proyectos.

| Proyecto | Total | Críticas | Altas | Moderadas | Evidencia guardada |
|---|---:|---:|---:|---:|---|
| Backend | 5 | 1 | 2 | 2 | [Reporte npm backend](../../H4/historico/evidencias/2026-11-03/npm-audit-backend.json) |
| Frontend | 6 | 1 | 3 | 2 | [Reporte npm frontend](../../H4/historico/evidencias/2026-11-03/npm-audit-frontend.json) |
| Mobile | No evaluable | No determinado | No determinado | No determinado | Auditoría detenida por falta de lockfile |

En backend se identificaron proxy-addr 2.0.7, xlsx 0.18.5, body-parser, qs e ip-address. El [aviso de proxy-addr](https://github.com/advisories/GHSA-jqcg-44mw-7w3h) describe un problema relacionado con subredes de confianza IPv4/IPv6. La aplicación usa trust proxy con un salto en producción. No se demostró que esa configuración concreta active la condición del aviso, pero la dependencia afectada requiere revisión.

En frontend aparecen dompurify 3.4.14, axios, follow-redirects, react-router y react-router-dom, además de xlsx 0.18.5. La alerta crítica de DOMPurify corresponde a [condiciones de SAFE_FOR_TEMPLATES y contenido de shadow root](https://github.com/advisories/GHSA-cg2g-xh64-v4q7). La ruta de PDF revisada usa html2canvas y addImage, no una llamada directa a DOMPurify con esa configuración. No se declara explotación de la pantalla de ventas. Es necesario verificar las rutas alcanzables y actualizar de forma compatible.

La [alerta de SheetJS](https://github.com/advisories/GHSA-4r6h-8v6p-xvw6) afecta la lectura de archivos preparados maliciosamente. RepuestoPro sí importa Excel, por lo que esta superficie merece atención prioritaria. npm no ofrece una corrección automática de xlsx dentro del árbol auditado. No se eligió una sustitución ni se cambió el proveedor de la librería durante esta tarea.

## 5. Matriz de operación real

Esta matriz reúne escenarios normales, adversos y ambiguos. No son funciones nuevas solicitadas para implementar de inmediato. Cada fila señala el proceso que una tienda debería aceptar mediante pruebas y decisiones explícitas.

| Área | Caso normal | Caso adverso | Caso ambiguo o decisión pendiente | Estado en esta revisión |
|---|---|---|---|---|
| Inicio de jornada | Usuario autorizado abre su sesión | Cuenta comprometida o empleado retirado | Quién puede abrir caja y recuperar acceso | Control parcial, R01 y R10 |
| Turnos y terminales | Cajeros distintos con cuentas propias | Compartir credenciales o dejar sesión abierta | Traspaso de caja y responsabilidad | Política pendiente |
| Catálogo | Producto con código y aplicación correctos | Código duplicado o aplicación errónea | Mismo repuesto para varios vehículos | Unicidad técnica no certifica compatibilidad |
| Unidad comercial | Se vende una pieza | Caja o kit registrado como pieza suelta | Metros, litros, pares y unidades fraccionarias | Cantidad entera sin unidad comercial explícita |
| Equivalencias | Coincidencia por código confiable | Sustituir una pieza incompatible | OEM, alternativo, original y equivalencias | Requiere catálogo validado |
| Estado y garantía | Repuesto nuevo vendible | Pieza defectuosa, usada o falsificada | Lote, serie, origen y garantía aplicable | No acreditada trazabilidad de ese nivel |
| Precio | POR MENOR o POR MAYOR del backend | Tarifa cambia durante el cobro | Descuento especial o excepción bajo costo | Regla estricta existente, excepciones no definidas |
| Moneda y redondeo | Venta en Bs con importes coherentes | Conversión o redondeo distintos | Moneda del proveedor y costo final | Acordar política, sin cambiar importes históricos |
| Stock visible | Unidad físicamente disponible | Robo, merma, rotura o stock desactualizado | Mercadería reservada o en tránsito | R04 y R05, más conteo físico pendiente |
| Dos cajas a la vez | Cada una vende unidades disponibles | Ambas intentan la última unidad | Venta confirmada con respuesta perdida | Locks existentes, R02 pendiente |
| Carrito | Confirmación una sola vez | Doble clic, dos pestañas o reconexión | Pago hecho sin respuesta de la API | Idempotencia y conciliación pendientes |
| Venta cancelada | Carrito se descarta antes de registrar | Error descubierto tras confirmar | Anulación frente a devolución | Falta contrato de anulación |
| Venta a crédito | Cliente identificado y deuda conocida | Impago o pagos repetidos | Límite, plazo, responsable y saldo a favor | R03, R06 y R07 |
| Efectivo | Importe recibido y cambio correcto | Billete falso, faltante o retiro no registrado | Redondeo, vuelto y autorización | Arqueo operativo no acreditado |
| QR y transferencia | Cobro conciliado | Captura falsa o referencia repetida | Pendiente bancario o reversión externa | R08, selección no confirma banco |
| Pagos combinados | Métodos suman el total | Reintento del mismo abono | Crédito como deuda frente a dinero recibido | Validación local sí, conciliación real pendiente |
| Nota y factura | Nota representa la venta guardada | Impresión falla o se duplica | Nota comercial frente a comprobante fiscal | No se acredita integración fiscal por guardar datosFactura |
| Entrega al cliente | Retiro confirmado | Cliente no recibe o pedido se pierde | Reserva, despacho, entrega parcial y prueba de recepción | Datos de entrega son texto, no flujo logístico completo |
| Compra a proveedor | Documento e ingreso concordantes | Reimportar o recibir cantidades equivocadas | Recepción parcial, deuda y producto sustituto | R12 y revisión de recepciones |
| Cambio de costo | Nueva compra actualiza costo válido | Costo supera precio autorizado | Aceptar mercadería antes de aprobar tarifa | R14 |
| Traslado | Origen baja y destino sube una vez | Reintento o pérdida durante transporte | En tránsito frente a recibido | Consistencia lógica protegida, disponibilidad física pendiente |
| Solicitud de reposición | Flujo autorizado y único abierto | Cancelación simultánea o doble entrega | Entrega parcial y diferencia recibida | Transiciones protegidas, parciales no acreditadas |
| Conteo físico | Recuento con motivo y control | Cambia stock durante el ajuste | Cómo aprobar diferencias y cierre de inventario | expectedStock protege concurrencia, proceso humano pendiente |
| Devolución | Cantidad legítima con valor histórico | Doble intento o devolución excesiva | Pieza dañada, otro mes, crédito o reintegro | Límites protegidos, R04 y R06 |
| Devolución a proveedor | Documento y salida autorizados | Pérdida de trazabilidad | Garantía, reemplazo o nota de crédito | No acreditado un flujo dedicado |
| Reportes | Mismos filtros y periodo de negocio | Muchas páginas o cambio de datos | Ventas, caja, deuda, devolución y utilidad son medidas distintas | Agregados y snapshot existentes, alcance contable pendiente |
| Cierre mensual | Días completos de La Paz | Carga retroactiva o reloj del dispositivo incorrecto | Reabrir periodo o corregir un mes cerrado | Zona protegida, cierre comercial no acreditado |
| Impresión y exportación | Totales legibles y archivos consistentes | Impresora sin papel o archivo enorme | Reimpresión, datos personales y copias | Tests técnicos no sustituyen impresora real |
| Web compartida | Sesión correcta tras refrescar | 401 durante venta o token robado | Borradores entre usuarios del mismo navegador | Recuperación probada, protección del dispositivo pendiente |
| Móvil | Búsqueda y venta según permiso | Red inestable o imagen sin permiso de cámara | Operación offline y sincronización | No existe garantía offline. Escaneo móvil usa endpoint legacy |
| Accesibilidad y uso | Controles visibles y comprensibles | Teclado, lector, zoom o pantalla pequeña | Necesidades reales del personal | Pendiente prueba visual y con usuarios |
| Visión | Foto con candidatos y compatibilidad revisada | Mala luz, pieza parecida o servicio caído | Confianza baja y vehículo no confirmado | No debe decidir automáticamente qué pieza vender |
| Privacidad | Solo acceso necesario | Dispositivo perdido o exportación compartida | Retención y eliminación autorizada | Logs, almacenamiento local y políticas requieren revisión |
| Soporte y abuso | Incidente registrado y trazable | Empleado altera datos o proveedor comprometido | Qué puede hacer soporte sin asumir identidad de cajero | Separación de funciones y evidencias pendientes |
| Corte de Internet | Lecturas y ventas se recuperan | Resultado desconocido y reintento | Se permite vender manualmente y cómo se concilia | Procedimiento de contingencia pendiente |
| Corte de energía | Estado confirmado sobrevive al reinicio | Caja se apaga a mitad del cobro | Documento manual y registro posterior | Pendiente prueba controlada y política |
| Recuperación de desastre | Base y adjuntos restaurados | Respaldo corrupto o credencial perdida | Cuánto dato y tiempo puede perderse | R16, no acreditado |
| Actualización del sistema | Despliegue compatible y reversible | Migración falla o versión vieja sigue abierta | Convivencia entre móvil, web y API | Pendiente ensayo de actualización y rollback |
| Escalamiento | Varias cajas operan sin bloqueos excesivos | Pool, memoria, cuota o CPU agotados | Nivel de carga aceptable y presupuesto | Sin benchmark de capacidad |
| Compra predictiva | Persona revisa una sugerencia | Sobrecompra por un modelo incorrecto | Capital, espacio, pedido mínimo y plazo del proveedor | H4 no automatiza estas decisiones |

Los requisitos fiscales, de garantía, privacidad y conservación de documentos deben definirse con los responsables del negocio y comprobarse según su situación real. No se concluye cumplimiento legal a partir del código o de esta tabla. Tampoco se presume que toda capacidad mencionada sea obligatoria para cualquier tienda. Hay que fijar el alcance comercial antes de implementarla.

## 6. Qué cambia para el dataset y H4

El dataset actual conserva 56 productos, tres tiendas, 4.032 observaciones mensuales y 3.528 filas supervisadas. Es sintético, con normales y adversos válidos en todos los cortes temporales. Sus diez grises son fichas conceptuales, no pruebas operativas de la tienda. El informe anterior ya documenta los huecos del validador de catálogo y del límite int64. No se corrigieron en esta revisión.

La nueva revisión añade la relación con el proceso físico. Una unidad en tránsito o una devolución dañada puede aparecer en Inventory sin ser vendible. Un pago elegido no demuestra cobro. Una venta repetida por red puede inflar cantidades. Un traslado cambia disponibilidad, pero no es demanda de cliente. Estos problemas deben resolverse antes de convertir registros de la plataforma en historia comercial certificada.

Las simulaciones futuras deberían distinguir eventos y su disponibilidad temporal. Ejemplos: cierre incompleto, falta de stock conocida, llegada retrasada del proveedor, apertura de tienda, devolución inspeccionada, cambio persistente de mercado o de precio y producto sustituido. Los parámetros que describan esos eventos no deben filtrarse automáticamente como features. La etiqueta de ambigüedad tampoco debe convertirse en una cantidad inventada.

La recomendación de compra posterior requiere además plazo de entrega, variación de demanda, stock disponible frente a reservado y en tránsito, compras ya comprometidas, pedido mínimo, unidades por caja, espacio y presupuesto. Inventory.minStock no contiene por sí solo esos elementos. Una fórmula sencilla de reposición sirve como demostración, no acredita una política de abastecimiento real.

El entrenamiento académico puede prepararse con alcance limitado cuando se autorice. Para usar un pronóstico en la tienda hacen falta procedencia real de los datos, integridad de las operaciones, evaluación temporal y supervisión humana. Ningún dato o escenario nuevo fue agregado al dataset durante esta auditoría.

## 7. Verificaciones realizadas y pendientes

| Verificación local | Resultado de esta ronda |
|---|---|
| Tests unitarios backend | 156 aprobados |
| Tests frontend | 224 aprobados en 26 archivos |
| Tests móviles disponibles | 3 aprobados |
| Tests servicio de visión | 77 aprobados |
| Tests dataset H4 | 7 aprobados |
| Total de pruebas anteriores | 467 aprobadas, cero fallidas en sus ejecuciones finales |
| Typecheck backend | Aprobado con tsc --noEmit |
| Typecheck móvil | Aprobado |
| Build frontend | Aprobado, incluye comprobación TypeScript |
| Auditoría npm de producción | Ejecutada en backend y frontend, con hallazgos. No equivale a pruebas aprobadas. Mobile pendiente por falta de lockfile |
| Integraciones con PostgreSQL local | No ejecutadas en esta ronda |
| Pruebas contra Neon | No ejecutadas. No hubo conexión |
| Prueba visual de navegador, teléfono e impresora | No ejecutada. No se declara validación visual completa |
| Restauración, banco, caja física y carga simultánea real | No ejecutadas |

El entorno restringido bloqueó conexiones HTTP de loopback en la primera ejecución del backend. La repetición con acceso local aprobó las 156. La primera ejecución de visión no produjo resultados y se detuvo. La repetición con su entorno autorizado aprobó 77. No se cambió ninguna prueba para conseguir esos resultados. Los tests de visión usaron su servicio y modelo existentes, sin entrenamiento.

Se observaron advertencias de React Router sobre opciones futuras, actualizaciones de estado fuera de act en pruebas de login, interpretación de módulos TypeScript en móvil, deprecación de Starlette/httpx y tamaño del bundle web. No impidieron finalizar las suites o el build. Deben revisarse por compatibilidad y rendimiento, sin presentar cada advertencia como un fallo productivo demostrado.

Los 625 tests de un informe anterior incluían integraciones locales que no se repitieron ahora. Las 467 pruebas de esta ronda no reemplazan ese conjunto ni significan que se hayan eliminado pruebas. Tampoco equivalen a una certificación de producción.

## 8. Secuencia de cierre para una tienda real

Primero deben cerrarse las decisiones de dinero, autorización y stock físico, además de evaluar las alertas de dependencias. La revocación de sesiones debe impedir operar con privilegios retirados. Los reintentos deben recuperar la venta o el cobro original. Las devoluciones deben distinguir inspección, reposición vendible, reducción de deuda y reintegro. El tránsito no debe confundirse con mercadería disponible. Estas decisiones necesitan pruebas de API además de pantallas.

Después se debe ejecutar una jornada piloto con responsables del negocio en un entorno aislado. Debe incluir dos cajeros intentando vender la última unidad, corte de respuesta después de confirmar, pago parcial, abono repetido, devolución dañada, entrega parcial, cierre de caja, cambio de rol con sesión abierta e importación de la misma factura en formatos diferentes. Se conciliarán los documentos, el dinero esperado y las unidades físicas. No se hará esa prueba destructiva sobre producción.

Antes de habilitar operación comercial se debe acreditar recuperación de datos y archivos, continuidad ante red y energía, límites bajo carga y procedimientos de soporte. El equipo deberá dejar responsables, evidencias, fecha y resultado para cada bloqueo. Los puntos no aplicables al alcance comercial se justificarán expresamente, no se marcarán cumplidos por omisión.

La aceptación debe distinguir cuatro estados: código con verificaciones locales aprobadas, dataset académico disponible, piloto operativo aprobado y producción reconciliada y recuperable. Esta revisión acredita las verificaciones locales indicadas y conserva el alcance académico del dataset. **No acredita todavía piloto operativo, conciliación completa ni preparación comercial integral.**

No hubo commit, push, deploy, modificaciones en Neon, migraciones, entrenamiento o correcciones automáticas de datos. Las acciones propuestas quedan documentadas para una autorización e implementación posteriores.
