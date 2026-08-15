# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import unicodedata


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.upper()
    s = s.replace("0", "O")
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def compact(s: str) -> str:
    s = fold(s).replace(" ", "")
    return s.replace("1", "I")


def variants(title: str) -> list[str]:
    out = [title]
    if ":" in title:
        left, right = title.split(":", 1)
        out.extend([left.strip(), right.strip(), f"{left} {right}"])
    return out


def first_words_compact(ocr_title: str, n: int) -> str:
    words = fold(ocr_title).split()
    return compact(" ".join(words[:n]))


def best_score(ocr_title: str, json_title: str) -> float:
    oc = compact(ocr_title)
    if not oc:
        return 0.0
    best = 0.0
    for v in variants(json_title):
        jc = compact(v)
        if len(jc) < 4:
            continue
        if oc == jc:
            return 1.0
        if oc.startswith(jc):
            best = max(best, 0.96 if len(jc) >= 5 else 0.93)
        for n in range(1, 7):
            if first_words_compact(ocr_title, n) == jc:
                best = max(best, 0.97)
        if oc in jc and len(oc) / max(len(jc), 1) >= 0.9 and len(oc) >= 8:
            best = max(best, 0.9)
    return best


def guess_title(lines: list[tuple[str, float, float]]) -> str:
    top = [x for x in lines if x[2] < 0.22 and x[1] >= 0.55]
    top.sort(key=lambda x: x[2])
    skip = re.compile(
        r"^(IDENTIDAD|EVENTO|PROGRAMA|HARDWARE|RECURSO|AGENDA|VENTAJA|"
        r"MEJORA|HIELO|OPERACION|OPERACIÓN|\d+|NISEI)$",
        re.I,
    )
    parts: list[str] = []
    for text, _conf, _y in top:
        t = text.strip()
        if skip.match(fold(t).replace(" ", "")) or re.fullmatch(r"\d+", t) or len(t) <= 1:
            continue
        parts.append(t)
        if len(parts) >= 2:
            break
    return " ".join(parts[:2]) if parts else ""


def guess_collector(lines: list[tuple[str, float, float]]) -> str | None:
    bottom = [x for x in lines if x[2] > 0.90]
    for text, _conf, _y in reversed(bottom):
        m = re.search(r"(\d{1,3})\s*$", text)
        if m:
            n = int(m.group(1))
            if 1 <= n <= 999:
                return str(n)
        if re.fullmatch(r"\d{1,3}", text.strip()):
            n = int(text.strip())
            if 1 <= n <= 999:
                return str(n)
    return None
