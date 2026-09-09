# Git Convention — RepuestoPro / Inventario Autopartes II

Convención de trabajo con Git para este repositorio.

## Ramas

| Rama   | Propósito                                        |
| ------ | ------------------------------------------------ |
| `main` | Rama integrada y estable. Solo recibe Pull Requests revisados. |
| `ross` | Rama personal de trabajo de Ross (backend/seguridad). |
| `erika`| Rama personal de trabajo de Erika (frontend/mobile/documentación). |

Reglas de ramas:

* Nadie desarrolla directamente sobre `main`.
* No se eliminan ramas salvo decisión expresa del responsable.
* No se usan ramas `develop`; si el repositorio adopta `develop` en el futuro será una decisión explícita y documentada.

## Sincronización antes de trabajar

Antes de comenzar una nueva tanda de trabajo:

```bash
git fetch origin
git status
git log --oneline origin/main..HEAD
```

Pasos:

1. `git fetch origin` para traer el estado remoto.
2. Comprobar el estado de la rama personal (`git status`).
3. Incorporar los cambios actuales de `main` a la rama personal (`git merge main` cuando corresponda).
4. Resolver cualquier situación (conflictos, ramas desactualizadas) antes de desarrollar.

No se promueven estas operaciones sobre historial publicado:

* `rebase` de ramas publicadas.
* `reset --hard`.
* `push --force` / force push.
* squash del historial ya existente.

El historial de commits y Pull Requests se conserva porque forma parte de la evidencia académica del proyecto.

## Conventional Commits

Formato:

```text
tipo(scope): descripción
```

### Tipos

* `feat` — nueva funcionalidad.
* `fix` — corrección de errores.
* `docs` — documentación.
* `refactor` — cambio interno sin cambiar comportamiento.
* `test` — pruebas.
* `chore` — tareas de mantenimiento (build, config, dependencias).
* `perf` — mejora de rendimiento.
* `style` — formato/estilo sin lógica.

### Scopes

* `backend`
* `frontend`
* `mobile`
* `auth`
* `products`
* `inventory`
* `sales`
* `public`
* `docs`
* `security`

### Ejemplos reales apropiados para este proyecto

```text
feat(backend): separate public and authenticated image search
fix(auth): require jwt secret at startup
feat(public): add POST /search-image for anonymous catalog
docs(backend): add stack documentation
refactor(products): extract OCR pipeline to shared service
test(inventory): add stock movement concurrency tests
chore(backend): install helmet and express-rate-limit
```

## Flujo de Pull Request

```text
rama personal (ross | erika)
→ cambios en archivos
→ pruebas y verificaciones
→ commit (realizado manualmente por el desarrollador)
→ push (manual)
→ Pull Request hacia main
→ revisión
→ integración a main
```

Notas:

* Los commits, pushes y Pull Requests los realiza el desarrollador manualmente (Ross o Erika), no la herramienta de asistencia.
* Cada PR debe estar enfocado en una tarea y describir qué se probó.
* Antes de abrir un PR se revisa `git status`, `git diff --stat` y el `git diff` de los archivos afectados.

## Archivos que no deben subirse

* `.env`, `.env.local`, `.env.development`, `.env.production` con valores reales.
* Claves o secretos (JWT_SECRET real, credenciales de base de datos de producción).
* Artefactos generados (`node_modules/`, `dist/`, `coverage/`).
* Artefactos locales de OCR (p. ej. `eng.traineddata`).