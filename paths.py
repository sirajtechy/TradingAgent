"""Centralised path configuration for MyTradingSpace.

Every script should import paths from here instead of hard-coding directory
names.  If the layout ever changes again, only this file needs updating.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent

# ── Input data ────────────────────────────────────────────────
DATA_DIR        = ROOT / "data"
HALAL_UNIVERSE  = DATA_DIR / "halal_universe"
HALAL_MASTER    = HALAL_UNIVERSE / "halal_master.json"
INPUT_DIR       = DATA_DIR / "input"
MASTER_DATA     = INPUT_DIR / "master_data"
TOP5_PER_SECTOR = MASTER_DATA / "halal_top5_per_sector.json"
POLYGON_CACHE   = INPUT_DIR / "polygon_cache"

# ── Output data ───────────────────────────────────────────────
OUTPUT_DIR      = DATA_DIR / "output"

# Backtests — per-ticker results
BACKTEST_DIR           = OUTPUT_DIR / "backtests"
FUND_BACKTEST          = BACKTEST_DIR / "fundamental"
TECH_BACKTEST          = BACKTEST_DIR / "technical"
ORCH_BACKTEST          = BACKTEST_DIR / "orchestrator"
PRED_BACKTEST          = BACKTEST_DIR / "prediction"
HALAL_ORCH_2025        = BACKTEST_DIR / "halal_orchestrator_2025"
HALAL_TECH_2025        = BACKTEST_DIR / "halal_technical_2025"

# Reports — generated markdown + metrics
REPORTS_DIR            = OUTPUT_DIR / "reports"
FUND_REPORTS           = REPORTS_DIR / "fundamental"
TECH_REPORTS           = REPORTS_DIR / "technical"
ORCH_REPORTS           = REPORTS_DIR / "orchestrator"

# Other output categories
ANALYSIS_DIR           = OUTPUT_DIR / "analysis"
PREDICTIONS_DIR        = OUTPUT_DIR / "predictions"
TRADE_SETUPS_DIR       = OUTPUT_DIR / "trade_setups"
DASHBOARD_EXPORT_DIR   = OUTPUT_DIR / "dashboard"

# Next.js dashboard (consumed by frontend — keep separate)
DASHBOARD_APP_DATA     = ROOT / "backtest-dashboard" / "app" / "data"

# ── Archive (stale / legacy data) ─────────────────────────────
ARCHIVE_DIR            = DATA_DIR / "archive"

# ── .env location ─────────────────────────────────────────────
ENV_FILE               = ROOT / ".env"


def ensure_dirs() -> None:
    """Create all output directories if they don't exist."""
    for d in (
        INPUT_DIR, POLYGON_CACHE,
        FUND_BACKTEST, TECH_BACKTEST, ORCH_BACKTEST,
        PRED_BACKTEST, HALAL_ORCH_2025, HALAL_TECH_2025,
        FUND_REPORTS, TECH_REPORTS, ORCH_REPORTS,
        ANALYSIS_DIR, PREDICTIONS_DIR, TRADE_SETUPS_DIR,
        DASHBOARD_EXPORT_DIR, ARCHIVE_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)
