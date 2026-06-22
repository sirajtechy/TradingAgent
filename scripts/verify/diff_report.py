"""Compare artifact rows against independently recomputed Polygon fields."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from .models import CheckResult, CheckStatus, RowVerification, VerifyRow


DEFAULT_PRICE_TOLERANCE_ABS = 0.01
DEFAULT_PRICE_TOLERANCE_REL = 0.0001  # 0.01%


def _price_match(expected: Optional[float], actual: Optional[float], tol_abs: float, tol_rel: float) -> bool:
    if expected is None and actual is None:
        return True
    if expected is None or actual is None:
        return False
    diff = abs(float(expected) - float(actual))
    if diff <= tol_abs:
        return True
    base = max(abs(float(expected)), abs(float(actual)), 1e-9)
    return diff / base <= tol_rel


def _bool_match(expected: Any, actual: Any) -> bool:
    if expected is None and actual is None:
        return True
    if expected is None or actual is None:
        return False
    return bool(expected) == bool(actual)


def _date_match(expected: Optional[str], actual: Optional[str]) -> bool:
    if expected is None and actual is None:
        return True
    if expected is None or actual is None:
        return False
    return str(expected)[:10] == str(actual)[:10]


def _worst_status(statuses: List[CheckStatus]) -> CheckStatus:
    order = {"FAIL": 0, "WARN": 1, "SKIP": 2, "PASS": 3}
    if not statuses:
        return "SKIP"
    return min(statuses, key=lambda s: order.get(s, 99))


def verify_row(
    row: VerifyRow,
    recomputed: Dict[str, Any],
    *,
    tol_abs: float = DEFAULT_PRICE_TOLERANCE_ABS,
    tol_rel: float = DEFAULT_PRICE_TOLERANCE_REL,
    fields: Optional[Set[str]] = None,
) -> RowVerification:
    """Diff one row's artifact values against recomputed Polygon fields."""
    want = fields or {"prices", "target_hit", "labels", "dates"}
    checks: List[CheckResult] = []

    if row.error and recomputed.get("polygon_error", "").startswith("Skipped"):
        return RowVerification(
            row=row,
            status="SKIP",
            checks=[
                CheckResult(
                    field="row",
                    status="SKIP",
                    detail=row.error or recomputed.get("polygon_error"),
                )
            ],
        )

    if recomputed.get("polygon_error") and recomputed.get("entry_price") is None:
        return RowVerification(
            row=row,
            status="SKIP",
            checks=[
                CheckResult(
                    field="polygon",
                    status="SKIP",
                    detail=str(recomputed.get("polygon_error")),
                )
            ],
        )

    if "prices" in want:
        for fld, exp, act in (
            ("entry_price", row.entry_price, recomputed.get("entry_price")),
            ("exit_reference_price", row.exit_reference_price, recomputed.get("exit_reference_price")),
        ):
            if exp is None and act is None:
                checks.append(CheckResult(field=fld, status="SKIP", expected=exp, actual=act))
                continue
            ok = _price_match(exp, act, tol_abs, tol_rel)
            checks.append(
                CheckResult(
                    field=fld,
                    status="PASS" if ok else "FAIL",
                    expected=exp,
                    actual=act,
                    detail=None if ok else f"Tolerance abs={tol_abs}, rel={tol_rel}",
                )
            )

    if "dates" in want and row.start_price_date is not None:
        ok = _date_match(row.start_price_date, recomputed.get("start_price_date"))
        checks.append(
            CheckResult(
                field="start_price_date",
                status="PASS" if ok else "FAIL",
                expected=row.start_price_date,
                actual=recomputed.get("start_price_date"),
            )
        )

    if "dates" in want and row.exit_reference_date is not None:
        ok = _date_match(row.exit_reference_date, recomputed.get("exit_reference_date"))
        checks.append(
            CheckResult(
                field="exit_reference_date",
                status="PASS" if ok else "FAIL",
                expected=row.exit_reference_date,
                actual=recomputed.get("exit_reference_date"),
            )
        )

    if "target_hit" in want:
        ok_hit = _bool_match(row.target_hit, recomputed.get("target_hit"))
        checks.append(
            CheckResult(
                field="target_hit",
                status="PASS" if ok_hit else "FAIL",
                expected=row.target_hit,
                actual=recomputed.get("target_hit"),
            )
        )
        if row.target_hit_date is not None or recomputed.get("target_hit_date"):
            ok_dt = _date_match(row.target_hit_date, recomputed.get("target_hit_date"))
            checks.append(
                CheckResult(
                    field="target_hit_date",
                    status="PASS" if ok_dt else "FAIL",
                    expected=row.target_hit_date,
                    actual=recomputed.get("target_hit_date"),
                )
            )

    if "labels" in want:
        for fld, exp, act in (
            ("signal_correct", row.signal_correct, recomputed.get("signal_correct")),
            ("signal_correct_technical", row.signal_correct_technical, recomputed.get("signal_correct_technical")),
            ("signal_correct_phoenix", row.signal_correct_phoenix, recomputed.get("signal_correct_phoenix")),
        ):
            if exp is None:
                continue
            ok = _bool_match(exp, act)
            checks.append(
                CheckResult(
                    field=fld,
                    status="PASS" if ok else "FAIL",
                    expected=exp,
                    actual=act,
                )
            )

    statuses = [c.status for c in checks if c.status != "SKIP"]
    if not statuses:
        row_status: CheckStatus = "SKIP"
    else:
        row_status = _worst_status(statuses)

    return RowVerification(row=row, status=row_status, checks=checks)


def build_summary(row_results: List[RowVerification]) -> Dict[str, Any]:
    """Aggregate pass/fail counts and mismatches by field."""
    total = len(row_results)
    by_status: Dict[str, int] = {"PASS": 0, "FAIL": 0, "SKIP": 0, "WARN": 0}
    mismatch_by_field: Dict[str, int] = {}

    for rv in row_results:
        by_status[rv.status] = by_status.get(rv.status, 0) + 1
        for chk in rv.checks:
            if chk.status == "FAIL":
                mismatch_by_field[chk.field] = mismatch_by_field.get(chk.field, 0) + 1

    checked = by_status.get("PASS", 0) + by_status.get("FAIL", 0)
    pass_rate = (by_status.get("PASS", 0) / checked * 100.0) if checked else None

    return {
        "rows_total": total,
        "rows_pass": by_status.get("PASS", 0),
        "rows_fail": by_status.get("FAIL", 0),
        "rows_skip": by_status.get("SKIP", 0),
        "rows_warn": by_status.get("WARN", 0),
        "pass_rate_pct": round(pass_rate, 2) if pass_rate is not None else None,
        "mismatch_by_field": mismatch_by_field,
    }
