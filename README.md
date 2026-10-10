# Service Bottleneck Predictor

**Tells an outpatient shift supervisor which station will overload next, why, and which staff move prevents it.**

Prototype use case: hospital outpatient services. Built for Track 1 (Predictive Model).

**Live demo:** _add link_ · **Docs:** [PRD](docs/PRD.md) · [TRD](docs/TRD.md) · [Design](docs/DESIGN.md)

---

## Contents

- [The problem](#the-problem)
- [What it does](#what-it-does)
- [Quick start](#quick-start)
- [Using the demo](#using-the-demo)
- [How it works](#how-it-works)
- [Repository layout](#repository-layout)
- [Data](#data)
- [Evaluation](#evaluation)
- [Assumptions and limits](#assumptions-and-limits)
- [Team](#team)

## The problem

Outpatient staff are assigned to stations at the start of the day, but the bottleneck moves during it: registration clears, consultation fills, pharmacy piles up late. The supervisor sees it only when the waiting room is full, and a backlog that builds in 20 minutes takes hours to clear.

The cost is patients leaving without medication, delayed care, staff overtime and rushed consultations.

## What it does

| Stage | Question | On screen |
| --- | --- | --- |
| **Detect** | Which station will pass a 30-minute wait, and when? | Wait now and expected wait for each station |
| **Categorize** | What kind of problem is it? | Demand surge, staffing gap, slow processing, peak load or mixed |
| **Prioritize** | Which problem first? | One "Do this now" card; the rest ranked below |
| **Explain** | Why believe it? | Three plain sentences; cause bars on request |
| **Recommend** | What should I do? | One allowed staff move, its gain, its cost and the next bottleneck |

It is one screen with no login. It is deliberately not a dashboard: the screen leads with an action, and stays quiet when nothing needs doing.

## Quick start

Requires Python 3.11 or later.

```bash
git clone <repo-url>
cd <repo-folder>
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

Run commands from the repository root.

| Task | Command |
| --- | --- |
| Run the app | `streamlit run app/streamlit_app.py` |
| Regenerate all results | `python eval/run_eval.py` |
| Check the engine contract | `python -m pytest tests/` |
| Check a prepared CSV | `python engine/calibrate.py check data/raw/HospitalOPD-noname.csv` |
| Rebuild calibration from the real log | `python engine/calibrate.py` |

### Deploy

The live demo runs on Streamlit Community Cloud and redeploys on every push to `main`.

1. At [share.streamlit.io](https://share.streamlit.io), choose **Create app** and pick this repository.
2. Branch `main`, main file path `app/streamlit_app.py`.
3. Under **Advanced settings**, choose Python 3.12.
4. Deploy, then open the public link in a private window to confirm it loads with no login.

Tag each working checkpoint (`git tag checkpoint-1 && git push --tags`). If a push breaks the live link, redeploy the last tag. Idle apps go to sleep, so open the link 10 minutes before presenting.

## Using the demo

1. Pick a day: **Ordinary busy day**, **Doctor called away**, **Holiday rush** or **Pharmacy system slow**.
2. Press **Play**. The clinic replays in 5-minute steps from 08:00 to 16:00.
3. When a card appears, read the action and its cause. Open **Why?** for the cause breakdown or **What if?** for other moves.
4. Press **Apply** to make the move. The replay changes course and shows the day's outcome with and without it.
5. Open **Why trust this?** for the evaluation results and assumptions.

## How it works

One forward simulator of the clinic is used three ways:

| Use | Method |
| --- | --- |
| Forecast | Simulate the next 60 minutes from the current state, 30 times. The share of runs over the limit is the chance of a breach. |
| Cause | Repeat with one driver reset to normal (arrivals, staff, or service speed). The reset that removes the most wait is the cause. |
| Recommendation | Repeat with each allowed staff move applied. Keep the move that saves the most waiting overall. |

A gradient-boosted model forecasts arrivals so that surges are picked up early. An alert is raised only when the chance of a breach is high on two consecutive checks, which keeps false alarms down.

Full detail is in the [TRD](docs/TRD.md).

## Repository layout

```text
config.yaml        every tunable value: stations, staff, limits, allowed moves
engine/            simulator, forecast, cause, recommendation
  api.py           the six functions the app uses
  mock.py          stand-in outputs in the same shapes, used until each real function lands
app/               the single Streamlit screen
  streamlit_app.py replay bar, pathway strip, action card, also watching, why trust this
  cards.py         sentence templates and card rendering
data/              day specs, calibration, demo days
models/            trained arrival forecaster
eval/              evaluation script and results.json
tests/             contract test
docs/              PRD, TRD, design
.streamlit/        theme
```

## Data

| Source | Used for |
| --- | --- |
| [HospitalOPD event log](https://data.mendeley.com/datasets/j2hd2239dr/1) (Mendeley Data, DOI 10.17632/j2hd2239dr.1) | Calibrating arrival pattern, service times and pathway shares |
| Simulated clinic days | Training, tuning, testing, what-ifs and the policy comparison |

A real log cannot answer "what if we had moved someone" and has no cause labels, so results come from simulated days: 60 to train, 10 to tune, 20 held out for testing.

Put the raw CSV at `data/raw/HospitalOPD-noname.csv`, or pass its path to the command. The `data/raw/` folder is ignored by git; do not commit raw event logs.

```bash
python engine/calibrate.py check data/raw/HospitalOPD-noname.csv
python engine/calibrate.py data/raw/HospitalOPD-noname.csv
```

Calibration writes only derived summary numbers to `data/calibration.json`. The engine uses that file automatically when `calibration.use` is `true` in `config.yaml`.

_State here whether this build is calibrated on the real log or runs on the assumptions in `config.yaml`._

## Evaluation

`python eval/run_eval.py` writes `eval/results.json`. All results use the 20 held-out days.

| Run | Question |
| --- | --- |
| Forecast accuracy | Is the forecast better than two simple baselines? |
| Alert quality | Are alerts early and rarely wrong? |
| Cause accuracy | Is the named cause the true one? |
| Robustness | Does it hold up on noisy inputs and unseen two-cause days? |
| Decision impact | Does following the tool beat a supervisor who reacts after the limit is passed? |

**Results:** _to be added once the evaluation has run._

## Assumptions and limits

- Results are from simulated days, not a live clinic.
- Staff numbers and the four allowed moves are assumptions set in `config.yaml`.
- A moved staff member is assumed to work at full speed immediately.
- Patients do not abandon the queue in the simulation.
- The tool recommends staffing moves only. It makes no clinical decisions.

A pilot would need one thing from a hospital: a timestamped event-log export from its queue or records system.

## Team

_Add names and roles._

## Acknowledgements

HospitalOPD dataset, Mendeley Data. Check the dataset page for its licence and citation before reuse.
