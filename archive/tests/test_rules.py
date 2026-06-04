from agents.fundamental.rules import evaluate_snapshot

from tests.fixtures import make_snapshot


def test_framework_math_for_fixture_snapshot():
    snapshot = make_snapshot()
    result = evaluate_snapshot(snapshot, include_experimental_score=True)

    piotroski = result["frameworks"]["piotroski"]
    assert piotroski["score"] == 6
    assert piotroski["max_score"] == 9

    altman = result["frameworks"]["altman"]
    assert altman["applicable"] is True
    assert 7.8 < altman["z_score"] < 8.0
    assert altman["zone"] == "safe"

    graham = result["frameworks"]["graham"]
    assert graham["applicable"] is True
    assert graham["passes"] == 4
    assert graham["dividend_streak_years"] == 20

    greenblatt = result["frameworks"]["greenblatt"]
    assert greenblatt["applicable"] is True
    assert greenblatt["earnings_yield_pct"] > 4.0
    assert greenblatt["return_on_capital_pct"] > 500.0

    lynch = result["frameworks"]["lynch"]
    assert lynch["applicable"] is True
    assert 0.5 < lynch["fair_value_ratio"] < 0.6

    shariah = result["frameworks"]["shariah"]
    assert shariah["status"] == "pass"
    assert shariah["debt_ratio"] < 0.05


def test_experimental_score_is_available_and_bounded():
    snapshot = make_snapshot()
    result = evaluate_snapshot(snapshot, include_experimental_score=True)
    score = result["experimental_score"]

    assert score["available"] is True
    assert 0.0 <= score["score"] <= 100.0
    assert score["confidence"] == "high"
