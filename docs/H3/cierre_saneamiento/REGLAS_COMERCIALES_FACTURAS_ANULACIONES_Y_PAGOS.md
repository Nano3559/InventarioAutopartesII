# Facturas, anulaciones y verificación manual de pagos

Fecha: 3 de noviembre de 2026. El equipo delegó la definición de estas reglas para cerrar los tres pendientes de la revisión integral. Se implementaron localmente, con respaldo previo. No se consultó Neon ni se modificaron datos productivos.

## 1. Identidad de factura de compra

Una factura se identifica por proveedor e identificador completo del documento. El campo de entrada se llama documentIdentity. Se debe copiar el número con sus ceros, serie, autorización o gestión cuando formen parte de la identificación impresa. No se utiliza el nombre del archivo. No se agrega automáticamente una gestión que el documento no contiene.

PurchaseInvoice conserva ese texto, una clave normalizada, la huella del contenido, el resultado registrado y su fecha de creación. La clave normalizada aplica Unicode NFKC, quita espacios externos, reúne espacios repetidos y convierte letras a mayúsculas. No elimina ceros ni signos del identificador. Existe una restricción única para supplierId e identityKey. Esto evita repetir una identidad aunque se use otro archivo, nombre o compresión.

El contenido comparable incluye productos, cantidades, costos calculados, ubicación y parámetros de importación. El orden de las líneas del Excel no cambia esa comparación. Repetir la identidad con el mismo contenido recupera el resultado anterior sin ingresar stock ni registrar nuevos costos. La respuesta indica replayed. Si cambia el contenido o destino, se bloquea la operación para revisión. La creación de cabecera, costos, ingresos y auditoría comparte una transacción con bloqueo por identidad.

La importación conserva además la protección anterior por hash del archivo. Un archivo ya importado con otra identidad, o con una importación histórica sin identidad certificada, exige revisión. No se asigna una factura nueva sobre un ingreso histórico por inferencia.

La recepción manual de una sola línea también exige documentIdentity y utiliza PurchaseInvoice. La factura completa debe registrarse en una sola operación. Para comprobantes con varios productos se utiliza la importación completa. Registrar varias líneas de una factura en peticiones independientes queda bloqueado, porque podría repetir el ingreso. La recepción parcial contra una factura ya registrada necesita un proceso posterior con saldo de recepción. No se simula ese proceso cambiando el identificador.

Los costos vinculados a la factura no admiten edición o eliminación por API. La interfaz los identifica como documentos conservados. Una corrección comercial requiere un documento correctivo y conciliación. Ese flujo todavía no está implementado. Los ajustes de costo sin ingreso físico conservan su contrato y no constituyen por sí mismos una cabecera de factura ni un libro contable.

Los archivos repetidos o rechazados recién subidos se eliminan de la carpeta temporal del flujo. El adjunto original vinculado se conserva. La persistencia y respaldo de uploads en producción sigue siendo un pendiente independiente.

La identidad depende de que ADMIN registre correctamente proveedor y documento. No existe lectura fiscal automática ni una certificación de autenticidad del comprobante. Proveedores duplicados o identificadores transcritos de forma diferente requieren control humano. Los documentos anteriores quedan sin PurchaseInvoice hasta una conciliación autorizada.

## 2. Anulación administrativa de una venta

Solo ADMIN puede anular. La venta debe carecer de cobros distintos de crédito y no tener devoluciones. El responsable debe declarar que toda la mercadería nunca fue entregada, sigue en la ubicación original, fue contada y está vendible. Se exige un motivo de 10 a 500 caracteres y una identidad de operación.

Si hubo entrega, un cobro o una devolución, se utiliza el proceso de devolución y conciliación. La anulación directa no ejecuta reintegros ni crea devoluciones ficticias. Una venta histórica sin detalle válido o con total inconsistente tampoco se anula automáticamente.

La API POST /api/sales/:id/void bloquea la venta, comprueba sus datos actuales y bloquea inventarios en el mismo orden que ventas. Restituye las cantidades verificadas una sola vez y cambia Sale.status a VOIDED. Conserva total, detalles y pagos originales. Guarda voidReason, voidedAt y voidedById, además de un AuditLog VOID_SALE con las cantidades restituidas y la declaración física. No se borra la venta ni se reescribe su fecha original.

Una venta anulada tiene saldo exigible cero. No admite abonos ni devoluciones posteriores. El backend comprueba esas condiciones dentro de la transacción, por lo que una carrera con un cobro o devolución no permite ambos resultados incompatibles. Reintentar la anulación no repone stock nuevamente. Recuperar o repetir el intento de creación muestra también el estado actual VOIDED.

Los agregados de ventas del dashboard y los reportes diarios, filtrados y mensuales excluyen VOIDED. El historial conserva la venta y muestra ANULADA. La nota de venta muestra estado, motivo, fecha en America/La_Paz y responsable. Los importes originales permanecen visibles como evidencia. El motivo se escapa antes de generar HTML. La anulación es interna de RepuestoPro y su nota no acredita un trámite fiscal externo.

ADMIN debe revisar las solicitudes de reposición abiertas después de anular. No se cancelan automáticamente, porque pueden cubrir otras ventas o estar despachadas. Tampoco se alteran traslados en curso. Las devoluciones conservan la regla aprobada de inspección antes de stock vendible.

## 3. QR y transferencia sin proveedor bancario

No existe una integración bancaria configurada. Para un nuevo cobro positivo por QR o transferencia, el operador debe comprobar el abono en la cuenta de la empresa antes de registrarlo. Una captura enviada por el cliente no basta.

ADMIN registra las cuentas receptoras desde el formulario de verificación web. ReceivingAccount contiene un código único, nombre visible y condición activa. Se utilizan alias de cuenta, nunca contraseñas, tokens ni claves bancarias. Administración debe mantener una sola ficha por cuenta real. Crear varios alias para la misma cuenta debilitaría la detección de duplicados.

La verificación exige cuenta receptora activa, referencia bancaria, fecha válida del abono y confirmación expresa. El servidor toma la hora y el usuario autenticado para verifiedAt y verifiedById. No acepta esos dos datos como evidencia enviada por el cliente. La fecha no puede ser futura respecto a America/La_Paz. La referencia conserva ceros y signos, normaliza espacios y mayúsculas.

La combinación receivingAccountId, bankReference y bankOperationDate es única. No incluye el método, porque el mismo abono podría intentarse registrar como QR y luego como transferencia. La restricción aplica entre ventas normales, mayoristas y abonos. Una carrera concurrente no puede registrar dos veces esa combinación. El mismo intento legítimo con la misma identidad de operación recupera el resultado previo.

Payment conserva la cuenta, referencia, fecha, responsable y hora de verificación. Se registra además CONFIRM_BANK_RECEIPT en auditoría dentro de la transacción comercial. Si la venta o el abono falla, esa evidencia tampoco se confirma. Web y móvil incluyen los campos necesarios. Cambiar datos del pago obliga a confirmar la comprobación otra vez. La nota explica si un pago bancario fue verificado manualmente o es histórico sin evidencia registrada.

Un nuevo QR o transferencia sin esa declaración se rechaza antes de confirmar la venta o el cobro. No se crea un pago pendiente que pudiera confundirse con dinero recibido. Si el negocio decide vender a crédito mientras espera el abono, debe registrar expresamente crédito con cliente identificado. No debe marcar QR como cobrado por anticipado.

Esta regla registra responsabilidad humana, no demuestra por software que el banco abonó el dinero. No se verifican automáticamente titular, moneda, importe real del movimiento, liquidación, reverso o contracargo. Una referencia transcrita con otra fecha o asociada a una ficha duplicada necesita conciliación. El mismo movimiento utilizado para pagar varias ventas debe registrarse en una sola operación compatible, o requerirá una futura entidad de abono con aplicaciones parciales. No se lo divide repitiendo la referencia.

Los pagos históricos conservan sus campos nuevos en NULL. No se certifican ni se convierten automáticamente en verificados. Tampoco se cambian sus importes o saldos por inferencia. Los reintegros de devoluciones siguen siendo registros de una salida declarada, sin ejecución bancaria automática.

## 4. Migración y validación local

La nueva migración 20261103b_commercial_controls agrega SaleStatus y los datos de anulación, ReceivingAccount, la evidencia bancaria de Payment, PurchaseInvoice y su relación con Cost. Incluye las restricciones únicas y las referencias necesarias. Es aditiva. No elimina columnas, completa referencias antiguas ni modifica precios.

Las diez migraciones se aplicaron desde una base local vacía. La segunda ejecución no encontró pendientes. Prisma validate y el diff entre base local y schema.prisma aprobaron. Prisma CLI y cliente instalados siguen en 5.22.0. La aplicación necesita estas columnas antes de desplegarse. Producción deberá seguir el procedimiento independiente de reconciliación, rama aislada y recuperación. No se ejecutó ninguna operación en Neon.

La suite nueva controlesComerciales.itest.ts contiene nueve pruebas. Comprueba ausencia de evidencia bancaria, fechas inválidas, cuentas y permisos, registro del responsable, reintento del mismo cobro, referencia repetida entre métodos, concurrencia entre ventas, abonos y mayoristas, factura equivalente en otro archivo, contenido cambiado, recepción manual, conservación de costos facturados, anulación concurrente, deuda cero, protección de cobros y devoluciones, recuperación de una venta posteriormente anulada, exclusión de reportes y nota con HTML escapado.

Los fixtures anteriores que representaban abonos legítimos ahora usan el adaptador explícito postVerifiedBankFixture. Proporciona una cuenta ficticia local y referencias diferentes para movimientos diferentes. Las pruebas nuevas llaman directamente a la API para comprobar que la falta de evidencia se rechaza. Los fixtures de recepción incluyen identidad de factura. Se conservaron las comprobaciones de cantidades, precios, saldo y concurrencia.

La web incorpora dos pruebas nuevas del formulario bancario. Comprueban que la confirmación no venga marcada, que cambiar referencia invalide la anterior y que TIENDA no pueda registrar cuentas. La revisión visual y las pruebas nativas físicas siguen pendientes. Un build o test de componentes no las reemplaza.

| Comprobación ejecutada en esta ampliación | Resultado |
|---|---|
| Backend unitario | 160 aprobadas |
| Integraciones en PostgreSQL local | 183 aprobadas |
| Frontend | 228 aprobadas en 28 archivos |
| Móvil | 3 aprobadas |
| Total ejecutado, sin repetir conteos | 574 aprobadas, cero fallidas u omitidas en las ejecuciones finales |
| TypeScript backend, frontend y móvil | Aprobado |
| Build frontend | Aprobado |
| Prisma validate y diff local | Aprobados, sin diferencias |
| Cadena desde base local vacía | Diez migraciones aplicadas, segunda ejecución sin pendientes |

Las 77 pruebas del servicio de visión y diez del dataset de la ronda anterior mantienen su evidencia. No se repitieron porque esos componentes no cambiaron en esta ampliación. El conjunto vigente suma 661 pruebas distintas, pero solo 574 se ejecutaron ahora. Una prueba nueva detectó una fecha bancaria imposible inicialmente aceptada y permitió corregir el validador. Su ejecución final aprobó. No se eliminó ni relajó esa prueba.

Se compararon además diez tablas del fixture ficticio local con su copia anterior a esta migración. Coinciden conteos y huellas de las columnas originales. Se excluyeron únicamente los campos nuevos de esa comparación. La evidencia está en controles-comerciales-conservacion-local.txt. Esto comprueba conservación del fixture local, no del historial de Neon, que no se consultó.

La evidencia final de pruebas está en auditorias/2026-11-03/controles-comerciales-integraciones.log, controles-comerciales-unitarios.log, controles-comerciales-frontend.log y controles-comerciales-build.log. El inventario de archivos modificados y nuevos, git status y git diff --stat está en estado-controles-comerciales.txt dentro de esa carpeta. Las ejecuciones repetidas no se suman como pruebas nuevas.

## 5. Efecto en H4 y límites restantes

No se generó otro dataset, se entrenó un modelo o se implementó una predicción en esta ronda. El panel sintético 1.1 permanece sin cambios. Para una extracción real futura, una venta anulada no representa una venta comercial válida. No se deben usar referencias bancarias, clientes o responsables como features.

La extracción temporal deberá considerar cuándo se conoció una anulación. Usar el estado actual para reconstruir lags pasados podría introducir información futura. voidedAt ayuda a identificar el momento, pero no sustituye snapshots completos o un proceso de cierre. Las devoluciones y sus reintegros tampoco deben convertirse en ventas negativas dentro del target bruto.

Se cierran localmente las reglas delegadas de identidad de factura, anulación restringida y comprobación bancaria manual. Permanecen pendientes las recepciones parciales de factura, documentos correctivos, conciliación y reversos bancarios, arqueo de caja, política de crédito, validación física, seguridad móvil y reconciliación productiva. No se declara toda la plataforma lista para una tienda real por haber aprobado estas pruebas.

No hubo commit, push, deploy, cambios de historia Git, conexión a Neon, reparación automática de históricos ni entrenamiento.
