#!/usr/bin/env python3
"""Copy local Spanish card JPGs from cards/<code>.jpg into deck-<name>/."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

API_DECKLIST = "https://netrunnerdb.com/api/2.0/public/decklist/{id}"
UA = "copiar-cartas-mazo-nrdb/1.0 (Cursor skill)"

WIN_BAD = re.compile(r'[<>:"/\\|?*]')
ID_FROM_URL = re.compile(
    r"(?:decklist/(?:view/)?)(\d+)|(?:/api/2\.0/public/decklist/)(\d+)",
    re.I,
)


def parse_id(raw: str) -> str:
    raw = raw.strip()
    if raw.isdigit():
        return raw
    m = ID_FROM_URL.search(raw)
    if not m:
        raise SystemExit(f"No pude extraer un id numérico de: {raw}")
    return m.group(1) or m.group(2)


def slug_name(name: str) -> str:
    name = WIN_BAD.sub("-", name).strip().rstrip(".")
    name = re.sub(r"\s+", " ", name)
    return name or "unnamed"


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code} al pedir {url}") from e


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", help="URL de decklist, API, o id numérico")
    p.add_argument(
        "--cards",
        type=Path,
        default=Path("cards"),
        help="Carpeta local de JPG ES (default: ./cards).",
    )
    p.add_argument(
        "--out-parent",
        type=Path,
        default=Path("."),
        help="Directorio padre (default: cwd). Se crea deck-<name>/ adentro.",
    )
    args = p.parse_args()
    cards_dir = args.cards
    if not cards_dir.is_dir():
        raise SystemExit(f"No existe la carpeta de cartas: {cards_dir.resolve()}")

    deck_id = parse_id(args.source)
    payload = get_json(API_DECKLIST.format(id=deck_id))
    if not payload.get("success") or not payload.get("data"):
        raise SystemExit(f"API sin data.success: {payload!r}"[:400])

    deck = payload["data"][0]
    name = deck.get("name") or f"decklist-{deck_id}"
    cards = deck.get("cards") or {}
    if not isinstance(cards, dict) or not cards:
        raise SystemExit("El JSON no trae data[0].cards (objeto card_code → quantity)")

    folder = args.out_parent / f"deck-{slug_name(name)}"
    folder.mkdir(parents=True, exist_ok=True)

    (folder / "decklist.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    missing: list[str] = []
    copied = 0
    for code, qty in sorted(cards.items(), key=lambda kv: str(kv[0])):
        src = cards_dir / f"{code}.jpg"
        n = int(qty)
        if not src.is_file():
            missing.append(str(code))
            print(f"falta {src}", file=sys.stderr)
            continue
        leftover = folder / f"{code}.jpg"
        if leftover.is_file():
            leftover.unlink()
        for old in folder.glob(f"{code}-x-*.jpg"):
            old.unlink()
        for i in range(1, n + 1):
            dest = folder / f"{code}-x-{i}.jpg"
            shutil.copy2(src, dest)
            copied += 1
        print(f"ok  {code} x{n} <- {src}")

    manifest = {
        "id": deck.get("id"),
        "name": name,
        "folder": folder.name,
        "cards": cards,
        "cards_dir": str(cards_dir),
        "missing": missing,
    }
    (folder / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if missing:
        raise SystemExit(
            f"Faltan {len(missing)} JPG en {cards_dir}: {', '.join(missing)}. "
            f"Ver {folder / 'manifest.json'}"
        )
    print(f"listo {folder} ({len(cards)} cartas únicas, {copied} copias)")


if __name__ == "__main__":
    main()
