# PLAN DE TRABAJO — REPUESTOPRO / INVENTARIO AUTOPARTES II

## 1. Objetivo

Este documento contiene la distribución oficial de tareas del proyecto entre:

* **Erika**
* **Ross**

Su objetivo es:

* registrar todo lo pendiente;
* evitar que ambos trabajen sobre los mismos archivos;
* controlar el avance mediante checklist;
* separar los requerimientos del ingeniero de las mejoras técnicas;
* facilitar el trabajo con OpenCode;
* reducir conflictos Git;
* revisar cada cambio antes de integrarlo a `main`.

---

# 2. Reglas generales de trabajo

## Git

Ramas actuales:

* `main`
* `erika`
* `ross`

Cada integrante debe trabajar únicamente en su propia rama.

Antes de comenzar una nueva etapa:

```bash
git checkout main
git pull origin main

git checkout erika
git merge main
```

Ross debe realizar el mismo procedimiento reemplazando `erika` por `ross`.

No realizar directamente cambios sobre `main`.

No hacer `push --force`.

No eliminar migraciones, archivos de configuración o documentación sin revisar previamente su función.

---

## Convención del checklist

* `[ ]` Pendiente
* `[x]` Completado
* `[~]` En proceso
* `[!]` Bloqueado o requiere revisión conjunta

Cada tarea debe marcarse como completada únicamente después de verificar que:

1. el código compila;
2. no se rompió funcionalidad existente;
3. se ejecutaron las verificaciones correspondientes;
4. se revisó `git diff`;
5. no se agregaron cambios ajenos a la tarea.

---

# 3. Distribución general

## ERIKA

Responsabilidad principal:

* Frontend
* Mobile
* Documentación general
* README
* `.gitignore`
* Archivos `.md`
* Testing frontend/mobile
* Integración cliente

## ROSS

Responsabilidad principal:

* Backend
* Base de datos
* Seguridad
* Prisma
* Git Convention
* Stack tecnológico
* AGENTS
* Agentes
* Skills
* Testing backend

---

# 4. ETAPA 1 — REQUERIMIENTOS SOLICITADOS POR EL INGENIERO

Esta etapa debe realizarse antes de comenzar mejoras técnicas opcionales.

---

# ERIKA — ETAPA 1

## E1. README principal

* [x] **E1.1 — Crear `README.md` en la raíz**

Debe incluir:

* nombre del proyecto;
* descripción;
* objetivo;
* funcionalidades principales;
* roles del sistema;
* arquitectura general;
* requisitos previos;
* instalación;
* configuración;
* ejecución;
* variables de entorno;
* backend;
* frontend;
* mobile;
* PostgreSQL;
* Prisma;
* testing;
* deployment;
* estructura de carpetas;
* comandos principales.

### Criterio de terminado

* existe `README.md`;
* no contiene credenciales reales;
* los comandos documentados funcionan;
* refleja el stack real;
* describe backend, frontend y mobile;
* utiliza la información del stack preparada por Ross.

### Archivos

```text
README.md
```

---

## E2. `.gitignore`

* [x] **E1.2 — Revisar y completar `.gitignore` raíz**

Debe revisar cobertura para:

```text
node_modules/
dist/
.env
.env.local
.env.development
.env.production
coverage/
uploads/
.expo/
.vscode/
.idea/
.DS_Store
Thumbs.db
*.log
*.tmp
*.swp
*.pem
*.key
*.tsbuildinfo
.codebase-memory/
```

### NO ignorar

```text
.env.example
package-lock.json
schema.prisma
prisma/migrations/
src/
```

### Importante

Antes de agregar reglas para archivos ya versionados, comprobar primero:

```bash
git ls-files
```

No eliminar archivos locales automáticamente.

### Criterio de terminado

* `.gitignore` cubre archivos privados y generados;
* `.env.example` continúa versionado;
* migraciones continúan versionadas;
* código fuente no fue ignorado;
* ningún archivo importante fue eliminado.

### Archivos

```text
.gitignore
```

---

## E3. Variables de entorno frontend/mobile

* [x] **E1.3 — Crear o completar `frontend/.env.example`**

Debe documentar únicamente variables necesarias.

No colocar valores secretos reales.

* [x] **E1.4 — Crear o completar `mobile/.env.example`**

Debe incluir las variables requeridas por Expo/mobile sin credenciales reales.

### Criterio de terminado

Un nuevo desarrollador puede configurar frontend y mobile siguiendo los `.env.example`.

---

## E4. Organización de archivos Markdown

* [x] **E1.5 — Revisar todos los archivos `.md` actuales**

Revisar:

```text
CORRECCION_OBERSERVACIONES.md
CORRECCIONES_DOCENTE_2026-09-01.md
PLAN_TRABAJO_MARTES.md
TAREAS_ERIKA_Y_ROSS.md
```

Para cada archivo determinar:

* si sigue vigente;
* si es histórico;
* si contiene pendientes;
* si contiene información duplicada;
* si contiene credenciales;
* si debería permanecer en raíz;
* si debería moverse a `docs/`.

---

* [x] **E1.6 — Eliminar credenciales escritas en documentación**

Eliminar únicamente credenciales reales o de prueba que no deban aparecer en Git.

No borrar información funcional del documento.

---

* [x] **E1.7 — Crear carpeta `docs/` si corresponde**

Mover allí documentación histórica o secundaria.

Ejemplo esperado:

```text
docs/
├── CORRECCION_OBERSERVACIONES.md
├── CORRECCIONES_DOCENTE_2026-09-01.md
├── PLAN_TRABAJO_MARTES.md
└── TAREAS_ERIKA_Y_ROSS.md
```

No mover `README.md`.

No mover `AGENTS.md`.

### Criterio de terminado

La raíz queda limpia y la documentación sigue disponible.

---

# ROSS — ETAPA 1

## R1. Git Convention

* [x] **R1.1 — Crear documentación de Git Convention**

Debe documentar el flujo actual:

```text
main
erika
ross
```

Debe explicar:

* cómo actualizar `main`;
* cómo actualizar la rama personal;
* cómo iniciar una tarea;
* cómo revisar cambios;
* cómo hacer commit;
* cómo hacer push;
* cómo crear Pull Request;
* cómo integrar cambios;
* cómo resolver conflictos;
* qué hacer cuando `main` cambió;
* qué archivos no deben subirse.

---

* [x] **R1.2 — Definir Conventional Commits**

Formato:

```text
tipo(scope): descripción
```

Tipos recomendados:

```text
feat
fix
docs
refactor
test
chore
```

Scopes recomendados:

```text
auth
sales
inventory
movements
reports
prices
products
frontend
mobile
db
docs
```

Ejemplos:

```text
feat(sales): add stock validation
fix(auth): require jwt secret
docs(readme): add installation guide
test(inventory): add stock movement tests
```

---

* [x] **R1.3 — Documentar flujo de Pull Request**

Debe establecer como mínimo:

```text
rama personal
↓
push
↓
Pull Request
↓
revisión
↓
main
```

No introducir `develop` salvo que exista una necesidad futura real.

### Criterio de terminado

Erika y Ross pueden seguir el documento sin necesitar instrucciones externas.

---

## R2. Stack tecnológico

* [x] **R1.4 — Documentar stack Backend**

Debe incluir el stack real encontrado en `package.json`:

* Node.js;
* TypeScript;
* Express;
* Prisma;
* PostgreSQL;
* bcryptjs;
* jsonwebtoken;
* Multer;
* Tesseract.js;
* XLSX;
* node-cron;
* CORS;
* dotenv;
* express-validator.

---

* [x] **R1.5 — Documentar stack Frontend**

Debe incluir:

* React;
* TypeScript;
* Vite;
* TailwindCSS;
* React Router;
* Zustand;
* Axios;
* Recharts;
* react-hot-toast;
* jsPDF;
* html2canvas;
* XLSX;
* lucide-react.

---

* [x] **R1.6 — Documentar stack Mobile**

Debe incluir:

* Expo;
* React Native;
* React Navigation;
* Axios;
* AsyncStorage;
* expo-image-picker.

---

* [x] **R1.7 — Documentar infraestructura**

Debe incluir:

* PostgreSQL;
* Prisma ORM;
* Neon;
* Railway;
* Vercel;
* Docker si corresponde;
* sistema de testing actual.

### Criterio de terminado

El stack debe salir del proyecto real y no de supuestos.

La información final debe entregarse a Erika para incorporarla al `README.md`.

---

## R3. AGENTS.md

* [x] **R1.8 — Crear `AGENTS.md`**

Debe explicar a asistentes IA:

* propósito del proyecto;
* arquitectura;
* estructura;
* stack;
* convenciones;
* reglas backend;
* reglas frontend;
* reglas mobile;
* reglas Prisma;
* reglas Git;
* reglas de seguridad;
* qué cosas no deben modificarse sin autorización.

Debe incluir reglas como:

```text
No cambiar Express por otro framework.
No reemplazar Prisma.
No modificar schema.prisma sin revisar migraciones.
No borrar migraciones existentes.
No hacer commit ni push automáticamente.
No cambiar arquitectura sin autorización.
No modificar archivos fuera del alcance de una tarea.
No introducir dependencias innecesarias.
```

### Criterio de terminado

Un nuevo agente puede leer `AGENTS.md` y comprender cómo trabajar sin romper el proyecto.

---

## R4. Agentes OpenCode

* [x] **R1.9 — Crear agente `backend-reviewer`**

Debe especializarse en:

* Express;
* routes;
* middlewares;
* Prisma;
* transacciones;
* autenticación;
* autorización;
* inventario;
* seguridad;
* integridad de datos.

Debe priorizar revisión antes de modificar.

---

* [x] **R1.10 — Crear agente `frontend-reviewer`**

Debe especializarse en:

* React;
* TypeScript;
* componentes;
* páginas;
* hooks;
* Zustand;
* Axios;
* responsive;
* errores;
* integración API;
* accesibilidad básica.

---

* [x] **R1.11 — Verificar que OpenCode detecta los agentes**

No continuar hasta confirmar que están disponibles.

---

## R5. Skills

* [x] **R1.12 — Crear skill `prisma-review`**

Debe permitir revisar:

* schema;
* relaciones;
* migraciones;
* índices;
* transacciones;
* integridad;
* posibles cambios peligrosos.

No debe modificar `schema.prisma` automáticamente.

---

* [x] **R1.13 — Crear skill `express-security`**

Debe revisar:

* JWT;
* autenticación;
* autorización;
* Helmet;
* rate limiting;
* uploads;
* validaciones;
* exposición de datos;
* errores;
* rutas públicas.

---

* [x] **R1.14 — Verificar que OpenCode reconoce ambas skills**

No crear skills adicionales salvo necesidad real.

---

# 5. ETAPA 2 — SEGURIDAD BACKEND

Responsable principal: **ROSS**

No comenzar cambios de base de datos innecesarios en esta etapa.

---

## JWT

* [x] **R2.1 — Eliminar fallback inseguro de `JWT_SECRET`**

No debe existir:

```text
secret-key
```

como valor automático.

Si `JWT_SECRET` no está definido, la aplicación debe fallar claramente al iniciar.

---

* [x] **R2.2 — Forzar algoritmo JWT**

Verificación:

```text
HS256
```

Debe comprobarse tanto generación como validación de tokens.

---

* [x] **R2.3 — Revisar JWT_SECRET actual**

No subir el nuevo secret a Git.

La rotación de secretos de producción debe hacerse manualmente en los servicios correspondientes.

---

## Helmet

* [x] **R2.4 — Instalar/configurar Helmet**

Debe integrarse sin romper frontend ni CORS.

---

## Rate limiting

* [x] **R2.5 — Configurar rate limiting general**

Evitar límites demasiado agresivos.

---

* [x] **R2.6 — Configurar rate limiting de login**

Debe reducir intentos abusivos sin afectar uso normal.

---

* [x] **R2.7 — Configurar rate limiting específico para OCR**

El procesamiento OCR consume CPU y debe tener límites independientes.

---

# 6. ETAPA 3 — SEARCH IMAGE CASO C

Esta funcionalidad tiene dos consumidores:

1. público;
2. autenticado.

No convertir todo el sistema en privado.

---

# ROSS — Backend Search Image

* [x] **R3.1 — Mantener búsqueda por imagen pública**

Debe existir un endpoint público para el catálogo.

Ejemplo esperado:

```text
POST /api/public/search-image
```

---

* [x] **R3.2 — Mantener endpoint interno autenticado**

```text
POST /api/products/search-image
```

Debe exigir autenticación.

---

* [x] **R3.3 — Reutilizar lógica OCR**

No duplicar innecesariamente:

* extracción;
* OCR;
* matching;
* búsqueda en Prisma.

---

* [x] **R3.4 — Limitar respuesta pública**

La respuesta pública puede incluir:

```text
id
itemCode
name
brand
model
year
image
price1
availability
score
```

No debe incluir:

```text
price2
totalStock exacto
locations[]
stock por ubicación
costos
información administrativa
```

---

* [x] **R3.5 — Reutilizar criterio actual de `availability`**

No crear una segunda lógica diferente a la utilizada por el catálogo público.

---

* [x] **R3.6 — Validar MIME en backend**

Permitir únicamente:

```text
image/jpeg
image/png
image/webp
```

---

* [x] **R3.7 — Limitar imagen a 5 MB**

---

* [x] **R3.8 — Aplicar rate limit específico al OCR**

---

## ERIKA — Frontend/Mobile Search Image

* [x] **E3.1 — Actualizar `PublicProductsPage.tsx`**

Debe utilizar el endpoint público.

No cambiar diseño.

---

* [x] **E3.2 — Verificar catálogo sin login**

Un visitante anónimo debe poder:

* abrir catálogo;
* realizar búsqueda por imagen;
* recibir resultados;
* no recibir stock interno.

---

* [x] **E3.3 — Mantener `ScannerScreen.tsx` sobre endpoint interno**

Debe continuar enviando token.

---

* [x] **E3.4 — Corregir MIME en ScannerScreen**

No enviar siempre `image/jpeg` si el archivo es PNG/WebP.

---

* [x] **E3.5 — Validar tamaño de imagen antes del upload**

Máximo:

```text
5 MB
```

---

* [x] **E3.6 — Verificar flujo mobile autenticado**

---

## REVISIÓN CONJUNTA SEARCH IMAGE

* [~] **J3.1 — Probar búsqueda pública anónima**
* [~] **J3.2 — Probar búsqueda interna con token**
* [x] **J3.3 — Confirmar que endpoint interno rechaza solicitud anónima**
* [x] **J3.4 — Confirmar que respuesta pública no contiene `price2`**
* [x] **J3.5 — Confirmar que respuesta pública no contiene stock exacto**
* [x] **J3.6 — Confirmar que respuesta pública no contiene `locations[]`**
* [x] **J3.7 — Confirmar que `availability` sigue funcionando**
* [x] **J3.8 — Probar JPEG**
* [~] **J3.9 — Probar PNG**
* [~] **J3.10 — Probar WebP**
* [~] **J3.11 — Probar archivo superior a 5 MB**

---

# 7. ETAPA 4 — INTEGRIDAD DE STOCK

Responsable principal: **ROSS**

---

* [x] **R4.1 — Revisar concurrencia en ventas**

Verificar:

```text
sales.routes.ts
```

La lectura y actualización de stock debe estar protegida dentro de la misma transacción.

---

* [x] **R4.2 — Implementar bloqueo de fila en ventas si corresponde**

Tomar como referencia el patrón existente de movimientos.

---

* [x] **R4.3 — Revisar concurrencia en wholesale**

Verificar:

```text
wholesale.routes.ts
```

---

* [x] **R4.4 — Implementar bloqueo de fila en wholesale si corresponde**

---

* [x] **R4.5 — Auditar returns**

Antes de modificarlo determinar:

* cómo incrementa stock;
* si existe riesgo real de concurrencia;
* si necesita bloqueo.

No agregar `FOR UPDATE` automáticamente sin comprobarlo.

---

* [x] **R4.6 — Verificar que stock nunca quede negativo**

Pruebas mínimas:

* stock suficiente;
* stock exacto;
* stock insuficiente;
* solicitudes simultáneas.

---

# 8. ETAPA 5 — FRONTEND Y MOBILE

Responsable principal: **ERIKA**

---

## Manejo de errores

* [x] **E5.1 — Revisar catches de `InventoryPage`**
* [x] **E5.2 — Revisar catches de `SalesPage`**
* [x] **E5.3 — Revisar catches de `ReportsPage`**

Los errores importantes deben mostrar:

```text
toast.error(...)
```

o manejo equivalente.

No agregar mensajes innecesarios en operaciones donde el silencio sea intencional.

---

## TypeScript

* [x] **E5.4 — Revisar `any` críticos de InventoryPage**
* [x] **E5.5 — Revisar `any` críticos de SettingsPage**
* [x] **E5.6 — Revisar `any` críticos de PricesPage**
* [x] **E5.7 — Revisar `any` críticos de ReportsPage**
* [x] **E5.8 — Revisar `any` críticos de WholesalePage**
* [x] **E5.9 — Revisar `any` críticos de SalesPage**

No es obligatorio eliminar absolutamente todos los `any`.

Priorizar los que puedan esconder errores reales.

---

## Mobile

* [x] **E5.10 — Verificar `price1` vs `price2` en `SalesScreen.tsx`**

No reemplazar automáticamente.

Primero determinar:

* cuál representa precio normal;
* cuál representa precio mayorista;
* qué utiliza el frontend web;
* qué exige el backend.

---

* [x] **E5.11 — Corregir precio mobile solo si se confirma error**

---

* [x] **E5.12 — Revisar paginación de InventoryScreen**

---

* [x] **E5.13 — Revisar paginación de SalesScreen**

Implementar solamente si la limitación actual impide usar correctamente la aplicación.

---

# 9. ETAPA 6 — TESTING BACKEND

Responsable: **ROSS**

Mantener los tests existentes.

---

* [x] **R6.1 — Test login válido**
* [x] **R6.2 — Test login inválido**
* [x] **R6.3 — Test permisos ADMIN**
* [x] **R6.4 — Test permisos TIENDA**
* [x] **R6.5 — Test permisos INVENTARIO**

---

## Ventas

* [x] **R6.6 — Test crear venta**
* [x] **R6.7 — Test descuento de stock**
* [x] **R6.8 — Test múltiples pagos**
* [x] **R6.9 — Test stock insuficiente**
* [x] **R6.10 — Test ventas concurrentes**

---

## Inventario

* [x] **R6.11 — Test movimiento de stock**
* [x] **R6.12 — Test movimiento concurrente**

---

## Devoluciones

* [x] **R6.13 — Test devolución válida**
* [x] **R6.14 — Test devolución superior a cantidad vendida**
* [x] **R6.15 — Test incremento de stock por devolución**

---

## Automatización

* [x] **R6.16 — Test reposición automática**

---

# 10. ETAPA 7 — TESTING FRONTEND

Responsable: **ERIKA**

---

* [x] **E7.1 — Configurar framework de testing frontend**

Vitest + @testing-library/react + @testing-library/jest-dom + @testing-library/user-event + jsdom.

---

* [x] **E7.2 — Test LoginPage**
* [x] **E7.3 — Test authStore**
* [x] **E7.4 — Test interceptor Axios**
* [x] **E7.5 — Test carrito de SalesPage**
* [x] **E7.6 — Test cálculo de total**
* [x] **E7.7 — Test catálogo público**
* [x] **E7.8 — Test búsqueda pública por imagen si es viable aislar el request**

No intentar crear una suite E2E enorme en esta fase.

---

# 11. ETAPA 8 — MEJORAS OPCIONALES

Estas tareas NO deben realizarse automáticamente.

Solo hacerlas si existe tiempo y después de que todo lo prioritario funcione.

---

## ERIKA — Opcionales

* [ ] Tipar todos los `any` restantes
* [ ] Agregar ErrorBoundary mobile
* [ ] Tipar completamente navegación React Native
* [ ] Eliminar dependencias mobile no usadas
* [ ] Optimizar bundle frontend
* [ ] Mejorar paginación mobile

---

## ROSS — Opcionales

* [x] Revisar caché de permisos
* [x] Revisar logging estructurado
* [x] Revisar score de search-image
* [x] Revisar pool de Tesseract
* [x] Revisar índices de PostgreSQL
* [!] Revisar precisión Decimal
* [!] Revisar campos `date` / `createdAt`
* [!] Revisar política `ON DELETE`
* [!] Revisar naming `RoleModel`

---

## NO realizar sin revisión conjunta

```text
Eliminar campos de schema.prisma
Cambiar precisión de columnas
Renombrar modelos Prisma
Eliminar migraciones
Crear migraciones destructivas
Cambiar relaciones
Cambiar ON DELETE
Reestructurar módulos completos
Cambiar Express
Cambiar Prisma
Cambiar React
```

---

# 12. ETAPA 9 — REVISIÓN FINAL

Responsables: **ERIKA + ROSS**

---

## Código

* [x] **J9.1 — Backend compila**
* [x] **J9.2 — Frontend compila**
* [x] **J9.3 — Mobile pasa TypeScript**
* [x] **J9.4 — Tests backend pasan**
* [x] **J9.5 — Tests frontend pasan**

---

## Funcionalidad

* [x] **J9.6 — Login**
* [x] **J9.7 — Roles**
* [x] **J9.8 — Productos**
* [x] **J9.9 — Inventario**
* [x] **J9.10 — Ventas**
* [x] **J9.11 — Pagos**
* [x] **J9.12 — Devoluciones**
* [x] **J9.13 — Solicitudes**
* [x] **J9.14 — Movimientos**
* [x] **J9.15 — Costos**
* [x] **J9.16 — Precios**
* [x] **J9.17 — Mayoristas**
* [x] **J9.18 — Reportes**
* [x] **J9.19 — Dashboard**
* [x] **J9.20 — Catálogo público**
* [x] **J9.21 — OCR público**
* [x] **J9.22 — OCR autenticado**
* [x] **J9.23 — Mobile**

---

## Seguridad

* [x] **J9.24 — No existen secretos reales en archivos versionados**
* [x] **J9.25 — JWT_SECRET seguro**
* [x] **J9.26 — JWT valida algoritmo**
* [x] **J9.27 — Helmet activo**
* [x] **J9.28 — Rate limiting activo**
* [x] **J9.29 — Search-image interno protegido**
* [x] **J9.30 — Search-image público no expone datos internos**

---

## Git

* [x] **J9.31 — Revisar `git status`**
* [x] **J9.32 — Revisar `git diff --stat`**
* [x] **J9.33 — Revisar cambios de Erika**
* [x] **J9.34 — Revisar cambios de Ross**
* [x] **J9.35 — Actualizar ramas con `main`**
* [x] **J9.36 — Resolver conflictos**
* [x] **J9.37 — Pull Request Erika**
* [x] **J9.38 — Pull Request Ross**
* [x] **J9.39 — Merge a `main`**
* [x] **J9.40 — Verificar versión desplegada**

---

# 13. ARCHIVOS QUE DEBE EVITAR MODIFICAR CADA PERSONA

## Erika normalmente NO modifica

```text
backend/src/
backend/prisma/schema.prisma
backend/prisma/migrations/
```

Excepto si una tarea lo requiere expresamente y se coordina previamente.

---

## Ross normalmente NO modifica

```text
frontend/src/
mobile/src/
```

Excepto si una tarea lo requiere expresamente y se coordina previamente.

---

# 14. PUNTOS DE COORDINACIÓN

Deben revisarse juntos:

* [x] Search Image público/interno
* [x] `price1` vs `price2`
* [x] cambios Prisma
* [x] migraciones
* [x] credenciales
* [x] contratos API frontend ↔ backend
* [x] integración final
* [x] merge a `main`

---

# 15. ESTADO GENERAL

## Requerimientos del ingeniero

### Erika

* [x] README
* [x] `.gitignore`
* [x] Archivos `.md`

### Ross

* [x] Git Convention
* [x] Stack tecnológico
* [x] AGENTS.md
* [x] Agentes
* [x] Skills

---

## Seguridad

### Ross

* [x] JWT
* [x] Helmet
* [x] Rate limiting
* [x] Search Image backend
* [x] Concurrencia stock

---

## Frontend/Mobile

### Erika

* [x] Search Image frontend/mobile
* [x] Manejo de errores
* [x] TypeScript
* [x] Precio mobile
* [x] Testing frontend

---

# 16. INSTRUCCIONES PARA OPENCODE

Cuando OpenCode reciba una tarea de este documento:

1. leer `PLAN_TRABAJO_ERIKA_ROSS.md`;
2. identificar el ID de la tarea;
3. trabajar únicamente sobre esa tarea;
4. revisar primero los archivos existentes;
5. no asumir que falta una implementación;
6. no modificar archivos fuera del alcance;
7. no eliminar funcionalidad existente;
8. no cambiar arquitectura;
9. no crear migraciones salvo autorización explícita;
10. no hacer commit;
11. no hacer push;
12. ejecutar verificaciones correspondientes;
13. mostrar `git diff --stat`;
14. informar todos los archivos modificados;
15. detenerse después del reporte.

OpenCode NO debe marcar `[x]` automáticamente.

El integrante responsable debe revisar el resultado y luego actualizar manualmente este checklist.

---

# 17. NUEVOS PENDIENTES

Si una auditoría posterior descubre un nuevo problema, debe agregarse aquí antes de implementarlo.

Formato:

```text
- [ ] ID — Nombre de tarea
  - Responsable:
  - Prioridad:
  - Origen:
  - Archivos:
  - Descripción:
  - Criterio de terminado:
```

No implementar nuevos hallazgos directamente sin registrarlos primero.

---

# 18. HISTORIAL DE AVANCE

Registrar avances importantes:

```text
AAAA-MM-DD — Responsable — Tarea — Estado
```

Ejemplo:

```text
2026-09-08 — Erika — E1.2 .gitignore — COMPLETADO
2026-09-08 — Ross — R1.1 Git Convention — COMPLETADO
2026-09-09 — Erika — E5.1-E5.3 Error handling audit (sin cambios de código) — COMPLETADO
2026-09-09 — Erika — E5.4-E5.9 Corrección 17 `any` críticos en 6 páginas frontend — COMPLETADO
2026-09-09 — Erika — E5.10-E5.13 Etapa 5 Frontend/Mobile completa (labels precio corregidos en InventoryScreen) — COMPLETADO
2026-09-09 — Erika — E7.1-E7.4, E7.7-E7.8 Primer bloque testing frontend (Vitest + 57 tests) — COMPLETADO
```

---

# 19. REGLA FINAL

La prioridad del proyecto es:

```text
1. Cumplir lo solicitado por el ingeniero
2. Mantener funcionalidad existente
3. Corregir errores reales
4. Resolver seguridad importante
5. Agregar tests
6. Mejorar calidad
7. Realizar optimizaciones opcionales
```

Una recomendación de auditoría no debe convertirse automáticamente en un cambio de código.

Antes de modificar una funcionalidad que actualmente trabaja correctamente, debe existir evidencia de que el cambio es necesario.
