"""Service Bottleneck Predictor: the single screen (DESIGN.md).

Zones, top to bottom: replay bar, pathway strip, action card, also watching,
why trust this. The app imports only the six functions in engine/api.py.
"""

import json
import sys
import time
import traceback
from pathlib import Path

import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "app"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import cards  # noqa: E402
from cards import STATIONS  # noqa: E402

st.set_page_config(page_title="Bottleneck Predictor", layout="centered",
                   initial_sidebar_state="collapsed")

DATA_MISSING = "Demo data could not be loaded. Choose another day or press Reset."

st.markdown(f"""
<style>
  .block-container {{ padding-top: 2rem; padding-bottom: 3rem; }}
  .clock {{ font-size: 1.6rem; font-weight: 700; color: {cards.COLOURS['text']};
            text-align: center; line-height: 2.4rem; }}
  .tile {{ background: {cards.COLOURS['surface']}; border-radius: 8px;
           padding: 0.5rem 0.4rem; text-align: center; }}
  .tile-name {{ font-weight: 700; font-size: 0.9rem; color: {cards.COLOURS['text']}; }}
  .tile-wait {{ font-size: 0.95rem; color: {cards.COLOURS['text']}; }}
  .tile-status {{ font-size: 0.8rem; text-transform: none; }}
  .action {{ font-size: 1.75rem; font-weight: 700; line-height: 1.25;
             color: {cards.COLOURS['text']}; margin: 0.2rem 0 0.6rem 0; }}
  .deadline {{ text-align: right; font-weight: 700; color: {cards.COLOURS['text']};
               font-size: 0.95rem; }}
  .st-key-action_card {{ border: 2px solid {cards.COLOURS['action']} !important; }}
</style>
""", unsafe_allow_html=True)


# ---------- loading ----------

def fail(err):
    traceback.print_exception(err, file=sys.stderr)
    st.error(DATA_MISSING)
    st.stop()


try:
    from engine import api
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        CFG = yaml.safe_load(f)
except Exception as err:  # noqa: BLE001 - show a plain message, never a stack trace
    fail(err)


def _minutes(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


OPEN, CLOSE = _minutes(CFG["open"]), _minutes(CFG["close"])
TICK = CFG.get("tick_min", 5)
LIMIT = CFG["wait_limit_min"]
CLEAR_AT = CFG["alert"]["clear_at"]

DEFAULT_DEMO_DAYS = {
    "Ordinary busy day": 0,
    "Doctor called away": 1,
    "Holiday rush": 2,
    "Pharmacy system slow": 3,
}
SPEEDS = {"slow": 1.0, "normal": 0.5, "fast": 0.2}  # seconds per 5-minute tick


def load_demo_days():
    """data/demo_days.json maps picker names to day ids; either
    {"Name": day} or [{"name": ..., "day": ...}]."""
    path = ROOT / "data" / "demo_days.json"
    if not path.exists():
        return DEFAULT_DEMO_DAYS
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            raw = {d["name"]: d["day"] for d in raw}
        return {str(k): int(v) for k, v in raw.items()} or DEFAULT_DEMO_DAYS
    except Exception as err:  # noqa: BLE001
        traceback.print_exception(err, file=sys.stderr)
        return DEFAULT_DEMO_DAYS


@st.cache_data(show_spinner=False)
def load_results():
    path = ROOT / "eval" / "results.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as err:  # noqa: BLE001
        traceback.print_exception(err, file=sys.stderr)
        return None


@st.cache_data(show_spinner=False, max_entries=2000)
def view(day, clock, actions):
    state = api.get_state(day, clock, actions)
    return state, api.forecast(state), api.alerts(state)


@st.cache_data(show_spinner=False, max_entries=2000)
def recommendations(day, clock, actions, station):
    return api.recommend(api.get_state(day, clock, actions), station)


@st.cache_data(show_spinner=False, max_entries=200)
def outcome(day, actions):
    return api.day_outcome(day, actions)


DEMO_DAYS = load_demo_days()


# ---------- session state ----------

ss = st.session_state
ss.setdefault("day", "Doctor called away" if "Doctor called away" in DEMO_DAYS else next(iter(DEMO_DAYS)))
ss.setdefault("clock", OPEN)
ss.setdefault("playing", False)
ss.setdefault("speed", "fast")
ss.setdefault("actions", ())
ss.setdefault("applied", [])          # [(label, clock)] for the confirmation line
ss.setdefault("selected_station", None)
if ss.day not in DEMO_DAYS:
    ss.day = next(iter(DEMO_DAYS))


def reset():
    ss.clock = OPEN
    ss.playing = False
    ss.actions = ()
    ss.applied = []
    ss.selected_station = None


def toggle_play():
    if ss.clock >= CLOSE:
        reset()
    ss.playing = not ss.playing


def apply_action(action, clock):
    ss.actions = ss.actions + ((action["action_id"], clock),)
    ss.applied = ss.applied + [(action["label"], clock)]
    ss.selected_station = None


def select_station(station):
    ss.selected_station = station


# ---------- 1 replay bar ----------

bar = st.columns([3.2, 1.3, 2.2, 1.4, 1.2], vertical_alignment="bottom")
bar[0].selectbox("Day", list(DEMO_DAYS), key="day", on_change=reset)
bar[1].button("Pause" if ss.playing else "Play", on_click=toggle_play, width="stretch")
bar[2].select_slider("Speed", options=list(SPEEDS), key="speed")
bar[3].markdown(f"<div class='clock'>{cards.hhmm(ss.clock)}</div>", unsafe_allow_html=True)
bar[4].button("Reset", on_click=reset, width="stretch")

day = DEMO_DAYS[ss.day]
actions = tuple(ss.actions)

try:
    with st.spinner("Checking the next hour..."):
        state, fc, alert_list = view(day, ss.clock, actions)
except Exception as err:  # noqa: BLE001
    fail(err)

alert_by_station = {a["station"]: a for a in alert_list}
if ss.selected_station not in alert_by_station:
    ss.selected_station = None
focus = alert_by_station.get(ss.selected_station) or (alert_list[0] if alert_list else None)


def status_of(station):
    s = state["stations"][station]
    if cards.whole(s["wait_now_min"]) > LIMIT:
        return "over limit"
    if station in alert_by_station:
        return "will breach"
    f = fc[station]
    if max(f[30]["breach_prob"], f[60]["breach_prob"]) >= CLEAR_AT:
        return "watch"
    return "ok"


# ---------- 2 pathway strip ----------

statuses = {s: status_of(s) for s in STATIONS}
tiles = st.columns(5, gap="small")
for col, station in zip(tiles, STATIONS):
    col.markdown(cards.tile_html(station, state["stations"][station]["wait_now_min"],
                                 fc[station][30]["wait_p50"], statuses[station],
                                 highlight=focus is not None and focus["station"] == station),
                 unsafe_allow_html=True)
st.caption("Wait now → expected in 30 minutes. Patients move left to right; "
           "laboratory and imaging are side branches after consultation.")

st.write("")

# ---------- 3 action card ----------

if ss.clock >= CLOSE:
    try:
        final = outcome(day, actions)
        msg = f"Clinic closed. Patients who waited over 30 minutes today: {cards.pct(final['share_over_30'])}%."
        if actions:
            msg += " " + cards.outcome_line(outcome(day, ()), final, len(actions))
        st.success(msg)
    except Exception as err:  # noqa: BLE001
        fail(err)
elif focus is not None:
    try:
        recs = recommendations(day, ss.clock, actions, focus["station"])
    except Exception as err:  # noqa: BLE001
        fail(err)
    cards.render_action_card(focus, state, fc, recs, CFG, on_apply=apply_action)
else:
    watching = [s for s in STATIONS if statuses[s] == "watch"]
    if watching:
        names = " and ".join(cards.name(s) for s in watching)
        st.info(f"No action needed yet. Keeping an eye on {names}.")
    else:
        st.success(f"No action needed. All stations are expected to stay under "
                   f"{LIMIT} minutes for the next hour.")

if ss.applied and ss.clock < CLOSE:
    label, at = ss.applied[-1]
    st.caption(f"Applied at {cards.hhmm(at)}: {label}.")
    try:
        st.success(cards.outcome_line(outcome(day, ()), outcome(day, actions), len(actions)))
    except Exception as err:  # noqa: BLE001
        fail(err)

# ---------- 4 also watching ----------

rest = [a for a in alert_list if focus is None or a["station"] != focus["station"]]
if rest and ss.clock < CLOSE:
    st.markdown(f"**Also watching ({len(rest)})**")
    for a in rest:
        st.button(cards.watching_line(a), key=f"watch_{a['station']}",
                  on_click=select_station, args=(a["station"],), width="stretch")

# ---------- 5 why trust this? ----------


def trust_statements(r):
    out = []
    al = r.get("alerts") or {}
    if al.get("median_warning_min") is not None:
        out.append(f"Warned a median of {cards.whole(al['median_warning_min'])} minutes "
                   f"before a station passed the limit.")
    fa = al.get("false_alarms_per_day")
    if fa is not None:
        fa = float(fa)
        if fa == 0:
            out.append("No false alarms on the test days.")
        elif fa < 1:
            out.append(f"False alarms: about {max(1, cards.whole(fa * 10))} in 10 days.")
        else:
            out.append(f"False alarms: about {cards.whole(fa)} per day.")
    cause = r.get("cause") or {}
    confusion = cause.get("confusion") or {}
    if confusion and all(isinstance(v, dict) for v in confusion.values()):
        total = sum(sum(row.values()) for row in confusion.values())
        right = sum(row.get(true, 0) for true, row in confusion.items())
        if total:
            out.append(f"Named the right cause in {right} of {total} test cases.")
    elif cause.get("accuracy") is not None:
        out.append(f"Named the right cause in {cards.pct(cause['accuracy'])}% of test cases.")
    pol = r.get("policy") or {}
    tool = (pol.get("tool") or {}).get("share_over_30")
    reactive = (pol.get("reactive") or {}).get("share_over_30")
    if tool is not None and reactive is not None:
        t, rv = cards.pct(tool), cards.pct(reactive)
        if t < rv:
            out.append(f"Following the top action cut patients waiting over 30 minutes from "
                       f"{rv}% to {t}%, against a supervisor who reacts only after the limit is passed.")
        else:
            out.append(f"Following the top action left {t}% of patients waiting over 30 minutes, "
                       f"against {rv}% for a supervisor who reacts only after the limit is passed.")
    return out


with st.expander("Why trust this?"):
    results = load_results()
    statements = trust_statements(results) if results else []
    if statements:
        for s in statements:
            st.markdown(f"- {s}")
    else:
        st.write("Test results will appear here once the evaluation has run.")
    if results:
        if results.get("data_mode") == "calibrated":
            st.caption("What is real: arrival pattern, service times and pathway shares are "
                       "calibrated on a public outpatient event log.")
        else:
            st.caption("What is assumed: arrival pattern, service times and staff numbers are "
                       "stated assumptions, not measured from a real clinic.")
        st.caption("What is simulated: results are from 20 simulated test days not used to build the model.")
        for a in results.get("assumptions") or []:
            st.caption(f"Assumption: {a}")
    if getattr(api.get_state, "__module__", "") == "engine.mock":
        st.caption("Demo numbers: the live engine is not connected yet, so this replay is illustrative.")


# ---------- replay loop ----------

if ss.playing:
    if ss.clock >= CLOSE:
        ss.playing = False
    else:
        time.sleep(SPEEDS[ss.speed])
        ss.clock = min(CLOSE, ss.clock + TICK)
        st.rerun()
