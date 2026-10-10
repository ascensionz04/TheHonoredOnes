"""Session state for the one screen: replay controls, applied moves, and the
current render (a view.Screen) rebuilt from the engine on every change."""

import asyncio
import logging

import reflex as rx

from . import view
from . import wording as w

log = logging.getLogger(__name__)


class State(rx.State):
    day: str = view.FIRST_DAY
    clock: int = view.OPEN
    playing: bool = False
    speed: str = "Fast"
    selected_station: str = ""
    applied: list[view.Applied] = []
    screen: view.Screen = view.Screen()
    loaded: bool = False

    _actions: list[tuple[str, int]] = []
    _loop: int = 0   # bumped to stop a running replay loop

    # ---------- derived values ----------

    @rx.var
    def clock_text(self) -> str:
        return w.hhmm(self.clock)

    @rx.var
    def closed(self) -> bool:
        return self.clock >= view.CLOSE

    @rx.var
    def mode_label(self) -> str:
        if self.clock >= view.CLOSE:
            return "Clinic closed"
        return "Replaying" if self.playing else "Paused"

    @rx.var
    def progress(self) -> float:
        return round((self.clock - view.OPEN) / (view.CLOSE - view.OPEN) * 100, 2)

    @rx.var
    def applied_marks(self) -> list[float]:
        span = view.CLOSE - view.OPEN
        return [round((at - view.OPEN) / span * 100, 2) for _, at in self._actions]

    # ---------- internals ----------

    def _refresh(self):
        day = view.DEMO_DAYS[self.day]
        try:
            self.screen = view.build(day, self.clock, tuple(self._actions), self.selected_station)
        except Exception:  # noqa: BLE001 - show a plain message, never a stack trace
            log.exception("engine call failed for day %s at %s", self.day, self.clock)
            self.screen = view.Screen(mode="error", note_title="Something went wrong",
                                      note_body=view.DATA_MISSING)
            self.playing = False
        if self.selected_station and self.screen.card.station != self.selected_station:
            self.selected_station = ""
        self.loaded = True

    def _reset(self):
        self._loop += 1
        self.clock = view.OPEN
        self.playing = False
        self._actions = []
        self.applied = []
        self.selected_station = ""

    # ---------- events ----------

    @rx.event
    def on_load(self):
        if self.day not in view.DEMO_DAYS:
            self.day = view.FIRST_DAY
        self._refresh()

    @rx.event
    def set_day(self, name: str):
        if name not in view.DEMO_DAYS:
            return
        self._reset()
        self.day = name
        self._refresh()

    @rx.event
    def reset_day(self):
        self._reset()
        self._refresh()

    @rx.event
    def set_speed(self, speed: str):
        if speed in view.SPEEDS:
            self.speed = speed

    @rx.event
    def toggle_play(self):
        if self.clock >= view.CLOSE:
            self._reset()
            self._refresh()
        self.playing = not self.playing
        self._loop += 1
        if self.playing:
            return State.run_replay

    @rx.event
    def step(self):
        """Advance one tick while paused."""
        if self.playing or self.clock >= view.CLOSE:
            return
        self.clock = min(view.CLOSE, self.clock + view.TICK)
        self._refresh()

    @rx.event
    def apply_move(self):
        card = self.screen.card
        if not card.helps or self.clock >= view.CLOSE:
            return
        if any(a == card.action_id and at == self.clock for a, at in self._actions):
            return
        self._actions = self._actions + [(card.action_id, self.clock)]
        self.applied = self.applied + [view.Applied(label=card.action_label, at=w.hhmm(self.clock))]
        self.selected_station = ""
        self._refresh()

    @rx.event
    def select_station(self, station: str):
        self.selected_station = station
        self._refresh()

    @rx.event(background=True)
    async def run_replay(self):
        async with self:
            me = self._loop
        while True:
            async with self:
                if not self.playing or self._loop != me:
                    return
                delay = view.SPEEDS.get(self.speed, 0.5)
            await asyncio.sleep(delay)
            async with self:
                if not self.playing or self._loop != me:
                    return
                self.clock = min(view.CLOSE, self.clock + view.TICK)
                self._refresh()
                if self.clock >= view.CLOSE:
                    self.playing = False
                    return
