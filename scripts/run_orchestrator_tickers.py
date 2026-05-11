#!/usr/bin/env python3
"""
Compatibility shim — forwards to scripts/run_trading.py analyze.

Prefer:
  python scripts/run_trading.py analyze --fusion phoenix-fa --date YYYY-MM-DD ...

Legacy flags:
  --strategy orchestrator → --fusion ta-fa
  --strategy phoenix      → --fusion phoenix
  --strategy both         → --fusion compare
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    argv = sys.argv[1:]
    mapped: list[str] = []
    strategy_map = {
        "orchestrator": "ta-fa",
        "phoenix": "phoenix",
        "both": "compare",
    }
    i = 0
    while i < len(argv):
        if argv[i] == "--strategy" and i + 1 < len(argv):
            old = argv[i + 1]
            mapped.extend(["--fusion", strategy_map.get(old, old)])
            i += 2
            continue
        mapped.append(argv[i])
        i += 1

    # Legacy default was TA+FA orchestrator, not phoenix-fa.
    if "--fusion" not in mapped:
        mapped = ["--fusion", "ta-fa"] + mapped

    script = ROOT / "scripts" / "run_trading.py"
    spec = importlib.util.spec_from_file_location("run_trading_cli", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {script}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.main(["analyze"] + mapped)


if __name__ == "__main__":
    main()
