#!/usr/bin/env python3
"""
Standalone dashboard generator.

Reads sector_backtest_results.json (or a custom file) and writes
backtest_dashboard.html (or a custom output file).

Useful for regenerating the dashboard without re-running the full backtest.

Usage:
    python generate_dashboard.py
    python generate_dashboard.py --input sector_backtest_results.json --output dashboard.html
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fundamental_agent.dashboard import generate_dashboard


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate HTML dashboard from backtest results JSON.")
    parser.add_argument(
        "--input",
        default="sector_backtest_results.json",
        help="Path to sector_backtest_results.json (default: sector_backtest_results.json)",
    )
    parser.add_argument(
        "--output",
        default="backtest_dashboard.html",
        help="Output HTML file path (default: backtest_dashboard.html)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: Results file not found: {input_path}")
        print("Run the sector backtest first:")
        print("  python run_sector_backtest.py --data-source yfinance --resume")
        sys.exit(1)

    print(f"Reading results from: {input_path}")
    out = generate_dashboard(results_json=input_path, output_html=args.output)
    print(f"✓  Dashboard written to: {out.resolve()}")
    print(f"\nOpen in your browser:")
    print(f"  open '{out.resolve()}'")


if __name__ == "__main__":
    main()
