"""
Agent registry — isolated agents expose analyze + envelope only.

Orchestrator fusion consumes native outputs via existing ``fuse_by_mode``;
this registry is for tooling, logging, and future multi-agent expansion.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from core.contracts.envelope import envelope_from_fundamental, envelope_from_phoenix

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


AGENT_REGISTRY: Dict[str, AgentSpec] = {
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
