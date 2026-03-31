from fundamental_agent.graph import build_graph
from fundamental_agent.reporting import build_text_report

from tests.fixtures import make_snapshot


class StaticProvider:
    def build_snapshot(self, request):
        snapshot = make_snapshot()
        return snapshot


def test_graph_runs_end_to_end_with_static_provider():
    snapshot = make_snapshot()
    graph = build_graph(StaticProvider())
    state = graph.invoke({"request": snapshot.request})

    assert "evaluation" in state
    assert state["evaluation"]["company"]["ticker"] == "AAPL"
    assert "report" in state["evaluation"]
    assert "Experimental score" in state["evaluation"]["report"]


def test_report_builder_mentions_shariah_status():
    snapshot = make_snapshot()
    from fundamental_agent.rules import evaluate_snapshot

    result = evaluate_snapshot(snapshot, include_experimental_score=True)
    report = build_text_report(result)

    assert "Shariah" in report
    assert "pass" in report