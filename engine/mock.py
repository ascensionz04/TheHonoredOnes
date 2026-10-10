"""Fake engine outputs in the agreed contract shapes (TRD section 8).

Each demo day follows a scripted story so the app can be built and rehearsed
before the real simulator lands. Numbers are illustrative, not simulated.
Day ids: 0 ordinary busy day, 1 doctor called away, 2 holiday rush,
3 pharmacy system slow. Any other id maps onto these four.
"""

from functools import lru_cache
from math import exp
from pathlib import Path

import yaml

STATIONS = ["registration", "consultation", "laboratory", "imaging", "pharmacy"]
CAUSES = ["demand_surge", "staffing_gap", "slow_processing"]

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"
with open(_CONFIG_PATH, encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)


def _hhmm(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


OPEN = _hhmm(CONFIG["open"])
CLOSE = _hhmm(CONFIG["close"])
LIMIT = CONFIG["wait_limit_min"]
ROSTER = {s: CONFIG["stations"][s]["staff"] for s in STATIONS}
SERVICE = {s: CONFIG["stations"][s]["service_min"] for s in STATIONS}
SHARE = {s: CONFIG["stations"][s]["share"] for s in STATIONS}
WEIGHT = {s: CONFIG["stations"][s]["weight"] for s in STATIONS}
MOVES = {m["id"]: m for m in CONFIG["allowed_moves"]}

# Wait profile of a normal day: off-peak level, peak height, peak centre, width.
_BASE = {
    "registration": (3, 6, 600, 60),
    "consultation": (8, 14, 630, 70),
    "laboratory": (3, 5, 660, 70),
    "imaging": (4, 6, 660, 80),
    "pharmacy": (5, 7, 690, 70),
}

# Per day: scripted extra wait (station, height, centre, width) and the
# scenario behind it (cause, station, start, end, strength).
_DAYS = {
    0: {"bumps": [("consultation", 7, 630, 20)], "scenarios": []},
    1: {
        "bumps": [("consultation", 30, 670, 35), ("pharmacy", 22, 700, 30)],
        "scenarios": [("staffing_gap", "consultation", 600, 720, 1),
                      ("demand_surge", "pharmacy", 650, 750, 1.5)],
    },
    2: {
        "bumps": [("registration", 34, 540, 35), ("consultation", 26, 620, 40)],
        "scenarios": [("demand_surge", "registration", 480, 600, 1.8),
                      ("demand_surge", "consultation", 540, 690, 1.8)],
    },
    3: {
        "bumps": [("pharmacy", 32, 830, 30)],
        "scenarios": [("slow_processing", "pharmacy", 780, 870, 1.5)],
    },
}

# Action effect: target station, share of excess wait removed, donor station.
_EFFECT = {
    "open_reserve_room": ("consultation", 0.7, None),
    "nurse_to_lab": ("laboratory", 0.6, None),
    "clerk_to_pharmacy": ("pharmacy", 0.55, "registration"),
    "fast_track_pharmacy": ("pharmacy", 0.4, None),
}
_DURATION = 60


def _gauss(t, height, centre, width):
    return height * exp(-0.5 * ((t - centre) / width) ** 2)


def _spec(day):
    return _DAYS[int(day) % 4]


def _base_wait(station, t):
    low, peak, centre, width = _BASE[station]
    return low + _gauss(t, peak, centre, width)


def _ramp(t, start):
    """0 before an action, 1 while in force, decaying after it ends."""
    if t < start:
        return 0.0
    if t < start + 20:
        return (t - start) / 20
    if t < start + _DURATION:
        return 1.0
    return exp(-(t - start - _DURATION) / 30)


def _in_force(t, start):
    return start <= t < start + _DURATION


def _wait(day, station, t, actions):
    w = _base_wait(station, t)
    for st, h, c, wd in _spec(day)["bumps"]:
        if st == station:
            w += _gauss(t, h, c, wd)
    floor = _BASE[station][0]
    for action_id, start in actions:
        target, strength, donor = _EFFECT[action_id]
        if target == station:
            w -= strength * _ramp(t, start) * max(0.0, w - floor)
        if donor == station and _in_force(t, start):
            w += 4 * min(1.0, (t - start) / 20)
    return max(0.0, w)


def _active_scenarios(day, station, t, pad_before=0, pad_after=0):
    return [s for s in _spec(day)["scenarios"]
            if s[1] == station and s[2] - pad_before <= t < s[3] + pad_after]


def _staff_on(day, station, t, actions):
    n = ROSTER[station]
    for cause, st, start, end, _ in _active_scenarios(day, station, t):
        if cause == "staffing_gap":
            n -= 1
    for action_id, start in actions:
        if not _in_force(t, start):
            continue
        move = MOVES[action_id]
        if move.get("to") == station:
            n += 1
        if move.get("from") == station:
            n -= 1
    return max(1, n)


def _service_min(day, station, t, actions):
    s = SERVICE[station]
    for cause, st, start, end, strength in _active_scenarios(day, station, t):
        if cause == "slow_processing":
            s *= strength
    for action_id, start in actions:
        move = MOVES[action_id]
        if move.get("station") == station and _in_force(t, start):
            s *= move.get("service_scale", 1.0)
    return s


def _arrival_rate(t):
    """Patients per hour arriving at registration."""
    a = CONFIG["arrivals_per_hour"]
    peak = _hhmm(a["peak_from"]) <= t < _hhmm(a["peak_to"])
    return a["peak"] if peak else a["default"]


def _arrivals_30m(day, station, t):
    rate = _arrival_rate(t) * SHARE[station] / 2
    for cause, st, start, end, strength in _active_scenarios(day, station, t):
        if cause == "demand_surge":
            rate *= strength
    return int(round(rate))


def _norm_actions(actions):
    return tuple((str(a), int(s)) for a, s in actions)


@lru_cache(maxsize=4096)
def _get_state(day, clock, actions):
    stations = {}
    for st in STATIONS:
        wait = _wait(day, st, clock, actions)
        staff = _staff_on(day, st, clock, actions)
        service = _service_min(day, st, clock, actions)
        waiting = int(round(wait * staff / service))
        stations[st] = {
            "waiting": waiting,
            "in_service": staff if waiting else max(0, staff - 1),
            "staff_on": staff,
            "wait_now_min": round(wait, 1),
            "arrivals_30m": _arrivals_30m(day, st, clock),
            "service_min_30m": round(service, 1),
        }
    return {"day": day, "clock": clock, "actions": actions, "stations": stations}


def get_state(day, clock, actions=()):
    clock = max(OPEN, min(CLOSE, int(clock)))
    return _get_state(int(day), clock, _norm_actions(actions))


def _breach_prob(p50):
    return round(1 / (1 + exp(-(p50 - LIMIT) / 3.5)), 2)


def _forecast_at(day, clock, actions):
    out = {}
    for st in STATIONS:
        out[st] = {}
        for h in (15, 30, 60):
            p50 = _wait(day, st, clock + h, actions)
            out[st][h] = {"wait_p50": round(p50, 1),
                          "wait_p90": round(p50 * 1.25 + 3, 1),
                          "breach_prob": _breach_prob(p50)}
    return out


def forecast(state):
    return _forecast_at(state["day"], state["clock"], state["actions"])


def diagnose(state, station):
    day, clock, actions = state["day"], state["clock"], state["actions"]
    excess = max(0.0, _wait(day, station, clock + 60, actions)
                 - _base_wait(station, clock + 60))
    contributions = {c: 0.5 for c in CAUSES}
    live = _active_scenarios(day, station, clock + 30, pad_before=60, pad_after=30)
    if live:
        contributions[live[0][0]] = round(excess, 1)
    ranked = sorted(contributions.values(), reverse=True)
    if ranked[0] < 3:
        cause = "peak_load"
    elif ranked[1] >= 0.8 * ranked[0]:
        cause = "mixed"
    else:
        cause = max(contributions, key=contributions.get)
    return {"cause": cause, "contributions": contributions}


def recommend(state, station):
    day, clock, actions = state["day"], state["clock"], state["actions"]
    active = {a for a, s in actions if _in_force(clock, s)}
    t = clock + 60
    before = {st: _wait(day, st, t, actions) for st in STATIONS}
    out = []
    for action_id, move in MOVES.items():
        if action_id in active:
            continue
        trial = actions + ((action_id, clock),)
        after = {st: _wait(day, st, t, trial) for st in STATIONS}
        donor = move.get("from") if move.get("from") in STATIONS else None
        patient_min = sum((before[st] - after[st]) * _staff_on(day, st, t, trial)
                          / _service_min(day, st, t, trial) * 30 for st in STATIONS)
        if patient_min <= 0 or (donor and after[donor] > LIMIT):
            continue
        out.append({
            "action_id": action_id,
            "label": move["label"],
            "wait_saved_min": round(before[station] - after[station], 1),
            "donor_station": donor,
            "donor_wait_added_min": round(after[donor] - before[donor], 1) if donor else 0.0,
            "total_wait_saved_patient_min": round(patient_min, 1),
            "bottleneck_after": max(STATIONS, key=lambda st: after[st]),
        })
    out.sort(key=lambda r: (r["wait_saved_min"], r["total_wait_saved_patient_min"]),
             reverse=True)
    return out


def _raised(fc, station):
    raise_at = CONFIG["alert"]["raise_at"]
    return max(fc[station][30]["breach_prob"], fc[station][60]["breach_prob"]) >= raise_at


def alerts(state):
    day, clock, actions = state["day"], state["clock"], state["actions"]
    if clock >= CLOSE:
        return []
    now = _forecast_at(day, clock, actions)
    prev = _forecast_at(day, max(OPEN, clock - 5), actions)
    out = []
    for st in STATIONS:
        if not (_raised(now, st) and _raised(prev, st)):
            continue
        to_breach = next((h for h in range(0, 65, 5)
                          if _wait(day, st, clock + h, actions) > LIMIT), None)
        s = state["stations"][st]
        affected = s["waiting"] + _arrivals_30m(day, st, clock) * 2
        bp = max(now[st][30]["breach_prob"], now[st][60]["breach_prob"])
        over = max(0.0, now[st][60]["wait_p50"] - LIMIT)
        recs = recommend(state, st)
        d = diagnose(state, st)
        out.append({
            "station": st,
            "breach_prob": bp,
            "minutes_to_breach": to_breach,
            "patients_affected": affected,
            "priority": round(bp * affected * max(over, 1.0) * WEIGHT[st], 2),
            "cause": d["cause"],
            "contributions": d["contributions"],
            "top_action": recs[0] if recs else None,
        })
    out.sort(key=lambda a: a["priority"], reverse=True)
    return out


_OFFSET = {"registration": 0, "consultation": 10, "laboratory": 30,
           "imaging": 30, "pharmacy": 40}


@lru_cache(maxsize=256)
def _day_outcome(day, actions):
    patients = 0.0
    over = 0.0
    wait_hours = 0.0
    for t in range(OPEN, CLOSE, 5):
        arrivals = _arrival_rate(t) * 5 / 60
        for cause, st, start, end, strength in _active_scenarios(day, "registration", t):
            if cause == "demand_surge":
                arrivals *= strength
        p_ok = 1.0
        for st in STATIONS:
            if _wait(day, st, t + _OFFSET[st], actions) > LIMIT:
                p_ok *= 1 - SHARE[st]
            wait = _wait(day, st, t, actions)
            waiting = wait * _staff_on(day, st, t, actions) / _service_min(day, st, t, actions)
            wait_hours += waiting * 5 / 60
        patients += arrivals
        over += arrivals * (1 - p_ok)
    return {"patients": int(round(patients)),
            "share_over_30": round(over / patients, 3),
            "total_wait_hours": round(wait_hours, 1)}


def day_outcome(day, actions=()):
    return _day_outcome(int(day), _norm_actions(actions))
