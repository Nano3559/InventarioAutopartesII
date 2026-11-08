# PILOTO DE DATOS SINTETICOS — CLASES FALTANTES

Fecha: 2026-09-22  
Metodo: `rembg[cpu]` 2.0.85 con U2-Net  
Alcance: piloto controlado, sin escalar y sin incorporar labels al dataset final.

## Resultados individuales

| Clase | Imagen | Mask | Box | Resultado |
|---|---|---|---|---|
| brake_rotor | brake_rotor__001 | ACEPTABLE | BUENA | Aprobada |
| brake_rotor | brake_rotor__002 | BUENA | BUENA | Aprobada |
| brake_rotor | brake_rotor__003 | BUENA | BUENA | Aprobada |
| brake_rotor | brake_rotor__004 | BUENA | BUENA | Aprobada |
| brake_rotor | brake_rotor__005 | BUENA | BUENA | Aprobada |
| brake_caliper | brake_caliper__001 | BUENA | BUENA | Aprobada |
| brake_caliper | brake_caliper__002 | BUENA | BUENA | Aprobada |
| brake_caliper | brake_caliper__003 | BUENA | BUENA | Aprobada |
| brake_caliper | brake_caliper__004 | BUENA | BUENA | Aprobada |
| brake_caliper | brake_caliper__005 | BUENA | BUENA | Aprobada |
| oil_filter | oil_filter__001 | BUENA | BUENA | Aprobada |
| oil_filter | oil_filter__002 | BUENA | BUENA | Aprobada |
| oil_filter | oil_filter__003 | BUENA | BUENA | Aprobada |
| oil_filter | oil_filter__004 | BUENA | BUENA | Aprobada |
| oil_filter | oil_filter__005 | BUENA | BUENA | Aprobada |

## Resumen

| Clase | Buenas | Aceptables | Malas | Boxes buenas | Decision |
|---|---:|---:|---:|---:|---|
| brake_rotor | 4 | 1 | 0 | 5 | APRUEBA PILOTO |
| brake_caliper | 5 | 0 | 0 | 5 | APRUEBA PILOTO |
| oil_filter | 5 | 0 | 0 | 5 | APRUEBA PILOTO |

Las 15 composiciones y sus previews estan en:

```text
ia-service/datasets/synthetic_pilot/
```

Cada clase conserva `originals/`, `masks/`, `cutouts/`, `composites/`, `previews/` y `labels/`. Los resultados por clase se registran en `synthetic_pilot_results.csv`.

## Decision

Las tres clases cumplen el criterio minimo de 4/5 imagenes con mascara `BUENA` o `ACEPTABLE` y box `BUENA`. Por tanto, **DATOS SINTETICOS VIABLES: SI, como experimento controlado**.

Esto no autoriza generar cientos de imagenes ni mezclar estos datos con el test real. Las mascaras y cajas sinteticas son datos de entrenamiento experimental, no ground truth real. Las imagenes originales RAW y los lotes existentes permanecen sin cambios.
