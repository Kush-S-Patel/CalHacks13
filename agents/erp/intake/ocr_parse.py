"""Parse daitavan/financial-documents OCR JSON ({word, bounding_box} tokens)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def load_ocr_tokens(path: Path | str | bytes | list) -> list[dict[str, Any]]:
    if isinstance(path, list):
        return path
    if isinstance(path, bytes):
        data = json.loads(path.decode("utf-8", errors="replace"))
    else:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("OCR JSON must be a list of {word, bounding_box} tokens")
    return data


def tokens_to_lines(tokens: list[dict[str, Any]], y_tol: int = 12) -> list[str]:
    """
    Reconstruct reading-order lines from word boxes.
    bounding_box = [x0, y0, x1, y1]
    """
    words: list[tuple[int, int, str]] = []
    for t in tokens:
        w = str(t.get("word") or "").strip()
        if not w:
            continue
        bb = t.get("bounding_box") or [0, 0, 0, 0]
        if len(bb) < 4:
            continue
        x0, y0 = int(bb[0]), int(bb[1])
        words.append((y0, x0, w))
    if not words:
        return []

    words.sort(key=lambda x: (x[0], x[1]))
    lines: list[list[tuple[int, int, str]]] = []
    current: list[tuple[int, int, str]] = []
    current_y: int | None = None
    for y, x, w in words:
        if current_y is None or abs(y - current_y) <= y_tol:
            current.append((y, x, w))
            current_y = y if current_y is None else current_y
        else:
            lines.append(current)
            current = [(y, x, w)]
            current_y = y
    if current:
        lines.append(current)

    out: list[str] = []
    for line in lines:
        line.sort(key=lambda t: t[1])
        out.append(" ".join(t[2] for t in line))
    return out


def tokens_to_text(tokens: list[dict[str, Any]]) -> str:
    return "\n".join(tokens_to_lines(tokens))


_AMOUNT = re.compile(
    r"(?<![\w.])(?:₹|Rs\.?|INR|USD|\$)?\s*\(?-?\d{1,3}(?:,\d{2,3})*(?:\.\d+)?\)?-?|\(\d[\d,]*\.?\d*\)",
    re.I,
)


def parse_money_token(raw: str) -> int | None:
    s = raw.strip()
    if not s:
        return None
    neg = "(" in s and ")" in s or s.endswith("-")
    s = s.replace("₹", "").replace("Rs.", "").replace("Rs", "")
    s = s.replace("INR", "").replace("USD", "").replace("$", "")
    s = s.replace(",", "").replace("(", "").replace(")", "").replace("-", "").strip()
    if not s:
        return None
    try:
        # Indian lac statements often omit decimals; treat as whole currency units → cents
        v = float(s)
    except ValueError:
        return None
    cents = int(round(v * 100))
    return -cents if neg else cents


def extract_labeled_amounts(lines: list[str]) -> list[dict[str, Any]]:
    """Pull (label, amount) pairs from OCR lines — core of financial statement intake."""
    rows: list[dict[str, Any]] = []
    for line in lines:
        amounts = list(_AMOUNT.finditer(line))
        if not amounts:
            continue
        # Prefer the rightmost amount as the period value
        m = amounts[-1]
        label = line[: m.start()].strip(" :-|")
        label = re.sub(r"\s+", " ", label).strip()
        if len(label) < 3:
            continue
        # Skip pure numeric / date noise labels
        if re.fullmatch(r"[\d\s./-]+", label):
            continue
        amt = parse_money_token(m.group(0))
        if amt is None:
            continue
        # Filter tiny garbage
        if abs(amt) < 100 and "cash" not in label.lower():
            continue
        rows.append({"label": label, "amount_cents": amt, "raw_line": line})
    return rows


def guess_class_from_path(path: Path | str) -> str | None:
    p = str(path).replace("\\", "/").lower()
    for cls in (
        "balance_sheets",
        "cash_flow",
        "income_statement",
        "notes",
        "others",
    ):
        if f"/{cls}/" in p or p.endswith(f"/{cls}"):
            return cls
    return None