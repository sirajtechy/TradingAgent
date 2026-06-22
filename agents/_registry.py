"""
Agent registry — isolated agents expose analyze + envelope only.

Orchestrator fusion consumes native outputs via existing ``fuse_by_mode``;
this registry is for tooling, logging, and future multi-agent expansion.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from core.contracts.envelope import (
    envelope_from_fundamental,
    envelope_from_geopolitics,
    envelope_from_insider,
    envelope_from_macro,
    envelope_from_market_summary,
    envelope_from_news,
    envelope_from_phoenix,
    envelope_from_sentiment,
)

from agents.technical.envelope import envelope_from_unified_technical
from agents.technical.service import analyze_technical

AnalyzeFn = Callable[..., Dict[str, Any]]
EnvelopeFn = Callable[..., Dict[str, Any]]


@dataclass(frozen=True)
class AgentSpec:
    agent_id: str
    analyze: AnalyzeFn
    to_envelope: EnvelopeFn
    description: str


def _phoenix_analyze(*, ticker: str, as_of_date: str, **_: Any) -> Dict[str, Any]:
    from agents.phoenix.service import analyze_ticker

    return analyze_ticker(ticker=ticker, as_of_date=as_of_date)


def _fundamental_analyze(
    *, ticker: str, as_of_date: str, data_source: str = "yfinance", **_: Any
) -> Dict[str, Any]:
    from agents.fundamental.service import analyze_ticker

    return analyze_ticker(ticker=ticker, as_of_date=as_of_date, data_source=data_source)


def _macro_analyze(*, as_of_date: str, ticker: str = "", **_: Any) -> Dict[str, Any]:
    from agents.macro.service import analyze_market

    return analyze_market(as_of_date=as_of_date)


def _market_summary_analyze(*, as_of_date: str, ticker: str = "", **_: Any) -> Dict[str, Any]:
    from agents.market_summary.service import analyze_market

    return analyze_market(as_of_date=as_of_date)


def _news_analyze(*, ticker: str, as_of_date: str, **_: Any) -> Dict[str, Any]:
    from agents.news.service import analyze_ticker

    return analyze_ticker(ticker=ticker, as_of_date=as_of_date)


def _insider_analyze(*, ticker: str, as_of_date: str, **_: Any) -> Dict[str, Any]:
    from agents.insider.service import analyze_ticker

    return analyze_ticker(ticker=ticker, as_of_date=as_of_date)


def _sentiment_analyze(*, ticker: str, as_of_date: str, **_: Any) -> Dict[str, Any]:
    from agents.sentiment.service import analyze_ticker

    return analyze_ticker(ticker=ticker, as_of_date=as_of_date)


def _geopolitics_analyze(*, as_of_date: str, ticker: str = "", **_: Any) -> Dict[str, Any]:
    from agents.geopolitics.service import analyze_market

    return analyze_market(as_of_date=as_of_date)


def _technical_analyze(
    *, ticker: str, as_of_date: str, strategy_profile: str = "blend", **kwargs: Any
) -> Dict[str, Any]:
    return analyze_technical(
        ticker=ticker,
        as_of_date=as_of_date,
        strategy_profile=strategy_profile,
        fund_result=kwargs.get("fund_result"),
    )


AGENT_REGISTRY: Dict[str, AgentSpec] = {
    "technical": AgentSpec(
        agent_id="technical",
        analyze=_technical_analyze,
        to_envelope=envelope_from_unified_technical,
        description="Unified technical agent (Phoenix + 4 trader strategies + fusion)",
    ),
    "phoenix": AgentSpec(
        agent_id="phoenix",
        analyze=_phoenix_analyze,
        to_envelope=envelope_from_phoenix,
        description="Phoenix pattern/stage technical agent",
    ),
    "fundamental": AgentSpec(
        agent_id="fundamental",
        analyze=_fundamental_analyze,
        to_envelope=envelope_from_fundamental,
        description="Fundamental scoring agent",
    ),
    "macro": AgentSpec(
        agent_id="macro",
        analyze=_macro_analyze,
        to_envelope=envelope_from_macro,
        description="Macroeconomics session agent (FRED)",
    ),
    "market_summary": AgentSpec(
        agent_id="market_summary",
        analyze=_market_summary_analyze,
        to_envelope=envelope_from_market_summary,
        description="Market-wide summary (VIX, sectors, macro)",
    ),
    "news": AgentSpec(
        agent_id="news",
        analyze=_news_analyze,
        to_envelope=envelope_from_news,
        description="News Analyst (FMP headlines, grades, PT)",
    ),
    "insider": AgentSpec(
        agent_id="insider",
        analyze=_insider_analyze,
        to_envelope=envelope_from_insider,
        description="Insider Trades (FMP insider activity)",
    ),
    "sentiment": AgentSpec(
        agent_id="sentiment",
        analyze=_sentiment_analyze,
        to_envelope=envelope_from_sentiment,
        description="Multi-dimension sentiment aggregator",
    ),
    "geopolitics": AgentSpec(
        agent_id="geopolitics",
        analyze=_geopolitics_analyze,
        to_envelope=envelope_from_geopolitics,
        description="Geopolitical risk scanner (FMP + LLM)",
    ),
}


def get_agent(agent_id: str) -> AgentSpec:
    key = agent_id.strip().lower()
    if key not in AGENT_REGISTRY:
        raise KeyError(f"Unknown agent_id {agent_id!r}. Known: {sorted(AGENT_REGISTRY)}")
    return AGENT_REGISTRY[key]


def analyze_and_envelope(
    agent_id: str,
    *,
    ticker: str,
    as_of_date: str,
    **analyze_kwargs: Any,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    spec = get_agent(agent_id)
    native = spec.analyze(ticker=ticker, as_of_date=as_of_date, **analyze_kwargs)
    envelope = spec.to_envelope(native, as_of_date=as_of_date, agent_id=spec.agent_id)
    return native, envelope
