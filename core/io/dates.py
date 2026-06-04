from __future__ import annotations

from datetime import datetime


def validate_date_iso(d: str) -> str:
    datetime.strptime(d.strip(), "%Y-%m-%d")
    return d.strip()
