#!/usr/bin/env python3
"""
export_to_dashboard.py — Transform backtest JSON to dashboard format

Reads the backtest JSON output and converts it to the format expected by
the Next.js dashboard (dashboard-data.json and prediction-data.json).
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

ROOT = Path(__file__).resolve().parent.parent
BACKTEST_JSON = ROOT / "data" / "output" / "backtests" / "2026-04-25" / "2026-04-25.json"
DASHBOARD_DIR = ROOT / "backtest-dashboard" / "app" / "data"


def transform_to_predictions(backtest_data: List[Dict]) -> Dict[str, Any]:
    """Transform backtest results to prediction format for the dashboard."""
    
    # Filter for latest run (2025-09-30) and exclude errors
    valid_records = [
        r for r in backtest_data 
        if r.get("Cutoff Date") == "2025-09-30" and r.get("Outcome") != "ERROR"
    ]
    
    # Count by signal type
    signal_counts = {"bullish": 0, "bearish": 0, "neutral": 0}
    for r in valid_records:
        signal = r.get("Signal", "")
        if signal == "BUY":
            signal_counts["bullish"] += 1
        elif signal == "AVOID":
            signal_counts["bearish"] += 1
        else:
            signal_counts["neutral"] += 1
    
    # Sector summaries
    sector_summaries = {}
    sectors_data = {}
    for r in valid_records:
        sector = r.get("Sector", "Unknown")
        signal = r.get("Signal", "")
        
        if sector not in sectors_data:
            sectors_data[sector] = {"bullish": 0, "bearish": 0, "neutral": 0, "scores": []}
        
        if signal == "BUY":
            sectors_data[sector]["bullish"] += 1
        elif signal == "AVOID":
            sectors_data[sector]["bearish"] += 1
        else:
            sectors_data[sector]["neutral"] += 1
        
        score = r.get("Confidence Score") or 0
        if score:
            sectors_data[sector]["scores"].append(float(score))
    
    # Calculate sector summaries
    for sector, data in sectors_data.items():
        dominant = max(data, key=lambda k: data[k] if k != "scores" else 0)
        avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
        
        sector_summaries[sector] = {
            "bullish": data["bullish"],
            "bearish": data["bearish"],
            "neutral": data["neutral"],
            "dominant": dominant,
            "avgScore": round(avg_score, 1)
        }
    
    # Transform individual predictions
    predictions = []
    high_confidence_setups = []
    
    for r in valid_records:
        ticker = r.get("Ticker", "")
        sector = r.get("Sector", "")
        signal = r.get("Signal", "")
        confidence_score = r.get("Confidence Score") or 0
        
        # Map signal to raw signal format
        if signal == "BUY":
            raw_signal = "bullish"
            signal_label = "BUY"
        elif signal == "AVOID":
            raw_signal = "bearish"
            signal_label = "SELL"
        else:
            raw_signal = "neutral"
            signal_label = "HOLD"
        
        entry_date = r.get("Entry Date (Earliest)", "") or r.get("Cutoff Date", "")
        exit_date = r.get("Est. Target Date", "")
        
        # Calculate holding days
        holding_days = None
        if entry_date and exit_date:
            try:
                entry_dt = datetime.fromisoformat(entry_date)
                exit_dt = datetime.fromisoformat(exit_date)
                holding_days = (exit_dt - entry_dt).days
            except:
                pass
        
        # Build prediction record
        prediction = {
            "ticker": ticker,
            "sector": sector,
            "date": r.get("Cutoff Date", ""),
            "entryDate": entry_date,
            "exitDate": exit_date,
            "holdingDays": holding_days,
            "signal": raw_signal,
            "signalLabel": signal_label,
            "sentiment": raw_signal,
            "orchestratorScore": round(float(confidence_score), 1) if confidence_score else 0,
            "confidence": round(float(confidence_score), 1) if confidence_score else 0,
            "conviction": r.get("Entry Conviction", ""),
            "targetPrice": r.get("Target Price"),
            "lastPrice": r.get("Entry Price (Est.)"),
            "profitPct": r.get("Gross P&L %"),
            "peakReturnPct": None,
            "targetHitProbPct": None,
            "maxDrawdownPct": None,
            "winRatePct": None,
            "seasonalMatch": False,
            "conflictDetected": False,
            "conflictResolution": None,
            "note": r.get("No Trade Reason") or r.get("Pattern Name"),
            "techSubscores": {
                "technical": r.get("Tech Score") or 0,
            },
            "fundSubscores": {
                "fundamental": r.get("Fund Score") or 0,
            },
            "weightTech": 0.7,
            "weightFund": 0.3,
        }
        
        predictions.append(prediction)
        
        # High confidence setups (confidence > 70 and BUY signal)
        if signal == "BUY" and confidence_score and float(confidence_score) >= 70:
            conviction = r.get("Entry Conviction", "")
            high_confidence_setups.append(
                f"{ticker} ({conviction}, {confidence_score})"
            )
    
    # Calculate averages
    total_score = sum(float(r.get("Confidence Score") or 0) for r in valid_records)
    avg_score = total_score / len(valid_records) if valid_records else 0
    
    return {
        "meta": {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "agents": "CWAF Orchestrator (Technical + Fundamental)",
            "totalTickers": len(valid_records),
            "errors": len([r for r in backtest_data if r.get("Outcome") == "ERROR"])
        },
        "summary": {
            "bullish": signal_counts["bullish"],
            "bearish": signal_counts["bearish"],
            "neutral": signal_counts["neutral"],
            "avgScore": round(avg_score, 1),
            "agreementRate": 100.0,
            "conflictCount": 0
        },
        "sectorSummaries": sector_summaries,
        "predictions": predictions,
        "highConfidenceSetups": high_confidence_setups
    }


def main():
    print(f"Reading backtest data from: {BACKTEST_JSON}")
    
    if not BACKTEST_JSON.exists():
        print(f"ERROR: Backtest JSON not found at {BACKTEST_JSON}")
        sys.exit(1)
    
    with open(BACKTEST_JSON) as f:
        backtest_data = json.load(f)
    
    print(f"Loaded {len(backtest_data)} backtest records")
    
    # Transform to prediction format
    prediction_data = transform_to_predictions(backtest_data)
    
    # Write to dashboard
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DASHBOARD_DIR / "prediction-data.json"
    
    with open(output_path, "w") as f:
        json.dump(prediction_data, f, indent=2)
    
    print(f"\n{'='*70}")
    print(f"Dashboard data exported successfully!")
    print(f"{'='*70}")
    print(f"Output: {output_path}")
    print(f"\nSummary:")
    print(f"  Total tickers: {prediction_data['meta']['totalTickers']}")
    print(f"  BUY signals: {prediction_data['summary']['bullish']}")
    print(f"  AVOID signals: {prediction_data['summary']['bearish']}")
    print(f"  HOLD signals: {prediction_data['summary']['neutral']}")
    print(f"  Avg confidence: {prediction_data['summary']['avgScore']}")
    print(f"  High confidence setups: {len(prediction_data['highConfidenceSetups'])}")
    
    if prediction_data['highConfidenceSetups']:
        print(f"\n  Top picks:")
        for setup in prediction_data['highConfidenceSetups'][:5]:
            print(f"    - {setup}")
    
    print(f"\n{'='*70}")
    print(f"Next steps:")
    print(f"  1. cd backtest-dashboard")
    print(f"  2. npm run dev (to test locally)")
    print(f"  3. git add . && git commit -m 'Update dashboard with 2025-09-30 backtest'")
    print(f"  4. git push (auto-deploys to Vercel)")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
