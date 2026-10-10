"""Sentence templates (DESIGN.md section 5) and card rendering.

Every sentence is filled only with numbers from the engine. Writing rules:
whole numbers, "chance" not "probability", no model terms, three sentences at
most above the Apply button, always say what happens next.
"""

import altair as alt
import pandas as pd
import streamlit as st

STATIONS = ["registration", "consultation", "laboratory", "imaging", "pharmacy"]

CAUSE_NAMES = {
    "demand_surge": "demand surge",
    "staffing_gap": "staffing gap",
    "slow_processing": "slow processing",
    "mixed": "mixed causes",
    "peak_load": "normal peak",
}

# (singular, plural) for the staff at each station.
STAFF_NOUN = {
    "registration": ("clerk", "clerks"),
    "consultation": ("doctor", "doctors"),
    "laboratory": ("technician", "technicians"),
    "imaging": ("radiographer", "radiographers"),
    "pharmacy": ("pharmacist", "pharmacists"),
}

# Each allowed move as a gerund, for "{Action} for an hour cuts ...".
ACTION_GERUND = {
    "clerk_to_pharmacy": "Moving a registration clerk to the pharmacy counter",
    "nurse_to_lab": "Sending the float nurse to laboratory sample-taking",
    "open_reserve_room": "Opening the reserve room",
    "fast_track_pharmacy": "Fast-tracking repeat prescriptions",
}

COLOURS = {
    "text": "#1A1F2B",
    "secondary": "#5B6472",
    "surface": "#F6F7F9",
    "border": "#D9DEE5",
    "action": "#1F5FBF",
    "ok": "#1E7B4F",
    "watch": "#B26A00",
    "will breach": "#C0392B",
    "over limit": "#8E1B1B",
}


# ---------- number formatting ----------

def hhmm(minutes):
    minutes = int(round(minutes))
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def whole(x):
    return int(round(float(x)))


def chance(p):
    """'80% chance', to the nearest 5%; never claims certainty."""
    c = int(round(float(p) * 20) * 5)
    return "over 95% chance" if c > 95 else f"{max(c, 5)}% chance"


def pct(share):
    """Share of patients as a whole percentage; accepts 0-1 or 0-100."""
    share = float(share)
    return whole(share * 100 if share <= 1 else share)


def name(station):
    return station.capitalize() if station else ""


def staff_noun(station, n):
    singular, plural = STAFF_NOUN.get(station, ("member of staff", "staff"))
    return singular if n == 1 else plural


def usual_arrivals_30m(cfg, station, clock):
    """Arrivals the config expects at a station in 30 minutes at this time."""
    a = cfg["arrivals_per_hour"]
    h_from, m_from = map(int, a["peak_from"].split(":"))
    h_to, m_to = map(int, a["peak_to"].split(":"))
    peak = h_from * 60 + m_from <= clock < h_to * 60 + m_to
    rate = a["peak"] if peak else a["default"]
    return rate * cfg["stations"][station]["share"] / 2


# ---------- sentences ----------

def deadline(alert):
    m = alert.get("minutes_to_breach")
    if m is None:
        return "act within the hour"
    if m <= 0:
        return "act now"
    return f"act within {whole(m)} min"


def what_sentence(alert, clock, limit):
    st_name = name(alert["station"])
    c = chance(alert["breach_prob"])
    m = alert.get("minutes_to_breach")
    if m is None:
        return f"{st_name} is likely to pass the {limit}-minute limit within the hour ({c})."
    if m <= 0:
        return (f"{st_name} has already passed the {limit}-minute limit and is likely "
                f"to stay over it ({c}).")
    return f"{st_name} is likely to pass the {limit}-minute limit by {hhmm(clock + m)} ({c})."


def _top_two(contributions):
    ranked = sorted(contributions.items(), key=lambda kv: kv[1], reverse=True)
    return [CAUSE_NAMES.get(k, k) for k, _ in ranked[:2]]


def why_sentence(alert, state, cfg):
    station = alert["station"]
    cause = alert.get("cause")
    s = state["stations"][station]
    roster = cfg["stations"][station]["staff"]
    if cause == "staffing_gap":
        on = s["staff_on"]
        return f"Cause: staffing gap. {on} of {roster} {staff_noun(station, roster)} are on duty."
    if cause == "demand_surge":
        usual = usual_arrivals_30m(cfg, station, state["clock"])
        ratio = s["arrivals_30m"] / usual if usual else 0
        if ratio >= 1.95:
            fact = f"Arrivals are about {whole(ratio)} times the usual level for this hour."
        elif ratio >= 1.05:
            fact = f"Arrivals are about {whole((ratio - 1) * 100)}% above the usual level for this hour."
        else:
            fact = "More patients than usual are reaching this station."
        return f"Cause: demand surge. {fact}"
    if cause == "slow_processing":
        now = whole(s["service_min_30m"])
        usual = whole(cfg["stations"][station]["service_min"])
        if now > usual:
            fact = f"Each patient is taking {now} minutes against the usual {usual}."
        else:
            fact = "Each patient is taking longer than usual."
        return f"Cause: slow processing. {fact}"
    if cause == "mixed":
        a, b = _top_two(alert.get("contributions", {}))
        return f"Causes: {a} and {b}, in roughly equal parts."
    if cause == "peak_load":
        return (f"Nothing unusual has happened; the normal peak is more than "
                f"{roster} {staff_noun(station, roster)} can clear.")
    return ""


def affected_sentence(alert):
    return f"About {whole(alert['patients_affected'])} patients will be affected."


def action_helps(action):
    return bool(action) and whole(action["wait_saved_min"]) >= 1


def effect_sentence(action, station, fc, cfg):
    gerund = ACTION_GERUND.get(action["action_id"], action["label"].rstrip("."))
    parts = [f"{gerund} for an hour cuts the {station} wait by about "
             f"{whole(action['wait_saved_min'])} minutes."]
    donor = action.get("donor_station")
    if donor:
        parts.append(f"It adds about {whole(action['donor_wait_added_min'])} minutes at {donor}.")
    parts.append(next_sentence(action.get("bottleneck_after"), station, fc, cfg))
    return " ".join(parts)


def next_sentence(after, station, fc, cfg):
    clear_at = cfg["alert"]["clear_at"]
    if not after or fc.get(after, {}).get(60, {}).get("breach_prob", 0) < clear_at:
        return "No other station is expected to pass the limit in the next hour."
    if after == station:
        return f"{name(station)} stays the busiest station."
    return f"{name(after)} then becomes the busiest station."


def no_move_sentence(alert, fc):
    f = fc[alert["station"]]
    wait = max(f[30]["wait_p50"], f[60]["wait_p50"])
    return (f"No allowed staff move reduces the wait. "
            f"Tell waiting patients to expect about {whole(wait)} minutes.")


def bars_sentence(alert):
    cause = alert.get("cause")
    if cause == "peak_load":
        return "No single cause stands out; this is the normal peak."
    if cause == "mixed":
        a, b = _top_two(alert.get("contributions", {}))
        return f"The expected wait comes from the {a} and the {b} in roughly equal parts."
    return f"Most of the expected wait comes from the {CAUSE_NAMES.get(cause, cause)}."


def what_if_line(action, station):
    added = whole(action["donor_wait_added_min"]) if action.get("donor_station") else 0
    after = name(action.get("bottleneck_after")) or "none"
    return (f"{action['label']}: saves {whole(action['wait_saved_min'])} min at {station}, "
            f"adds {added} min elsewhere. Busiest station after: {after}.")


def watching_line(alert):
    m = alert.get("minutes_to_breach")
    if m is None:
        when = "may pass the limit within the hour"
    elif m <= 0:
        when = "already past the limit"
    else:
        when = f"may pass the limit in about {whole(m)} min"
    cause = CAUSE_NAMES.get(alert.get("cause"), "").capitalize()
    return f"{name(alert['station'])}: {when}. {cause}."


def outcome_line(without, with_, n_actions):
    which = "this action" if n_actions == 1 else "these actions"
    return (f"Today, patients waiting over 30 minutes: {pct(without['share_over_30'])}% "
            f"without {which}, {pct(with_['share_over_30'])}% with {'it' if n_actions == 1 else 'them'}.")


# ---------- rendering ----------

def render_action_card(alert, state, fc, recs, cfg, on_apply):
    """The 'Do this now' card. `recs` is recommend() for this station."""
    clock = state["clock"]
    limit = cfg["wait_limit_min"]
    station = alert["station"]
    action = alert.get("top_action")
    helps = action_helps(action)

    with st.container(border=True, key="action_card"):
        left, right = st.columns([3, 2])
        left.caption("**DO THIS NOW**")
        right.markdown(f"<div class='deadline'>{deadline(alert)}</div>", unsafe_allow_html=True)

        if helps:
            st.markdown(f"<div class='action'>{action['label']}.</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='action'>Warn waiting patients.</div>", unsafe_allow_html=True)

        sentences = [what_sentence(alert, clock, limit), why_sentence(alert, state, cfg)]
        if alert.get("cause") != "peak_load":
            sentences.append(affected_sentence(alert))
        st.write(" ".join(s for s in sentences if s))

        if helps:
            st.button("Apply", type="primary", key=f"apply_{station}_{clock}",
                      on_click=on_apply, args=(action, clock))
            st.write(effect_sentence(action, station, fc, cfg))
        else:
            st.warning(no_move_sentence(alert, fc))

    with st.expander("Why?"):
        render_why(alert)
    others = [r for r in recs if helps and r["action_id"] != action["action_id"]]
    if others:
        with st.expander("What if?"):
            for r in others:
                st.write(what_if_line(r, station))


def render_why(alert):
    contrib = alert.get("contributions") or {}
    rows = [{"Cause": CAUSE_NAMES[k].capitalize(),
             "Minutes": max(0, whole(contrib.get(k, 0)))}
            for k in ("demand_surge", "staffing_gap", "slow_processing")]
    df = pd.DataFrame(rows)
    chart = (
        alt.Chart(df)
        .mark_bar(color=COLOURS["secondary"], cornerRadiusEnd=4, height=18)
        .encode(
            x=alt.X("Minutes:Q", title="Minutes of expected wait explained",
                    axis=alt.Axis(tickMinStep=1, grid=False)),
            y=alt.Y("Cause:N", title=None, sort=None),
            tooltip=[alt.Tooltip("Cause:N"), alt.Tooltip("Minutes:Q", title="Minutes")],
        )
        .properties(height=120)
    )
    labels = chart.mark_text(align="left", dx=4, color=COLOURS["text"]).encode(text="Minutes:Q")
    st.altair_chart(chart + labels, width="stretch")
    st.write(bars_sentence(alert))


def tile_html(station, wait_now, wait_30, status, highlight):
    now = whole(wait_now)
    later = whole(wait_30)
    wait = f"{now} → {later} min" if abs(later - now) >= 5 else f"{now} min"
    border = f"2px solid {COLOURS['action']}" if highlight else f"1px solid {COLOURS['border']}"
    weight = "800" if status == "over limit" else "700"
    return (
        f"<div class='tile' style='border:{border}'>"
        f"<div class='tile-name'>{name(station)}</div>"
        f"<div class='tile-wait'>{wait}</div>"
        f"<div class='tile-status' style='color:{COLOURS[status]};font-weight:{weight}'>{status}</div>"
        f"</div>"
    )
