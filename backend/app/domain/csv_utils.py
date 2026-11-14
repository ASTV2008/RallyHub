"""Utilidades CSV seguras (mitigación de inyección de fórmulas en hojas de cálculo)."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Sequence

_DANGEROUS = ("=", "+", "-", "@", "\t", "\r")


def safe_cell(value: object) -> str:
    text = "" if value is None else str(value)
    if text.startswith(_DANGEROUS):
        return "'" + text
    return text


def to_csv(headers: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([safe_cell(c) for c in row])
    return buf.getvalue()
