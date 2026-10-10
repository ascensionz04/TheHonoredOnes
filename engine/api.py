"""The six functions the app imports. Nothing else in engine/ is part of the contract.

Hour 1: every function is the fake from mock.py. Each is swapped for the real one as it
lands, so the app never changes an import.
"""
from .mock import alerts, day_outcome, diagnose, forecast, get_state, recommend

__all__ = ["get_state", "forecast", "diagnose", "recommend", "alerts", "day_outcome"]
