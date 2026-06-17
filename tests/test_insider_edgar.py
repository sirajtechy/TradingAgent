from __future__ import annotations

from datetime import date

from agents.insider.edgar_client import (
    _dedupe_trades,
    _form4_xml_url,
    _parse_form4_xml,
)


SAMPLE_FORM4 = """<?xml version="1.0"?>
<ownershipDocument>
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerName>Jane Smith</rptOwnerName>
    </reportingOwnerId>
    <reportingOwnerRelationship>
      <officerTitle>Chief Executive Officer</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <securityTitle><value>Common Stock</value></securityTitle>
      <transactionDate><value>2026-05-20</value></transactionDate>
      <transactionCoding>
        <transactionCode>P</transactionCode>
      </transactionCoding>
      <transactionAmounts>
        <transactionShares><value>10000</value></transactionShares>
        <transactionPricePerShare><value>50.00</value></transactionPricePerShare>
      </transactionAmounts>
    </nonDerivativeTransaction>
    <nonDerivativeTransaction>
      <securityTitle><value>Common Stock</value></securityTitle>
      <transactionDate><value>2026-05-22</value></transactionDate>
      <transactionCoding>
        <transactionCode>S</transactionCode>
      </transactionCoding>
      <transactionAmounts>
        <transactionShares><value>5000</value></transactionShares>
        <transactionPricePerShare><value>48.50</value></transactionPricePerShare>
      </transactionAmounts>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>
"""


def test_parse_form4_xml_extracts_only_code_s_common_stock_sales():
    trades = _parse_form4_xml(SAMPLE_FORM4, filing_date=date(2026, 5, 25))
    assert len(trades) == 1
    assert trades[0].owner_name == "Jane Smith"
    assert trades[0].title == "Chief Executive Officer"
    assert trades[0].transaction_type == "sale"
    assert trades[0].shares == 5000
    assert trades[0].price == 48.50
    assert trades[0].value == 242500.0


def test_skips_non_common_stock_and_zero_price():
    xml = """<?xml version="1.0"?>
<ownershipDocument>
  <reportingOwner><reportingOwnerId><rptOwnerName>Insider</rptOwnerName></reportingOwnerId></reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <securityTitle><value>Restricted Stock Unit</value></securityTitle>
      <transactionCoding><transactionCode>S</transactionCode></transactionCoding>
      <transactionAmounts>
        <transactionShares><value>1000</value></transactionShares>
        <transactionPricePerShare><value>10</value></transactionPricePerShare>
      </transactionAmounts>
    </nonDerivativeTransaction>
    <nonDerivativeTransaction>
      <securityTitle><value>Common Stock</value></securityTitle>
      <transactionCoding><transactionCode>S</transactionCode></transactionCoding>
      <transactionAmounts>
        <transactionShares><value>100</value></transactionShares>
        <transactionPricePerShare><value>0</value></transactionPricePerShare>
      </transactionAmounts>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>"""
    trades = _parse_form4_xml(xml, filing_date=date(2026, 5, 25))
    assert trades == []


def test_form4_xml_url_uses_accession_pattern():
    url = _form4_xml_url(320193, "0001140361-26-023363")
    assert url.endswith("/320193/000114036126023363/000114036126023363.xml")


def test_dedupe_trades_keeps_latest_filing():
    from agents.insider.models import InsiderTrade

    first = InsiderTrade(
        filing_date=date(2026, 6, 8),
        transaction_date=date(2026, 6, 8),
        owner_name="Insider A",
        title="CEO",
        transaction_type="sale",
        shares=25000,
        price=10.0,
        value=250000.0,
    )
    amended = InsiderTrade(
        filing_date=date(2026, 6, 10),
        transaction_date=date(2026, 6, 8),
        owner_name="Insider A",
        title="CEO",
        transaction_type="sale",
        shares=25000,
        price=10.0,
        value=250000.0,
    )
    deduped = _dedupe_trades([first, amended])
    assert len(deduped) == 1
    assert deduped[0].filing_date == date(2026, 6, 10)
