# Netrunner — PDFs en español, cartas y mazos

Flujo: bajar el PnP oficial → extraer JPG a `cards/` → armar la carpeta del mazo desde una decklist de NetrunnerDB → generar el PDF final con PNPTools.

## 1. Descargar PDFs en castellano (System Gateway)

Fuente: [System Gateway (ES) — Conjunto](https://nullsignal.games/es/productos/system-gateway/#conjunto)

1. Abrí la página con el sitio en **español** (selector de idioma arriba a la derecha). Si ves la versión en inglés, cambiá a ES; los enlaces PnP siguen el idioma de la página.
2. Bajá hasta **Conjunto System Gateway** (`#conjunto`). El Starter y el Deckbuilding Pack por separado **no** tienen PnP propio: el imprimir-y-jugar está en el conjunto.
3. En **Imprimir y jugar** elegí el PDF:
   - **A4, 1×** — una copia de cada carta, 9 por hoja. Es el que usa el skill de extracción (`sg.pdf`).
   - **A4, 3×** — playset completo (tres copias). Sirve para imprimir el set, no para extraer códigos únicos.
   - Letter (EE.UU.) solo si tu impresora no es A4.
4. Guardá el archivo **1× A4** en la raíz de este repo como `sg.pdf` (la abreviatura del set en NetrunnerDB es `sg`).
5. NSG suele pedir un donativo opcional (PayPal / Ko-fi) después de bajar.

Otros sets: misma idea en la ficha del producto en español → Imprimir y jugar → A4 1×, con nombre `<abrev>.pdf` (`su21.pdf`, etc.).

## 2. Extraer cartas — skill `extraer-cartas-pnp-nsg`

Convierte el PDF 9-up de Null Signal Games en JPG en español, una por código de carta.

- PDF en la raíz: `sg.pdf`
- JSON de títulos ES: [translations/es/pack/sg.es.json](https://github.com/Null-Signal-Games/netrunner-cards-json/blob/main/translations/es/pack/sg.es.json)
- Salida global: `cards/<card-code>.jpg` (todos los packs mezclados en `cards/`)

```bash
pip install -r .cursor/skills/extraer-cartas-pnp-nsg/requirements.txt
python .cursor/skills/extraer-cartas-pnp-nsg/scripts/pnp_pack.py run --pdf sg.pdf --abrev sg
```

Si hay dudas de matching, revisá `cards/_work/sg/dudas.md`, confirmá overrides y:

```bash
python .cursor/skills/extraer-cartas-pnp-nsg/scripts/pnp_pack.py export --abrev sg
```

Sin PDF o si el JSON 404, el skill para y pide el archivo / la abreviatura. No inventa códigos.

## 3. Armar un mazo — skill `copiar-cartas-mazo-nrdb`

Copia las JPG locales (español) según una **decklist publicada** en NetrunnerDB. No baja arte de NRDB.

```bash
python .cursor/skills/copiar-cartas-mazo-nrdb/scripts/fetch_deck.py https://netrunnerdb.com/en/decklist/88740
```

Acepta URL de la página, URL de la API, o el id numérico. Las URLs nuevas con UUID también sirven si la API pública las resuelve (el JSON trae `id` numérico).

La decklist tiene que estar **publicada**. El mazo privado del deckbuilder (`/en/deck/…`) no tiene endpoint público.

Salida: `deck-<nombre>/`

| Archivo | Rol |
| --- | --- |
| `{code}-x-1.jpg` … `{code}-x-n.jpg` | Una copia por cada unidad del mazo |
| `manifest.json` | id, nombre, cantidades, `missing` |
| `decklist.json` | Respuesta completa de la API |

Si falta algún `cards/{code}.jpg`, el script lista esos códigos, los deja en `missing` y corta. Extraé el pack con el skill anterior; no uses imágenes en inglés de NetrunnerDB.

## 4. PDF final del mazo — PNPTools

Las carpetas `deck-*/` son caras sueltas, no un PDF de impresión.

Para armar el PDF del mazo (hojas listas para imprimir): usá **PNPTools** en `C:\pnptools`, con las JPG de `deck-<nombre>/` (una por copia: `*-x-1.jpg`, `*-x-2.jpg`, …).
