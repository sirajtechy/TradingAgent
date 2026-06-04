#!/usr/bin/env python3
"""
Summarize unified master_pilot.json and optionally send Telegram notification.

Env (optional):
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent.parent


def _load_master(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _summarize(doc: Dict[str, Any]) -> Dict[str, Any]:
    tickers = doc.get("tickers") or {}
    manifest = doc.get("manifest") or {}
    cm = ((doc.get("confusion_matrix") or {}).get("cumulative") or {}).get("overall") or {}

    buy: List[str] = []
    watch: List[str] = []
    errors = 0
    for sym, row in tickers.items():
        if not isinstance(row, dict):
            continue
        if row.get("error"):
            errors += 1
            continue
        px = str(row.get("phoenix_signal") or "").upper()
        if px == "BUY":
            buy.append(str(sym).upper())
        elif px == "WATCH":
            watch.append(str(sym).upper())

    return {
        "signal_date": manifest.get("signal_date"),
        "eval_days": manifest.get("eval_days"),
        "tickers_total": len(tickers),
        "phoenix_buy_count": len(buy),
        "phoenix_watch_count": len(watch),
        "pilot_errors": errors,
        "phoenix_buy_tickers": sorted(buy)[:40],
        "confusion_overall": cm,
        "run_id": doc.get("run_id"),
    }


def _format_message(summary: Dict[str, Any], master_path: Path, excel_path: Optional[Path]) -> str:
    lines = [
        "MyTradingSpace daily pilot",
        f"signal_date: {summary.get('signal_date')}",
        f"tickers: {summary.get('tickers_total')} | BUY: {summary.get('phoenix_buy_count')} | WATCH: {summary.get('phoenix_watch_count')} | errors: {summary.get('pilot_errors')}",
    ]
    cm = summary.get("confusion_overall") or {}
    if cm:
        lines.append(
            f"confusion (directional): TP={cm.get('TP')} FP={cm.get('FP')} TN={cm.get('TN')} FN={cm.get('FN')} "
            f"acc%={cm.get('accuracy_pct')}"
        )
    buys = summary.get("phoenix_buy_tickers") or []
    if buys:
        lines.append("BUY: " + ", ".join(buys[:25]))
        if len(buys) > 25:
            lines.append(f"(+{len(buys) - 25} more in file)")
    lines.append(f"master: {master_path}")
    if excel_path and excel_path.is_file():
        lines.append(f"excel: {excel_path}")
    return "\n".join(lines)


def _telegram_send(text: str, token: str, chat_id: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": text[:4000], "disable_web_page_preview": "true"}
    ).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    if not body.get("ok"):
        raise RuntimeError(f"Telegram API error: {body}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--master-pilot",
        type=Path,
        help="Path to master_pilot.json (default: unified_master_<today>)",
    )
    ap.add_argument(
        "--excel",
        type=Path,
        default=None,
        help="Optional phoenix BUY excel path to mention in message",
    )
    ap.add_argument("--no-telegram", action="store_true", help="Print only; do not send Telegram")
    ap.add_argument("--json", action="store_true", help="Print summary JSON to stdout")
    args = ap.parse_args()

    if args.master_pilot:
        mp = args.master_pilot.expanduser().resolve()
    else:
        from datetime import date

        today = date.today().isoformat()
        mp = ROOT / "data/output/trading_runs" / f"unified_master_{today}" / "master_pilot.json"

    if not mp.is_file():
        print(f"master_pilot not found: {mp}", file=sys.stderr)
        return 1

    doc = _load_master(mp)
    summary = _summarize(doc)
    msg = _format_message(summary, mp, args.excel)

    if args.json:
        out = {**summary, "message": msg, "master_pilot": str(mp)}
        print(json.dumps(out, indent=2))
    else:
        print(msg)

    if args.no_telegram:
        return 0

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("(Telegram skipped: set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)", file=sys.stderr)
        return 0

    _telegram_send(msg, token, chat_id)
    print("Telegram notification sent.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
