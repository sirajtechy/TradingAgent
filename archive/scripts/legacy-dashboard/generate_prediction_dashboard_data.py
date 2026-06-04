#!/usr/bin/env python3
"""
generate_prediction_dashboard_data.py — Convert orchestrator prediction JSON
into the dashboard-consumable format.

Reads: data/predictions/predictions_YYYY-MM-DD.json
Writes: backtest-dashboard/app/data/prediction-data.json
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backtests.common import SECTORS


def _get_sector(ticker: str) -> str:
    for sector, tickers in SECTORS.items():
        if ticker in tickers:
            return sector
    return "Unknown"


def main():
    base = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(base))
    import paths
    today = date.today().isoformat()

    pred_path = paths.PREDICTIONS_DIR / f"predictions_{today}.json"
    if not pred_path.exists():
        print(f"No predictions found at {pred_path}")
        sys.exit(1)

    raw = json.loads(pred_path.read_text())
    print(f"Loaded {len(raw)} ticker predictions from {pred_path.name}")

    # Build prediction entries
    predictions = []
    sector_agg = {}
    bullish = bearish = neutral = errors = 0
    total_score = 0.0
    conflict_count = 0

    for ticker, r in sorted(raw.items()):
        sector = _get_sector(ticker)

        if "error" in r and "final_signal" not in r:
            errors += 1
            continue

        sig = r.get("final_signal", "neutral")
        score = r.get("orchestrator_score", 0)
        conf = r.get("final_confidence", 0)
        conflict = r.get("conflict_detected", False)

        tech = r.get("tech_output")
        fund = r.get("fund_output")

        entry = {
            "ticker": ticker,
            "sector": sector,
            "date": today,
            "signal": sig,
            "signalLabel": "BUY" if sig == "bullish" else ("SELL" if sig == "bearish" else "HOLD"),
            "orchestratorScore": round(score, 1),
            "confidence": round(conf, 2),
            "conflictDetected": conflict,
            "conflictResolution": r.get("conflict_resolution"),
            "note": r.get("note"),
            # Technical agent
            "techSignal": tech["signal"] if tech else None,
            "techScore": round(tech["score"], 1) if tech else None,
            "techBand": tech.get("band") if tech else None,
            "techConfidence": tech.get("adx_confidence") if tech else None,
            "techSubscores": {
                k: round(v, 0) if isinstance(v, (int, float)) else v
                for k, v in (tech.get("subscores", {}) or {}).items()
            } if tech else {},
            # Fundamental agent
            "fundSignal": fund["signal"] if fund else None,
            "fundScore": round(fund["score"], 1) if fund else None,
            "fundBand": fund.get("band") if fund else None,
            "fundDataQuality": fund.get("data_quality") if fund else None,
            "fundSubscores": {
                k: round(v, 0) if isinstance(v, (int, float)) else v
                for k, v in (fund.get("subscores", {}) or {}).items()
            } if fund else {},
            # Weights
            "weightTech": r.get("weights_applied", {}).get("tech", 0),
            "weightFund": r.get("weights_applied", {}).get("fund", 0),
        }
        predictions.append(entry)

        # Aggregations
        total_score += score
        if conflict:
            conflict_count += 1
        if sig == "bullish":
            bullish += 1
        elif sig == "bearish":
            bearish += 1
        else:
            neutral += 1

        if sector not in sector_agg:
            sector_agg[sector] = {"bullish": 0, "bearish": 0, "neutral": 0, "totalScore": 0, "count": 0}
        sector_agg[sector][sig] += 1
        sector_agg[sector]["totalScore"] += score
        sector_agg[sector]["count"] += 1

    total = bullish + bearish + neutral
    avg_score = round(total_score / total, 1) if total else 0

    # Sector summaries
    sector_summaries = {}
    for sec, a in sector_agg.items():
        dominant = max(["bullish", "bearish", "neutral"], key=lambda s: a[s])
        sector_summaries[sec] = {
            "bullish": a["bullish"],
            "bearish": a["bearish"],
            "neutral": a["neutral"],
            "dominant": dominant,
            "avgScore": round(a["totalScore"] / a["count"], 1) if a["count"] else 0,
        }

    # High confidence setups
    high_conf = sorted(
        [p for p in predictions if p["signal"] != "neutral" and p["confidence"] >= 0.15 and not p["conflictDetected"]],
        key=lambda x: x["confidence"],
        reverse=True,
    )

    output = {
        "meta": {
            "date": today,
            "agents": "Technical v2 + Fundamental v3 → Orchestrator CWAF",
            "totalTickers": total,
            "errors": errors,
        },
        "summary": {
            "bullish": bullish,
            "bearish": bearish,
            "neutral": neutral,
            "avgScore": avg_score,
            "agreementRate": round((total - conflict_count) / total * 100, 0) if total else 0,
            "conflictCount": conflict_count,
        },
        "sectorSummaries": sector_summaries,
        "predictions": predictions,
        "highConfidenceSetups": [p["ticker"] for p in high_conf[:10]],
    }

    out_path = paths.DASHBOARD_APP_DATA / "prediction-data.json"
    out_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"Wrote {out_path} ({len(predictions)} predictions)")


if __name__ == "__main__":
    main()
