# Stack Mobile

Documentación basada en el repositorio real (`mobile/package.json`, `mobile/app.json`).

## Resumen

| Área             | Tecnología / versión                               |
| ---------------- | -------------------------------------------------- |
| Plataforma       | Expo `~51.0.0` (React Native `0.74.5`, React `18.2.0`) |
| Lenguaje         | TypeScript `^5.5.4` (`@types/react ~18.2.45`)      |
| Navegación       | `@react-navigation/native ^6.1.18` + `native-stack ^6.10.1` + `react-native-screens ~3.31.1` + `react-native-safe-area-context ~4.10.5` |
| Almacenamiento   | `@react-native-async-storage/async-storage 1.23.1` |
| Consumo API      | Axios `^1.7.5`                                     |
| Cámara/imágenes  | `expo-camera ~15.0.0`, `expo-image-picker ~15.0.0`, `expo-file-system ~17.0.0` |
| Notificaciones   | `react-native-toast-message ^2.2.0`                |
| Sistema          | `expo-status-bar ~1.12.1`                          |

## Configuración de la app (`mobile/app.json`)

* Nombre: `InventarioApp` — slug `inventario-app` — versión `1.0.0`.
* Orientación `portrait`, tema claro.
* Identificadores: iOS `com.inventario.app` / Android `com.inventario.app` (icono adaptativo).
* Splash con `backgroundColor: #2563eb`.

## Scripts

| Script     | Comando            |
| ---------- | ------------------ |
| `start`    | `expo start`       |
| `android`  | `expo start --android` |
| `ios`      | `expo start --ios` |
| `web`      | `expo start --web` |

## Estructura relevante

* App orientada a dispositivos Android/iOS mediante Expo.
* Autenticación con token (Axios + AsyncStorage).
* `ScannerScreen` para búsqueda por imagen usando cámara/galería (`expo-camera`, `expo-image-picker`) contra el endpoint autenticado `/products/search-image`.
* Variables de entorno para Expo documentadas en `mobile/.env.example`.

## Notas

* No se documentan versiones ni APIs que no estén en `mobile/package.json` o `mobile/app.json`.
* Mobile es responsabilidad principal de Erika; Ross solo documenta su stack.