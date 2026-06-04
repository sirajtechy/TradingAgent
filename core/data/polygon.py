"""
core.data.polygon — Re-export of the canonical Polygon client.

Canonical location is agents.polygon_data. This file provides a
convenience import path under core.data for consistency.

Usage:
    from core.data.polygon import PolygonClient, PolygonDataError
    # or (canonical)
    from agents.polygon_data import PolygonClient, PolygonDataError
"""

from agents.polygon_data import (
    PolygonClient,
    PolygonDataError,
    POLYGON_API_KEY,
)

__all__ = ["PolygonClient", "PolygonDataError", "POLYGON_API_KEY"]
