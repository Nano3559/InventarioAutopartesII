# Registro cronológico de prompts de H4

Este archivo es un log de solicitudes. La única guía vigente es [H4_IMPLEMENTACION_MODELO_PREDICTIVO.md](H4_IMPLEMENTACION_MODELO_PREDICTIVO.md). No contiene otro diseño del modelo ni resultados de entrenamiento.

## 3 de noviembre de 2026. Consolidación documental

Origen: solicitud del equipo en el chat de trabajo del proyecto. Se conserva este extracto literal disponible, no una transcripción completa:

> NECESITO REORGANIZAR Y CONSOLIDAR TODA LA DOCUMENTACIÓN ACTUAL DE H4 ANTES DE CONTINUAR CON LA IMPLEMENTACIÓN.
>
> LA FUENTE PRINCIPAL PARA DEFINIR QUÉ DEBEMOS PRESENTAR ES LA INDICACIÓN DEL DOCENTE RESUMIDA EN ESTA TAREA.
>
> NO IMPLEMENTAR TODAVÍA NUEVO CÓDIGO DE MACHINE LEARNING.
>
> PRIMERO QUIERO DEJAR UNA SOLA DOCUMENTACIÓN OFICIAL, CLARA Y COHERENTE.

Resultado documental: guía oficial consolidada, propuestas anteriores archivadas, evidencia histórica conservada y enlaces revisados. No hubo entrenamiento, regeneración de datos ni cambios productivos. La validación concreta está enlazada desde la guía oficial.

Los documentos anteriores registran auditoría, generación del dataset y correcciones, pero no equivalen a una transcripción de sus prompts. Su texto completo todavía figura como **NO RECUPERADO en este log**. No se inventaron fechas, comandos o solicitudes de entrenamiento para completar ese vacío. Cuando se recuperen mensajes originales se incorporarán con procedencia y fecha verificable.

Las próximas entradas registrarán auditoría, dataset, entrenamiento, ajustes, pruebas, integración o documentación cuando realmente ocurran. Cada entrada distinguirá texto literal de resumen, identificará la versión afectada y enlazará la evidencia obtenida. Entrenamiento e integración predictiva continúan pendientes.

## 3 de noviembre de 2026. Ampliación del documento oficial

Origen: solicitud adjunta por el equipo en el chat. Extracto literal, no transcripción completa:

> NECESITO COMPLETAR Y MEJORAR LA DOCUMENTACIÓN OFICIAL DE H4.
>
> NO crear otra propuesta paralela.
>
> La tarea es DOCUMENTAL Y DE ANÁLISIS.
>
> NO entrenar.

Alcance solicitado: base del modelo, escenarios reales, monitoreo, reentrenamiento, champion/challenger, versionado, rollback, stack comprobado y trabajo paralelo de Erika y Ross durante tres semanas. La ruta indicada en la solicitud era anterior a la reorganización. Se actualiza únicamente la guía vigente en docs/H4/H4_IMPLEMENTACION_MODELO_PREDICTIVO.md.

Resultado: ampliación documental dentro de la misma guía. Se verificaron versiones instaladas mediante metadatos, sin instalar dependencias. No se crearon modelos, registro de modelos, botón administrativo o experiments.csv. No se entrenó, regeneró dataset, modificó código, Prisma o Neon. La documentación separa lo existente, lo propuesto y el alcance H5.

## 3 de noviembre de 2026. Simulador interactivo obligatorio

Origen: nueva solicitud adjunta del equipo en el chat, posterior a la ampliación del ciclo de vida. Extractos literales, no transcripción completa:

> EL SIMULADOR NO DEBE SER SOLAMENTE UN GENERADOR DE CSV O UN SCRIPT ESTÁTICO.
>
> PARA LA DEMOSTRACIÓN DE H4 DEBE EXISTIR UN SIMULADOR INTERACTIVO QUE PERMITA MODIFICAR DATOS Y ESCENARIOS EN TIEMPO REAL Y OBSERVAR CÓMO RESPONDE EL MODELO.
>
> NO alterar dataset 1.1 histórico.

Alcance: actualizar la misma guía oficial, arquitectura, stack, plan de quince días, definición del 70 %, pruebas y demo. Se separan EDITAR, PREDECIR y REENTRENAR. El alcance H4 incorpora controles locales de escenarios, observados, avance temporal, monitoreo, candidato, promoción y rollback. La operación comercial integrada sigue en H5.

Resultado de esta actualización: diseño documentado con Streamlit como dependencia propuesta exclusiva H4, después de comparar con React y servicio Python local. Se revisaron los archivos actuales del generador, catálogo, manifiesto y stack, sin ejecutar el generador. Se consultó documentación oficial de formularios, sesiones y caché de Streamlit. Se registran pruebas pendientes, no resultados inventados. No se instaló Streamlit, implementó interfaz, entrenó, alteró el dataset, cambió código, conectó a Neon o ejecutó Git. La ruta antigua indicada en la solicitud corresponde ahora a docs/H4/H4_IMPLEMENTACION_MODELO_PREDICTIVO.md.

## 4 de noviembre de 2026. Primera interfaz de Ross

Solicitud literal del chat:

> implementa la 1ra tarea de ross de la semana 1

El equipo adjuntó la fila de responsabilidades: Ross a cargo de interfaz Streamlit, controles, edición, gráficos y validaciones. Erika conserva motor, generación dinámica, escenarios, reloj y lags.

Resultado: interfaz local en streamlit_app.py, contrato de entradas separado, dependencias de interfaz fijadas en un entorno H4 aislado y 16 pruebas aprobadas. Se revisaron pantalla, edición y gráfico en navegador local. Las ocho opciones de escenario son etiquetas de revisión hasta conectar el motor, sin precargas inventadas. Predicción y avance permanecen deshabilitados. No se entrenó, generó dataset, modificó Neon o Prisma ni ejecutó Git. La guía oficial registra cómo abrir la interfaz y lo que sigue pendiente.

## 4 de noviembre de 2026. Tareas de Ross de las tres semanas

Solicitud literal del chat:

> implementa de todo el plan de trabajo todo lo que le corresponde a Ross

El equipo adjuntó responsabilidades por semana. Ross mantiene interfaz, controles, edición, gráficos y validaciones. Añade integración de predicción, métricas, errores, monitoreo, drift y comparación visual. Erika conserva motor, generación, escenarios, reloj, entrenamiento, experimentos, inferencia, versiones, candidato y rollback.

Resultado: adaptador de runtime local, registro de emisiones y observados, métricas con coberturas, errores por grupos, monitoreo demostrativo y comparación visual con reportes validados. Las pruebas utilizan dobles exclusivos, sin entrenar. La guía oficial define el contrato para conectar el trabajo de Erika. La validación conjunta con su motor y artefactos reales queda pendiente porque todavía no existen. No se cambió Neon, Prisma, dataset 1.1 o el entorno de dependencias. No se ejecutó Git, commit o push.

Cierre de validación: 50 pruebas aprobadas, 90 enlaces locales sin roturas y hashes de datos guardados, catálogo, generador y Prisma conservados. Se revisaron las pestañas en navegador y los flujos con dobles mediante AppTest. Un error inicial del constructor de un doble fue corregido sin debilitar las comprobaciones. Los fallos de inferencia quedan como abstenciones, diferenciados de errores de datos o drift. No se registraron métricas de modelos reales ni se declaró seleccionada V1.

## 4 de noviembre de 2026. Segunda revisión de coherencia de Ross

Solicitud literal del chat:

> ahora que sigue de lo que toca a Ross, algo más? Verifica que todo sea coherente, si necesitas hacer pruebas para verificar y corregir errores hazlo

Se revisaron código, contrato y pendientes del plan. Se corrigieron la edición después de revelar el observado, la sustitución involuntaria del reporte del runtime por un archivo ya cargado, el rechazo seguro de enteros extremos y el uso de historias con lags incompatibles para recomendar drift. Las pruebas de regresión también comprobaron el cierre con valor congelado y su conservación al cambiar de tienda.

La suite de Ross pasó de 50 a 59 pruebas. El cierre con el motor y artefactos reales de Erika continúa pendiente, sin confundir esos componentes con dobles de prueba. La guía oficial incluye los pasos concretos de integración, validación conjunta, revisión visual y presentación. No se entrenó, regeneró dataset, modificó Neon, Prisma o migraciones ni ejecutó Git.
