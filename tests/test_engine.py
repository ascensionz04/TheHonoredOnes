"""Simulator sanity, determinism and demo-day checks (TRD section 11).

Run from the repository root: python -m pytest tests/
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import api, sim  # noqa: E402

P = sim.params()
NORMAL = [d for d in sim.day_ids() if sim.day_spec(d)["scenario"] == "normal"]
DEMO = ROOT / "data" / "demo_days.json"


def test_day_specs():
    days = [sim.day_spec(d) for d in sim.day_ids() if d < 1000]
    assert len(days) == 90
    assert sum(d["scenario"] == "normal" for d in days) == 42
    for kind in sim.CAUSES:
        assert sum(d["scenario"] == kind for d in days) == 16
        for split in ("train", "tune", "test"):     # every type in every split
            assert any(d["scenario"] == kind and d["split"] == split for d in days)
    assert [sum(d["split"] == s for d in days) for s in ("train", "tune", "test")] == [60, 10, 20]


def test_patient_count_matches_arrival_profile():
    expected = sum(P.hourly.values())      # average weekday
    counts = [api.day_outcome(d)["patients"] for d in NORMAL]
    assert abs(sum(counts) / len(counts) - expected) < 0.1 * expected


def test_no_negative_waits_and_every_patient_accounted_for():
    for day in NORMAL[:10] + sim.day_ids("test"):
        r = sim.day_run(day)
        assert all(start >= arrive and end > start for _, _, arrive, start, end, _ in r.rows)
        # the day run serves until the clinic is empty, so every patient registers once
        registered = [row[0] for row in r.rows if row[1] == 0]
        assert sorted(registered) == list(range(r.outcome["patients"]))
        assert r.waiting[-1].sum() == 0 and r.in_service[-1].sum() == 0


def test_consultation_is_the_busiest_station_at_peak():
    peak = max(P.hourly, key=P.hourly.get) * 60 - P.open
    busy = [0.0] * 5
    for day in NORMAL:
        r = sim.day_run(day)
        for si in range(5):
            busy[si] += r.in_service[peak:peak + 60, si].mean() / P.roster[si] / len(NORMAL)
    assert busy[1] == max(busy)
    assert 0.7 < busy[1] < 0.95


def test_one_day_simulates_in_under_a_second():
    import time
    sim._day_run.cache_clear()
    t0 = time.perf_counter()
    sim.day_run(NORMAL[0])
    assert time.perf_counter() - t0 < 1.0


def test_deterministic():
    day = sim.day_ids("test")[1]
    actions = (("open_reserve_room", 10 * 60 + 30),)
    first = api.get_state(day, "11:00", actions)
    alerts_first = api.alerts(first)
    sim._day_run.cache_clear()
    second = api.get_state(day, "11:00", actions)
    assert first == second
    assert api.forecast(first) == api.forecast(second)
    assert alerts_first == api.alerts(second)
    assert api.day_outcome(day, actions) == api.day_outcome(day, actions)


def test_state_is_a_prefix_of_the_day():
    """An action cannot change what happened before it started."""
    day = sim.day_ids("test")[1]
    later = (("clerk_to_pharmacy", 12 * 60),)
    assert api.get_state(day, "11:00") == api.get_state(day, "11:00", later)
    before = api.get_state(day, "11:55")
    after = api.get_state(day, "11:55", later)
    assert {k: v for k, v in before.items() if k != "actions"} == \
           {k: v for k, v in after.items() if k != "actions"}


def test_action_changes_staff_and_expires():
    day = NORMAL[0]
    start = 10 * 60
    on = api.get_state(day, start + 30, (("open_reserve_room", start),))
    off = api.get_state(day, start + 60, (("open_reserve_room", start),))
    assert on["stations"]["consultation"]["staff_on"] == P.roster[1] + 1
    assert off["stations"]["consultation"]["staff_on"] == P.roster[1]
    moved = api.get_state(day, start + 30, (("clerk_to_pharmacy", start),))
    assert moved["stations"]["registration"]["staff_on"] == P.roster[0] - 1
    assert moved["stations"]["pharmacy"]["staff_on"] == P.roster[4] + 1


def test_unknown_action_is_rejected():
    with pytest.raises(ValueError):
        api.get_state(NORMAL[0], "10:00", (("move_a_doctor", 600),))


def test_state_does_not_reveal_the_scenario():
    state = api.get_state(sim.day_ids("test")[1], "11:00")
    assert "scenario" not in state and "events" not in state


@pytest.mark.skipif(not DEMO.exists(), reason="demo days not chosen yet")
def test_demo_days_replay_open_to_close_and_show_their_cause():
    demo = json.loads(DEMO.read_text(encoding="utf-8"))
    assert len(demo) == 4
    for entry in demo:
        causes = set()
        for clock in range(P.open, P.close + 1, P.tick):
            state = api.get_state(entry["day"], clock)
            api.forecast(state)
            for alert in api.alerts(state):
                api.recommend(state, alert["station"])
                causes.add(alert["cause"])
        api.day_outcome(entry["day"])
        if entry["expected_cause"]:
            assert entry["expected_cause"] in causes, f"{entry['name']}: saw {sorted(causes)}"
