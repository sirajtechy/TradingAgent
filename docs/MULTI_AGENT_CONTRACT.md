# Multi-Agent Contract

This is a lightweight envelope for adding future agents such as insider, macro, news, sentiment, or event-risk agents without forcing them into the existing TA/FA/Phoenix internals.

## Suggested Envelope

Each adapter should normalize agent output into these fields before orchestration:

```json
{
  "agent_id": "news",
  "as_of_date": "2025-09-30",
  "signal": "bullish",
  "score": 68.0,
  "confidence": "medium",
  "band": "good",
  "abstain": false,
  "reason": null,
  "data_quality": "good",
  "warnings": [],
  "extras": {}
}
```

## Field Guidance

- `agent_id`: Stable identifier such as `technical`, `fundamental`, `phoenix`, `insider`, `macro`, or `news`.
- `as_of_date`: Cutoff date for the signal. Agent inputs must not include post-cutoff data.
- `signal`: Directional normalized signal: `bullish`, `neutral`, or `bearish`.
- `score`: 0-100 score where higher is more constructive unless the adapter explicitly documents otherwise.
- `confidence`: Human label such as `low`, `medium`, or `high`.
- `band`: Agent-specific score band normalized enough for orchestrator rules.
- `abstain`: True when the agent intentionally refuses a directional view.
- `reason`: Short explanation for abstention, errors, or major limitations.
- `data_quality`: Suggested labels: `good`, `fair`, `poor`, or `unknown`.
- `warnings`: Non-fatal issues that should survive into reports.
- `extras`: Agent-specific structured details that should not affect generic orchestration unless an adapter opts in.

## Adapter Pattern

New agents should not couple directly to `FusionResult`. Instead:

1. Keep the agent's native output schema inside its own package.
2. Add a small adapter near the orchestrator or agent boundary.
3. Convert native output into the envelope.
4. Let orchestrator fusion consume normalized envelopes or convert them into `AgentOutput`.
5. Keep agent-specific extras available for reports and audits.

This keeps future agents pluggable while preserving deterministic, reviewable fusion behavior.

## Reference implementation

- `agents/orchestrator/agent_envelope.py` — `envelope_from_technical`, `envelope_from_fundamental`, and `envelope_from_phoenix` map native evaluation dicts to the envelope fields above (fusion still consumes `AgentOutput` internally).
- `agents/orchestrator/modes.py` — `FusionMode` + `fuse_by_mode` routes TA+FA vs Phoenix+FA fusion without duplicating branching logic (`ORCHESTRATOR_MODES.md`).
