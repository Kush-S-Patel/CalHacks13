"""
FinCriticalED intake helpers (TheFinAI/FinCriticalED).

Dataset: https://huggingface.co/datasets/TheFinAI/FinCriticalED
Local mirror: data/train_data/scans/raw_input.csv  (id, image, matched_html)
"""

from __future__ import annotations

import csv
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterator


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag in {"script", "style"}:
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip:
            t = data.strip()
            if t:
                self.parts.append(t)


def html_to_text(html: str) -> str:
    p = _TextExtractor()
    try:
        p.feed(html)
    except Exception:  # noqa: BLE001
        return re.sub(r"<[^>]+>", " ", html)
    return "\n".join(p.parts)


def detect_sec_form(text: str) -> str:
    t = text.lower()
    if "form 4" in t or "sec form 4" in t:
        return "form4"
    if "form 10-k" in t or "annual report pursuant" in t:
        return "10k"
    if "form 10-q" in t:
        return "10q"
    if "form 8-k" in t:
        return "8k"
    return "sec_filing"


def iter_fincritical_rows(
    csv_path: Path,
    *,
    limit: int = 25,
    max_html_chars: int = 200_000,
) -> Iterator[dict[str, Any]]:
    csv.field_size_limit(50_000_000)
    with csv_path.open("r", encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh)
        for i, row in enumerate(reader):
            if i >= limit:
                break
            html = row.get("matched_html") or ""
            if len(html) > max_html_chars:
                html = html[:max_html_chars]
            text = html_to_text(html)
            yield {
                "id": row.get("id", str(i)),
                "image_ref": (row.get("image") or "")[:200],
                "text": text,
                "form": detect_sec_form(text),
                "html_chars": len(row.get("matched_html") or ""),
            }


def default_fincritical_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "train_data" / "scans" / "raw_input.csv"