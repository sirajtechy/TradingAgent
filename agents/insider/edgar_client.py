"""SEC EDGAR Form 4 insider sales — Ticker → CIK → Form 4s → XML → sum code-S rows."""

from __future__ import annotations

import os
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import requests

from .exceptions import InsiderDataError
from .models import InsiderSnapshot, InsiderTrade

SEC_DATA_BASE = "https://data.sec.gov"
SEC_ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"
COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

_MAX_FORM4_FETCH = 20
_CIK_BY_TICKER: Optional[Dict[str, int]] = None


def _user_agent() -> str:
    return os.getenv("SEC_EDGAR_USER_AGENT", "MyTradingSpace research@example.com").strip()


def _session() -> requests.Session:
    sess = requests.Session()
    sess.headers.update(
        {
            "User-Agent": _user_agent(),
            "Accept-Encoding": "gzip, deflate",
            "Host": "data.sec.gov",
        }
    )
    return sess


def _archives_session() -> requests.Session:
    sess = requests.Session()
    sess.headers.update(
        {
            "User-Agent": _user_agent(),
            "Accept-Encoding": "gzip, deflate",
        }
    )
    return sess


def _load_cik_map() -> Dict[str, int]:
    global _CIK_BY_TICKER
    if _CIK_BY_TICKER is not None:
        return _CIK_BY_TICKER

    resp = _archives_session().get(COMPANY_TICKERS_URL, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    mapping: Dict[str, int] = {}
    for item in payload.values():
        if not isinstance(item, dict):
            continue
        ticker = str(item.get("ticker") or "").upper()
        cik = item.get("cik_str") or item.get("cik")
        if ticker and cik is not None:
            mapping[ticker] = int(cik)
    _CIK_BY_TICKER = mapping
    return mapping


def resolve_cik(ticker: str) -> Optional[int]:
    return _load_cik_map().get(ticker.strip().upper())


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _find_child_text(parent: ET.Element, local_name: str) -> Optional[str]:
    for child in parent.iter():
        if _local(child.tag) != local_name:
            continue
        if child.text and child.text.strip():
            return child.text.strip()
        for sub in child:
            if _local(sub.tag) == "value" and sub.text and sub.text.strip():
                return sub.text.strip()
    return None


def _parse_form4_xml(xml_text: str, *, filing_date: date) -> List[InsiderTrade]:
    """
    Parse Form 4 XML for non-derivative common-stock sales only.

    Include a row when:
      - node is nonDerivativeTransaction
      - transactionCoding/transactionCode == \"S\"
      - securityTitle contains \"Common Stock\"
      - shares > 0 and price > 0
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    owner_name = ""
    owner_title = ""
    for node in root.iter():
        ln = _local(node.tag)
        if ln == "rptOwnerName" and node.text:
            owner_name = node.text.strip()
        elif ln in ("officerTitle", "directorTitle", "otherText") and node.text and not owner_title:
            owner_title = node.text.strip()

    trades: List[InsiderTrade] = []
    for node in root.iter():
        if _local(node.tag) != "nonDerivativeTransaction":
            continue

        tx_code = (_find_child_text(node, "transactionCode") or "").upper()
        if tx_code != "S":
            continue

        security_title = _find_child_text(node, "securityTitle") or ""
        if "common stock" not in security_title.lower():
            continue

        tx_date_raw = _find_child_text(node, "transactionDate") or _find_child_text(node, "deemedExecutionDate")
        tx_date = _parse_date(tx_date_raw) or filing_date

        shares = _safe_float(_find_child_text(node, "transactionShares")) or 0.0
        price = _safe_float(_find_child_text(node, "transactionPricePerShare"))
        if shares <= 0 or price is None or price <= 0:
            continue

        trades.append(
            InsiderTrade(
                filing_date=filing_date,
                transaction_date=tx_date,
                owner_name=owner_name,
                title=owner_title,
                transaction_type="sale",
                shares=shares,
                price=price,
                value=round(shares * price, 2),
            )
        )

    return trades


def _dedupe_trades(trades: List[InsiderTrade]) -> List[InsiderTrade]:
    """Drop duplicate rows from original + amended Form 4 filings."""
    best: Dict[Tuple[str, Optional[date], float, Optional[float], str], InsiderTrade] = {}
    for trade in trades:
        key = (
            trade.owner_name,
            trade.transaction_date,
            trade.shares,
            trade.price,
            trade.transaction_type,
        )
        existing = best.get(key)
        if existing is None or trade.filing_date > existing.filing_date:
            best[key] = trade
    return list(best.values())


def _filter_trades_for_as_of(trades: List[InsiderTrade], as_of_date: date) -> List[InsiderTrade]:
    return [
        t
        for t in trades
        if t.transaction_date is None or t.transaction_date <= as_of_date
    ]


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(str(value).split(" ")[0][:10], "%Y-%m-%d").date()
    except (ValueError, IndexError):
        return None


def _safe_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _recent_form4_filings(
    cik: int,
    as_of_date: date,
    lookback_days: int,
) -> List[Tuple[str, date]]:
    """Return (accession_number, filing_date) for recent Form 4 within the window."""
    cik_padded = str(cik).zfill(10)
    url = f"{SEC_DATA_BASE}/submissions/CIK{cik_padded}.json"
    resp = _session().get(url, timeout=30)
    resp.raise_for_status()
    doc = resp.json()

    recent = (doc.get("filings") or {}).get("recent") or {}
    forms = recent.get("form") or []
    dates = recent.get("filingDate") or []
    accessions = recent.get("accessionNumber") or []

    cutoff = as_of_date - timedelta(days=lookback_days)
    out: List[Tuple[str, date]] = []
    for form, filing_date_raw, accession in zip(forms, dates, accessions):
        if str(form).upper() not in ("4", "4/A"):
            continue
        filing_date = _parse_date(filing_date_raw)
        if filing_date is None or filing_date > as_of_date or filing_date < cutoff:
            continue
        if not accession:
            continue
        out.append((str(accession), filing_date))
        if len(out) >= _MAX_FORM4_FETCH:
            break
    return out


def _form4_xml_url(cik: int, accession: str) -> str:
    """
    SEC EDGAR archive layout:
    https://www.sec.gov/Archives/edgar/data/{cikNoZeros}/{accClean}/{accClean}.xml
    """
    cik_path = str(int(cik))
    acc_clean = accession.replace("-", "")
    return f"{SEC_ARCHIVES_BASE}/{cik_path}/{acc_clean}/{acc_clean}.xml"


def _form4_xml_url_candidates(cik: int, accession: str) -> List[str]:
    cik_path = str(int(cik))
    acc_clean = accession.replace("-", "")
    base = f"{SEC_ARCHIVES_BASE}/{cik_path}/{acc_clean}"
    return [
        f"{base}/{acc_clean}.xml",
        f"{base}/form4.xml",
    ]


def _resolve_form4_xml_urls(cik: int, accession: str, sess: requests.Session) -> List[str]:
    candidates = _form4_xml_url_candidates(cik, accession)
    acc_clean = accession.replace("-", "")
    base = f"{SEC_ARCHIVES_BASE}/{str(int(cik))}/{acc_clean}"
    try:
        resp = sess.get(f"{base}/index.json", timeout=30)
        if resp.status_code == 200:
            items = (resp.json().get("directory") or {}).get("item") or []
            names = [
                str(item.get("name"))
                for item in items
                if isinstance(item, dict) and item.get("name")
            ]
            for prefer in ("form4.xml", "primary_doc.xml", "doc4.xml"):
                url = f"{base}/{prefer}"
                if prefer in names and url not in candidates:
                    candidates.append(url)
            for name in names:
                if name.endswith(".xml") and "xsl" not in name.lower():
                    url = f"{base}/{name}"
                    if url not in candidates:
                        candidates.append(url)
    except (requests.RequestException, ValueError, TypeError):
        pass
    return candidates


def _fetch_form4_xml(cik: int, accession: str, sess: requests.Session) -> Optional[str]:
    for url in _resolve_form4_xml_urls(cik, accession, sess):
        try:
            resp = sess.get(url, timeout=30)
            if resp.status_code != 200:
                continue
            body = resp.text.lstrip()
            if body.startswith("<?xml") or "<ownershipDocument" in body[:500]:
                return resp.text
        except requests.RequestException:
            continue
    return None


def build_snapshot(
    ticker: str,
    as_of_date: date,
    *,
    lookback_days: int = 90,
) -> InsiderSnapshot:
    """
    Ticker → CIK → recent Form 4 accessions → parse XML → common-stock code-S sales.
    """
    tk = ticker.strip().upper()
    warnings: List[str] = []
    cik = resolve_cik(tk)
    if cik is None:
        return InsiderSnapshot(
            ticker=tk,
            as_of_date=as_of_date,
            trades=[],
            data_sources=[],
            warnings=[f"No SEC CIK mapping for ticker {tk}"],
        )

    try:
        filings = _recent_form4_filings(cik, as_of_date, lookback_days)
    except Exception as exc:
        raise InsiderDataError(f"SEC submissions fetch failed for {tk}: {exc}") from exc

    if not filings:
        warnings.append(f"No SEC Form 4 filings for {tk} in last {lookback_days}d")
        return InsiderSnapshot(
            ticker=tk,
            as_of_date=as_of_date,
            trades=[],
            data_sources=["sec:submissions"],
            warnings=warnings,
        )

    sess = _archives_session()
    all_trades: List[InsiderTrade] = []
    fetch_failures = 0
    for accession, filing_date in filings:
        xml_text = _fetch_form4_xml(cik, accession, sess)
        if xml_text is None:
            fetch_failures += 1
            warnings.append(f"Form 4 XML fetch failed: {accession}")
            continue
        all_trades.extend(_parse_form4_xml(xml_text, filing_date=filing_date))
        time.sleep(0.12)

    raw_count = len(all_trades)
    all_trades = _filter_trades_for_as_of(all_trades, as_of_date)
    dropped_future = raw_count - len(all_trades)

    pre_dedupe = len(all_trades)
    all_trades = _dedupe_trades(all_trades)
    dropped_dupes = pre_dedupe - len(all_trades)

    if dropped_future:
        warnings.append(f"Dropped {dropped_future} sale(s) with transaction date after {as_of_date}")
    if dropped_dupes:
        warnings.append(f"Deduplicated {dropped_dupes} repeated Form 4 sale(s)")
    if fetch_failures:
        warnings.append(f"Could not fetch XML for {fetch_failures} Form 4 filing(s)")

    sources = ["sec:form4", "sec:submissions"] if all_trades else ["sec:submissions"]
    if not all_trades and not fetch_failures:
        warnings.append(
            f"Form 4 filings found ({len(filings)}) but no common-stock code-S sales with price"
        )

    return InsiderSnapshot(
        ticker=tk,
        as_of_date=as_of_date,
        trades=all_trades,
        data_sources=sources,
        warnings=warnings,
    )
