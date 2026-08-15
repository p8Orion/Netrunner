---
name: extraer-cartas-pnp-nsg
description: >-
  Extrae cartas de un PDF PnP Null Signal Games (9 por hoja A4) y las guarda
  en cards/<card-code>.jpg (códigos globales) usando translations/es/pack/<abrev>.es.json.
  Use when the user starts this skill, mentions PnP Netrunner, sg.pdf, pack
  abbreviation, cards/, card-code.jpg, or netrunner-cards-json Spanish translations.
disable-model-invocation: true
---

# PnP NSG → códigos de carta

## Al iniciar

Mostrá esto primero (input esperado), antes de extraer nada:

Recibir un pdf con 9 cartas por página con nombre `<abrev-expansion>.pdf` (ej. `sg.pdf`) y devolver en `cards/<card-code>.jpg` a partir de https://github.com/Null-Signal-Games/netrunner-cards-json/blob/main/translations/es/pack/<abrev-expansion>.es.json

El `code` es global (único en todo el juego): todos los packs escriben en la misma carpeta `cards/`.

Requisitos concretos:

| Pieza | Ejemplo |
| --- | --- |
| PDF en la raíz del repo | `sg.pdf` |
| Abreviatura = stem del PDF | `sg` (JSON del pack y work) |
| JSON ES (raw) | `https://raw.githubusercontent.com/Null-Signal-Games/netrunner-cards-json/main/translations/es/pack/sg.es.json` |
| Salida | `cards/30001.jpg`, `cards/30002.jpg`, … un archivo por `code` |

Si falta el PDF o el JSON 404, paramí y pedí el archivo / la abreviatura. No inventes códigos.

## Scripts (ejecutar, no reescribir)

Directorio del skill: `.cursor/skills/extraer-cartas-pnp-nsg/`

```text
scripts/pnp_pack.py      # extract + OCR + match + export
scripts/matchlib.py      # título compacto / identidades / hielo+texto pegado
requirements.txt         # pypdfium2, Pillow, rapidocr-onnxruntime
```

Instalar deps si hace falta: `pip install -r .cursor/skills/extraer-cartas-pnp-nsg/requirements.txt`

Desde la raíz del repo:

```bash
python .cursor/skills/extraer-cartas-pnp-nsg/scripts/pnp_pack.py run --pdf sg.pdf --abrev sg
```

Tras overrides:

```bash
python .cursor/skills/extraer-cartas-pnp-nsg/scripts/pnp_pack.py export --abrev sg
```

`--out` default: `cards/`. No uses una carpeta por expansión para los JPG.

El PDF 9-up de NSG trae **cada carta como XObject imagen** (no capa de texto). El script recorta esas imágenes (no recorta a ciegas la página). OCR es solo para nombrar.

Playsets: varias copias de la misma carta → **un** `{code}.jpg` (primera coincidencia).

## Artefactos

| Ruta | Rol |
| --- | --- |
| `cards/{code}.jpg` | Entrega global |
| `cards/_work/<abrev>/dudas.md` | Qué falta / qué no matcheó, con rutas |
| `cards/_work/<abrev>/crops/pXX_rY_cZ.jpg` | Recorte por casillero |
| `cards/_work/<abrev>/mapeo.json` | OCR + match por recorte |
| `cards/_work/<abrev>/{abrev}.es.json` | Copia del pack ES |
| `cards/_work/<abrev>/dudas.json` | Misma info, máquina |
| `cards/_work/<abrev>/overrides.json` | Ajustes `{ "p08_r2_c3.jpg": "30075" }` |

Antecedentes de la sesión System Gateway (no son el pipeline): `system-gateway-cartas/`, `system-gateway-cartas-mapeo.json`, `_identify_cards.py`, `_rematch_cards.py`, `sg.es.json`.

## Inconsistencias (obligatorio)

Si `unmatched_crops` o `json_codes_without_image` no están vacíos, **no cierres** el trabajo. Para cada duda:

1. **Recorte:** citá `cards/_work/<abrev>/crops/pXX_rY_cZ.jpg` y **leé la imagen** con Read. Mostrá título OCR vs JSON (`code` + `title`).
2. **JSON:** citá `{ "code", "title" }` del pack. Si hay `proposed` por coleccionista, es hipótesis.
3. **Código JSON sin imagen:** listá `code` + `title` y cruzalo con recortes sin match (típico: impreso «Fondos de Riesgo» vs JSON `30075` «Fondo de Cobertura»).
4. **Ayudas PnP:** no van a `cards/{code}.jpg`.
5. Pedí confirmación. Escribí `cards/_work/<abrev>/overrides.json` y corré `export`. Volvé a leer `dudas.md`. No pises JPG de otros packs salvo el mismo `code`.

No asignes un `code` por “se parece” sin override o match ≥ umbral del script.

Detalle de matching: [reference.md](reference.md)
