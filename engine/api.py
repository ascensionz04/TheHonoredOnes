<<<<<<< HEAD
"""The six functions the app imports. Nothing else in engine/ is part of the contract.

All six are the real engine. engine/mock.py keeps the hard-coded versions in the same
shapes; tests/test_contract.py checks the two stay in step.

Conventions
- day is a day id from data/days.json (or data/demo_days.json, which names four of them).
- clock is minutes since midnight (625) or "HH:MM" ("10:25"); state["clock"] is minutes.
- actions is a tuple of (action_id, start_minute); each lasts 60 minutes.
- Every function is deterministic for the same inputs and returns fresh objects.
"""
from .diagnose import diagnose
from .forecast import forecast
from .recommend import alerts, recommend
from .sim import day_outcome, get_state

__all__ = ["get_state", "forecast", "diagnose", "recommend", "alerts", "day_outcome"]
=======
"""The six functions the app imports. Nothing else in engine/ is imported by app/.

Each line re-exports the mock until the real function lands; swap one line at
a time (e.g. `from engine.sim import get_state, day_outcome`).
"""

from engine.mock import get_state, day_outcome  # noqa: F401
from engine.mock import forecast  # noqa: F401
from engine.mock import diagnose  # noqa: F401
from engine.mock import recommend, alerts  # noqa: F401
>>>>>>> c584d7444b6ef316e06f2a4f18c168138bd00e19
