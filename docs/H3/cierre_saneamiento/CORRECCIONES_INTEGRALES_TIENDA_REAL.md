# Correcciones integrales para una tienda real

Inicio: 3 de noviembre de 2026. Trabajo local autorizado por el equipo después de la segunda revisión integral.

Actualización posterior del mismo día: el equipo delegó las tres reglas comerciales pendientes. Ya se implementaron identidad de factura, anulación restringida de ADMIN y verificación manual de pagos. La especificación vigente está en [reglas comerciales](REGLAS_COMERCIALES_FACTURAS_ANULACIONES_Y_PAGOS.md). Los resultados de la primera parte de esta ronda se conservan como antecedente.

## Alcance y orden

La corrección se realizará primero sobre sesiones y permisos, identificación de operaciones repetidas, manejo de errores, comprobaciones de disponibilidad y validación de datos. Después se revisarán dependencias y las reglas comerciales confirmadas por el equipo. No se modificará Neon ni se desplegará la aplicación.

Se conservó un respaldo externo de fuentes, documentación, dataset y contratos antes de comenzar. Las pruebas de integración utilizarán un PostgreSQL aislado en loopback, nunca una base productiva. No se reescribirá historia Git ni se eliminarán los documentos previos.

## Reglas confirmadas y cambios realizados

El equipo confirmó que la mercadería permanece en tránsito hasta su recepción física. El despacho descuenta una sola vez en origen. La recepción ingresa únicamente la cantidad recibida en destino, dentro de una transacción. Los traslados manuales admiten recepción parcial. Una solicitud vinculada se recibe desde su propio flujo, con estado e historial en la misma transacción. No se puede recibir nuevamente desde la ruta de traslados para duplicar el ingreso. La pantalla denomina ese estado «En tránsito».

También se confirmó que una devolución solo vuelve a stock vendible después de inspección. Se registran cantidades aprobadas o no vendibles, motivo, responsable y auditoría. Se permite inspección parcial. Dos inspecciones simultáneas no pueden aprobar más unidades que las recibidas. Una cantidad no vendible queda fuera de Inventory, pero su separación física y destino final siguen siendo responsabilidad del negocio.

El importe de una devolución reduce primero la deuda pendiente. Solo el excedente ya cobrado se registra como reintegro. Por ejemplo, una venta de 100 con 40 cobrados y 60 pendientes recibe una devolución de 20. Quedan 40 pendientes y no se registra salida de dinero. Si después se devuelven otros 50, se cancelan los 40 pendientes y se registran 10 de reintegro. El saldo incorpora esos reintegros para evitar crear deuda artificial. La aplicación registra este hecho, no ejecuta ni confirma una transferencia bancaria.

Las nuevas ventas a crédito requieren un cliente identificado. Esto evita crear deuda anónima. No sustituye una política de cupos, vencimientos, autorización de crédito o verificación de identidad.

La autenticación verifica el usuario, rol y ubicación actuales en la base. Cambiar contraseña, rol o ubicación revoca las sesiones anteriores de forma transaccional. El cierre de sesión registra una huella del token, nunca su valor. Un token de administrador anterior no conserva ese privilegio después de cambiar el rol. Si el servidor no puede verificar la sesión, responde 503 y no concede acceso. Un cierre de sesión sin red limpia el dispositivo, pero no puede garantizar revocación remota.

Ventas normales, mayoristas, abonos y devoluciones admiten una identidad de operación. El servidor bloquea esa identidad, compara la huella de la solicitud y guarda resultado y cambio comercial juntos. El mismo intento devuelve el resultado anterior. Otra solicitud con la misma identidad pero distinto contenido se rechaza. Web y venta móvil conservan la identidad pendiente para recuperarse de una respuesta perdida. La recuperación está limitada al usuario, módulo, rol y ubicación correspondientes. No se guarda el carrito ni el cliente en ese almacenamiento de intentos.

Se conserva compatibilidad con clientes antiguos que no envían identidad en ventas, abonos o devoluciones. Es una limitación abierta: esos clientes todavía pueden duplicar operaciones al reintentar. Hacer obligatoria la identidad requiere cerrar y comprobar el contrato de todos los consumidores. La inspección y la recepción parcial sí la exigen. No se presenta esta compatibilidad como idempotencia universal.

Se centralizó el cliente Prisma de los módulos y del proceso de reposición. Se agregó /api/ready, que verifica conexión y columnas necesarias para esta versión. /api/health conserva la comprobación de proceso vivo. El servidor drena conexiones al recibir señales de apagado. Los clientes tienen un tiempo máximo de espera de 35 segundos. El vencimiento de ese tiempo indica resultado desconocido, no fracaso comercial confirmado.

Se retiraron mensajes, SQL y objetos de error sin filtrar de 83 registros de errores, además de notificaciones y el manejador general. Se conserva un código controlado. La prueba de este filtro comprueba que no se registren contraseñas, consultas ni cuerpos. La configuración de acceso, retención y centralización de los logs de producción sigue pendiente.

Las tres rutas de importación Excel comparten límites de 10 MB de archivo, 32 MB declarados descomprimidos, 1.000 entradas ZIP, 5.000 filas de datos y 100 columnas en la primera hoja. Se rechazan archivos excesivos con una explicación. No se acepta una importación silenciosamente truncada. Estos controles reducen el riesgo, pero no equivalen a aislamiento del parser en un proceso separado ni a un límite garantizado de CPU frente a cualquier archivo malicioso.

La interfaz actualiza las listas después de recibir o inspeccionar stock. Los estados de devolución se explican en español. Se mantienen POR MENOR = Product.price1, POR MAYOR = Product.wholesalePrice y Product.price2 legacy. No se alteraron precios ni datos históricos reales.

## Prisma y pruebas de migración

Se creó 20261103_physical_stock_and_returns. Agrega Movement.status, receivedQuantity y receivedAt. Agrega Return.disposition, restockedQuantity, discardedQuantity, debtReduction, refundAmount e inspectedAt. Incluye índices y restricciones sobre cantidades y distribución económica. No elimina columnas ni cambia valores comerciales existentes. Los registros previos quedan LEGACY, con cantidades nuevas en cero. No se infiere que una pieza histórica fue inspeccionada ni que hubo un reintegro bancario.

La migración histórica 20260909_close_schema_drift conservaba EN_PREPARACION, ENVIADO y RECIBIDO dentro de RequestStatus. Prisma no los declaraba. Se añadieron al enum del schema en el orden físico original como valores legacy. La API no los admite en nuevas transiciones. No se borró, convirtió ni reescribió la migración histórica.

Prisma CLI y cliente instalados: 5.22.0. Después de la migración comercial adicional, se aplicaron las diez migraciones sobre una base PostgreSQL 16 local vacía. Una segunda ejecución no encontró migraciones pendientes. migrate diff no encontró diferencias representables por Prisma frente al schema. Las restricciones CHECK e índices parciales también se conservan en SQL, aunque el diff de Prisma no describe todos esos objetos. La revisión de migración no certifica por sí sola el esquema productivo.

La migración aditiva 20261103b_commercial_controls incorpora las reglas comerciales delegadas. Se explica junto a sus límites en el documento de reglas comerciales. No modifica la migración anterior.

No se consultó ni modificó Neon. No se utilizó neontest. Antes de desplegar esta versión será necesario reconciliar producción mediante el procedimiento autorizado de rama aislada, respaldo y revisión de datos. La aplicación nueva necesita las columnas nuevas. No debe desplegarse contra el esquema anterior.

## Resultado de los hallazgos anteriores

Los IDs corresponden a SEGUNDA_REVISION_INTEGRAL_TIENDA_REAL.md. «Corregido localmente» indica el comportamiento comprobado que se describe, no una certificación comercial completa.

| ID | Estado posterior | Corrección o pendiente concreto |
|---|---|---|
| R01 | Corregido localmente | Estado actual de usuario, revocación por cambios y logout. Falta una política explícita de suspensión de cuentas |
| R02 | Parcial | Venta web y móvil conservan identidad. API protege y permite consultar esos intentos. Clientes antiguos sin identidad permanecen expuestos |
| R03 | Parcial | Abonos con identidad se registran una vez. Falta hacerla obligatoria y conciliar el comprobante bancario |
| R04 | Corregido para operaciones nuevas | Inspección antes de stock vendible. Legacy no se reinspecciona ni repone automáticamente |
| R05 | Corregido para operaciones nuevas | Despacho, tránsito y recepción separados. Falta proceso de pérdida o diferencia física en tránsito |
| R06 | Corregido para operaciones nuevas | Deuda primero, reintegro del excedente, saldo coherente. Legacy requiere conciliación humana |
| R07 | Parcial | Cliente obligatorio si hay crédito. Cupos, vencimientos y autorización pendientes |
| R08 | Verificación manual implementada localmente | Cuenta receptora, referencia única por fecha, confirmación expresa, usuario y auditoría. Sin integración bancaria automática. Históricos sin certificar |
| R09 | Anulación restringida implementada localmente | Solo ADMIN, sin cobros o devoluciones, mercadería nunca entregada y verificada. Conserva evidencia, repone una vez, excluye reportes y deja deuda cero |
| R10 | Pendiente de proceso comercial | Falta alcance de apertura, cierre, fondo inicial, arqueo, retiros y aprobación de diferencias |
| R11 | Parcial | Logs de errores filtrados. Retención, acceso y revisión del resto de observabilidad productiva pendientes |
| R12 | Identidad implementada localmente | Proveedor e identificador completo, contenido comparable y cabecera única. Incluye recepción manual. Legacy, parciales y documentos correctivos pendientes |
| R13 | Pendiente de criterio contable | El costo agregado del reporte no acredita utilidad contable por línea. Ventas netas no equivalen a dinero de caja |
| R14 | Pendiente de recepción comercial | No se cambian precios silenciosamente. Falta recepción pendiente cuando el nuevo costo exige revisión de precios |
| R15 | Corregido localmente | Ready comprueba base y columnas. Falta configurar su uso en hosting y alertas |
| R16 | Parcial | Respaldo y restauración local con datos ficticios verificados. No acredita recuperación de Neon o adjuntos reales |
| R17 | Pendiente de infraestructura | Persistencia y respaldo de uploads en hosting no comprobados |
| R18 | Pendiente de capacidad | Límite general por IP conservado. Falta dimensionarlo con cajas reales que compartan red |
| R19 | Pendiente de escalamiento | Caché y limitador siguen por proceso. No se certifica consistencia inmediata entre varias instancias |
| R20 | Corregido localmente | Pool compartido en módulos y job. Falta medir conexiones bajo carga |
| R21 | Parcial | Manejo de señales y drenaje implementados. Falta ensayo de terminación forzada y corte de energía |
| R22 | Pendiente de continuidad | Reposición posterior al commit y job conservados. Falta acreditar recuperación, supervisión y aviso ante fallos persistentes |
| R23 | Parcial | Timeout y recuperación de resultado en clientes actualizados. Offline y consumidores antiguos no certificados |
| R24 | Parcial | Límites comunes de importación y pruebas. Falta aislamiento de proceso, carga y límites estrictos de tiempo |
| R25 | Pendiente de capacidad | Pruebas de visión aprobadas. No se midió saturación simultánea real de CPU/GPU |
| R26 | Corregido en build local | Pantallas cargadas bajo demanda. Principal de unos 2 MB a 292 kB. Archivos inferiores a 500 kB. Falta medir red y teléfono reales |
| R27 | Pendiente productivo | Diez migraciones comprendidas y probadas localmente. Neon permanece sin consultar |
| R28 | Pendiente de infraestructura | Alertas, cuotas, certificados, soporte y responsables productivos sin acreditar |
| R29 | Parcial | Auditoría npm de producción: backend 0, frontend 0. Móvil conserva 55 paquetes afectados, incluida una alerta crítica |
| R30 | Parcial | Lockfile móvil creado y parches compatibles aplicados. Expo 51 necesita una actualización mayor planificada y prueba nativa |

## Dependencias y rendimiento

Se actualizaron dependencias compatibles del backend y frontend. Se mantuvo Express 4. SheetJS se instaló desde su distribución oficial 0.20.3, porque la publicación antigua de npm no ofrecía el parche necesario. React Router se actualizó a 7.18.5 conservando las rutas declarativas y pasando los tests. No se utilizó audit fix --force.

La auditoría final de dependencias de producción reportó cero vulnerabilidades en backend y frontend. El lockfile móvil permitió detectar 62 inicialmente. Después de parches compatibles quedan 55: tres bajas, 35 moderadas, 16 altas y una crítica. La crítica corresponde a tar dentro del árbol de herramientas de Expo. Esto no demuestra una explotación de la aplicación instalada, pero impide declarar cerrada la seguridad móvil. No se forzó una actualización de Expo 51 a una versión mayor sin pruebas nativas. La resolución también avisó conflictos de peers en dependencias internas, que requieren revisión durante esa actualización.

La carga de pantallas bajo demanda redujo el principal a aproximadamente 292,38 kB, 96,99 kB gzip. El archivo mayor del build quedó alrededor de 414,26 kB. Ya no apareció la advertencia de 500 kB. El resultado prueba separación del build, no tiempo de respuesta comercial en un dispositivo real.

## Dataset H4

Se conserva data/escenarios_v1 y su generador exacto en versions/generate_v1_0_0.py. La nueva versión 1.1 valida pertenencia al catálogo, exclusión de reservados, IDs duplicados o booleanos, campos mínimos de productos y tiendas, cantidades no negativas y límite int64. Las pruebas agregadas rechazan un catálogo con IDs inventados y cantidades que desbordan el rango. El conteo de tiendas ya no está fijado a tres en el generador.

La versión nueva está en ml/demand/data/escenarios_v1_1. Conserva 56 productos del snapshot anterior, tres tiendas, 24 meses, seed 42, 4.032 filas mensuales y 3.528 supervisadas. Hay 2.897 observaciones normales y 1.135 adversas válidas en la base. Se rechazan 15 fixtures inválidos. Los diez grises permanecen separados con evidencia incompleta, fecha de disponibilidad y necesidad de revisión. No se inventa target para ellos. Las ventas simuladas no cambiaron para mejorar métricas de algún modelo.

El snapshot del catálogo sigue fechado el 27 de octubre de 2026. No se presenta como una lectura actual. El dataset puede servir para un experimento académico acotado cuando se autorice. No certifica demanda perdida por falta de stock ni toda la operación comercial. Faltan, entre otros, cambios persistentes de mercado, aperturas o cierres, retrasos físicos y evaluación de esos grupos. Los grises son fixtures documentales comprobados en su separación, no un resolvedor automático de ambigüedades. No se entrenó baseline, regresión, bosque ni red neuronal.

## Pruebas y límites

| Comprobación | Resultado final |
|---|---|
| Backend unitario | 160 aprobadas |
| Integraciones con PostgreSQL local | 183 aprobadas |
| Frontend | 228 aprobadas en 28 archivos |
| Móvil | 3 aprobadas y typecheck aprobado |
| Visión | 77 aprobadas en la ejecución anterior, servicio sin cambios en esta ampliación |
| Dataset | 10 aprobadas en la ejecución anterior, dataset sin cambios en esta ampliación |
| Total de pruebas distintas vigentes | 661 aprobadas, incluidas 87 de visión y dataset sin cambios que no se repitieron en la ampliación comercial |
| TypeScript backend | Aprobado |
| Build frontend | Aprobado, con TypeScript |
| Prisma validate | Aprobado |
| Cadena de migraciones desde base local vacía | Diez aplicadas, segunda ejecución sin pendientes, diff sin diferencias |
| Restauración local con datos ficticios | Diez tablas con conteos y huellas iguales |
| Revisión visual web | Bloqueada por la herramienta al no poder verificar con seguridad la URL del navegador |
| Teléfono, cámara e impresora físicos | No comprobados |
| Neon, banco y producción | Sin conexión ni pruebas de escritura |

Las 661 pruebas vigentes incluyen las 625 de la aplicación informadas anteriormente, los diez tests del dataset y las nuevas comprobaciones de ambas partes de esta ronda. La ampliación comercial repitió 574 pruebas de backend, frontend y móvil, sin sumar ejecuciones duplicadas. No se suman las repeticiones. Los tests que esperaban ingreso inmediato de mercadería se actualizaron a la regla aprobada. Primero comprueban que no existe ingreso y después conservan la comprobación de stock tras recepción o inspección. Los fixtures de crédito ahora incluyen un cliente identificado. No se retiraron esas validaciones para esconder errores.

La primera ejecución sin acceso a loopback falló por restricciones del entorno. Una repetición sin DATABASE_URL explícita no pudo inicializar el fixture. Ambas se repitieron con la conexión local fijada, sin cambiar a Neon. No se cuentan como regresiones corregidas del producto. Hubo además dos errores de comillas en comandos de comprobación que no ejecutaron sus operaciones y se corrigieron. Las ejecuciones finales aprobadas son las registradas arriba.

Persisten advertencias de act en algunos tests React, capacidades de navegación y canvas que jsdom no implementa, interpretación de módulos TypeScript en móvil y deprecación de Starlette/httpx en visión. Las integraciones también muestran mensajes de OCR por imágenes de fixture inválidas y MaxListenersExceededWarning durante esas pruebas. No se ocultó elevando artificialmente el límite de listeners. Se requiere aislar su origen antes de certificar estabilidad bajo carga. Los avisos de finales de línea Git son informativos. Ninguno equivale a validación visual o nativa.

La comprobación de respaldo usó pg_dump y pg_restore en el PostgreSQL aislado, puerto 55447. Se creó un fixture ficticio mediante la utilidad testing/restoreFixture.ts, protegida para rechazar bases remotas. Incluye producto, inventario, venta, detalle, dos pagos, devolución, traslado, solicitud, tres usuarios y auditoría. Se compararon diez tablas no vacías por conteo y huella del contenido. Los archivos están fuera del repositorio en el respaldo externo de esta ronda. El fixture permanece solo en ese clúster local. No se demuestra con ello la recuperación de documentos, hardware o producción.

## Decisiones pendientes y criterio de aceptación

El equipo respondió delegando la identidad de factura, las reglas de anulación y la verificación bancaria. Las decisiones implementadas y sus límites están en REGLAS_COMERCIALES_FACTURAS_ANULACIONES_Y_PAGOS.md. Se conservaron los históricos y no se simuló una conexión bancaria.

También quedan por acordar caja y arqueo, crédito y vencimientos, costo contable, diferencias físicas, garantías, recepción de compras con costo nuevo y responsables de contingencia. Los datos históricos dudosos del informe anterior conservan su condición. No se repararon categorías, ventas demo, ubicaciones históricas o registros legacy por inferencia.

El estado final es **correcciones locales verificadas con pendientes explícitos**. No está acreditado que todo el sistema esté listo para una tienda real. Tampoco se declara producción reconciliada ni seguridad móvil cerrada. Antes de aceptar operación comercial deben cerrarse las reglas pendientes, actualizar y probar móvil, completar la revisión visual y realizar un piloto con conciliación física, dinero, recuperación, cortes de red y carga real.

No hubo commit, push, deploy, cambios de historia Git, conexión a Neon ni entrenamiento. La migración nueva fue probada únicamente en bases locales. La evidencia de archivos modificados y nuevos, junto con git status y git diff --stat, se guarda en auditorias/2026-11-03/estado-local-final.txt. Los logs de pruebas y auditorías quedan en esa misma carpeta. La revisión anterior se conserva como evidencia, con un enlace al estado posterior.
