#!/usr/bin/env python3
"""
Generate 3 independent backtest reports — one per agent.
Each report includes:
  1. 12-Month Backtest Performance Report
  2. Entry & Exit Signal Log
  3. 3×3 Confusion Matrix (BUY/SELL/HOLD)
  4. Misclassification Report (every wrong signal with market conditions)
  5. Metrics: Win Rate, Sharpe Ratio, Max Drawdown, Profit Factor, Total Trades
  6. Orchestrator also gets Agent Agreement Rate

Runs 3 workers in parallel via ThreadPoolExecutor.
"""

import json
import math
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE = Path(__file__).parent
OUTPUT = BASE / "backtest_output"

# ── Sector mapping (same 5 sectors × 10 tickers as orchestrator run) ──────────
SECTORS: Dict[str, List[str]] = {
    "Technology": [
        "AAPL", "MSFT", "NVDA", "GOOGL", "META",
        "AMZN", "TSLA", "ORCL", "ANET", "CRM",
    ],
    "Healthcare": [
        "JNJ", "UNH", "LLY", "ABBV", "MRK",
        "PFE", "BMY", "CVS", "CI", "ABT",
    ],
    "Financials": [
        "JPM", "BAC", "WFC", "GS", "MS",
        "V", "MA", "AXP", "BLK", "C",
    ],
    "Consumer_Staples": [
        "PEP", "KO", "PG", "WMT", "COST",
        "MCD", "PM", "MO", "GIS", "CL",
    ],
    "Energy": [
        "XOM", "CVX", "COP", "SLB", "OXY",
        "PSX", "VLO", "MPC", "EOG", "HAL",
    ],
}

TICKER_TO_SECTOR = {}
for _sec, _tks in SECTORS.items():
    for _t in _tks:
        TICKER_TO_SECTOR[_t] = _sec

SIGNAL_MAP = {"bullish": "BUY", "bearish": "SELL", "neutral": "HOLD"}


# ── Data loaders ──────────────────────────────────────────────────────────────

def _load_ticker_json(path: Path) -> Optional[Dict]:
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def load_technical_data() -> Dict[str, Dict]:
    """Load technical backtest JSONs → {ticker: {periods, summary}}"""
    d = BASE / "technical_sector_results"
    out = {}
    for f in sorted(d.glob("*_technical_backtest_results.json")):
        ticker = f.name.replace("_technical_backtest_results.json", "")
        data = _load_ticker_json(f)
        if data:
            out[ticker] = data
    return out


def load_fundamental_data() -> Dict[str, Dict]:
    """Load fundamental backtest JSONs → {ticker: {periods, summary}}"""
    d = BASE / "sector_results"
    out = {}
    for f in sorted(d.glob("*_backtest_results.json")):
        ticker = f.name.replace("_backtest_results.json", "")
        data = _load_ticker_json(f)
        if data:
            out[ticker] = data
    return out


def load_orchestrator_data() -> Dict[str, Dict]:
    """Load orchestrator backtest JSONs → {ticker: {periods, summary}}"""
    d = BASE / "orchestrator_sector_results"
    out = {}
    for f in sorted(d.glob("*_orchestrator_backtest.json")):
        ticker = f.name.replace("_orchestrator_backtest.json", "")
        data = _load_ticker_json(f)
        if data:
            out[ticker] = data
    return out


# ── Period normalizer ─────────────────────────────────────────────────────────

@dataclass
class NormalizedPeriod:
    ticker: str
    sector: str
    month: str
    signal_date: str
    result_date: str
    start_price: float
    end_price: float
    price_return_pct: float
    actual_direction: str        # "up" / "down"
    raw_signal: str              # bullish / bearish / neutral
    mapped_signal: str           # BUY / SELL / HOLD
    signal_correct: Optional[bool]
    score: Optional[float]
    score_band: Optional[str]
    frameworks: Optional[Dict]
    # orchestrator-specific
    confidence: Optional[float] = None
    conflict_detected: Optional[bool] = None
    conflict_resolution: Optional[str] = None
    weights_applied: Optional[Dict] = None
    tech_score: Optional[float] = None
    fund_score: Optional[float] = None
    data_quality: Optional[str] = None


def normalize_periods(ticker_data: Dict[str, Dict], agent: str) -> List[NormalizedPeriod]:
    """Convert raw JSON periods to normalized periods for analysis."""
    periods = []
    for ticker, data in ticker_data.items():
        sector = TICKER_TO_SECTOR.get(ticker, "Unknown")
        for p in data.get("periods", []):
            raw_sig = p.get("signal", "neutral")
            # Score field differs by agent
            if agent == "orchestrator":
                score = p.get("orchestrator_score")
            else:
                score = p.get("experimental_score")
            np_ = NormalizedPeriod(
                ticker=ticker,
                sector=sector,
                month=p.get("month", ""),
                signal_date=p.get("signal_date", ""),
                result_date=p.get("result_date", ""),
                start_price=p.get("start_price", 0),
                end_price=p.get("end_price", 0),
                price_return_pct=p.get("price_return_pct", 0),
                actual_direction=p.get("actual_direction", ""),
                raw_signal=raw_sig,
                mapped_signal=SIGNAL_MAP.get(raw_sig, "HOLD"),
                signal_correct=p.get("signal_correct"),
                score=score,
                score_band=p.get("score_band"),
                frameworks=p.get("frameworks"),
                confidence=p.get("confidence"),
                conflict_detected=p.get("conflict_detected"),
                conflict_resolution=p.get("conflict_resolution"),
                weights_applied=p.get("weights_applied"),
                tech_score=p.get("tech_score"),
                fund_score=p.get("fund_score"),
                data_quality=p.get("data_quality"),
            )
            periods.append(np_)
    return periods


# ── Metrics calculator ────────────────────────────────────────────────────────

@dataclass
class AgentMetrics:
    total_periods: int = 0
    total_trades: int = 0        # directional signals (BUY + SELL)
    buys: int = 0
    sells: int = 0
    holds: int = 0
    correct_trades: int = 0
    incorrect_trades: int = 0
    win_rate_pct: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    profit_factor: Optional[float] = None
    # confusion matrix 3×3: predicted × actual
    # rows: BUY, SELL, HOLD / cols: UP, DOWN
    cm_buy_up: int = 0
    cm_buy_down: int = 0
    cm_sell_up: int = 0
    cm_sell_down: int = 0
    cm_hold_up: int = 0
    cm_hold_down: int = 0
    # agreement rate (orchestrator only)
    agreement_rate_pct: Optional[float] = None


def compute_metrics(periods: List[NormalizedPeriod], agent: str) -> AgentMetrics:
    m = AgentMetrics()
    m.total_periods = len(periods)

    trade_returns = []   # returns for all directional signals
    gross_gains = 0.0
    gross_losses = 0.0

    for p in periods:
        actual_up = p.actual_direction == "up"

        # Confusion matrix
        if p.mapped_signal == "BUY":
            m.buys += 1
            m.total_trades += 1
            if actual_up:
                m.cm_buy_up += 1
            else:
                m.cm_buy_down += 1
            # Trade return: buy → get the actual return
            trade_returns.append(p.price_return_pct)
        elif p.mapped_signal == "SELL":
            m.sells += 1
            m.total_trades += 1
            if actual_up:
                m.cm_sell_up += 1
            else:
                m.cm_sell_down += 1
            # Trade return: sell → inverse (profit from short)
            trade_returns.append(-p.price_return_pct)
        else:
            m.holds += 1
            if actual_up:
                m.cm_hold_up += 1
            else:
                m.cm_hold_down += 1

        # Correct/incorrect for directional signals
        if p.signal_correct is True:
            m.correct_trades += 1
        elif p.signal_correct is False:
            m.incorrect_trades += 1

    # Win Rate
    if m.total_trades > 0:
        m.win_rate_pct = round(m.correct_trades / m.total_trades * 100, 1)

    # Profit Factor
    for r in trade_returns:
        if r > 0:
            gross_gains += r
        elif r < 0:
            gross_losses += abs(r)
    if gross_losses > 0:
        m.profit_factor = round(gross_gains / gross_losses, 2)
    elif gross_gains > 0:
        m.profit_factor = float("inf")

    # Sharpe Ratio (annualized, monthly returns)
    if len(trade_returns) >= 2:
        mean_r = sum(trade_returns) / len(trade_returns)
        var_r = sum((r - mean_r) ** 2 for r in trade_returns) / (len(trade_returns) - 1)
        std_r = math.sqrt(var_r) if var_r > 0 else 0
        if std_r > 0:
            m.sharpe_ratio = round((mean_r / std_r) * math.sqrt(12), 2)

    # Max Drawdown (cumulative equity curve of trade returns)
    if trade_returns:
        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0
        for r in trade_returns:
            cumulative += r
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd
        m.max_drawdown_pct = round(max_dd, 2)

    # Agreement Rate (orchestrator only)
    if agent == "orchestrator":
        agree_count = 0
        both_present = 0
        for p in periods:
            if p.tech_score is not None and p.fund_score is not None:
                both_present += 1
                # Both agents agree if they're on the same side of 50
                tech_bullish = p.tech_score >= 50
                fund_bullish = p.fund_score >= 50
                if tech_bullish == fund_bullish:
                    agree_count += 1
        if both_present > 0:
            m.agreement_rate_pct = round(agree_count / both_present * 100, 1)

    return m


# ── Per-sector metrics ────────────────────────────────────────────────────────

def compute_sector_metrics(periods: List[NormalizedPeriod], agent: str) -> Dict[str, AgentMetrics]:
    sector_periods = {}
    for p in periods:
        sector_periods.setdefault(p.sector, []).append(p)
    return {s: compute_metrics(ps, agent) for s, ps in sector_periods.items()}


# ── Misclassification report ─────────────────────────────────────────────────

@dataclass
class Misclassification:
    ticker: str
    sector: str
    month: str
    signal_date: str
    predicted: str        # BUY / SELL
    actual: str           # up / down
    price_return_pct: float
    score: Optional[float]
    score_band: Optional[str]
    frameworks_summary: str
    confidence: Optional[float] = None
    conflict_info: str = ""
    data_quality: Optional[str] = None


def build_misclassifications(periods: List[NormalizedPeriod], agent: str) -> List[Misclassification]:
    misses = []
    for p in periods:
        if p.signal_correct is False:
            # Framework summary
            fw_summary = ""
            if p.frameworks:
                parts = []
                for fname, fdata in p.frameworks.items():
                    if isinstance(fdata, dict) and fdata.get("applicable"):
                        s = fdata.get("score_pct")
                        parts.append(f"{fname}={s}")
                fw_summary = ", ".join(parts)

            conflict_info = ""
            if agent == "orchestrator":
                if p.conflict_detected:
                    conflict_info = f"CONFLICT: {p.conflict_resolution or 'unknown'}"
                if p.weights_applied:
                    conflict_info += f" w=[T:{p.weights_applied.get('tech','-')}/F:{p.weights_applied.get('fund','-')}]"
                if p.tech_score is not None and p.fund_score is not None:
                    conflict_info += f" scores=[T:{p.tech_score}/F:{p.fund_score}]"

            misses.append(Misclassification(
                ticker=p.ticker,
                sector=p.sector,
                month=p.month,
                signal_date=p.signal_date,
                predicted=p.mapped_signal,
                actual=p.actual_direction,
                price_return_pct=p.price_return_pct,
                score=p.score,
                score_band=p.score_band,
                frameworks_summary=fw_summary,
                confidence=p.confidence,
                conflict_info=conflict_info,
                data_quality=p.data_quality,
            ))
    return sorted(misses, key=lambda x: (x.sector, x.ticker, x.signal_date))


# ── Report renderer (Markdown) ───────────────────────────────────────────────

def _pct(v: Optional[float]) -> str:
    return f"{v:.1f}%" if v is not None else "N/A"


def _val(v: Optional[float]) -> str:
    return f"{v}" if v is not None else "N/A"


def render_report(
    agent_name: str,
    periods: List[NormalizedPeriod],
    metrics: AgentMetrics,
    sector_metrics: Dict[str, AgentMetrics],
    misclassifications: List[Misclassification],
) -> str:
    lines = []
    a = lines.append

    # ── Header ────────────────────────────────────────────────────────────
    a(f"# {agent_name} Agent — 12-Month Sector Backtest Report")
    a(f"")
    a(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    a(f"**Window**: March 2025 – February 2026 (12 months)")
    a(f"**Total Periods**: {metrics.total_periods}")
    a(f"**Total Trades (Directional)**: {metrics.total_trades}")
    a(f"**Abstentions (HOLD)**: {metrics.holds}")
    a(f"")

    # ── 1. Performance Summary ────────────────────────────────────────────
    a(f"## 1. Performance Summary")
    a(f"")
    a(f"| Metric | Value |")
    a(f"|--------|-------|")
    a(f"| Win Rate | {_pct(metrics.win_rate_pct)} |")
    a(f"| Sharpe Ratio (annualized) | {_val(metrics.sharpe_ratio)} |")
    a(f"| Max Drawdown | {_val(metrics.max_drawdown_pct)}% |")
    a(f"| Profit Factor | {_val(metrics.profit_factor)} |")
    a(f"| Total Trades | {metrics.total_trades} |")
    a(f"| BUY Signals | {metrics.buys} |")
    a(f"| SELL Signals | {metrics.sells} |")
    a(f"| HOLD Signals | {metrics.holds} |")
    a(f"| Correct | {metrics.correct_trades} |")
    a(f"| Incorrect | {metrics.incorrect_trades} |")
    if metrics.agreement_rate_pct is not None:
        a(f"| Agent Agreement Rate | {_pct(metrics.agreement_rate_pct)} |")
    a(f"")

    # ── 2. Sector Breakdown ───────────────────────────────────────────────
    a(f"## 2. Sector Breakdown")
    a(f"")
    a(f"| Sector | Trades | Win Rate | Sharpe | Max DD | Profit Factor | BUY | SELL | HOLD |")
    a(f"|--------|--------|----------|--------|--------|---------------|-----|------|------|")
    for sec_name in SECTORS:
        sm = sector_metrics.get(sec_name)
        if sm is None:
            continue
        a(f"| {sec_name} | {sm.total_trades} | {_pct(sm.win_rate_pct)} | "
          f"{_val(sm.sharpe_ratio)} | {_val(sm.max_drawdown_pct)}% | "
          f"{_val(sm.profit_factor)} | {sm.buys} | {sm.sells} | {sm.holds} |")
    a(f"")

    # ── 3. Confusion Matrix (3×3: BUY/SELL/HOLD × UP/DOWN) ───────────────
    a(f"## 3. Confusion Matrix")
    a(f"")
    a(f"3-class confusion matrix: predicted signal (rows) vs actual market direction (columns).")
    a(f"")
    a(f"|              | Actual UP | Actual DOWN | Row Total |")
    a(f"|--------------|-----------|-------------|-----------|")
    buy_total = metrics.cm_buy_up + metrics.cm_buy_down
    sell_total = metrics.cm_sell_up + metrics.cm_sell_down
    hold_total = metrics.cm_hold_up + metrics.cm_hold_down
    a(f"| **Pred BUY**  | {metrics.cm_buy_up} (TP) | {metrics.cm_buy_down} (FP) | {buy_total} |")
    a(f"| **Pred SELL** | {metrics.cm_sell_up} (FN) | {metrics.cm_sell_down} (TN) | {sell_total} |")
    a(f"| **Pred HOLD** | {metrics.cm_hold_up} (Missed) | {metrics.cm_hold_down} (Avoided) | {hold_total} |")
    a(f"| **Col Total** | {metrics.cm_buy_up + metrics.cm_sell_up + metrics.cm_hold_up} | "
      f"{metrics.cm_buy_down + metrics.cm_sell_down + metrics.cm_hold_down} | "
      f"{metrics.total_periods} |")
    a(f"")

    # Derived metrics from confusion matrix
    tp, fp = metrics.cm_buy_up, metrics.cm_buy_down
    fn, tn = metrics.cm_sell_up, metrics.cm_sell_down
    directional = tp + fp + fn + tn
    correct = tp + tn
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    specificity = tn / (tn + fp) if (tn + fp) else None
    f1 = 2 * precision * recall / (precision + recall) if precision and recall else None
    accuracy = correct / directional if directional else None
    abstention = metrics.holds / metrics.total_periods if metrics.total_periods else None

    a(f"### Derived Classification Metrics")
    a(f"")
    a(f"| Metric | Value |")
    a(f"|--------|-------|")
    a(f"| Accuracy (TP+TN)/(TP+FP+TN+FN) | {_pct(accuracy * 100 if accuracy else None)} |")
    a(f"| Precision (TP/(TP+FP)) | {_pct(precision * 100 if precision else None)} |")
    a(f"| Recall (TP/(TP+FN)) | {_pct(recall * 100 if recall else None)} |")
    a(f"| Specificity (TN/(TN+FP)) | {_pct(specificity * 100 if specificity else None)} |")
    a(f"| F1 Score | {_pct(f1 * 100 if f1 else None)} |")
    a(f"| Abstention Rate | {_pct(abstention * 100 if abstention else None)} |")
    a(f"")

    # Per-sector confusion matrices
    a(f"### Per-Sector Confusion Matrices")
    a(f"")
    for sec_name in SECTORS:
        sm = sector_metrics.get(sec_name)
        if sm is None:
            continue
        a(f"#### {sec_name}")
        a(f"")
        a(f"|              | Actual UP | Actual DOWN |")
        a(f"|--------------|-----------|-------------|")
        a(f"| **Pred BUY**  | {sm.cm_buy_up} | {sm.cm_buy_down} |")
        a(f"| **Pred SELL** | {sm.cm_sell_up} | {sm.cm_sell_down} |")
        a(f"| **Pred HOLD** | {sm.cm_hold_up} | {sm.cm_hold_down} |")
        sec_dir = sm.cm_buy_up + sm.cm_buy_down + sm.cm_sell_up + sm.cm_sell_down
        sec_correct = sm.cm_buy_up + sm.cm_sell_down
        sec_acc = sec_correct / sec_dir * 100 if sec_dir else None
        a(f"")
        a(f"Directional Accuracy: {_pct(sec_acc)} ({sec_correct}/{sec_dir})")
        a(f"")

    # ── 4. Entry & Exit Signal Log ────────────────────────────────────────
    a(f"## 4. Entry & Exit Signal Log")
    a(f"")
    a(f"| # | Ticker | Sector | Month | Signal Date | Signal | Score | Actual Dir | Return % | Correct |")
    a(f"|---|--------|--------|-------|-------------|--------|-------|------------|----------|---------|")
    for i, p in enumerate(sorted(periods, key=lambda x: (x.signal_date, x.ticker)), 1):
        icon = "✅" if p.signal_correct is True else ("❌" if p.signal_correct is False else "➖")
        sc = f"{p.score:.1f}" if p.score is not None else "-"
        a(f"| {i} | {p.ticker} | {p.sector} | {p.month} | {p.signal_date} | "
          f"{p.mapped_signal} | {sc} | {p.actual_direction} | {p.price_return_pct:+.1f}% | {icon} |")
    a(f"")

    # ── 5. Misclassification Report ──────────────────────────────────────
    a(f"## 5. Misclassification Report")
    a(f"")
    a(f"**Total Misclassifications**: {len(misclassifications)} out of {metrics.total_trades} directional signals")
    a(f"**Misclassification Rate**: {_pct(len(misclassifications) / metrics.total_trades * 100 if metrics.total_trades else None)}")
    a(f"")

    # Summary by type
    buy_wrong = [m for m in misclassifications if m.predicted == "BUY"]
    sell_wrong = [m for m in misclassifications if m.predicted == "SELL"]
    a(f"### Misclassification Breakdown")
    a(f"")
    a(f"| Type | Count | Description |")
    a(f"|------|-------|-------------|")
    a(f"| False Positive (BUY → DOWN) | {len(buy_wrong)} | Predicted BUY but market went down |")
    a(f"| False Negative (SELL → UP) | {len(sell_wrong)} | Predicted SELL but market went up |")
    a(f"")

    # By sector frequency
    sector_miss = {}
    for m in misclassifications:
        sector_miss.setdefault(m.sector, []).append(m)
    a(f"### Misclassification Frequency by Sector")
    a(f"")
    a(f"| Sector | Misclassifications | FP (BUY→DOWN) | FN (SELL→UP) |")
    a(f"|--------|--------------------|----------------|--------------|")
    for sec_name in SECTORS:
        ms = sector_miss.get(sec_name, [])
        fp = len([m for m in ms if m.predicted == "BUY"])
        fn = len([m for m in ms if m.predicted == "SELL"])
        a(f"| {sec_name} | {len(ms)} | {fp} | {fn} |")
    a(f"")

    # By month frequency
    month_miss = {}
    for m in misclassifications:
        month_miss.setdefault(m.month, []).append(m)
    a(f"### Misclassification Frequency by Month")
    a(f"")
    a(f"| Month | Misclassifications | FP | FN |")
    a(f"|-------|--------------------|----|----|")
    for month_name, ms in sorted(month_miss.items(), key=lambda x: x[1][0].signal_date):
        fp = len([m for m in ms if m.predicted == "BUY"])
        fn = len([m for m in ms if m.predicted == "SELL"])
        a(f"| {month_name} | {len(ms)} | {fp} | {fn} |")
    a(f"")

    # Full detail table
    a(f"### Detailed Misclassification Log")
    a(f"")
    a(f"| # | Ticker | Sector | Month | Predicted | Actual | Return % | Score | Band | Market Conditions |")
    a(f"|---|--------|--------|-------|-----------|--------|----------|-------|------|-------------------|")
    for i, m in enumerate(misclassifications, 1):
        sc = f"{m.score:.1f}" if m.score is not None else "-"
        band = m.score_band or "-"
        conditions = m.frameworks_summary or ""
        if m.confidence is not None:
            conditions = f"conf={m.confidence:.2f}; " + conditions
        if m.conflict_info:
            conditions = m.conflict_info + "; " + conditions
        if m.data_quality:
            conditions = f"DQ={m.data_quality}; " + conditions
        # Truncate long conditions for table readability
        if len(conditions) > 120:
            conditions = conditions[:117] + "..."
        a(f"| {i} | {m.ticker} | {m.sector} | {m.month} | {m.predicted} | "
          f"{m.actual} | {m.price_return_pct:+.1f}% | {sc} | {band} | {conditions} |")
    a(f"")

    # ── 6. Top Misclassified Tickers ──────────────────────────────────────
    a(f"### Top Misclassified Tickers")
    a(f"")
    ticker_miss = {}
    for m in misclassifications:
        ticker_miss.setdefault(m.ticker, []).append(m)
    sorted_tickers = sorted(ticker_miss.items(), key=lambda x: -len(x[1]))
    a(f"| Ticker | Sector | Misclassifications | FP | FN | Avg Return on Misclass |")
    a(f"|--------|--------|--------------------|----|----|-----------------------|")
    for ticker, ms in sorted_tickers[:15]:
        fp = len([m for m in ms if m.predicted == "BUY"])
        fn = len([m for m in ms if m.predicted == "SELL"])
        avg_ret = sum(m.price_return_pct for m in ms) / len(ms)
        sec = ms[0].sector
        a(f"| {ticker} | {sec} | {len(ms)} | {fp} | {fn} | {avg_ret:+.1f}% |")
    a(f"")

    return "\n".join(lines)


# ── Worker functions ──────────────────────────────────────────────────────────

def generate_technical_report() -> str:
    print("[Technical] Loading data...")
    raw = load_technical_data()
    # Filter to only tickers in our 5-sector universe
    all_sector_tickers = set(TICKER_TO_SECTOR.keys())
    filtered = {t: d for t, d in raw.items() if t in all_sector_tickers}
    print(f"[Technical] {len(filtered)} tickers loaded ({len(filtered) * 12} periods)")

    periods = normalize_periods(filtered, "technical")
    metrics = compute_metrics(periods, "technical")
    sector_metrics = compute_sector_metrics(periods, "technical")
    misclassifications = build_misclassifications(periods, "technical")

    report = render_report("Technical", periods, metrics, sector_metrics, misclassifications)

    out_dir = OUTPUT / "technical_agent"
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "backtest_report.md", "w") as f:
        f.write(report)

    # Save raw data as JSON
    json_data = {
        "agent": "technical",
        "tickers": list(filtered.keys()),
        "total_periods": metrics.total_periods,
        "metrics": {
            "win_rate_pct": metrics.win_rate_pct,
            "sharpe_ratio": metrics.sharpe_ratio,
            "max_drawdown_pct": metrics.max_drawdown_pct,
            "profit_factor": metrics.profit_factor,
            "total_trades": metrics.total_trades,
            "buys": metrics.buys,
            "sells": metrics.sells,
            "holds": metrics.holds,
        },
        "confusion_matrix": {
            "BUY_UP": metrics.cm_buy_up, "BUY_DOWN": metrics.cm_buy_down,
            "SELL_UP": metrics.cm_sell_up, "SELL_DOWN": metrics.cm_sell_down,
            "HOLD_UP": metrics.cm_hold_up, "HOLD_DOWN": metrics.cm_hold_down,
        },
        "misclassifications": len(misclassifications),
    }
    with open(out_dir / "metrics.json", "w") as f:
        json.dump(json_data, f, indent=2)

    print(f"[Technical] ✓ Report saved → {out_dir}/")
    return f"Technical: {metrics.total_trades} trades, {_pct(metrics.win_rate_pct)} win rate, {len(misclassifications)} misclassifications"


def generate_fundamental_report() -> str:
    print("[Fundamental] Loading data...")
    raw = load_fundamental_data()
    all_sector_tickers = set(TICKER_TO_SECTOR.keys())
    filtered = {t: d for t, d in raw.items() if t in all_sector_tickers}
    print(f"[Fundamental] {len(filtered)} tickers loaded ({len(filtered) * 12} periods)")

    periods = normalize_periods(filtered, "fundamental")
    metrics = compute_metrics(periods, "fundamental")
    sector_metrics = compute_sector_metrics(periods, "fundamental")
    misclassifications = build_misclassifications(periods, "fundamental")

    report = render_report("Fundamental", periods, metrics, sector_metrics, misclassifications)

    out_dir = OUTPUT / "fundamental_agent"
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "backtest_report.md", "w") as f:
        f.write(report)

    json_data = {
        "agent": "fundamental",
        "tickers": list(filtered.keys()),
        "total_periods": metrics.total_periods,
        "metrics": {
            "win_rate_pct": metrics.win_rate_pct,
            "sharpe_ratio": metrics.sharpe_ratio,
            "max_drawdown_pct": metrics.max_drawdown_pct,
            "profit_factor": metrics.profit_factor,
            "total_trades": metrics.total_trades,
            "buys": metrics.buys,
            "sells": metrics.sells,
            "holds": metrics.holds,
        },
        "confusion_matrix": {
            "BUY_UP": metrics.cm_buy_up, "BUY_DOWN": metrics.cm_buy_down,
            "SELL_UP": metrics.cm_sell_up, "SELL_DOWN": metrics.cm_sell_down,
            "HOLD_UP": metrics.cm_hold_up, "HOLD_DOWN": metrics.cm_hold_down,
        },
        "misclassifications": len(misclassifications),
    }
    with open(out_dir / "metrics.json", "w") as f:
        json.dump(json_data, f, indent=2)

    print(f"[Fundamental] ✓ Report saved → {out_dir}/")
    return f"Fundamental: {metrics.total_trades} trades, {_pct(metrics.win_rate_pct)} win rate, {len(misclassifications)} misclassifications"


def generate_orchestrator_report() -> str:
    print("[Orchestrator] Loading data...")
    raw = load_orchestrator_data()
    all_sector_tickers = set(TICKER_TO_SECTOR.keys())
    filtered = {t: d for t, d in raw.items() if t in all_sector_tickers}
    print(f"[Orchestrator] {len(filtered)} tickers loaded ({len(filtered) * 12} periods)")

    periods = normalize_periods(filtered, "orchestrator")
    metrics = compute_metrics(periods, "orchestrator")
    sector_metrics = compute_sector_metrics(periods, "orchestrator")
    misclassifications = build_misclassifications(periods, "orchestrator")

    report = render_report("Orchestrator", periods, metrics, sector_metrics, misclassifications)

    out_dir = OUTPUT / "orchestrator_agent"
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "backtest_report.md", "w") as f:
        f.write(report)

    json_data = {
        "agent": "orchestrator",
        "tickers": list(filtered.keys()),
        "total_periods": metrics.total_periods,
        "metrics": {
            "win_rate_pct": metrics.win_rate_pct,
            "sharpe_ratio": metrics.sharpe_ratio,
            "max_drawdown_pct": metrics.max_drawdown_pct,
            "profit_factor": metrics.profit_factor,
            "total_trades": metrics.total_trades,
            "buys": metrics.buys,
            "sells": metrics.sells,
            "holds": metrics.holds,
            "agreement_rate_pct": metrics.agreement_rate_pct,
        },
        "confusion_matrix": {
            "BUY_UP": metrics.cm_buy_up, "BUY_DOWN": metrics.cm_buy_down,
            "SELL_UP": metrics.cm_sell_up, "SELL_DOWN": metrics.cm_sell_down,
            "HOLD_UP": metrics.cm_hold_up, "HOLD_DOWN": metrics.cm_hold_down,
        },
        "misclassifications": len(misclassifications),
    }
    with open(out_dir / "metrics.json", "w") as f:
        json.dump(json_data, f, indent=2)

    print(f"[Orchestrator] ✓ Report saved → {out_dir}/")
    return f"Orchestrator: {metrics.total_trades} trades, {_pct(metrics.win_rate_pct)} win rate, {len(misclassifications)} misclassifications"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  PARALLEL REPORT GENERATION — 3 Independent Agent Workers")
    print("=" * 70)
    print()

    workers = {
        "Technical": generate_technical_report,
        "Fundamental": generate_fundamental_report,
        "Orchestrator": generate_orchestrator_report,
    }

    results = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(fn): name for name, fn in workers.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                result = future.result()
                results[name] = result
                print(f"\n✅ {name} complete: {result}")
            except Exception as e:
                results[name] = f"ERROR: {e}"
                print(f"\n❌ {name} failed: {e}")

    print()
    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    for name in ["Technical", "Fundamental", "Orchestrator"]:
        print(f"  {name}: {results.get(name, 'N/A')}")
    print()
    print(f"  Reports saved to: {OUTPUT}/")
    print("=" * 70)


if __name__ == "__main__":
    main()
