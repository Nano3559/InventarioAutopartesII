# RepuestoPro — Sistema de Inventario y Ventas

Sistema web para la gestión de inventario, ventas y repuestos automotrices. El proyecto está compuesto por un backend API, un frontend web y una aplicación móvil.

## Características

* **Gestión de productos:** CRUD de productos con información de marca, modelo, año, códigos y datos asociados.
* **Inventario por ubicación:** Control de stock distribuido entre almacenes y tiendas.
* **Ventas normales y mayoristas:** Registro de ventas con diferentes métodos de pago.
* **Pagos múltiples:** Soporte para efectivo, QR, transferencia y crédito.
* **Devoluciones:** Validación de cantidades y actualización del inventario.
* **Movimientos de inventario:** Transferencias entre ubicaciones con control de stock.
* **Solicitudes a almacén:** Flujo de solicitudes con estados e historial.
* **Costos y precios:** Registro de costos por producto y factura, con gestión de precios de venta.
* **Reportes:** Reportes de ventas, inventario, mensual y por proveedor con exportación a Excel y PDF.
* **Dashboard:** Estadísticas e indicadores visuales del sistema.
* **Reposición automática:** Proceso programado para generar solicitudes cuando el stock alcanza niveles definidos.
* **Búsqueda por imagen:** Identificación y búsqueda de productos mediante OCR con Tesseract.js.
* **Catálogo público:** Consulta de productos disponible sin iniciar sesión.
* **Aplicación móvil:** Acceso móvil a funciones de inventario, ventas y búsqueda por imagen.

## Roles del Sistema

| Rol            | Permisos principales                                                                 |
| -------------- | ------------------------------------------------------------------------------------ |
| **ADMIN**      | Acceso administrativo a productos, usuarios, reportes, configuración e importaciones |
| **TIENDA**     | Ventas, devoluciones, solicitudes y consulta de inventario                           |
| **INVENTARIO** | Movimientos, gestión de stock y solicitudes                                          |

## Stack Tecnológico

| Componente                  | Tecnología                           |
| --------------------------- | ------------------------------------ |
| Backend                     | Node.js, Express, TypeScript         |
| Frontend                    | React, Vite, TailwindCSS, TypeScript |
| Móvil                       | Expo, React Native                   |
| Base de datos               | PostgreSQL 16                        |
| ORM                         | Prisma ^5.19.0                       |
| Autenticación               | JWT, bcryptjs, jsonwebtoken          |
| Comunicación HTTP           | Axios                                |
| Estado global frontend      | Zustand                              |
| Reportes                    | jsPDF, html2canvas, xlsx             |
| OCR                         | Tesseract.js                         |
| Gráficos                    | Recharts                             |
| Tareas programadas          | node-cron                            |
| Deployment backend          | Railway                              |
| Deployment frontend         | Vercel                               |
| Base de datos en producción | Neon                                 |

## Estructura del Proyecto

```text
InventarioAutopartesII/
├── backend/
│   ├── prisma/
│   │   ├── schema.prisma
│   │   ├── seed.ts
│   │   ├── seed-data.ts
│   │   └── migrations/
│   └── src/
│       ├── config/
│       ├── shared/
│       │   ├── middlewares/
│       │   └── utils/
│       ├── modules/
│       │   ├── auth/
│       │   ├── users/
│       │   ├── products/
│       │   ├── inventory/
│       │   ├── sales/
│       │   ├── wholesale/
│       │   ├── returns/
│       │   ├── movements/
│       │   ├── requests/
│       │   ├── costs/
│       │   ├── prices/
│       │   ├── reports/
│       │   ├── dashboard/
│       │   ├── permissions/
│       │   ├── notifications/
│       │   ├── customers/
│       │   ├── suppliers/
│       │   ├── locations/
│       │   └── public/
│       ├── jobs/
│       └── utils/
├── frontend/
│   └── src/
│       ├── pages/
│       ├── components/
│       ├── services/
│       ├── stores/
│       ├── types/
│       └── utils/
├── mobile/
│   └── src/
│       ├── screens/
│       ├── navigation/
│       └── services/
└── docker-compose.yml
```

## Requisitos Previos

* Node.js 20 o superior
* npm
* PostgreSQL 16 o Docker
* Entorno compatible con Expo para ejecutar la aplicación móvil

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/Nano3559/InventarioAutopartesII.git
cd InventarioAutopartesII
```

### 2. Base de datos

#### Opción A — Docker

```bash
docker-compose up -d
```

#### Opción B — PostgreSQL local

Crear una base de datos PostgreSQL y configurar posteriormente la variable `DATABASE_URL` del backend.

### 3. Backend

```bash
cd backend
npm install
```

Crear el archivo de variables de entorno a partir del ejemplo disponible:

```bash
cp .env.example .env
```

Editar `.env` con la configuración correspondiente.

Luego ejecutar:

```bash
npx prisma generate
npx prisma migrate dev
npm run prisma:seed
npm run dev
```

La API se ejecuta por defecto en:

```text
http://localhost:3000/api
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

El frontend de desarrollo utiliza normalmente:

```text
http://localhost:5173
```

### 5. Aplicación móvil

```bash
cd mobile
npm install
npm start
```

Para abrir en una plataforma específica:

```bash
npm run android
npm run ios
npm run web
```

## Variables de Entorno

Nunca se deben versionar archivos `.env` que contengan credenciales o secretos reales.

Los archivos `.env.example`, cuando estén disponibles, deben utilizarse únicamente como referencia de configuración.

### Backend

Archivo local:

```text
backend/.env
```

Variables principales:

| Variable       | Descripción                                         |
| -------------- | --------------------------------------------------- |
| `DATABASE_URL` | Cadena de conexión a PostgreSQL                     |
| `JWT_SECRET`   | Secreto utilizado para firmar tokens JWT            |
| `PORT`         | Puerto del servidor                                 |
| `FRONTEND_URL` | URL permitida para el frontend mediante CORS        |
| `MOBILE_URL`   | URL permitida para el cliente móvil, si corresponde |

Ejemplo de estructura:

```env
DATABASE_URL=postgresql://usuario:password@localhost:5432/inventario_db
JWT_SECRET=cambiar-por-un-secreto-seguro
PORT=3000
FRONTEND_URL=http://localhost:5173
MOBILE_URL=http://localhost:19006
```

### Frontend

El frontend utiliza variables de entorno de Vite.

| Variable       | Descripción                                   |
| -------------- | --------------------------------------------- |
| `VITE_API_URL` | URL base utilizada para conectarse al backend |

### Mobile

La aplicación móvil utiliza variables de entorno de Expo.

| Variable              | Descripción                                |
| --------------------- | ------------------------------------------ |
| `EXPO_PUBLIC_API_URL` | URL base utilizada por la aplicación móvil |

## Datos Iniciales

El proyecto dispone de un proceso de seed para cargar información inicial necesaria durante el desarrollo.

```bash
cd backend
npm run prisma:seed
```

La configuración del seed se encuentra en:

```text
backend/prisma/seed.ts
backend/prisma/seed-data.ts
```

## Scripts

### Backend

| Comando                | Descripción                        |
| ---------------------- | ---------------------------------- |
| `npm run dev`          | Servidor en desarrollo             |
| `npm run build`        | Compilar TypeScript                |
| `npm run start`        | Ejecutar versión compilada         |
| `npm run prisma:generate` | Generar cliente Prisma          |
| `npm run prisma:migrate`  | Ejecutar migraciones            |
| `npm run prisma:seed`     | Cargar datos iniciales           |
| `npm test`            | Ejecutar tests                      |
| `npm run test:watch`  | Tests en modo watch                 |

### Frontend

| Comando          | Descripción               |
| ---------------- | ------------------------- |
| `npm run dev`    | Servidor de desarrollo    |
| `npm run build`  | Compilar para producción  |
| `npm run preview`| Vista previa de la build  |

### Mobile

| Comando          | Descripción                  |
| ---------------- | ---------------------------- |
| `npm start`      | Iniciar Expo                 |
| `npm run android`| Abrir en Android             |
| `npm run ios`    | Abrir en iOS                 |
| `npm run web`    | Abrir en navegador           |

## Testing

```bash
cd backend
npm test
```

Las pruebas existentes cubren utilidades y validaciones internas.

## API

La API utiliza el prefijo `/api`.

### Autenticación

| Método | Ruta             | Autenticación | Descripción        |
| ------ | ---------------- | ------------- | ------------------ |
| POST   | `/auth/login`    | No            | Iniciar sesión     |
| POST   | `/auth/register` | Admin         | Crear usuario      |
| GET    | `/auth/me`       | Sí            | Usuario actual     |

### Productos

| Método | Ruta                    | Autenticación       | Descripción                   |
| ------ | ----------------------- | ------------------- | ----------------------------- |
| GET    | `/products`             | Opcional            | Listar productos              |
| GET    | `/products/filters`     | Opcional            | Filtros de productos          |
| GET    | `/products/:id`         | Opcional            | Detalle de producto           |
| POST   | `/products`             | Admin               | Crear producto                |
| PUT    | `/products/:id`         | Admin               | Actualizar producto           |
| DELETE | `/products/:id`         | Admin               | Eliminar producto             |
| POST   | `/products/search-image`| No                  | Buscar por imagen (OCR)       |
| POST   | `/products/import`      | Admin               | Importar desde Excel          |

### Inventario

| Método | Ruta                      | Autenticación | Descripción             |
| ------ | ------------------------- | ------------- | ----------------------- |
| GET    | `/inventory`              | Sí            | Consultar inventario    |
| GET    | `/inventory/product/:id`  | Sí            | Stock por producto      |
| PUT    | `/inventory/:id`          | Admin         | Actualizar stock        |

### Ubicaciones

| Método | Ruta           | Autenticación | Descripción        |
| ------ | -------------- | ------------- | ------------------ |
| GET    | `/locations`   | Sí            | Listar ubicaciones |

### Ventas

| Método | Ruta               | Autenticación | Descripción          |
| ------ | ------------------ | ------------- | -------------------- |
| GET    | `/sales`           | Sí            | Listar ventas        |
| GET    | `/sales/:id`       | Sí            | Detalle de venta     |
| GET    | `/sales/:id/nota`  | Sí            | Nota de venta (HTML) |
| POST   | `/sales`           | Sí            | Registrar venta      |

### Ventas mayoristas

| Método | Ruta                  | Autenticación | Descripción               |
| ------ | --------------------- | ------------- | ------------------------- |
| GET    | `/wholesale`          | Sí            | Listar ventas mayoristas  |
| POST   | `/wholesale`          | Sí            | Registrar venta mayorista |
| POST   | `/wholesale/import`   | Admin         | Importar desde Excel      |

### Devoluciones

| Método | Ruta                      | Autenticación | Descripción                |
| ------ | ------------------------- | ------------- | -------------------------- |
| GET    | `/returns`                | Sí            | Listar devoluciones        |
| GET    | `/returns/recent-sales`   | Sí            | Ventas recientes           |
| GET    | `/returns/sale/:saleId`   | Sí            | Detalle de venta para dev. |
| POST   | `/returns`                | Sí            | Registrar devolución       |

### Movimientos

| Método | Ruta           | Autenticación | Descripción                  |
| ------ | -------------- | ------------- | ---------------------------- |
| GET    | `/movements`   | Sí            | Listar movimientos           |
| POST   | `/movements`   | Sí            | Registrar movimiento         |

### Solicitudes

| Método | Ruta              | Autenticación | Descripción               |
| ------ | ----------------- | ------------- | ------------------------- |
| GET    | `/requests`       | Sí            | Listar solicitudes        |
| GET    | `/requests/:id`   | Sí            | Detalle de solicitud      |
| POST   | `/requests`       | Sí            | Crear solicitud           |
| PUT    | `/requests/:id`   | Sí            | Actualizar estado         |
| DELETE | `/requests/:id`   | Sí            | Cancelar solicitud        |

### Costos

| Método | Ruta                      | Autenticación | Descripción              |
| ------ | ------------------------- | ------------- | ------------------------ |
| GET    | `/costs`                  | Sí            | Listar costos            |
| POST   | `/costs`                  | Admin         | Crear costo              |
| PUT    | `/costs/:id`              | Admin         | Actualizar costo         |
| DELETE | `/costs/:id`              | Admin         | Eliminar costo           |
| GET    | `/costs/invoice/:file`    | Sí            | Obtener factura          |

### Precios

| Método | Ruta                  | Autenticación | Descripción          |
| ------ | --------------------- | ------------- | -------------------- |
| GET    | `/prices`             | Sí            | Listar precios       |
| PUT    | `/prices/:productId`  | Sí            | Actualizar precios   |
| POST   | `/prices/apply`       | Sí            | Aplicar porcentajes  |
| GET    | `/prices/export`      | Sí            | Exportar precios     |

### Pagos

| Método | Ruta                    | Autenticación | Descripción          |
| ------ | ----------------------- | ------------- | -------------------- |
| GET    | `/payments`             | Sí            | Listar pagos         |
| POST   | `/payments`             | Sí            | Registrar pago       |
| GET    | `/payments/summary/:id` | Sí            | Resumen de pagos     |

### Reportes

| Método | Ruta                  | Autenticación | Descripción              |
| ------ | --------------------- | ------------- | ------------------------ |
| GET    | `/reports/sales`      | Sí            | Reporte de ventas        |
| GET    | `/reports/inventory`  | Sí            | Reporte de inventario    |
| GET    | `/reports/suppliers`  | Sí            | Reporte de proveedores   |
| GET    | `/reports/monthly`    | Sí            | Reporte mensual          |

### Dashboard

| Método | Ruta           | Autenticación | Descripción        |
| ------ | -------------- | ------------- | ------------------ |
| GET    | `/dashboard`   | Sí            | Estadísticas       |

### Permisos

| Método | Ruta                          | Autenticación | Descripción           |
| ------ | ----------------------------- | ------------- | --------------------- |
| GET    | `/permissions/roles`          | Sí            | Listar roles          |
| GET    | `/permissions/roles/modules`  | Sí            | Módulos por rol       |
| PUT    | `/permissions/roles/:id/permissions` | Admin | Actualizar permisos   |
| PUT    | `/permissions/roles/:id/columns`    | Admin | Actualizar columnas   |
| GET    | `/permissions/audit`          | Admin         | Log de auditoría      |
| GET    | `/permissions/permissions/me` | Sí            | Mis permisos          |

### Usuarios

| Método | Ruta                     | Autenticación | Descripción          |
| ------ | ------------------------ | ------------- | -------------------- |
| GET    | `/users`                 | Admin         | Listar usuarios      |
| GET    | `/users/roles`           | Admin         | Listar roles         |
| POST   | `/users`                 | Admin         | Crear usuario        |
| PUT    | `/users/:id`             | Admin         | Actualizar usuario   |
| DELETE | `/users/:id`             | Admin         | Eliminar usuario     |
| GET    | `/users/me/preferences`  | Sí            | Mis preferencias     |
| PUT    | `/users/me/preferences`  | Sí            | Guardar preferencias |

### Clientes

| Método | Ruta              | Autenticación | Descripción        |
| ------ | ----------------- | ------------- | ------------------ |
| GET    | `/customers`      | Sí            | Listar clientes    |
| GET    | `/customers/:id`  | Sí            | Detalle de cliente |
| POST   | `/customers`      | Sí            | Crear cliente      |
| PUT    | `/customers/:id`  | Sí            | Actualizar cliente |

### Proveedores

| Método | Ruta              | Autenticación | Descripción         |
| ------ | ----------------- | ------------- | ------------------- |
| GET    | `/suppliers`      | Sí            | Listar proveedores  |
| GET    | `/suppliers/:id`  | Sí            | Detalle de proveedor|
| POST   | `/suppliers`      | Sí            | Crear proveedor     |
| PUT    | `/suppliers/:id`  | Sí            | Actualizar proveedor|
| DELETE | `/suppliers/:id`  | Sí            | Eliminar proveedor  |

### Notificaciones

| Método | Ruta                  | Autenticación | Descripción            |
| ------ | --------------------- | ------------- | ---------------------- |
| GET    | `/notifications`      | Sí            | Listar notificaciones  |
| PUT    | `/notifications/:id/read` | Sí        | Marcar como leída      |
| PUT    | `/notifications/read-all` | Sí        | Marcar todas leídas    |

### Catálogo público

| Método | Ruta                       | Autenticación | Descripción              |
| ------ | -------------------------- | ------------- | ------------------------ |
| GET    | `/public/products`         | No            | Catálogo de productos    |
| GET    | `/public/products/:id`     | No            | Detalle de producto      |
| GET    | `/public/filters`          | No            | Filtros disponibles      |
| GET    | `/public/filters/models`   | No            | Modelos por marca        |
| GET    | `/public/filters/years`    | No            | Años por marca/modelo    |
| GET    | `/public/importers`        | No            | Importadoras             |

### Búsqueda por imagen

El sistema dispone de búsqueda por imagen mediante OCR.

Esta funcionalidad se encuentra pendiente de revisión para diferenciar entre el flujo público del catálogo y el uso interno autenticado.

## Deployment

### Backend

El backend se encuentra preparado para despliegue en Railway.

### Frontend

El frontend se encuentra preparado para despliegue en Vercel.

### Base de datos

La base de datos de producción utiliza PostgreSQL alojado en Neon.

Las credenciales de producción deben configurarse únicamente mediante variables de entorno de las plataformas de despliegue y nunca almacenarse dentro del repositorio.

## Seguridad

Consideraciones generales del proyecto:

* los secretos deben almacenarse mediante variables de entorno;
* los archivos `.env` no deben subirse al repositorio;
* las contraseñas se almacenan mediante hash;
* las rutas privadas requieren autenticación y autorización según rol;
* los uploads deben validarse antes de ser procesados;
* las funcionalidades públicas no deben exponer información interna del inventario.

## Licencia

Proyecto académico universitario — 9.° semestre.
