---
name: copiar-cartas-mazo-nrdb
description: >-
  Arma una carpeta deck-<name>/ copiando JPG en español desde ./cards/<card-code>.jpg
  según el campo cards (card_code → quantity) del JSON público de NetrunnerDB
  /api/2.0/public/decklist/{id}. Explica cómo llegar a ese JSON desde una
  decklist de netrunnerdb.com. Use when the user pastes a NetrunnerDB decklist
  URL, decklist id, API JSON, pide imágenes del mazo en ES, o pregunta cómo
  obtener el JSON de una decklist.
---

# Imágenes de decklist NetrunnerDB

## Al iniciar

Si el usuario pregunta **cómo** obtener el JSON (sin pedir imágenes todavía), explicá la sección [De la web al JSON](#de-la-web-al-json) y no descargues nada.

Si pega URL / id / JSON y quiere imágenes, ejecutá el script (no lo reescribas). Las imágenes **no** se bajan de NetrunnerDB: se copian de `./cards/<card-code>.jpg` (ES, skill `extraer-cartas-pnp-nsg`).

## De la web al JSON

Una **decklist publicada** en NetrunnerDB tiene un id numérico en la URL:

| Qué ves | Ejemplo |
| --- | --- |
| Página | `https://netrunnerdb.com/en/decklist/88740` |
| Con slug | `https://netrunnerdb.com/en/decklist/view/88740/a-letter-to-beginnings-and-endings` |
| JSON público | `https://netrunnerdb.com/api/2.0/public/decklist/88740` |

Pasos para el usuario:

1. Abrí la decklist en [netrunnerdb.com](https://netrunnerdb.com) (tiene que estar **publicada**; el mazo privado del deckbuilder no sirve este endpoint).
2. Copiá el número después de `/decklist/` o `/decklist/view/`.
3. Pedí `https://netrunnerdb.com/api/2.0/public/decklist/{id}`.

Forma del payload relevante:

```json
{
  "success": true,
  "data": [
    {
      "id": 88740,
      "name": "A Letter to Beginnings and Endings",
      "cards": { "26002": 2, "35001": 1 }
    }
  ]
}
```

`cards` es un objeto **`card_code` (string de 5 dígitos) → quantity**. Una entrada por carta distinta; la cantidad no duplica claves.

No uses mazos no publicados (`/en/deck/…` del usuario logueado): el API público de decklist responde 404 o vacío.

## Imágenes (locales, español)

Fuente: `./cards/{card_code}.jpg` (misma convención que `extraer-cartas-pnp-nsg`). **No** uses `card_image` de NetrunnerDB (inglés).

Una copia **por unidad** (`quantity`). Nombres: `{code}-x-1.jpg`, `{code}-x-2.jpg`, … `{code}-x-{n}.jpg`. Quantity también queda en `manifest.json`.

Carpeta de salida (cwd del repo, salvo que indiquen otra):

`deck-<name>/`

`<name>` es `data[0].name` con caracteres ilegales de Windows (`<>:"/\|?*`) reemplazados por `-`.

Contenido:

| Archivo | Rol |
| --- | --- |
| `{code}-x-{i}.jpg` | Una copia por cada unidad (`i` = 1…quantity) |
| `manifest.json` | id, name, cards (quantities), missing |
| `decklist.json` | Respuesta API completa |

## Script (ejecutar)

Directorio del skill: `.cursor/skills/copiar-cartas-mazo-nrdb/`

Desde la raíz del repo (stdlib only):

```bash
python .cursor/skills/copiar-cartas-mazo-nrdb/scripts/fetch_deck.py https://netrunnerdb.com/en/decklist/88740
```

Acepta la URL de la página, la del API, o solo `88740`.

`--cards DIR` si las JPG no están en `./cards`. `--out-parent DIR` cambia el padre de `deck-<name>/`.

Si falta algún `cards/{code}.jpg`, listá esos códigos, no inventes imágenes ni bajes de NRDB, y pará. Sugerí extraer el pack con `extraer-cartas-pnp-nsg`.

## Checklist

- [ ] Id extraído de la URL o del JSON
- [ ] `GET` decklist API, `data[0].cards` y `data[0].name`
- [ ] Copias desde `cards/{code}.jpg` (ES); códigos faltantes listados, sin fallback NRDB
- [ ] Carpeta `deck-<name>/` con jpg + manifest
- [ ] Si pidieron la explicación web→JSON, dála en claro (tabla de URLs)
