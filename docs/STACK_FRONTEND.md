# Stack Frontend

Documentación basada en el repositorio real (`frontend/package.json`, `frontend/vite.config.ts`, `frontend/tailwind.config.js`, `frontend/index.html`).

## Resumen

| Área           | Tecnología / versión                          |
| -------------- | --------------------------------------------- |
| Framework      | React `^18.3.1` + `react-dom ^18.3.1`         |
| Lenguaje       | TypeScript `^5.5.4`                           |
| Bundler        | Vite `^5.4.2` con `@vitejs/plugin-react ^4.3.1` |
| Estilos        | TailwindCSS `^3.4.10` (+ `postcss ^8.4.41`, `autoprefixer ^10.4.20`) |
| Routing        | React Router DOM `^6.26.1`                    |
| Estado         | Zustand `^4.5.5`                              |
| Consumo API    | Axios `^1.7.5`                                |
| Gráficas       | Recharts `^2.12.7`                            |
| Notificaciones | `react-hot-toast ^2.4.1`                      |
| Reportes/PDF   | `jspdf ^4.2.1` + `html2canvas ^1.4.1`         |
| Excel          | `xlsx ^0.18.5`                                |
| Iconos         | `lucide-react ^0.436.0`                       |

## Configuración de build

* `frontend/vite.config.ts`: plugin React, alias `@` → `./src`, puerto de dev `5173`.
* `frontend/tailwind.config.js` + `postcss.config.js`: Tailwind vía PostCSS.
* `frontend/index.html`: punto de entrada.
* Módulo ESM (`"type": "module"`).

## Scripts

| Script   | Comando                |
| -------- | ---------------------- |
| `dev`    | `vite`                 |
| `build`  | `tsc -b && vite build` |
| `preview`| `vite preview`         |

## Estructura relevante

* Aplicación organizada por páginas/componentes en `frontend/src`.
* Consumo de API a través de Axios (interceptores para token y manejo de errores).
* Estado de sesión gestionado por store (Zustand).
* `PublicProductsPage` (catálogo público) y búsqueda por imagen pública (`/public/search-image`).
* Variables de entorno con prefijo `VITE_*` documentadas en `frontend/.env.example`.

## Deploy

No hay configuración de deploy verificable en el repositorio (no existe `vercel.json`). Vercel aparece mencionado en la documentación general del proyecto, pero su configuración no es comprobable únicamente desde el código.