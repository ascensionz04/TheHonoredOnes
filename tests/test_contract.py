"""Contract test: every real function returns the same keys as its mock.

Run from the repository root: python -m pytest tests/
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import api, mock  # noqa: E402

CLOCK = 10 * 60 + 25


def _days():
    path = ROOT / "data" / "days.json"
    if not path.exists():          # hour 1: only the mock exists
        return [0]
    days = json.loads(path.read_text())
    scenario = [d["day"] for d in days if d["split"] == "test" and d["scenario"]]
    return scenario or [days[0]["day"]]


def same_keys(real, fake, path="result"):
    """Recursively assert that dict keys match. None and empty lists match anything."""
    if real is None or fake is None:
        return
    if isinstance(fake, dict):
        assert isinstance(real, dict), f"{path}: expected a dict, got {type(real).__name__}"
        assert set(real) == set(fake), (
            f"{path}: keys differ. missing={sorted(map(str, set(fake) - set(real)))} "
            f"extra={sorted(map(str, set(real) - set(fake)))}")
        for key in fake:
            same_keys(real[key], fake[key], f"{path}[{key!r}]")
    elif isinstance(fake, (list, tuple)):
        assert isinstance(real, (list, tuple)), f"{path}: expected a list"
        if fake and isinstance(fake[0], dict):
            for i, item in enumerate(real):
                same_keys(item, fake[0], f"{path}[{i}]")


def _first_alert_state():
    """A state with at least one alert that carries a top action."""
    fallback = None
    for day in _days():
        for clock in range(8 * 60 + 30, 15 * 60, 5):
            state = api.get_state(day, clock)
            found = api.alerts(state)
            if found:
                fallback = fallback or state
                if any(a["top_action"] for a in found):
                    return state
    return fallback


def test_get_state_keys():
    same_keys(api.get_state(_days()[0], CLOCK), mock.get_state(0, CLOCK))


def test_get_state_accepts_hhmm_and_actions():
    day = _days()[0]
    state = api.get_state(day, "10:25", actions=(("open_reserve_room", 10 * 60),))
    assert state["clock"] == CLOCK
    same_keys(state, mock.get_state(0, CLOCK))


def test_forecast_keys():
    state = api.get_state(_days()[0], CLOCK)
    result = api.forecast(state)
    same_keys(result, mock.forecast(None))
    for station in result.values():
        for horizon in station.values():
            assert 0.0 <= horizon["breach_prob"] <= 1.0
            assert horizon["wait_p90"] >= horizon["wait_p50"] >= 0.0


def test_diagnose_keys():
    state = api.get_state(_days()[0], CLOCK)
    result = api.diagnose(state, "consultation")
    same_keys(result, mock.diagnose(None, "consultation"))
    assert result["cause"] in ("demand_surge", "staffing_gap", "slow_processing",
                               "mixed", "peak_load")


def test_alerts_and_recommend_keys():
    state = _first_alert_state()
    assert state is not None, "no alert on any scenario test day: the engine never fires"
    found = api.alerts(state)
    same_keys(found, mock.alerts(None))
    priorities = [a["priority"] for a in found]
    assert priorities == sorted(priorities, reverse=True), "alerts must be highest priority first"
    for alert in found:
        moves = api.recommend(state, alert["station"])
        same_keys(moves, mock.recommend(None, alert["station"]))
        if moves:
            assert alert["top_action"] == moves[0], "top_action is the first item of recommend()"
        else:
            assert alert["top_action"] is None


def test_day_outcome_keys():
    day = _days()[0]
    same_keys(api.day_outcome(day), mock.day_outcome(0))
    same_keys(api.day_outcome(day, actions=(("open_reserve_room", 10 * 60),)), mock.day_outcome(0))
