# -*- coding: utf-8 -*-
"""Extract 9-up Netrunner PnP PDFs and match crops to NSG translation JSON codes."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

from matchlib import best_score, guess_collector, guess_title

JSON_URL = (
    "https://raw.githubusercontent.com/Null-Signal-Games/netrunner-cards-json/"
    "main/translations/es/pack/{abrev}.es.json"
)
MATCH_THRESHOLD = 0.82


DEFAULT_CARDS = Path("cards")


def work_dir(cards: Path, abrev: str) -> Path:
    d = cards / "_work" / abrev
    d.mkdir(parents=True, exist_ok=True)
    return d


def extract(pdf_path: Path, crops_dir: Path) -> list[Path]:
    import pypdfium2 as pdfium

    crops_dir.mkdir(parents=True, exist_ok=True)
    for old in crops_dir.glob("p*.jpg"):
        old.unlink()
    pdf = pdfium.PdfDocument(str(pdf_path))
    written: list[Path] = []
    for pi, page in enumerate(pdf, start=1):
        cards = []
        for o in page.get_objects():
            if type(o).__name__ != "PdfImage":
                continue
            _l, _b, _r, t = o.get_bounds()
            l = o.get_bounds()[0]
            img = o.get_bitmap().to_pil()
            cards.append((t, l, img))
        cards.sort(key=lambda x: (-round(x[0], 1), round(x[1], 1)))
        for idx, (_, _, img) in enumerate(cards, start=1):
            row = (idx - 1) // 3 + 1
            col = (idx - 1) % 3 + 1
            path = crops_dir / f"p{pi:02d}_r{row}_c{col}.jpg"
            img.convert("RGB").save(path, quality=92, optimize=True)
            written.append(path)
    return written


def fetch_catalog(abrev: str, dest: Path) -> list[dict]:
    url = JSON_URL.format(abrev=abrev)
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = resp.read()
        dest.write_bytes(data)
    except Exception as e:
        if dest.exists():
            print(f"warn: could not fetch {url} ({e}); using cache {dest}", file=sys.stderr)
        else:
            raise SystemExit(f"Could not download {url}: {e}") from e
    catalog = json.loads(dest.read_text(encoding="utf-8"))
    if not isinstance(catalog, list):
        raise SystemExit(f"Unexpected JSON shape in {dest}")
    return catalog


def ocr_match(crops_dir: Path, catalog: list[dict], mapeo_path: Path) -> list[dict]:
    from PIL import Image
    from rapidocr_onnxruntime import RapidOCR

    ocr = RapidOCR()
    files = sorted(crops_dir.glob("p*.jpg"))
    results = []
    for i, path in enumerate(files, 1):
        img = Image.open(path).convert("RGB")
        res, _ = ocr(img)
        h = img.size[1]
        lines = []
        for item in res or []:
            box, text, conf = item
            ys = [p[1] for p in box]
            y = (min(ys) + max(ys)) / 2 / h
            lines.append((text.strip(), float(conf), y))
        ocr_title = guess_title(lines)
        ocr_num = guess_collector(lines)
        scored = []
        for c in catalog:
            scored.append((best_score(ocr_title, c["title"]), c["code"], c["title"]))
        scored.sort(reverse=True)
        s, code, title = scored[0] if scored else (0.0, None, None)
        matched = bool(code) and s >= MATCH_THRESHOLD
        proposed = None
        if not matched and ocr_num:
            hits = [
                c
                for c in catalog
                if c["code"].endswith(ocr_num.zfill(3))
                or c["code"].endswith(ocr_num)
            ]
            if len(hits) == 1:
                proposed = {
                    "code": hits[0]["code"],
                    "title": hits[0]["title"],
                    "why": "collector_number_unique",
                }
        rec = {
            "file": path.name,
            "path": str(path),
            "ocr_title": ocr_title,
            "ocr_collector": ocr_num,
            "matched": matched,
            "score": round(s, 3) if s else 0,
            "code": code if matched else None,
            "json_title": title if matched else None,
            "best_candidate": (
                {"code": code, "title": title, "score": round(s, 3)} if code else None
            ),
            "proposed": proposed,
        }
        results.append(rec)
        if i % 20 == 0:
            print(f"ocr {i}/{len(files)}", flush=True)
    mapeo_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


def apply_overrides(results: list[dict], overrides: dict[str, str], catalog: list[dict]) -> list[dict]:
    by_code = {c["code"]: c for c in catalog}
    for r in results:
        code = overrides.get(r["file"])
        if not code:
            continue
        if code not in by_code:
            r["override_error"] = f"unknown code {code}"
            continue
        r["matched"] = True
        r["code"] = code
        r["json_title"] = by_code[code]["title"]
        r["match_how"] = "override"
    return results


def build_dudas(results: list[dict], catalog: list[dict]) -> dict:
    matched = [r for r in results if r.get("matched")]
    unmatched = [r for r in results if not r.get("matched")]
    found = {r["code"] for r in matched if r.get("code")}
    missing = [
        {"code": c["code"], "title": c["title"]}
        for c in catalog
        if c["code"] not in found
    ]
    return {
        "unmatched_crops": [
            {
                "file": r["file"],
                "path": r["path"],
                "ocr_title": r.get("ocr_title"),
                "ocr_collector": r.get("ocr_collector"),
                "best_candidate": r.get("best_candidate"),
                "proposed": r.get("proposed"),
            }
            for r in unmatched
        ],
        "json_codes_without_image": missing,
        "override_hint": {
            "file": "cards/_work/<abrev>/overrides.json",
            "shape": {"p08_r2_c3.jpg": "30075"},
        },
    }


def export_codes(results: list[dict], crops_dir: Path, out: Path) -> list[str]:
    by_code: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        if r.get("matched") and r.get("code"):
            by_code[r["code"]].append(r)
    written = []
    for code, recs in sorted(by_code.items()):
        src = crops_dir / recs[0]["file"]
        dest = out / f"{code}.jpg"
        shutil.copyfile(src, dest)
        written.append(code)
    return written


def write_dudas_md(dudas: dict, path: Path) -> None:
    lines = ["# Dudas PnP", "", "## Recortes sin match (abrir la imagen)", ""]
    if not dudas["unmatched_crops"]:
        lines.append("Ninguno.")
    else:
        for r in dudas["unmatched_crops"]:
            prop = ""
            if r.get("proposed"):
                prop = f" propuesta=`{r['proposed']['code']}` {r['proposed']['title']}"
            cand = r.get("best_candidate") or {}
            lines.append(
                f"- `{r['path']}` OCR=«{r.get('ocr_title') or ''}» "
                f"n={r.get('ocr_collector')} candidato={cand.get('code')} "
                f"{cand.get('title')} score={cand.get('score')}{prop}"
            )
    lines += ["", "## Códigos del JSON sin imagen", ""]
    if not dudas["json_codes_without_image"]:
        lines.append("Ninguno.")
    else:
        for c in dudas["json_codes_without_image"]:
            lines.append(f"- `{c['code']}` — {c['title']}")
    lines += [
        "",
        "## Cómo ajustar",
        "",
        "Escribir `cards/_work/<abrev>/overrides.json` con `{ \"pXX_rY_cZ.jpg\": \"30075\" }` y rerun `export`.",
        "",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_run(args: argparse.Namespace) -> None:
    pdf = Path(args.pdf)
    abrev = args.abrev or pdf.stem.lower()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    wd = work_dir(out, abrev)
    crops = wd / "crops"
    print(f"extract {pdf} -> {crops}")
    extract(pdf, crops)
    catalog = fetch_catalog(abrev, wd / f"{abrev}.es.json")
    print(f"catalog {len(catalog)} cards")
    mapeo = wd / "mapeo.json"
    results = ocr_match(crops, catalog, mapeo)
    ov_path = wd / "overrides.json"
    if ov_path.exists():
        overrides = json.loads(ov_path.read_text(encoding="utf-8"))
        results = apply_overrides(results, overrides, catalog)
        mapeo.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    dudas = build_dudas(results, catalog)
    (wd / "dudas.json").write_text(json.dumps(dudas, ensure_ascii=False, indent=2), encoding="utf-8")
    write_dudas_md(dudas, wd / "dudas.md")
    codes = export_codes(results, crops, out)
    print(f"exported {len(codes)} / {len(catalog)} -> {out}")
    print(f"unmatched crops {len(dudas['unmatched_crops'])}")
    print(f"json missing images {len(dudas['json_codes_without_image'])}")
    print("see", wd / "dudas.md")


def cmd_export(args: argparse.Namespace) -> None:
    out = Path(args.out)
    wd = work_dir(out, args.abrev)
    catalog = json.loads((wd / f"{args.abrev}.es.json").read_text(encoding="utf-8"))
    results = json.loads((wd / "mapeo.json").read_text(encoding="utf-8"))
    ov_path = wd / "overrides.json"
    if ov_path.exists():
        overrides = json.loads(ov_path.read_text(encoding="utf-8"))
        results = apply_overrides(results, overrides, catalog)
        (wd / "mapeo.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    dudas = build_dudas(results, catalog)
    (wd / "dudas.json").write_text(json.dumps(dudas, ensure_ascii=False, indent=2), encoding="utf-8")
    write_dudas_md(dudas, wd / "dudas.md")
    export_codes(results, wd / "crops", out)
    print("re-exported", out)


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--pdf", required=True)
    r.add_argument("--abrev")
    r.add_argument("--out", default=str(DEFAULT_CARDS))
    r.set_defaults(func=cmd_run)
    e = sub.add_parser("export")
    e.add_argument("--out", default=str(DEFAULT_CARDS))
    e.add_argument("--abrev", required=True)
    e.set_defaults(func=cmd_export)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
