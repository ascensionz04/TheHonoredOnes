"""The screen's building blocks. Layout and look live in assets/styles.css."""

import reflex as rx

from . import view
from .state import State

STATUS_LEGEND = [("ok", "OK"), ("watch", "Watch"), ("breach", "Will breach"), ("over", "Over limit")]


def pill(status, word):
    return rx.el.span(rx.el.span(class_name="dot"), word, class_name=f"pill p-{status}")


# ---------- top bar ----------

def navbar():
    return rx.el.header(
        rx.el.div(
            rx.el.div(
                rx.el.div(rx.icon("activity", size=18, stroke_width=2.4), class_name="logo"),
                rx.el.div(
                    rx.el.div("Bottleneck Predictor", class_name="brand-name"),
                    rx.el.div("Outpatient services", class_name="brand-sub"),
                ),
                class_name="brand",
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.span("Clinic time", class_name="clock-label"),
                    rx.el.span(State.clock_text, class_name="clock-time num",
                               aria_label="Clinic time"),
                    class_name="clock",
                ),
                rx.el.span(
                    rx.el.span(class_name="dot"),
                    State.mode_label,
                    class_name=rx.cond(State.closed, "mode m-closed",
                                       rx.cond(State.playing, "mode m-live", "mode m-paused")),
                ),
                rx.el.button(
                    rx.color_mode_cond(light=rx.icon("moon", size=16), dark=rx.icon("sun", size=16)),
                    on_click=rx.toggle_color_mode,
                    class_name="icon-btn",
                    aria_label="Switch light or dark theme",
                    title="Switch theme",
                ),
                class_name="nav-right",
            ),
            class_name="nav-inner",
        ),
        class_name="nav",
    )


# ---------- replay controls ----------

def day_chip(opt):
    return rx.el.button(
        rx.el.span(rx.icon(opt.icon, size=16), class_name="chip-icon"),
        rx.el.span(
            rx.el.span(opt.name, class_name="chip-name"),
            rx.el.span(opt.tag, class_name="chip-tag"),
            class_name="chip-text",
        ),
        on_click=State.set_day(opt.name),
        class_name=rx.cond(State.day == opt.name, "day-chip active", "day-chip"),
        aria_pressed=rx.cond(State.day == opt.name, "true", "false"),
    )


def speed_control():
    return rx.el.div(
        *[rx.el.button(s, on_click=State.set_speed(s),
                       class_name=rx.cond(State.speed == s, "seg active", "seg"),
                       aria_pressed=rx.cond(State.speed == s, "true", "false"))
          for s in view.SPEEDS],
        class_name="segmented",
        role="group",
        aria_label="Replay speed",
    )


def timeline():
    hours = list(range(view.OPEN, view.CLOSE + 1, 120))
    return rx.el.div(
        rx.el.div(
            rx.el.div(class_name="tl-fill", style={"width": f"{State.progress}%"}),
            rx.foreach(State.applied_marks,
                       lambda m: rx.el.span(class_name="tl-mark", style={"left": f"{m}%"},
                                            title="Move applied")),
            rx.el.div(class_name="tl-thumb", style={"left": f"{State.progress}%"}),
            class_name="tl-track",
        ),
        rx.el.div(*[rx.el.span(f"{h // 60:02d}:{h % 60:02d}") for h in hours], class_name="tl-ticks"),
        class_name="timeline",
        aria_hidden="true",
    )


def controls():
    return rx.el.section(
        rx.el.div("Demo day", class_name="eyebrow"),
        rx.el.div(*[day_chip(o) for o in view.DAY_OPTIONS], class_name="day-chips"),
        rx.el.div(
            rx.el.div(
                rx.el.button(
                    rx.cond(State.playing,
                            rx.fragment(rx.icon("pause", size=16), "Pause"),
                            rx.fragment(rx.icon("play", size=16),
                                        rx.cond(State.closed, "Replay", "Play"))),
                    on_click=State.toggle_play,
                    class_name="btn btn-primary play-btn",
                ),
                rx.el.button(
                    rx.icon("skip-forward", size=15), "5 min",
                    on_click=State.step,
                    disabled=State.playing | State.closed,
                    class_name="btn btn-ghost",
                    title="Step forward 5 minutes",
                ),
                speed_control(),
                rx.el.button(rx.icon("rotate-ccw", size=15), "Reset",
                             on_click=State.reset_day, class_name="btn btn-ghost"),
                class_name="replay-row",
            ),
            timeline(),
            class_name="controls-bottom",
        ),
        class_name="panel controls",
    )


# ---------- patient flow ----------

def trend_icon(direction):
    return rx.match(
        direction,
        ("up", rx.icon("trending-up", size=14)),
        ("down", rx.icon("trending-down", size=14)),
        rx.icon("arrow-right", size=14),
    )


def station_tile(s, small=False):
    size = " is-small" if small else ""
    return rx.el.div(
        rx.el.div(
            rx.el.span(s.name, class_name="tile-name"),
            pill(s.status, s.status_word),
            class_name="tile-top",
        ),
        rx.el.div(
            rx.el.span(s.wait_now, class_name="tile-num num"),
            rx.el.span("min wait", class_name="tile-unit"),
            class_name="tile-wait",
        ),
        rx.el.div(trend_icon(s.trend_dir), rx.el.span(s.trend), class_name=f"tile-trend t-{s.trend_dir}"),
        rx.el.div(
            rx.el.div(class_name="meter-fill", style={"width": f"{s.fill}%"}),
            class_name="meter",
            title=f"Wait now against the {view.LIMIT}-minute limit",
        ),
        rx.el.div(
            rx.el.span(rx.icon("users", size=13), s.staff, class_name="foot-item"),
            rx.el.span(
                rx.cond(s.chance > 0, rx.fragment(s.chance, "% chance"), "Clear"),
                class_name="foot-item foot-chance",
                title=f"Chance of passing the {view.LIMIT}-minute limit within the hour",
            ),
            class_name="tile-foot",
        ),
        class_name=rx.cond(s.focus, f"tile s-{s.status} is-focus{size}", f"tile s-{s.status}{size}"),
        role="listitem",
    )


def connector():
    return rx.el.div(rx.icon("chevron-right", size=16), class_name="connector", aria_hidden="true")


def flow_section():
    st = State.screen.stations
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.el.h2("Patient flow", class_name="section-title"),
                rx.el.p("Wait now at each station, and the trend over the next 30 minutes.",
                        class_name="section-sub"),
            ),
            rx.el.div(*[pill(k, word) for k, word in STATUS_LEGEND], class_name="legend"),
            class_name="section-head",
        ),
        rx.cond(
            State.loaded & (st.length() == 5),
            rx.el.div(
                station_tile(st[0]),
                connector(),
                station_tile(st[1]),
                connector(),
                rx.el.div(
                    rx.el.span("If needed", class_name="branch-label"),
                    station_tile(st[2], small=True),
                    station_tile(st[3], small=True),
                    class_name="branch",
                ),
                connector(),
                station_tile(st[4]),
                class_name="route",
                role="list",
                aria_label="Stations in the order patients move",
            ),
            rx.el.div(*[rx.el.div(class_name="tile skeleton") for _ in range(5)], class_name="route-skeleton"),
        ),
        class_name="panel flow",
    )


# ---------- action card ----------

def cause_row(c):
    return rx.el.div(
        rx.el.span(c.label, class_name="cause-label"),
        rx.el.div(
            rx.el.div(class_name=rx.cond(c.top, "cause-fill top", "cause-fill"),
                      style={"width": f"{c.width}%"}),
            class_name="cause-track",
        ),
        rx.el.span(c.minutes, " min", class_name="cause-min num"),
        class_name="cause-row",
    )


def what_if_row(r):
    return rx.el.li(
        rx.el.div(r.label, class_name="whatif-label"),
        rx.el.div(
            rx.el.span(rx.icon("arrow-down", size=12), "Saves ", r.saved, " min",
                      class_name=rx.cond(r.saved > 0, "tag tag-good", "tag")),
            rx.el.span(rx.icon("arrow-up", size=12), "Adds ", r.added, " min elsewhere", class_name="tag"),
            rx.el.span("Busiest after: ", r.after, class_name="tag"),
            class_name="whatif-tags",
        ),
        class_name="whatif",
    )


def disclosure(icon, title, *body):
    return rx.el.details(
        rx.el.summary(
            rx.icon(icon, size=15),
            rx.el.span(title),
            rx.icon("chevron-down", size=15, class_name="chev"),
        ),
        rx.el.div(*body, class_name="disclosure-body"),
        class_name="disclosure",
    )


def action_card():
    c = State.screen.card
    return rx.el.section(
        rx.el.div(
            rx.el.span(rx.el.span(class_name="pulse"), "Do this now", class_name="band-label"),
            rx.el.span(rx.icon("clock", size=14), c.deadline, class_name="band-deadline"),
            class_name="band",
        ),
        rx.el.div(
            rx.el.span(rx.icon("map-pin", size=13), c.station_name, class_name="meta-chip"),
            rx.el.span(rx.icon("gauge", size=13), c.chance, "% chance", class_name="meta-chip"),
            class_name="meta",
        ),
        rx.el.h2(c.title, class_name="action-title"),
        rx.el.p(
            c.what, " ",
            rx.el.strong(c.why_head), " ", c.why_rest, " ",
            c.affected,
            class_name="action-body",
        ),
        rx.cond(
            c.helps,
            rx.el.div(
                rx.el.button(rx.icon("check", size=18, stroke_width=2.6), "Apply move",
                             on_click=State.apply_move, class_name="btn btn-apply"),
                rx.el.div(
                    rx.el.div(rx.icon("sparkles", size=13), "Expected effect", class_name="inset-label"),
                    rx.el.p(c.effect),
                    class_name="inset",
                ),
                class_name="apply-row",
            ),
            rx.el.div(
                rx.el.div(rx.icon("megaphone", size=13), "No move helps", class_name="inset-label"),
                rx.el.p(c.no_move),
                class_name="inset inset-warn",
            ),
        ),
        rx.el.div(
            disclosure("chart-bar-big", "Why?",
                       rx.el.div(rx.foreach(c.causes, cause_row), class_name="causes"),
                       rx.el.p(c.causes_note, class_name="fine")),
            rx.cond(
                c.what_ifs.length() > 0,
                disclosure("git-branch", "What if?",
                           rx.el.ul(rx.foreach(c.what_ifs, what_if_row), class_name="whatifs")),
            ),
            class_name="disclosures",
        ),
        class_name=f"action-card tone-{c.tone}",
        aria_live="polite",
    )


def note_card():
    mode = State.screen.mode
    return rx.el.section(
        rx.el.div(
            rx.match(
                mode,
                ("calm", rx.icon("circle-check", size=22)),
                ("watch", rx.icon("eye", size=22)),
                ("closed", rx.icon("moon", size=22)),
                rx.icon("triangle-alert", size=22),
            ),
            class_name="note-icon",
        ),
        rx.el.div(
            rx.el.h2(State.screen.note_title, class_name="note-title"),
            rx.el.p(State.screen.note_body, class_name="note-body"),
        ),
        class_name=f"note-card n-{mode}",
        aria_live="polite",
    )


def decision():
    return rx.cond(
        State.loaded,
        rx.cond(State.screen.mode == "alert", action_card(), note_card()),
        rx.el.div(class_name="action-card skeleton tall"),
    )


# ---------- side column ----------

def watch_row(a):
    return rx.el.li(
        rx.el.button(
            rx.el.span(class_name=f"wdot w-{a.tone}"),
            rx.el.span(
                rx.el.span(a.name, class_name="watch-name"),
                rx.el.span(a.when, class_name="watch-when"),
                class_name="watch-text",
            ),
            rx.el.span(a.cause, class_name="tag"),
            rx.icon("chevron-right", size=16, class_name="watch-chev"),
            on_click=State.select_station(a.station),
            class_name="watch-row",
            title="Show this in the action card",
        ),
    )


def side_card(icon, title, count, *body):
    return rx.el.section(
        rx.el.div(
            rx.el.div(rx.icon(icon, size=15), rx.el.h3(title), class_name="side-title"),
            count,
            class_name="side-head",
        ),
        *body,
        class_name="panel side-card",
    )


def watching_card():
    items = State.screen.watching
    return side_card(
        "radar", "Also watching",
        rx.cond(items.length() > 0, rx.el.span(items.length(), class_name="count"), rx.fragment()),
        rx.cond(
            items.length() > 0,
            rx.el.ul(rx.foreach(items, watch_row), class_name="watch-list"),
            rx.el.p("Nothing else is close to the limit.", class_name="empty"),
        ),
    )


def moves_card():
    o = State.screen.outcome
    return side_card(
        "history", "Moves applied",
        rx.cond(State.applied.length() > 0, rx.el.span(State.applied.length(), class_name="count"),
                rx.fragment()),
        rx.cond(
            State.applied.length() > 0,
            rx.el.ul(
                rx.foreach(State.applied, lambda a: rx.el.li(
                    rx.el.span(a.at, class_name="move-time num"),
                    rx.el.span(a.label, class_name="move-label"),
                    class_name="move",
                )),
                class_name="moves",
            ),
            rx.el.p("None yet. Apply a recommendation to see how the day changes.", class_name="empty"),
        ),
        rx.cond(
            State.screen.show_outcome,
            rx.el.div(
                rx.el.div(f"Patients waiting over {view.LIMIT} min today", class_name="compare-label"),
                rx.el.div(
                    rx.el.div(rx.el.span(o.without_pct, "%", class_name="cmp-num before num"),
                              rx.el.span(o.without_label, class_name="cmp-cap")),
                    rx.icon("arrow-right", size=18, class_name="cmp-arrow"),
                    rx.el.div(rx.el.span(o.with_pct, "%", class_name="cmp-num after num"),
                              rx.el.span(o.with_label, class_name="cmp-cap")),
                    class_name="compare-row",
                ),
                class_name="compare",
            ),
        ),
    )


# ---------- why trust this ----------

def trust_section():
    if not view.METRICS and not view.NOTES:
        body = [rx.el.p("Test results will appear here once the evaluation has run.", class_name="empty")]
    else:
        body = [
            rx.el.div(
                *[rx.el.div(rx.el.div(m.value, class_name="metric-value num"),
                            rx.el.p(m.caption, class_name="metric-caption"),
                            class_name="metric")
                  for m in view.METRICS],
                class_name="metrics",
            ),
            disclosure(
                "file-text", "Data and assumptions",
                rx.el.ul(*[rx.el.li(n) for n in view.NOTES + view.ASSUMPTIONS], class_name="notes"),
            ),
        ]
    days = (view.RESULTS or {}).get("test_days")
    sub = (f"Measured on {days} simulated clinic days held out from building the model."
           if days else "Evidence from the evaluation run.")
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.el.h2(rx.icon("shield-check", size=18), "Why trust this?", class_name="section-title"),
                rx.el.p(sub, class_name="section-sub"),
            ),
            class_name="section-head",
        ),
        *body,
        class_name="panel trust",
    )


def footer():
    mock = [rx.el.p("Demo numbers: the live engine is not connected yet, so this replay is illustrative.",
                    class_name="footnote")] if view.USES_MOCK else []
    return rx.el.footer(
        *mock,
        rx.el.p("Prototype on simulated clinic days. Recommends staffing moves only; "
                "makes no clinical decisions."),
        class_name="footer",
    )
