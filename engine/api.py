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
