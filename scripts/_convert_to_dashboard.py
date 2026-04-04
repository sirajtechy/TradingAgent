#!/usr/bin/env python3
"""Convert halal orchestrator backtest per-ticker JSONs → dashboard-data.json.

Reads all *_halal_orch_2025.json files, extracts technical / fundamental /
orchestrator signals per period, builds the DashboardData shape expected by
the Next.js backtest-dashboard, and writes it to app/data/dashboard-data.json.

Also converts forward_predictions → prediction-data.json.
"""

import json, glob, os, sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# ── Paths ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "data" / "output" / "backtests" / "halal_orchestrator_2025"
DASHBOARD_DATA = ROOT / "backtest-dashboard" / "app" / "data" / "dashboard-data.json"
PREDICTION_DATA = ROOT / "backtest-dashboard" / "app" / "data" / "prediction-data.json"


def _score_band(score):
    if score is None:
        return None
    if score >= 75:
        return "strong"
    elif score >= 60:
        return "good"
    elif score >= 50:
        return "mixed_positive"
    elif score >= 35:
        return "mixed"
    else:
        return "weak"


def _signal_label(raw):
    """Map raw signal string to BUY/SELL/HOLD."""
    if raw in ("bullish", "LONG"):
        return "BUY"
    elif raw in ("bearish", "SHORT"):
        return "SELL"
    return "HOLD"


def _direction(d):
    if d and d.upper() == "UP":
        return "up"
    return "down"


def build_signals():
    """Read per-ticker JSONs → list of Signal dicts for all 3 agents."""
    signals = []
    all_tickers = set()
    all_sectors = set()
    all_months = set()
    predictions_by_ticker = {}

    files = sorted(RESULTS_DIR.glob("*_halal_orch_2025.json"))
    files = [f for f in files if not f.name.startswith("master")]

    for fp in files:
        with open(fp) as fh:
            data = json.load(fh)

        ticker = data["ticker"]
        sector = data["sector"]
        cap_tier = data.get("market_cap_tier", "large")
        all_tickers.add(ticker)
        all_sectors.add(sector)

        for period in data.get("periods", []):
            month = period["month"]
            signal_date = period["signal_date"]
            result_date = period["result_date"]
            all_months.add(month)

            outcome = period.get("actual_outcome") or {}
            end_price = outcome.get("end_price")
            return_pct = outcome.get("price_return_pct", 0)
            actual_dir = _direction(outcome.get("actual_direction", "down"))

            ts = period.get("trade_setup") or {}
            entry_price = ts.get("entry_price") or 0

            # Derive start price: use trade entry if available,
            # else back-calculate from end_price and return_pct
            if entry_price > 0:
                start_price = entry_price
            elif end_price and return_pct != 0:
                start_price = end_price / (1 + return_pct / 100)
            elif end_price:
                start_price = end_price
            else:
                start_price = 0

            # ── Technical signal ──────────────────────────────────────
            tech = period.get("tech_summary") or {}
            tech_score = tech.get("score")
            tech_band = tech.get("band")
            tech_subscores = tech.get("subscores", {})
            # Use actual band to determine signal (matches agent logic)
            if tech_band in ("strong", "good", "mixed_positive"):
                tech_raw = "bullish"
            elif tech_band == "weak":
                tech_raw = "bearish"
            else:  # mixed or None → neutral
                tech_raw = "neutral"

            # Correctness: only evaluate directional signals
            tech_correct = None
            actual_raw = outcome.get("actual_direction", "").upper()
            if actual_raw and tech_raw == "bullish":
                tech_correct = actual_raw == "UP"
            elif actual_raw and tech_raw == "bearish":
                tech_correct = actual_raw == "DOWN"

            # ── Shared fields: patterns + trade setup ─────────────────
            raw_patterns = period.get("patterns_detected") or []
            patterns_list = [
                {
                    "name": pt.get("name", ""),
                    "direction": pt.get("direction", ""),
                    "confidence": round(pt.get("confidence", 0), 2),
                }
                for pt in raw_patterns[:5]  # top 5 to limit payload
            ]
            tech_conf = tech.get("confidence")
            tech_conf_pct = tech.get("confidence_pct")
            # confidence may be string label; use confidence_pct (0-100) if available
            if isinstance(tech_conf_pct, (int, float)):
                tech_conf_val = round(tech_conf_pct / 100, 3)
            elif isinstance(tech_conf, (int, float)):
                tech_conf_val = round(tech_conf, 3)
            else:
                _conf_map = {"high_conviction": 0.9, "high": 0.8, "moderate": 0.5, "low": 0.3}
                tech_conf_val = _conf_map.get(str(tech_conf).lower(), None)

            signals.append({
                "ticker": ticker,
                "sector": sector,
                "agent": "technical",
                "month": month,
                "signalDate": signal_date,
                "resultDate": result_date,
                "startPrice": round(start_price, 2),
                "endPrice": round(end_price, 2) if end_price else 0,
                "returnPct": round(return_pct, 2),
                "actualDirection": actual_dir,
                "rawSignal": tech_raw,
                "signal": _signal_label(tech_raw),
                "correct": tech_correct,
                "score": round(tech_score, 1) if tech_score else None,
                "scoreBand": _score_band(tech_score),
                "frameworks": {k: round(v, 1) if v else None for k, v in tech_subscores.items()},
                "confidence": tech_conf_val,
                "patterns": patterns_list,
                "targetPrice": round(ts.get("target_price", 0), 2) if ts.get("target_price") else None,
                "stopLoss": round(ts.get("stop_loss", 0), 2) if ts.get("stop_loss") else None,
                "entryDate": ts.get("entry_date"),
                "exitDateEst": ts.get("exit_date_est"),
                "tradeDurationDays": ts.get("trade_duration_days"),
                "direction": ts.get("direction"),
            })

            # ── Fundamental signal ────────────────────────────────────
            fund = period.get("fund_summary") or {}
            fund_score = fund.get("score")
            fund_band = fund.get("band")
            fund_subscores = fund.get("subscores", {})
            # Use actual band to determine signal (matches agent logic)
            if fund_band in ("strong", "good", "mixed_positive"):
                fund_raw = "bullish"
            elif fund_band == "weak":
                fund_raw = "bearish"
            else:  # mixed or None → neutral
                fund_raw = "neutral"
            fund_dq = fund.get("data_quality", "unknown")

            # Correctness: only evaluate directional signals
            fund_correct = None
            if actual_raw and fund_raw == "bullish":
                fund_correct = actual_raw == "UP"
            elif actual_raw and fund_raw == "bearish":
                fund_correct = actual_raw == "DOWN"

            fund_conf = fund.get("confidence")
            # Fund confidence is also a string label
            if isinstance(fund_conf, (int, float)):
                fund_conf_val = round(fund_conf, 3)
            else:
                _fconf_map = {"high": 0.8, "moderate": 0.5, "low": 0.3}
                fund_conf_val = _fconf_map.get(str(fund_conf).lower(), None)

            signals.append({
                "ticker": ticker,
                "sector": sector,
                "agent": "fundamental",
                "month": month,
                "signalDate": signal_date,
                "resultDate": result_date,
                "startPrice": round(start_price, 2),
                "endPrice": round(end_price, 2) if end_price else 0,
                "returnPct": round(return_pct, 2),
                "actualDirection": actual_dir,
                "rawSignal": fund_raw,
                "signal": _signal_label(fund_raw),
                "correct": fund_correct,
                "score": round(fund_score, 1) if fund_score else None,
                "scoreBand": _score_band(fund_score),
                "frameworks": {k: round(v, 1) if v else None for k, v in fund_subscores.items()},
                "dataQuality": fund_dq,
                "confidence": fund_conf_val,
                "patterns": patterns_list,
                "targetPrice": round(ts.get("target_price", 0), 2) if ts.get("target_price") else None,
                "stopLoss": round(ts.get("stop_loss", 0), 2) if ts.get("stop_loss") else None,
                "entryDate": ts.get("entry_date"),
                "exitDateEst": ts.get("exit_date_est"),
                "tradeDurationDays": ts.get("trade_duration_days"),
                "direction": ts.get("direction"),
            })

            # ── Orchestrator signal ───────────────────────────────────
            orch_signal = period.get("orchestrator_signal", "neutral")
            orch_score = period.get("orchestrator_score")
            orch_conf = period.get("final_confidence")
            conflict = period.get("conflict_detected", False)
            conflict_res = period.get("conflict_resolution")
            weights = period.get("weights_applied", {})

            orch_correct = None
            if orch_signal == "bullish" and actual_raw:
                went_up = actual_raw == "UP"
                orch_correct = went_up  # bullish=BUY, correct if UP
            elif orch_signal == "bearish" and actual_raw:
                went_up = actual_raw == "UP"
                orch_correct = not went_up  # bearish=SELL, correct if DOWN

            orch_entry = {
                "ticker": ticker,
                "sector": sector,
                "agent": "orchestrator",
                "month": month,
                "signalDate": signal_date,
                "resultDate": result_date,
                "startPrice": round(start_price, 2),
                "endPrice": round(end_price, 2) if end_price else 0,
                "returnPct": round(return_pct, 2),
                "actualDirection": actual_dir,
                "rawSignal": orch_signal,
                "signal": _signal_label(orch_signal),
                "correct": orch_correct,
                "score": round(orch_score, 1) if orch_score else None,
                "scoreBand": _score_band(orch_score),
                "confidence": round(orch_conf, 3) if orch_conf else None,
                "conflictDetected": conflict,
                "conflictResolution": conflict_res,
                "patterns": patterns_list,
                "techScore": round(tech_score, 1) if tech_score else None,
                "fundScore": round(fund_score, 1) if fund_score else None,
                "weightTech": weights.get("tech"),
                "weightFund": weights.get("fund"),
            }

            # Trade setup fields (only for orchestrator LONG trades)
            if ts:
                orch_entry.update({
                    "entryPrice": round(ts.get("entry_price", 0), 2),
                    "targetPrice": round(ts.get("target_price", 0), 2),
                    "stopLoss": round(ts.get("stop_loss", 0), 2),
                    "entryDate": ts.get("entry_date"),
                    "exitDateEst": ts.get("exit_date_est"),
                    "expectedProfitPct": round(ts.get("expected_profit_pct", 0), 2),
                    "riskPct": round(ts.get("risk_pct", 0), 2),
                    "rewardRiskRatio": round(ts.get("reward_risk_ratio", 0), 2) if ts.get("reward_risk_ratio") else None,
                    "confidenceScore": round(ts.get("confidence_score", 0), 1),
                    "profitProbability": ts.get("profit_probability"),
                    "direction": ts.get("direction"),
                    "tradeDurationDays": ts.get("trade_duration_days"),
                })

            signals.append(orch_entry)

        # Predictions — also grab last known price for target calc
        fp_data = data.get("forward_predictions")
        if fp_data:
            # Last known price = end_price of the final backtest period
            last_price = None
            for p_rev in reversed(data.get("periods", [])):
                oc = p_rev.get("actual_outcome") or {}
                if oc.get("end_price"):
                    last_price = oc["end_price"]
                    break

            predictions_by_ticker[ticker] = {
                "ticker": ticker,
                "sector": sector,
                "capTier": cap_tier,
                "predictions": fp_data,
                "learnedProfile": data.get("learned_profile"),
                "lastPrice": last_price,
            }

    return signals, sorted(all_tickers), sorted(all_sectors), sorted(all_months, key=lambda m: _month_sort_key(m)), predictions_by_ticker


def _month_sort_key(m):
    """Convert 'January 2025' → sortable date."""
    try:
        return datetime.strptime(m, "%B %Y")
    except ValueError:
        return datetime.min


def build_summaries(signals):
    """Build per-agent AgentSummary objects with confusion matrices."""
    agents = defaultdict(lambda: {
        "totalPeriods": 0,
        "totalTrades": 0,
        "correct": 0,
        "incorrect": 0,
        "buys": 0,
        "sells": 0,
        "holds": 0,
        "tickers": set(),
        "cm": {"buyUp": 0, "buyDown": 0, "sellUp": 0, "sellDown": 0, "holdUp": 0, "holdDown": 0},
        "bySector": {},
    })

    for s in signals:
        agent = s["agent"]
        a = agents[agent]
        a["totalPeriods"] += 1
        a["tickers"].add(s["ticker"])

        sig = s["signal"]
        direction = s["actualDirection"]

        if sig == "BUY":
            a["buys"] += 1
        elif sig == "SELL":
            a["sells"] += 1
        else:
            a["holds"] += 1

        is_trade = sig in ("BUY", "SELL")
        if is_trade:
            a["totalTrades"] += 1
            if s["correct"] is True:
                a["correct"] += 1
            elif s["correct"] is False:
                a["incorrect"] += 1

        # Confusion matrix
        if sig == "BUY" and direction == "up":
            a["cm"]["buyUp"] += 1
        elif sig == "BUY" and direction == "down":
            a["cm"]["buyDown"] += 1
        elif sig == "SELL" and direction == "up":
            a["cm"]["sellUp"] += 1
        elif sig == "SELL" and direction == "down":
            a["cm"]["sellDown"] += 1
        elif sig == "HOLD" and direction == "up":
            a["cm"]["holdUp"] += 1
        elif sig == "HOLD" and direction == "down":
            a["cm"]["holdDown"] += 1

        # Per-sector
        sector = s["sector"]
        if sector not in a["bySector"]:
            a["bySector"][sector] = {
                "totalPeriods": 0, "totalTrades": 0, "correct": 0,
                "winRate": None, "buys": 0, "sells": 0, "holds": 0,
                "cm": {"buyUp": 0, "buyDown": 0, "sellUp": 0, "sellDown": 0, "holdUp": 0, "holdDown": 0},
            }
        bs = a["bySector"][sector]
        bs["totalPeriods"] += 1
        if sig == "BUY":
            bs["buys"] += 1
        elif sig == "SELL":
            bs["sells"] += 1
        else:
            bs["holds"] += 1
        if is_trade:
            bs["totalTrades"] += 1
            if s["correct"] is True:
                bs["correct"] += 1

        # Sector CM
        if sig == "BUY" and direction == "up":
            bs["cm"]["buyUp"] += 1
        elif sig == "BUY" and direction == "down":
            bs["cm"]["buyDown"] += 1
        elif sig == "SELL" and direction == "up":
            bs["cm"]["sellUp"] += 1
        elif sig == "SELL" and direction == "down":
            bs["cm"]["sellDown"] += 1
        elif sig == "HOLD" and direction == "up":
            bs["cm"]["holdUp"] += 1
        elif sig == "HOLD" and direction == "down":
            bs["cm"]["holdDown"] += 1

    # Finalize
    summaries = []
    for agent_name in ["technical", "fundamental", "orchestrator"]:
        a = agents[agent_name]
        total_trades = a["totalTrades"]
        win_rate = round(a["correct"] / total_trades * 100, 1) if total_trades > 0 else None

        for sector_key in a["bySector"]:
            bs = a["bySector"][sector_key]
            st = bs["totalTrades"]
            bs["winRate"] = round(bs["correct"] / st * 100, 1) if st > 0 else None

        summaries.append({
            "agent": agent_name,
            "totalPeriods": a["totalPeriods"],
            "totalTrades": total_trades,
            "correct": a["correct"],
            "incorrect": a["incorrect"],
            "winRate": win_rate,
            "buys": a["buys"],
            "sells": a["sells"],
            "holds": a["holds"],
            "tickers": sorted(a["tickers"]),
            "cm": a["cm"],
            "bySector": a["bySector"],
        })

    return summaries


def build_prediction_data(predictions_by_ticker, sectors):
    """Build prediction-data.json matching the PredictionData TypeScript interface."""
    if not predictions_by_ticker:
        return None

    entries = []
    sector_counts = defaultdict(lambda: {"bullish": 0, "bearish": 0, "neutral": 0, "scores": []})
    total_bullish = total_bearish = total_neutral = 0
    all_scores = []
    conflict_count = 0
    high_conf_setups = []

    for ticker, pdata in sorted(predictions_by_ticker.items()):
        preds = pdata.get("predictions") or []
        profile = pdata.get("learnedProfile") or {}
        sector = pdata.get("sector", "")
        win_rate = profile.get("win_rate_pct")
        last_price = pdata.get("lastPrice")

        for pred in preds:
            # Map from actual forward prediction fields
            bull_prob = pred.get("bullish_probability_pct", 0) or 0
            conviction = pred.get("conviction", "NO DATA")
            expected_ret = pred.get("expected_return_pct")
            hist_wr = pred.get("historical_win_rate_pct")
            seasonal = pred.get("seasonal_match", False)
            peak_ret = pred.get("expected_peak_return_pct")
            target_prob = pred.get("target_hit_probability_pct")
            max_dd = pred.get("max_historical_drawdown_pct")
            holding_days = pred.get("predicted_holding_days")

            # Entry / exit dates
            entry_date = pred.get("predicted_entry_date")
            exit_date = pred.get("predicted_exit_date")

            # Derive signal from bullish probability
            if bull_prob >= 60:
                raw = "bullish"
                signal_label = "BUY"
            elif bull_prob <= 40:
                raw = "bearish"
                signal_label = "SELL"
            else:
                raw = "neutral"
                signal_label = "HOLD"

            # Map conviction → confidence (0-1)
            conv_map = {"HIGH": 0.80, "MODERATE": 0.50, "LOW": 0.30, "NO DATA": 0.0}
            p_conf = conv_map.get(conviction, 0.0)
            p_score = bull_prob  # 0-100 scale

            # Target price based on last known price + expected peak return
            target_price = None
            if last_price and peak_ret is not None:
                target_price = round(last_price * (1 + peak_ret / 100), 2)

            # Expected profit %
            profit_pct = round(expected_ret, 2) if expected_ret is not None else None

            # Track sector totals
            sc = sector_counts[sector]
            sc[raw] += 1
            sc["scores"].append(p_score)

            if raw == "bullish":
                total_bullish += 1
            elif raw == "bearish":
                total_bearish += 1
            else:
                total_neutral += 1
            all_scores.append(p_score)

            if conviction == "HIGH" and raw == "bullish":
                high_conf_setups.append(f"{ticker} ({pred.get('month', '')})")

            entries.append({
                "ticker": ticker,
                "sector": sector,
                "date": pred.get("month", ""),
                "entryDate": entry_date,
                "exitDate": exit_date,
                "holdingDays": holding_days,
                "signal": raw,
                "signalLabel": signal_label,
                "sentiment": raw,
                "orchestratorScore": round(p_score, 1),
                "confidence": round(p_conf, 3),
                "conviction": conviction,
                "targetPrice": target_price,
                "lastPrice": round(last_price, 2) if last_price else None,
                "profitPct": profit_pct,
                "peakReturnPct": round(peak_ret, 2) if peak_ret is not None else None,
                "targetHitProbPct": round(target_prob, 1) if target_prob is not None else None,
                "maxDrawdownPct": round(max_dd, 2) if max_dd is not None else None,
                "winRatePct": round(hist_wr, 1) if hist_wr is not None else None,
                "seasonalMatch": seasonal,
                "conflictDetected": False,
                "conflictResolution": None,
                "note": None,
                "techSubscores": {},
                "fundSubscores": {},
                "weightTech": 0.85,
                "weightFund": 0.15,
            })

    # Build sector summaries
    sector_summaries = {}
    for sec, sc in sector_counts.items():
        total = sc["bullish"] + sc["bearish"] + sc["neutral"]
        dominant = max(["bullish", "bearish", "neutral"], key=lambda x: sc[x])
        avg_score = sum(sc["scores"]) / len(sc["scores"]) if sc["scores"] else 0
        sector_summaries[sec] = {
            "bullish": sc["bullish"],
            "bearish": sc["bearish"],
            "neutral": sc["neutral"],
            "dominant": dominant,
            "avgScore": round(avg_score, 1),
        }

    total_all = total_bullish + total_bearish + total_neutral
    avg_all = sum(all_scores) / len(all_scores) if all_scores else 0

    # Agreement rate: how often both agents agree (non-conflict)
    agreement_rate = round((total_all - conflict_count) / total_all * 100, 1) if total_all else 0

    return {
        "meta": {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "agents": "CWAF Orchestrator (Technical + Fundamental)",
            "totalTickers": len(predictions_by_ticker),
            "errors": 0,
        },
        "summary": {
            "bullish": total_bullish,
            "bearish": total_bearish,
            "neutral": total_neutral,
            "avgScore": round(avg_all, 1),
            "agreementRate": agreement_rate,
            "conflictCount": conflict_count,
        },
        "sectorSummaries": sector_summaries,
        "predictions": entries,
        "highConfidenceSetups": high_conf_setups[:10],
    }


def main():
    print("Reading per-ticker JSONs ...")
    signals, tickers, sectors, months, predictions_by_ticker = build_signals()
    print(f"  → {len(signals)} signals ({len(signals)//3} per agent × 3 agents)")
    print(f"  → {len(tickers)} tickers, {len(sectors)} sectors, {len(months)} months")

    print("Building summaries ...")
    summaries = build_summaries(signals)
    for s in summaries:
        print(f"  {s['agent']:15s}  trades={s['totalTrades']:4d}  winRate={s['winRate']}%")

    dashboard = {
        "meta": {
            "window": "January 2025 – December 2025",
            "months": len(months),
            "sectors": sectors,
            "generated": datetime.now().strftime("%Y-%m-%d"),
        },
        "summaries": summaries,
        "signals": signals,
    }

    DASHBOARD_DATA.parent.mkdir(parents=True, exist_ok=True)
    with open(DASHBOARD_DATA, "w") as f:
        json.dump(dashboard, f, indent=2)
    size_mb = DASHBOARD_DATA.stat().st_size / 1024 / 1024
    print(f"\n✓ Dashboard data → {DASHBOARD_DATA}  ({size_mb:.1f} MB)")

    # Prediction data
    pred_data = build_prediction_data(predictions_by_ticker, sectors)
    if pred_data:
        with open(PREDICTION_DATA, "w") as f:
            json.dump(pred_data, f, indent=2)
        print(f"✓ Prediction data → {PREDICTION_DATA}  ({len(pred_data['predictions'])} predictions)")

    print("\nDone. Start the dashboard with: cd backtest-dashboard && npm run dev")


if __name__ == "__main__":
    main()
