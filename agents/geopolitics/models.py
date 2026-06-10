from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class GeopoliticsRequest:
    as_of_date: date


@dataclass
class GeoHeadline:
    title: str
    published_date: date
    source: str
    url: str
    matched_keywords: List[str]


@dataclass
class GeopoliticsSnapshot:
    as_of_date: date
    headlines: List[GeoHeadline] = field(default_factory=list)
    total_scanned: int = 0
    data_sources: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
