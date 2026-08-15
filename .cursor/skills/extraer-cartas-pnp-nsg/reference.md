# Matching y dudas

## Cómo se elige el título OCR

Se toman líneas del tercio superior (y < 0.22). Se ignoran tipos (`EVENTO`, `HIELO`, …) y dígitos sueltos (coste). Identidades: nombre + subtítulo (`LE CATALIZADORE ROMPEMOLDES` vs `Le Catalizadore: RompeMoldes`).

El número de coleccionista (pie de carta) **no** confirma el match solo: el OCR lo confunde con coste, fuerza o memoria. Solo entra como `proposed` si el sufijo del `code` es único en el pack.

## Score

`matchlib.best_score`: forma compacta (sin acentos ni espacios, `1`/`I`). El título JSON debe ser **prefijo** del OCR o coincidir con las primeras N palabras. Así «VIDENTE Inflige 1 punto…» pega a `Vidente`, y no «CONDUCTO» dentro de `CENTRALSUPERCONDUCTORA`.

Umbral de match automático: `0.82` en `pnp_pack.py`.

## Caso conocido

Pack `sg`, código `30075`: JSON `Fondo de Cobertura`, PDF «FONDOS DE RIESGO». Debe quedar en dudas hasta override `p08_r2_c3.jpg` → `30075` (y las otras copias del playset).
