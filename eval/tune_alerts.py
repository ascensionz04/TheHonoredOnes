"""Choose the alert thresholds on the 10 tuning days.

    python eval/tune_alerts.py

Sweeps raise_at from 0.2 to 0.8 (clear_at stays at two thirds of it, as in the starting
guess of 0.6 and 0.4) and reports, for each setting, breaches caught and false alarms per
day. The setting to use is the one that catches the most breaches within the false-alarm
budget in config.yaml; ties go to fewer false alarms, then the longer warning time. This script only prints and writes
eval/tuning.json: put the chosen values in config.yaml by hand so the config stays the
single source of truth. Test days are never read here.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import sim  # noqa: E402
from eval.run_eval import P, alert_quality, rule, watch  # noqa: E402


def main():
    days = sim.day_ids("tune")
    budget = float(P.cfg["alert"]["false_alarm_budget_per_day"])
    ticks = int(P.cfg["alert"]["ticks"])
    probs = {d: watch(d, cause=False)["probs"] for d in days}
    rows = []
    for raise_at in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
        settings = (raise_at, round(raise_at * 2 / 3, 2), ticks)
        q = alert_quality(days, {d: rule(probs[d], settings) for d in days})
        rows.append({"raise_at": raise_at, "clear_at": settings[1], "ticks": ticks,
                     **{k: q[k] for k in ("alerts", "breaches", "breaches_caught_early", "recall",
                                          "precision", "median_warning_min", "false_alarms_per_day")}})
        print(rows[-1])
    ok = [r for r in rows if r["false_alarms_per_day"] <= budget]
    best = max(ok, key=lambda r: (r["breaches_caught_early"], -r["false_alarms_per_day"],
                                  r["median_warning_min"] or 0)) if ok else None
    print("within budget of", budget, "per day ->", best)
    (ROOT / "eval" / "tuning.json").write_text(json.dumps(
        {"tuning_days": days, "false_alarm_budget_per_day": budget, "sweep": rows, "chosen": best},
        indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
