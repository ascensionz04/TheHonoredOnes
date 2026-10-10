"""Clinic simulator: config, the minute-step loop, scenarios, day generation, stored days.

One forward simulator is used three ways (forecast, cause, what-if), so the loop is plain
Python that can start from any mid-day state and is repeatable from a seed.

    python -m engine.sim make-days    # write data/days.json and data/two_cause_days.json
    python -m engine.sim check        # sanity report on normal days
"""
from __future__ import annotations

import json
import math
import sys
from collections import deque
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
STATIONS = ("registration", "consultation", "laboratory", "imaging", "pharmacy")
REG, CON, LAB, IMG, PHA = range(5)
CAUSES = ("demand_surge", "staffing_gap", "slow_processing")
DRAIN_LIMIT_MIN = 360     # how long after closing the day run keeps serving patients
N_DRAWS = 1024            # service-time and routing draws held per run (wraps if exceeded)


def to_min(value) -> int:
    """'10:25' or 625 -> 625 (minutes since midnight)."""
    if isinstance(value, str):
        hours, minutes = value.split(":")
        return int(hours) * 60 + int(minutes)
    return int(value)


def to_hhmm(minute) -> str:
    minute = int(minute)
    return f"{minute // 60:02d}:{minute % 60:02d}"


# --------------------------------------------------------------------------- config

class Params:
    """Config plus calibration, flattened into the form the loop needs."""

    def __init__(self, cfg, cal):
        self.cfg = cfg
        self.calibration = cal
        self.data_mode = "calibrated" if cal else "assumptions"
        self.open = to_min(cfg["open"])
        self.close = to_min(cfg["close"])
        self.tick = int(cfg["tick_min"])
        self.limit = float(cfg["wait_limit_min"])
        self.action_min = int(cfg["action_duration_min"])
        st = cfg["stations"]
        assert tuple(st) == STATIONS, "config stations must be the five stations in pathway order"
        self.roster = [int(st[s]["staff"]) for s in STATIONS]
        self.service_min = [float(st[s]["service_min"]) for s in STATIONS]
        self.weight = [float(st[s]["weight"]) for s in STATIONS]
        self.cv = float(cfg["service_cv"])
        sigma2 = math.log(1 + self.cv ** 2)
        self.sigma = math.sqrt(sigma2)
        self.mu = [math.log(m) - sigma2 / 2 for m in self.service_min]

        share = {s: float(st[s]["share"]) for s in STATIONS}
        both = share["laboratory"] * share["imaging"]
        if cal:
            share.update(cal["share"])
            both = cal["lab_and_imaging_share"]
        self.share = share
        # Routing after consultation: one uniform picks the tests, another the pharmacy.
        self.p_both = both
        self.p_lab = share["laboratory"]                       # cumulative: both, then lab only
        self.p_tests = share["laboratory"] + share["imaging"] - both
        self.p_pharm = share["pharmacy"]
        self.p_img_given_lab = both / share["laboratory"] if share["laboratory"] else 0.0

        hourly = {}
        if cal:
            hourly = {int(h): float(v) for h, v in cal["arrivals_per_hour"].items()}
            self.weekday_factor = {int(d): float(f) for d, f in cal["weekday_factor"].items()}
        else:
            a = cfg["arrivals_per_hour"]
            lo, hi = to_min(a["peak_from"]), to_min(a["peak_to"])
            for h in range(self.open // 60, (self.close + 59) // 60):
                hourly[h] = float(a["peak"] if lo <= h * 60 < hi else a["default"])
            self.weekday_factor = {}
        self.hourly = hourly
        base = np.zeros(1440)
        for h, rate in hourly.items():
            base[h * 60:(h + 1) * 60] = rate / 60.0
        base[:self.open] = 0.0
        base[self.close:] = 0.0
        self._base = base
        self.moves = {m["id"]: m for m in cfg["allowed_moves"]}
        sp = cfg["service_speed"]
        self.speed_clip = (float(sp["clip"][0]), float(sp["clip"][1]))
        self.speed_k = float(sp["shrink_k"])
        self.speed_min_z = float(sp["min_z"])
        self.speed_cap = float(sp["cap_ratio"])
        self.demand_min_z = float(cfg["diagnose"]["demand_min_z"])

    def usual(self, weekday) -> np.ndarray:
        """Usual arrivals per minute at registration, for each minute of the day."""
        return self._base * self.weekday_factor.get(int(weekday), 1.0)

    def wait(self, waiting, staff_on, si, speed=1.0) -> float:
        """The one wait definition: patients waiting x average service time / staff on duty.
        `speed` is the current service-time multiplier (1.0 = the station's usual)."""
        return waiting * self.service_min[si] * speed / max(staff_on, 1)

    def speed(self, mean_service, completed, si, expected=1.0) -> float:
        """Unexplained service-time multiplier at a station, from recent completions.

        `expected` is the multiplier already explained by applied actions. The estimate is
        1.0 unless the evidence is clear (z-score of the mean at least min_z), then shrunk
        towards 1.0 by shrink_k pseudo-observations and clipped.
        """
        if completed <= 0:
            return 1.0
        ratio = mean_service / (self.service_min[si] * expected)
        z = (ratio - 1.0) / (self.cv / math.sqrt(completed))
        if abs(z) < self.speed_min_z:
            return 1.0
        ratio = (completed * ratio + self.speed_k) / (completed + self.speed_k)
        return min(max(ratio, self.speed_clip[0]), self.speed_clip[1])


@lru_cache(maxsize=1)
def params() -> Params:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    cal = None
    path = ROOT / cfg["calibration"]["file"]
    if cfg["calibration"]["use"] and path.exists():
        cal = json.loads(path.read_text(encoding="utf-8"))
    return Params(cfg, cal)


# --------------------------------------------------------------------------- the loop

class Clinic:
    """Internal state: per station a queue and the services in progress.

    A patient is (visit_id, minute_joined, needs_imaging, needs_pharmacy).
    A service in progress is (end_minute, patient, staff_slot).
    """
    __slots__ = ("clock", "q", "busy", "zi", "ri", "next_id", "exits")

    def __init__(self, clock):
        self.clock = clock
        self.q = [deque() for _ in STATIONS]
        self.busy = [[] for _ in STATIONS]
        self.zi = [0] * len(STATIONS)   # next service-time draw per station
        self.ri = 0                     # next routing draw
        self.next_id = 0
        self.exits = 0

    def copy(self):
        other = Clinic(self.clock)
        other.q = [deque(q) for q in self.q]
        other.busy = [list(b) for b in self.busy]
        other.zi = list(self.zi)
        other.ri = self.ri
        other.next_id = self.next_id
        other.exits = self.exits
        return other

    def in_building(self):
        return sum(len(q) for q in self.q) + sum(len(b) for b in self.busy)


def run(c, minutes, arr, staff, scale, z, ru, P, rows=None, joins=None,
        step=0, samples=None, area=None, joined=None):
    """Advance clinic `c` by `minutes`, one minute at a time.

    arr[i]          arrivals at registration in minute i
    staff[si][i]    staff on duty; scale[si][i] service-time multiplier
    z[si], ru       pre-drawn standard normals (service times) and uniform pairs (routing).
                    Each station consumes its own stream in order, so two runs that share
                    draws differ only through the change being tested.
    rows            if a list, receives (visit_id, station, arrive, start, end, slot)
    joins           if a list of 5 lists, receives the minute of every join per station
    samples         if a list, receives queue lengths (plus in-service counts when rows
                    are recorded) every `step` minutes
    area, joined    if lists of 5, accumulate patient-minutes waiting and joins per station
    """
    q, busy, zi = c.q, c.busy, c.zi
    mu, sigma = P.mu, P.sigma
    p_both, p_lab, p_tests, p_pharm = P.p_both, P.p_lab, P.p_tests, P.p_pharm
    exp = math.exp
    nz = len(z[0])
    nr = len(ru)
    t = c.clock
    for i in range(minutes):
        n = arr[i]
        if n:
            q0 = q[0]
            for _ in range(n):
                q0.append((c.next_id, t, 0, 0))
                c.next_id += 1
            if joined is not None:
                joined[0] += n
            if joins is not None:
                joins[0].extend([t] * n)
        for si in range(5):
            b = busy[si]
            if b:
                k = 0
                while k < len(b):
                    if b[k][0] > t:
                        k += 1
                        continue
                    p = b.pop(k)[1]
                    # route the patient onward
                    if si == 0:
                        dest = 1
                    elif si == 1:
                        u1, u2 = ru[c.ri % nr]
                        c.ri += 1
                        pharm = 1 if u2 < p_pharm else 0
                        if u1 < p_both:
                            dest, p = 2, (p[0], t, 1, pharm)
                        elif u1 < p_lab:
                            dest, p = 2, (p[0], t, 0, pharm)
                        elif u1 < p_tests:
                            dest, p = 3, (p[0], t, 0, pharm)
                        else:
                            dest, p = (4 if pharm else -1), (p[0], t, 0, pharm)
                    elif si == 2:
                        dest = 3 if p[2] else (4 if p[3] else -1)
                    elif si == 3:
                        dest = 4 if p[3] else -1
                    else:
                        dest = -1
                    if dest < 0:
                        c.exits += 1
                    else:
                        q[dest].append((p[0], t, p[2], p[3]))
                        if joined is not None:
                            joined[dest] += 1
                        if joins is not None:
                            joins[dest].append(t)
            qs = q[si]
            if qs:
                free = staff[si][i] - len(b)
                while free > 0 and qs:
                    p = qs.popleft()
                    j = zi[si]
                    zi[si] = j + 1
                    d = int(exp(mu[si] + sigma * z[si][j % nz]) * scale[si][i] + 0.5) or 1
                    if rows is None:
                        b.append((t + d, p, 0))
                    else:
                        used = {e[2] for e in b}
                        slot = 0
                        while slot in used:
                            slot += 1
                        b.append((t + d, p, slot))
                        rows.append((p[0], si, p[1], t, t + d, slot))
                    free -= 1
        if area is not None:
            for si in range(5):
                area[si] += len(q[si])
        t += 1
        if step and (i + 1) % step == 0:
            if rows is None:
                samples.append([len(x) for x in q])
            else:
                samples.append([len(x) for x in q] + [len(x) for x in busy])
    c.clock = t


def poisson_from_uniform(u, lam):
    """Poisson counts from uniforms by inverse CDF, so runs sharing `u` stay aligned
    when only the rate changes. u and lam are arrays of the same shape (or broadcast)."""
    u = np.asarray(u, dtype=float)
    lam = np.broadcast_to(np.asarray(lam, dtype=float), u.shape)
    k = np.zeros(u.shape, dtype=np.int64)
    p = np.exp(-lam)
    cdf = p.copy()
    for i in range(1, 40):
        above = u > cdf
        if not above.any():
            break
        k += above
        p = p * lam / i
        cdf = cdf + p
    return k


def draws(rng):
    """Service-time and routing draws for one run."""
    z = rng.standard_normal((len(STATIONS), N_DRAWS)).tolist()
    ru = rng.random((N_DRAWS, 2)).tolist()
    return z, ru


def simulate(state, minutes, arrival_rate_fn, staff, service_scale, seed):
    """One forward run from `state`, as specified in the build guide.

    state            a Clinic, or None for an empty clinic at opening time
    arrival_rate_fn  minute of day -> arrivals per minute at registration
    staff            {station: int} or {station: fn(minute) -> int}
    service_scale    {station: float} or {station: fn(minute) -> float}; missing means 1.0
    Returns (new_state, visit_rows). The input state is not modified. visit_rows holds
    (visit_id, station, arrive, start, end, staff_slot) for services started in the run.
    """
    P = params()
    c = state.copy() if state is not None else Clinic(P.open)
    rng = np.random.default_rng(seed)
    clock = range(c.clock, c.clock + minutes)
    rates = np.array([arrival_rate_fn(m) for m in clock], dtype=float)
    arr = poisson_from_uniform(rng.random(minutes), rates).tolist()

    def series(spec, station, default):
        value = spec.get(station, default) if spec else default
        return [value(m) for m in clock] if callable(value) else [value] * minutes

    staff_s = [series(staff, s, P.roster[i]) for i, s in enumerate(STATIONS)]
    scale_s = [series(service_scale, s, 1.0) for s in STATIONS]
    z, ru = draws(rng)
    rows = []
    run(c, minutes, arr, staff_s, scale_s, z, ru, P, rows=rows)
    return c, [(v, STATIONS[si], a, s, e, slot) for v, si, a, s, e, slot in rows]


# --------------------------------------------------------------------------- actions

def norm_actions(actions, upto=None) -> tuple:
    """Actions as a sorted tuple of (action_id, start_minute), dropping any after `upto`."""
    P = params()
    out = set()
    for action in actions or ():
        if isinstance(action, dict):
            action_id, start = action["action_id"], action.get("start", action.get("start_minute"))
        else:
            action_id, start = action
        if action_id not in P.moves:
            raise ValueError(f"unknown action {action_id!r}; allowed: {sorted(P.moves)}")
        start = to_min(start)
        if upto is None or start <= upto:
            out.add((str(action_id), start))
    return tuple(sorted(out))


def apply_move(move, staff, scale, lo, hi):
    """Apply one allowed move to minute indices [lo, hi) of the staff and scale series."""
    hi = min(hi, len(staff[0]))
    lo = max(lo, 0)
    if "service_scale" in move:
        si = STATIONS.index(move["station"])
        for i in range(lo, hi):
            scale[si][i] *= move["service_scale"]
        return
    to = STATIONS.index(move["to"])
    donor = STATIONS.index(move["from"]) if move["from"] in STATIONS else None
    for i in range(lo, hi):
        if donor is not None:
            if staff[donor][i] < 2:      # never strip a station of its last staff member
                continue
            staff[donor][i] -= 1
        staff[to][i] += 1


def action_windows(actions, P):
    """{action_id: sorted list of (start, end)} with overlapping applications merged."""
    spans = {}
    for action_id, start in actions:
        spans.setdefault(action_id, []).append((start, start + P.action_min))
    merged = {}
    for action_id, items in spans.items():
        items.sort()
        out = [list(items[0])]
        for lo, hi in items[1:]:
            if lo <= out[-1][1]:
                out[-1][1] = max(out[-1][1], hi)
            else:
                out.append([lo, hi])
        merged[action_id] = [tuple(x) for x in out]
    return merged


def active_actions(actions, clock, P=None) -> set:
    """Ids of actions in force at `clock`."""
    P = P or params()
    return {a for a, spans in action_windows(actions, P).items()
            if any(lo <= clock < hi for lo, hi in spans)}


def action_scale(actions, si, lo, hi, P=None) -> float:
    """Average service-time multiplier that applied actions explain at station `si` over
    minutes [lo, hi). 1.0 when no applied action changes the station's service time."""
    P = P or params()
    out = 1.0
    for action_id, spans in action_windows(actions, P).items():
        move = P.moves[action_id]
        if "service_scale" not in move or STATIONS.index(move["station"]) != si:
            continue
        overlap = sum(max(0, min(hi, b) - max(lo, a)) for a, b in spans)
        share = overlap / max(hi - lo, 1)
        out *= 1.0 - share + share * move["service_scale"]
    return out


def station_speed(state, name, P=None):
    """(unexplained, total) service-time multipliers at a station, as observed in `state`.
    `unexplained` is slowness nobody chose; `total` also includes applied actions."""
    P = P or params()
    si = STATIONS.index(name)
    st = state["stations"][name]
    clock, actions = state["clock"], state["actions"]
    expected = action_scale(actions, si, clock - 30, clock, P)
    unexplained = P.speed(st["service_min_30m"], st["completed_30m"], si, expected)
    return unexplained, unexplained * action_scale(actions, si, clock, clock + 1, P)


def refresh_waits(state, P=None):
    """Recompute wait_now_min from the other observed fields (used after adding noise)."""
    P = P or params()
    for si, name in enumerate(STATIONS):
        st = state["stations"][name]
        st["wait_now_min"] = round(P.wait(st["waiting"], st["staff_on"], si,
                                          station_speed(state, name, P)[1]), 1)
    return state


# --------------------------------------------------------------------------- stored days

@lru_cache(maxsize=1)
def _registry() -> dict:
    days = {}
    for name in ("days.json", "two_cause_days.json", "demo_only_days.json"):
        path = ROOT / "data" / name
        if path.exists():
            for spec in json.loads(path.read_text(encoding="utf-8")):
                days[int(spec["day"])] = spec
    return days


def day_spec(day) -> dict:
    registry = _registry()
    if int(day) not in registry:
        raise KeyError(f"day {day} is not in data/days.json (run: python -m engine.sim make-days)")
    return registry[int(day)]


def day_ids(split=None) -> list:
    return [d for d, s in sorted(_registry().items()) if split is None or s["split"] == split]


class DayRun:
    """One stored day simulated from opening until the last patient leaves."""
    __slots__ = ("spec", "actions", "minutes", "waiting", "in_service", "staff_on", "arr30",
                 "svc_sum30", "svc_n30", "reg15", "reg30", "reg60", "rows", "reg_per_min",
                 "outcome", "true_wait", "roster_now")


def _day_schedules(spec, actions, P, n):
    """Arrival rates, staff and service scale for each of n minutes from opening."""
    rates = P.usual(spec["weekday"])[P.open:P.open + n].copy()
    if len(rates) < n:
        rates = np.concatenate([rates, np.zeros(n - len(rates))])
    staff = [[r] * n for r in P.roster]
    scale = [[1.0] * n for _ in STATIONS]
    for ev in spec.get("events", []):
        lo = max(to_min(ev["start"]) - P.open, 0)
        hi = min(lo + int(ev["duration"]), n)
        if ev["type"] == "demand_surge":
            rates[lo:hi] *= ev["strength"]
        elif ev["type"] == "staffing_gap":
            si = STATIONS.index(ev["station"])
            for i in range(lo, hi):
                staff[si][i] = max(staff[si][i] - 1, 0)
        elif ev["type"] == "slow_processing":
            si = STATIONS.index(ev["station"])
            for i in range(lo, hi):
                scale[si][i] *= ev["strength"]
    expected = [[r] * n for r in P.roster]         # the roster as changed by actions only
    flat = [[1.0] * n for _ in STATIONS]
    for action_id, spans in action_windows(actions, P).items():
        for lo, hi in spans:
            apply_move(P.moves[action_id], staff, scale, lo - P.open, hi - P.open)
            apply_move(P.moves[action_id], expected, flat, lo - P.open, hi - P.open)
    return rates, staff, scale, expected


@lru_cache(maxsize=96)
def _day_run(day: int, actions: tuple) -> DayRun:
    P = params()
    spec = day_spec(day)
    span = P.close - P.open
    n = span + DRAIN_LIMIT_MIN
    rates, staff, scale, expected = _day_schedules(spec, actions, P, n)
    rng = np.random.default_rng(spec["seed"])
    # The day's randomness depends only on its seed, so the same patients arrive and need
    # the same service whatever actions are applied.
    arr = poisson_from_uniform(rng.random(n), rates).tolist()
    z, ru = draws(rng)
    c = Clinic(P.open)
    rows, samples = [], []
    joins = [[] for _ in STATIONS]
    run(c, span, arr, staff, scale, z, ru, P, rows=rows, joins=joins, step=1, samples=samples)
    done = span
    while c.in_building() and done < n:
        chunk = min(P.tick, n - done)
        run(c, chunk, arr[done:done + chunk], [s[done:done + chunk] for s in staff],
            [s[done:done + chunk] for s in scale], z, ru, P,
            rows=rows, joins=joins, step=1, samples=samples)
        done += chunk

    r = DayRun()
    r.spec, r.actions, r.minutes, r.rows = spec, actions, done, rows
    s = np.array(samples, dtype=np.int32).reshape(done, 10)
    zero = np.zeros((1, 5), dtype=np.int32)
    r.waiting = np.vstack([zero, s[:, :5]])            # index k = state after k minutes
    r.in_service = np.vstack([zero, s[:, 5:]])
    r.staff_on = np.array(staff, dtype=np.int32).T[:done + 1]
    r.roster_now = np.array(expected, dtype=np.int32).T[:done + 1]
    # Ground truth for evaluation: the wait estimate with the true service speed.
    r.true_wait = (r.waiting * np.array(P.service_min) * np.array(scale).T[:done + 1]
                   / np.maximum(r.staff_on, 1))

    def rolling(per_min, window):
        cum = np.vstack([np.zeros((1, per_min.shape[1])), np.cumsum(per_min, axis=0)])
        idx = np.arange(done + 1)
        return cum[idx] - cum[np.maximum(idx - window, 0)]

    j = np.zeros((done, 5))
    for si in range(5):
        if joins[si]:
            np.add.at(j[:, si], np.array(joins[si]) - P.open, 1)
    r.reg_per_min = j[:, 0].copy()
    r.arr30 = rolling(j, 30)
    reg = j[:, :1]
    r.reg15, r.reg30, r.reg60 = (rolling(reg, w)[:, 0] for w in (15, 30, 60))
    dur = np.zeros((done, 5))
    cnt = np.zeros((done, 5))
    arr_rows = np.array(rows, dtype=np.int64).reshape(-1, 6)
    if len(arr_rows):
        end = arr_rows[:, 4] - P.open
        ok = end < done
        # One very long case should not read as a slowdown: cap each at cap_ratio x usual.
        length = np.minimum(arr_rows[:, 4] - arr_rows[:, 3],
                            P.speed_cap * np.array(P.service_min)[arr_rows[:, 1]])
        np.add.at(dur, (end[ok], arr_rows[ok, 1]), length[ok])
        np.add.at(cnt, (end[ok], arr_rows[ok, 1]), 1)
    r.svc_sum30 = rolling(dur, 30)
    r.svc_n30 = rolling(cnt, 30)

    patients = c.next_id
    if len(arr_rows):
        waits = arr_rows[:, 3] - arr_rows[:, 2]
        worst = np.zeros(patients)
        np.maximum.at(worst, arr_rows[:, 0], waits)
        share = float((worst > P.limit).mean()) if patients else 0.0
        hours = float(waits.sum()) / 60.0
    else:
        share, hours = 0.0, 0.0
    r.outcome = {"patients": int(patients), "share_over_30": round(share, 4),
                 "total_wait_hours": round(hours, 2)}
    return r


def get_state(day, clock, actions=()):
    """Re-simulate the stored day from its seed, with any applied actions, up to `clock`.

    clock is minutes since midnight or 'HH:MM'. Each action is (action_id, start_minute)
    and lasts 60 minutes. Returns what a supervisor's system could observe at that moment;
    the day's scenario is deliberately not part of it.
    """
    P = params()
    clock = to_min(clock)
    acts = norm_actions(actions, upto=clock)
    r = _day_run(int(day), acts)
    k = min(max(clock - P.open, 0), r.minutes)
    stations = {}
    for si, name in enumerate(STATIONS):
        waiting = int(r.waiting[k, si])
        staff_on = int(r.staff_on[k, si])
        n_done = int(r.svc_n30[k, si])
        svc = r.svc_sum30[k, si] / n_done if n_done else P.service_min[si]
        stations[name] = {
            "waiting": waiting,
            "in_service": int(r.in_service[k, si]),
            "staff_on": staff_on,
            "wait_now_min": 0.0,
            "arrivals_30m": int(r.arr30[k, si]),
            "service_min_30m": round(float(svc), 1),
            "completed_30m": n_done,
        }
    return refresh_waits({
        "day": int(day),
        "clock": clock,
        "weekday": int(r.spec["weekday"]),
        "actions": acts,
        "recent_arrivals": {15: int(r.reg15[k]), 30: int(r.reg30[k]), 60: int(r.reg60[k])},
        "stations": stations,
    }, P)


def day_outcome(day, actions=()):
    """Whole-day result: patients seen, share who waited over the limit at any station
    (their real wait, start of service minus joining the queue), and total waiting hours."""
    return dict(_day_run(int(day), norm_actions(actions)).outcome)


def day_run(day, actions=()) -> DayRun:
    """Engine-internal access to the full day (evaluation and training)."""
    return _day_run(int(day), norm_actions(actions))


def event_log(day, actions=()) -> list:
    """The simulated event log for a day: one dict per visit to a station."""
    r = day_run(day, actions)
    staff_prefix = {"registration": "c", "consultation": "d", "laboratory": "t",
                    "imaging": "r", "pharmacy": "p"}
    return [{"day": int(day), "visit_id": f"v{v:04d}", "station": STATIONS[si],
             "arrive_ts": to_hhmm(a), "start_ts": to_hhmm(s), "end_ts": to_hhmm(e),
             "staff_id": f"{staff_prefix[STATIONS[si]]}{slot + 1}",
             "scenario": r.spec["scenario"]}
            for v, si, a, s, e, slot in r.rows]


# --------------------------------------------------------------------------- day generation

def _event(kind, station, rng, P, start=None):
    sc = P.cfg["scenarios"]
    spec = sc[kind]
    lo, hi = to_min(sc["start_from"]), to_min(sc["start_to"])
    if start is None:
        start = int(rng.integers(lo // 5, hi // 5 + 1)) * 5
    d_lo, d_hi = spec["duration_min"]
    duration = int(rng.integers(d_lo // 5, d_hi // 5 + 1)) * 5
    if kind == "staffing_gap":
        strength = 1.0
    else:
        s_lo, s_hi = spec["strength"]
        strength = round(float(rng.uniform(s_lo, s_hi)), 2)
    return {"type": kind, "station": station, "start": to_hhmm(start),
            "duration": duration, "strength": strength}


def make_days():
    """Write the 90 day specs and the two-cause robustness days. Deterministic."""
    P = params()
    cfg = P.cfg["days"]
    sc = P.cfg["scenarios"]
    rng = np.random.default_rng(cfg["base_seed"])
    plan = []
    for split, mix in cfg["split"].items():
        for kind, count in mix.items():
            for k in range(count):
                if kind == "normal":
                    plan.append((split, kind, None))
                elif kind == "demand_surge":
                    plan.append((split, kind, "registration"))
                else:   # cycle stations so every split sees each one
                    stations = sc[kind]["stations"]
                    plan.append((split, kind, stations[k % len(stations)]))
    order = rng.permutation(len(plan))
    weekdays = cfg["weekdays"]
    days = []
    for day, idx in enumerate(order):
        split, kind, station = plan[idx]
        events = [] if kind == "normal" else [_event(kind, station, rng, P)]
        days.append({"day": day, "seed": int(rng.integers(1, 2 ** 31)),
                     "weekday": weekdays[day % len(weekdays)], "split": split,
                     "scenario": kind, "events": events})
    out = ROOT / "data" / "days.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(days, indent=1) + "\n", encoding="utf-8")

    # Two causes at once: never seen in training or tuning (robustness run).
    pairs = [("demand_surge", "staffing_gap"), ("demand_surge", "slow_processing"),
             ("staffing_gap", "slow_processing")]
    rng2 = np.random.default_rng(cfg["base_seed"] + 1)
    two = []
    for k in range(cfg["two_cause"]):
        first, second = pairs[k % len(pairs)]
        events = []
        for kind in (first, second):
            if kind == "demand_surge":
                station = "registration"
            else:
                stations = sc[kind]["stations"]
                station = stations[(k // len(pairs)) % len(stations)]
            start = None
            if events:   # the second cause starts within 30 minutes of the first
                start = to_min(events[0]["start"]) + int(rng2.integers(0, 7)) * 5
            events.append(_event(kind, station, rng2, P, start))
        two.append({"day": 1000 + k, "seed": int(rng2.integers(1, 2 ** 31)),
                    "weekday": weekdays[k % len(weekdays)], "split": "two_cause",
                    "scenario": "two_cause", "events": events})
    (ROOT / "data" / "two_cause_days.json").write_text(json.dumps(two, indent=1) + "\n",
                                                        encoding="utf-8")
    _registry.cache_clear()
    _day_run.cache_clear()
    return days, two


def check():
    """Sanity report: patient count, busy share at peak, waits, conservation."""
    import time
    P = params()
    normal = [d for d in day_ids() if day_spec(d)["scenario"] == "normal"]
    t0 = time.perf_counter()
    runs = [day_run(d) for d in normal]
    per_day = (time.perf_counter() - t0) / len(runs)
    print(f"data mode: {P.data_mode}; {len(runs)} normal days; {per_day * 1000:.0f} ms per day")
    print("patients per day: mean %.1f (min %d, max %d)" % (
        np.mean([r.outcome["patients"] for r in runs]),
        min(r.outcome["patients"] for r in runs), max(r.outcome["patients"] for r in runs)))
    peak_hour = max(P.hourly, key=P.hourly.get)
    lo, hi = peak_hour * 60 - P.open, peak_hour * 60 + 60 - P.open
    print(f"peak hour {peak_hour}:00, usual arrivals {P.hourly[peak_hour]:.1f}/h (average weekday)")
    for si, name in enumerate(STATIONS):
        busy = np.mean([r.in_service[lo:hi, si].mean() / P.roster[si] for r in runs])
        svc = np.mean([(row[4] - row[3]) for r in runs for row in r.rows if row[1] == si])
        share = np.mean([len({row[0] for row in r.rows if row[1] == si}) / r.outcome["patients"]
                         for r in runs])
        breach = np.mean([(r.true_wait[:481, si] > P.limit).any() for r in runs])
        print(f"  {name:13s} busy at peak {busy:5.0%}  service {svc:5.1f} min  "
              f"share {share:5.0%}  normal days with a breach {breach:4.0%}")
    neg = sum(1 for r in runs for row in r.rows if row[3] < row[2])
    unfinished = sum(1 for r in runs if r.minutes >= P.close - P.open + DRAIN_LIMIT_MIN)
    print(f"negative waits: {neg}; days not drained: {unfinished}")
    print("share over limit: mean %.1f%%; waiting hours: mean %.1f" % (
        100 * np.mean([r.outcome["share_over_30"] for r in runs]),
        np.mean([r.outcome["total_wait_hours"] for r in runs])))
    by_wd = {}
    for r in runs:
        by_wd.setdefault(r.spec["weekday"], []).append(r.outcome["share_over_30"])
    print("share over limit by weekday:", {k: round(float(np.mean(v)), 3) for k, v in sorted(by_wd.items())})


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "check"
    if command == "make-days":
        days, two = make_days()
        print(f"wrote {len(days)} day specs and {len(two)} two-cause days")
    else:
        check()
