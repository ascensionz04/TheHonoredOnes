# Design Document: Service Bottleneck Predictor

**Prototype use case:** Hospital outpatient services
**Status:** Draft v1, 10 October 2026
**Related docs:** [PRD.md](PRD.md) (requirements), [TRD.md](TRD.md) (engine and data)

This document specifies the single screen: its layout, its states, its exact wording and how to build it in Streamlit.

---

## 1. Design principles

| Principle | What it means in practice |
| --- | --- |
| **Decision first** | The largest thing on screen is a recommended action. Numbers appear only to support it. |
| **Not a dashboard** | No chart is visible until the user clicks something. No grid of gauges, no sidebar of filters, no second page. |
| **Calm by default** | When nothing needs doing, the screen says so in one line. Silence is a feature. |
| **Plain language** | A supervisor reads the card once and can repeat the action and the reason. No model terms. |
| **Show the trade-off** | Every recommendation names its gain, its cost elsewhere, and what happens next. |
| **Never colour alone** | Every status has a word as well as a colour. |
| **No barriers** | No login, no setup, no empty state on first load. The link opens into a running demo. |

## 2. Screen layout

One page, one column, read top to bottom. Five zones.

```text
+----------------------------------------------------------------+
| 1 REPLAY BAR                                                   |
| Day: [Doctor called away v]   > Play   Speed x60   10:25  Reset|
+----------------------------------------------------------------+
| 2 PATHWAY STRIP                                                |
| Registration > Consultation > Laboratory | Imaging > Pharmacy  |
|   6 min         24 > 41 min     9 min       12 min    15 min   |
|   ok            will breach     ok          ok        ok       |
+----------------------------------------------------------------+
| 3 ACTION CARD                                                  |
| DO THIS NOW                                 act within 20 min  |
| Open the reserve room with the on-call doctor.                 |
| Consultation is likely to pass 30 minutes by 10:45 (80%).      |
| Cause: staffing gap. 3 of 4 doctors are on duty.               |
| [ Apply ]                                                      |
| > Why?        > What if?                                       |
+----------------------------------------------------------------+
| 4 ALSO WATCHING (1)                                            |
| Pharmacy: may pass the limit in about 50 min. Demand surge.    |
+----------------------------------------------------------------+
| 5 > Why trust this?                                            |
+----------------------------------------------------------------+
```

All numbers in this document's sketches and examples are illustrative.

| Zone | Purpose | Brief stage |
| --- | --- | --- |
| 1 Replay bar | Drives the demo; stands in for a live feed | — |
| 2 Pathway strip | Where patients are waiting now and soon | Detect |
| 3 Action card | The one thing to do, and why | Categorize, Explain, Recommend |
| 4 Also watching | Other problems, in rank order | Prioritize |
| 5 Why trust this? | Evidence and assumptions | Proof |

## 3. Components

### 3.1 Replay bar

| Element | Behaviour |
| --- | --- |
| Day picker | Four named days (section 7). Changing the day resets the clock and clears applied actions. |
| Play / Pause | Toggles the replay. Label shows the action it will perform. |
| Speed | Three steps: slow, normal, fast. |
| Clock | Current simulated time, 24-hour, e.g. `10:25`. |
| Reset | Returns to 08:00 and clears applied actions. |

The replay bar is visually quiet. It is demo scaffolding, not part of the product.

### 3.2 Pathway strip

Five station tiles in one row, in the order patients move through the clinic. Each tile shows three lines:

1. Station name.
2. Wait now, then expected wait in 30 minutes when they differ by 5 minutes or more: `24 > 41 min`. Otherwise just `9 min`.
3. Status word.

Statuses:

| Status word | Condition | Colour |
| --- | --- | --- |
| `ok` | No alert; chance of passing the limit is below the clear threshold | Green |
| `watch` | Chance is above the clear threshold but no alert is raised | Amber |
| `will breach` | Alert raised; current wait still under the limit | Red |
| `over limit` | Current wait estimate is above the limit | Dark red |

The tile for the station in the action card gets a heavier border so the eye connects the two.

### 3.3 Action card

The only prominent element on the screen. Contents, in order:

| Line | Content | Rule |
| --- | --- | --- |
| Header | `DO THIS NOW` and, right-aligned, `act within N min` | N is minutes to breach |
| Action | The recommended move, as an instruction | Largest text on the screen; one sentence |
| What | What will happen and when | One sentence, with the chance in brackets |
| Why | The cause and the fact behind it | One sentence starting `Cause:` |
| Effect | Gain, cost and next bottleneck | One sentence; shown under the Apply button |
| Apply | Primary button | Applies the move in the replay |

Two expanders sit under the card, closed by default.

**Why?** shows three horizontal bars, one per cause, sized by the minutes of wait each explains, with one sentence: "Most of the expected wait comes from the staffing gap."

**What if?** lists the other allowed moves, one line each:
`Send the float nurse to laboratory: saves 0 min at consultation, adds 0 min elsewhere. Next bottleneck: consultation.`

### 3.4 After Apply

- The Apply button is replaced by a confirmation: `Applied at 10:25.`
- One outcome line appears under the card:
  `Today, patients waiting over 30 minutes: 31% without this action, 12% with it.`
- The replay continues with the action in force, so the pathway strip visibly changes course.
- The card then shows the next alert, if any.

### 3.5 Also watching

Remaining alerts, one line each, highest priority first:
`Pharmacy: may pass the limit in about 50 min. Demand surge.`

Selecting a line shows that alert in the action card. The header count, `Also watching (1)`, is hidden when there are none.

### 3.6 Why trust this?

One collapsed section at the bottom. When opened it shows four plain statements read from `eval/results.json`:

1. `Warned a median of N minutes before a station passed the limit.`
2. `False alarms: N per day.`
3. `Named the right cause in N of M test cases.`
4. `Following the top action cut patients waiting over 30 minutes from X% to Y%, against a supervisor who reacts only after the limit is passed.`

Beneath them, in smaller text:

- What is real: `Arrival pattern, service times and pathway shares are calibrated on a public outpatient event log.` (or the assumptions statement if calibration was skipped)
- What is simulated: `Results are from 20 simulated test days not used to build the model.`
- The list of assumptions from `results.json`.

No statement is shown until its number exists.

## 4. Screen states

| State | Pathway strip | Action card area | Also watching |
| --- | --- | --- | --- |
| **Calm** | All `ok` | `No action needed. All stations are expected to stay under 30 minutes for the next hour.` | Hidden |
| **Watch** | One or more `watch` | `No action needed yet. Keeping an eye on Pharmacy.` | Hidden |
| **Alert with action** | One or more `will breach` | Full action card | Other alerts |
| **Alert, no move helps** | `will breach` | Card with the "no move helps" text and no Apply button | Other alerts |
| **Peak load** | `will breach` | Card with the peak-load sentence; action if one helps | Other alerts |
| **Action applied** | Updating | Confirmation and outcome line | Other alerts |
| **Day finished** | Final values | `Clinic closed. Patients who waited over 30 minutes today: X%.` plus the with/without line if an action was applied | Hidden |
| **Loading** | Previous values | `Checking the next hour...` | Previous values |
| **Data missing** | Hidden | `Demo data could not be loaded. Choose another day or press Reset.` | Hidden |

The calm state must be shown in the demo. It is the visible evidence that the tool minimises false alarms.

## 5. Wording

### 5.1 Sentence templates

Filled only with numbers from the engine. One template per case.

| Case | Template |
| --- | --- |
| What (all causes) | `{Station} is likely to pass the 30-minute limit by {time} ({chance}% chance).` |
| Why: staffing gap | `Cause: staffing gap. {on} of {roster} {staff type} are on duty.` |
| Why: demand surge | `Cause: demand surge. Arrivals are {ratio} times the usual level for this hour.` |
| Why: slow processing | `Cause: slow processing. Each patient is taking {now} minutes against the usual {usual}.` |
| Why: mixed | `Causes: {cause 1} and {cause 2}, in roughly equal parts.` |
| Why: peak load | `Nothing unusual has happened; the normal peak is more than {roster} {staff type} can clear.` |
| Affected | `About {n} patients will be affected.` |
| Effect | `{Action, as a gerund} for an hour cuts the {station} wait by about {saved} minutes.` |
| Cost | `It adds about {added} minutes at {donor}.` (omitted when the staff member comes from the float pool) |
| Next | `{Next station} becomes the busiest station about {m} minutes later.` |
| No move helps | `No allowed staff move reduces the wait. Tell waiting patients to expect about {wait} minutes.` |

### 5.2 Worked example

> **Open the reserve room with the on-call doctor.**
> Consultation is likely to pass the 30-minute limit by 10:45 (80% chance).
> Cause: staffing gap. 3 of 4 doctors are on duty. About 18 patients will be affected.
>
> Opening the reserve room for an hour cuts the consultation wait by about 12 minutes. Pharmacy becomes the busiest station about 40 minutes later.

### 5.3 Writing rules

- Three sentences at most above the Apply button.
- Whole numbers only. Minutes to the nearest minute, chance to the nearest 5%.
- Prefix estimates with "about". Never show decimals.
- Times in 24-hour `HH:MM`.
- The action is an instruction to a person: starts with a verb, names who moves and where.
- Always say what happens next, even if the answer is "no further bottleneck expected in the next hour".

### 5.4 Vocabulary

| Use | Avoid |
| --- | --- |
| chance | probability, confidence, likelihood score |
| wait | latency, delay metric, queue time |
| station | node, stage, server |
| staff, doctor, clerk, nurse | resource, server, capacity unit |
| pass the 30-minute limit | breach, SLA violation, threshold exceedance |
| cause | root cause, driver, attribution |
| busiest station | bottleneck (acceptable in the pitch, not on the card) |
| expected | forecast, predicted, p50 |

`will breach` is kept as a status word on the tile because it is short; everywhere else use "pass the limit".

## 6. Visual style

The look follows Apple's interface conventions, adapted for the web: white cards on a light grey page, one translucent toolbar, system type with size-specific tracking, and instant feedback when a control is pressed. All values live in `app/style.py`.

### 6.1 Colour

| Role | Hex | Used for |
| --- | --- | --- |
| Page | `#F5F5F7` | Background behind the cards |
| Card | `#FFFFFF` | Station tiles, action card, lists, expanders |
| Fill | `#F2F2F5` | Inset boxes inside the card (expected effect) |
| Hairline | `rgba(0,0,0,0.08)` | Card outlines and row separators |
| Text | `#1D1D1F` | Headings, action sentence, numbers |
| Secondary text | `#515154` | Card sentences, station names |
| Tertiary text | `#6E6E73` | Labels, captions, assumptions |
| Action | `#0066CC` | Apply button, action card ring, focused station tile |
| OK | `#1E7B3E` | `ok` status, improved outcome figure |
| Watch | `#A34F00` | `watch` status, "no move helps" box |
| Breach | `#C4161C` | `will breach` status, deadline badge |
| Over limit | `#8E0F14` | `over limit` status (solid badge, white text) |

Colour carries status only, plus the action blue for the one thing to do. A red word always means something. Status badges are tinted pills with a dot and the word; `over limit` is a solid pill so it differs from `will breach` by shape as well as shade. If you change these values, check that text remains legible against its background.

### 6.2 Type and spacing

One family throughout: the system font (`-apple-system`, SF Pro on Apple devices, Segoe UI on Windows). Hierarchy comes from weight, size and leading together.

| Element | Treatment |
| --- | --- |
| Page title | 2.25 rem, bold, tracking −0.025 em, leading 1.08 |
| Action sentence | Largest text in the card: up to 2 rem, bold, tracking −0.022 em |
| Card sentences | 1.04 rem, leading 1.55, secondary colour; "Cause: …" lead-in in bold |
| Wait values | 1.85 rem, semibold, tabular figures, tracking −0.03 em |
| Clock | 1.7 rem, semibold, tabular figures |
| Labels ("DO THIS NOW", "PATIENT FLOW") | 0.72 rem, uppercase, semibold, tracking +0.06 em |
| Status words | Small tinted pill, semibold |

Cards use 16–22 px corner radius and a soft two-layer shadow; the action card has the largest radius and the deepest shadow. Generous space above and below the action card; tight spacing inside the pathway strip.

### 6.3 Materials and motion

- **Toolbar:** the replay bar is a translucent, blurred layer (`backdrop-filter`) that stays at the top while the page scrolls under it.
- **Press feedback:** buttons scale to 97% on press, within 100 ms. Feedback comes on press, not release.
- **No motion on replay ticks.** The screen re-renders every 5 simulated minutes, so nothing animates on change, and Streamlit's dimming of stale elements is turned off to avoid flicker.
- **Preferences:** reduced motion removes press scaling; reduced transparency makes the toolbar solid; increased contrast darkens hairlines and secondary text.

### 6.4 Theme file

`.streamlit/config.toml`:

```toml
[theme]
base = "light"
primaryColor = "#0066CC"
backgroundColor = "#F5F5F7"
secondaryBackgroundColor = "#FFFFFF"
textColor = "#1D1D1F"
font = "sans serif"
```

## 7. Demo days

| Name in picker | Scenario | What the audience sees |
| --- | --- | --- |
| Ordinary busy day | Normal | Mostly calm. A short spike at peak, a `watch`, no alert. Shows restraint. |
| Doctor called away | Staffing gap at consultation, mid-morning | `will breach` at consultation while the current wait is still under the limit. Action: open the reserve room. Pharmacy flagged as next. |
| Holiday rush | Demand surge from opening | Registration fills first, then the pressure moves to consultation. Shows the bottleneck moving. |
| Pharmacy system slow | Slow processing at pharmacy, early afternoon | Cause is slow processing, not volume. Action: fast-track repeat prescriptions or move a clerk. |

Pick the specific day for each from the 20 test days after the engine works, choosing ones where the story is clear.

## 8. Interaction flow

The path the 3-minute demo follows:

1. Screen opens on "Doctor called away", paused at 08:00, calm state.
2. Press Play at fast speed. Tiles update every tick.
3. Consultation turns `will breach`. The action card appears. Pause.
4. Read the card aloud. Open "Why?": the staffing bar is longest.
5. Point at "Also watching": pharmacy is ranked second.
6. Press Apply. Confirmation and outcome line appear.
7. Press Play. Consultation recovers; the card moves on to pharmacy.
8. Switch to "Ordinary busy day". Play. The screen stays calm.
9. Open "Why trust this?".

Every step uses a control that is visible without scrolling on a laptop screen, except step 9.

## 9. Accessibility

- Status is always a word plus a colour.
- Buttons have text labels, not icons alone.
- The page reads correctly top to bottom as plain text.
- Nothing depends on hover.
- Text can be read from the back of a room when projected: the action sentence must be legible at presentation distance.

## 10. Streamlit implementation

| Zone | Streamlit elements |
| --- | --- |
| Page | `st.set_page_config(page_title=..., layout="centered", initial_sidebar_state="collapsed")` |
| Replay bar | `st.columns` holding `st.selectbox` (day), `st.button` (Play/Pause), `st.select_slider` (speed), `st.markdown` (clock), `st.button` (Reset) |
| Pathway strip | One `st.markdown` HTML block: a five-column grid of station tiles with chevrons |
| Status words | Coloured markdown: `:green[ok]`, `:orange[watch]`, `:red[will breach]`, bold `:red[over limit]` |
| Action card | `st.container(border=True)`; `st.caption` for the header, `st.subheader` for the action, `st.write` for sentences, `st.button(..., type="primary")` for Apply |
| Why? / What if? | `st.expander`; bars with a small Altair horizontal bar chart |
| Outcome line | `st.success` |
| Calm and watch states | `st.success` and `st.info` |
| No move helps | `st.warning` |
| Also watching | One `st.button` per line that sets the selected station in `st.session_state` |
| Why trust this? | `st.expander` with `st.markdown` statements and `st.caption` for assumptions |
| Errors | `st.error` with the plain message from section 4 |

Session state keys: `day`, `clock`, `playing`, `speed`, `actions`, `selected_station`.

Replay loop: when `playing` is true, sleep for the speed's interval, add 5 minutes to `clock`, and call `st.rerun()`. Stop at closing time.

If five tiles are cramped in the centred layout, switch to `layout="wide"` and keep the action card in a centred middle column.

## 11. What this screen must not become

- More than one chart visible without a click.
- A sidebar, tabs or a second page.
- A table of all stations with many columns.
- Gauges, sparklines or KPI tiles beyond the five station tiles.
- Settings, filters or date ranges.
- A sign-in step.

If something new is proposed, the test is: does it help the supervisor decide what to do in the next hour? If not, it goes behind an expander or is left out.
