"""Sentence templates (DESIGN.md section 5) and card rendering.

Every sentence is filled only with numbers from the engine. Writing rules:
whole numbers, "chance" not "probability", no model terms, three sentences at
most above the Apply button, always say what happens next.
"""

from html import escape

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

STATUS_CLASS = {"ok": "s-ok", "watch": "s-watch", "will breach": "s-breach",
                "over limit": "s-over"}

CHART_FONT = "-apple-system, BlinkMacSystemFont, Segoe UI, system-ui, sans-serif"

# Small line icons, drawn in currentColor.
_SVG = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="{w}" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{d}</svg>')
ICONS = {
    "check": _SVG.format(w=2.6, d='<path d="M5 12.5l4.5 4.5L19 7.5"/>'),
    "eye": _SVG.format(w=2, d='<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/>'
                               '<circle cx="12" cy="12" r="3"/>'),
    "clock": _SVG.format(w=2.2, d='<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'),
    "moon": _SVG.format(w=2, d='<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>'),
    "chevron": _SVG.format(w=2.6, d='<path d="M9 5l7 7-7 7"/>'),
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
        added = whole(action["donor_wait_added_min"])
        if added >= 1:
            parts.append(f"It adds about {added} minutes at {donor}.")
        else:
            parts.append(f"It adds no noticeable wait at {donor}.")
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

def html(markup):
    st.markdown(markup, unsafe_allow_html=True)


def esc(text):
    return escape(str(text), quote=False)


def header_html(limit):
    return (
        "<div class='eyebrow'>Outpatient department &middot; Shift supervisor</div>"
        "<div class='title'>Bottleneck Predictor</div>"
        f"<p class='subtitle'>Which station will pass the {limit}-minute limit in the next hour, "
        "why, and the staff move that prevents it.</p>"
    )


def clock_html(clock):
    return (f"<div class='clock'><span class='eyebrow'>Clinic time</span>"
            f"<span class='clock-time'>{hhmm(clock)}</span></div>")


def section_head(title, legend=""):
    right = f"<span class='legend'>{esc(legend)}</span>" if legend else ""
    html(f"<div class='section-head'><span class='eyebrow'>{esc(title)}</span>{right}</div>")


def _tile(station, wait_now, wait_30, status, focus):
    now, later = whole(wait_now), whole(wait_30)
    if abs(later - now) >= 5:
        nxt = f"&rarr; {later} min in 30 min"
    else:
        nxt = "Steady for 30 min"
    cls = STATUS_CLASS[status]
    return (
        f"<div class='tile {cls}{' focus' if focus else ''}'>"
        f"<div class='tile-name'>{name(station)}</div>"
        f"<div class='tile-wait'><span class='num'>{now}</span><span class='unit'>min</span></div>"
        f"<div class='tile-next'>{nxt}</div>"
        f"<span class='pill {cls}'>{status}</span>"
        f"</div>"
    )


def flow_html(state, fc, statuses, focus_station):
    """Five stations in patient order. Laboratory and imaging are branches."""
    parts = []
    for i, station in enumerate(STATIONS):
        if i:
            if station == "imaging":
                parts.append("<div class='chev branch'>or</div>")
            else:
                parts.append(f"<div class='chev'>{ICONS['chevron']}</div>")
        parts.append(_tile(station, state["stations"][station]["wait_now_min"],
                           fc[station][30]["wait_p50"], statuses[station],
                           station == focus_station))
    return f"<div class='flow'>{''.join(parts)}</div>"


def state_card(kind, title, body):
    icon = {"s-ok": "check", "s-watch": "eye", "s-closed": "moon"}[kind]
    html(f"<div class='state'><div class='state-icon {kind}'>{ICONS[icon]}</div>"
         f"<div><div class='state-title'>{esc(title)}</div>"
         f"<div class='state-body'>{esc(body)}</div></div></div>")


def applied_html(label, at, without, with_, n_actions):
    which = "this action" if n_actions == 1 else "these actions"
    after = "with it" if n_actions == 1 else "with them"
    return (
        "<div class='applied'>"
        f"<div class='applied-head'><div class='state-icon s-ok'>{ICONS['check']}</div>"
        f"<div><div class='applied-title'>Applied at {hhmm(at)}</div>"
        f"<div class='applied-sub'>{esc(label)}.</div></div></div>"
        "<div class='compare'>"
        "<div class='compare-label'>Patients waiting over 30 minutes today</div>"
        f"<div class='stat'><div class='stat-num before'>{pct(without['share_over_30'])}%</div>"
        f"<div class='stat-cap'>without {which}</div></div>"
        "<div class='to'>&rarr;</div>"
        f"<div class='stat'><div class='stat-num after'>{pct(with_['share_over_30'])}%</div>"
        f"<div class='stat-cap'>{after}</div></div>"
        "</div></div>"
    )


def _bold_cause(sentence):
    """Make the 'Cause: x.' lead-in stand out."""
    for lead in ("Cause:", "Causes:"):
        if sentence.startswith(lead):
            head, _, rest = sentence.partition(". ")
            if rest:
                return f"<strong>{esc(head)}.</strong> {esc(rest)}"
            return f"<strong>{esc(sentence)}</strong>"
    return esc(sentence)


def render_action_card(alert, state, fc, recs, cfg, on_apply):
    """The 'Do this now' card. `recs` is recommend() for this station."""
    clock = state["clock"]
    limit = cfg["wait_limit_min"]
    station = alert["station"]
    action = alert.get("top_action")
    helps = action_helps(action)
    title = esc(action["label"]) + "." if helps else "Warn waiting patients."

    with st.container(key="action_card"):
        sentences = [esc(what_sentence(alert, clock, limit)),
                     _bold_cause(why_sentence(alert, state, cfg))]
        if alert.get("cause") != "peak_load":
            sentences.append(esc(affected_sentence(alert)))
        html("<div class='card-head'><span class='eyebrow action'>Do this now</span>"
             f"<span class='deadline'>{ICONS['clock']}{deadline(alert).capitalize()}</span></div>"
             f"<div class='action-title'>{title}</div>"
             f"<p class='card-body'>{' '.join(s for s in sentences if s)}</p>")

        if helps:
            st.button("Apply", type="primary", icon=":material/check:",
                      key=f"apply_{station}_{clock}", on_click=on_apply, args=(action, clock))
            html("<div class='inset'><div class='eyebrow'>Expected effect</div>"
                 f"<p>{esc(effect_sentence(action, station, fc, cfg))}</p></div>")
        else:
            html("<div class='inset warn'><div class='eyebrow'>No move helps</div>"
                 f"<p>{esc(no_move_sentence(alert, fc))}</p></div>")

        with st.expander("Why?"):
            render_why(alert)
        others = [r for r in recs if helps and r["action_id"] != action["action_id"]]
        if others:
            with st.expander("What if?"):
                items = "".join(f"<li>{_what_if_html(r, station)}</li>" for r in others)
                html(f"<ul class='whatif'>{items}</ul>")


def _what_if_html(action, station):
    head, _, rest = what_if_line(action, station).partition(": ")
    return f"<strong>{esc(head)}</strong>: {esc(rest)}"


def render_why(alert):
    contrib = alert.get("contributions") or {}
    rows = [{"Cause": CAUSE_NAMES[k].capitalize(),
             "Minutes": max(0, whole(contrib.get(k, 0)))}
            for k in ("demand_surge", "staffing_gap", "slow_processing")]
    df = pd.DataFrame(rows)
    base = alt.Chart(df).encode(
        x=alt.X("Minutes:Q", title="Minutes of expected wait explained",
                axis=alt.Axis(tickMinStep=1, grid=False, domain=False, tickColor="#C9D4D6")),
        y=alt.Y("Cause:N", title=None, sort=None, axis=alt.Axis(domain=False, ticks=False)),
        tooltip=[alt.Tooltip("Cause:N"), alt.Tooltip("Minutes:Q", title="Minutes")],
    )
    bars = base.mark_bar(color="#7C8F94", cornerRadiusEnd=4, height=16)
    labels = base.mark_text(align="left", dx=6, color="#0F2A33",
                            fontWeight=600).encode(text="Minutes:Q")
    chart = ((bars + labels).properties(height=118)
             .configure(background="transparent", font=CHART_FONT)
             .configure_view(stroke=None)
             .configure_axis(labelColor="#5B6F74", titleColor="#5B6F74",
                             labelFontSize=12, titleFontSize=11, titleFontWeight=500))
    st.altair_chart(chart, width="stretch")
    html(f"<p class='fineprint'>{esc(bars_sentence(alert))}</p>")


def watching_label(alert, status):
    dot = ":red[●]" if status in ("will breach", "over limit") else ":orange[●]"
    return f"{dot}  {watching_line(alert)}"


def trust_html(statements):
    return "<ul class='trust'>" + "".join(f"<li>{esc(s)}</li>" for s in statements) + "</ul>"
