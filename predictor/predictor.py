"""Service Bottleneck Predictor: the single screen (docs/DESIGN.md).

Top to bottom: navigation with clinic time, replay controls, patient flow,
the decision (action card or calm note) beside what else is being watched and
the moves applied, then the evidence. The app imports only engine/api.py.
"""

import reflex as rx

from . import components as ui
from .state import State


def index():
    return rx.el.div(
        ui.navbar(),
        rx.el.main(
            ui.controls(),
            ui.flow_section(),
            rx.el.div(
                rx.el.div(ui.decision(), class_name="decision"),
                rx.el.aside(
                    rx.cond(~State.closed, ui.watching_card()),
                    ui.moves_card(),
                    class_name="side",
                ),
                class_name="workspace",
            ),
            ui.trust_section(),
            ui.footer(),
            class_name="container",
        ),
        class_name="app",
    )


app = rx.App(
    theme=None,
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap",
        "/styles.css",
    ],
    head_components=[rx.el.link(rel="icon", href="/favicon.svg", type="image/svg+xml")],
)
app.add_page(
    index,
    route="/",
    title="Bottleneck Predictor",
    description="Which outpatient station will pass the 30-minute limit in the next hour, "
                "why, and the staff move that prevents it.",
    on_load=State.on_load,
)
