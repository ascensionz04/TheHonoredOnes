"""Visual style for the single screen (DESIGN.md section 6).

Direction: a ward board, not a dashboard. Cool clinical white page, deep
navy-teal ink, one typeface (Public Sans, built for public-service screens).
Colour carries status only: green OK, amber watch, red breach. The action card
is the one loud element: a solid status band on top, the move in large type.
The pathway is one connected route, read left to right in the order patients
move. No entrance motion, because the replay re-renders every tick.
"""

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700&display=swap');

:root {
  --page: #F3F6F7;
  --surface: #FFFFFF;
  --fill: #EEF3F4;
  --ink: #0F2A33;
  --ink-2: #3E555D;
  --ink-3: #566B73;
  --line: #D9E2E5;
  --line-strong: #C3D0D4;
  --ok: #1D7346;      --ok-wash: #E7F3EC;
  --watch: #975200;   --watch-wash: #FBF1E3;
  --breach: #BA2230;  --breach-wash: #FBECEC;
  --over: #8C1722;
  --focus-ring: 0 0 0 3px rgba(15, 42, 51, 0.28);
  --font: "Public Sans", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

/* ---------- page ---------- */
.stApp { background: var(--page); color: var(--ink); font-family: var(--font); }
/* Streamlit sets its own face on inner elements; icons live outside these. */
.stApp [data-testid="stMarkdownContainer"], .stApp [data-testid="stMarkdownContainer"] *,
.stApp button, .stApp input, .stApp [data-baseweb="select"] *, .stApp [role="listbox"] *,
.stApp [data-testid="stExpander"] summary p { font-family: var(--font); }
[data-testid="stHeader"], [data-testid="stDecoration"] { display: none; }
.block-container, [data-testid="stMainBlockContainer"] {
  max-width: 880px; padding: 2rem 1rem 4rem 1rem; }
/* The replay re-renders every tick; never dim stale elements. */
[data-stale="true"] { opacity: 1 !important; transition: none !important; }
.num { font-variant-numeric: tabular-nums; }

/* ---------- header ---------- */
.hd { display: flex; justify-content: space-between; align-items: flex-end; gap: 1.5rem;
      padding-bottom: 1rem; }
.hd-title { font-size: 1.6rem; font-weight: 700; letter-spacing: -0.015em; line-height: 1.15;
            color: var(--ink); }
[data-testid="stMarkdownContainer"] p.hd-sub { margin: 0.35rem 0 0 0; max-width: 46ch;
  font-size: 1rem; line-height: 1.5; color: var(--ink-2); }
.hd-clock { display: flex; flex-direction: column; align-items: flex-end; flex: 0 0 auto; }
.hd-time { font-size: 2.6rem; font-weight: 700; line-height: 1; letter-spacing: -0.02em;
           color: var(--ink); font-variant-numeric: tabular-nums; }
.hd-mode { display: inline-flex; align-items: center; gap: 0.4rem; margin-top: 0.35rem;
           font-size: 0.85rem; font-weight: 600; color: var(--ink-3); }
.hd-mode::before { content: ""; width: 0.55rem; height: 0.55rem; border-radius: 50%;
                   border: 2px solid currentColor; box-sizing: border-box; }
.hd-mode.live { color: var(--ok); }
.hd-mode.live::before { background: currentColor; }

/* ---------- replay controls: a quiet strip between two rules ---------- */
.st-key-toolbar { border-top: 1px solid var(--line); border-bottom: 1px solid var(--line);
                  padding: 0.65rem 0; }
.st-key-toolbar [data-testid="stHorizontalBlock"] { gap: 0.6rem; }

.stButton button {
  min-height: 2.5rem; border-radius: 8px; font-weight: 600; color: var(--ink);
  background: var(--surface); border: 1px solid var(--line-strong); box-shadow: none; }
.stButton button:hover { background: var(--fill); border-color: var(--ink-3); color: var(--ink); }
.stButton button:active { background: #E2EAEC; }
.stButton button:focus-visible { outline: none; box-shadow: var(--focus-ring); }
.stButton button[data-testid="stBaseButton-primary"] {
  background: var(--ink); border: 1px solid var(--ink); color: #FFFFFF;
  padding: 0.55rem 1.5rem; font-size: 1rem; }
.stButton button[data-testid="stBaseButton-primary"]:hover { background: #1C3E49; border-color: #1C3E49; color: #FFFFFF; }
.stButton button[data-testid="stBaseButton-primary"] p,
.stButton button[data-testid="stBaseButton-primary"] span { color: #FFFFFF; }

/* select box: older Streamlit (baseweb) and newer (react-aria) markup */
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stSelectbox"] .react-aria-ComboBox > [role="group"] {
  min-height: 2.5rem; border-radius: 8px; background: var(--surface);
  border: 1px solid var(--line-strong); color: var(--ink); }
[data-testid="stSelectbox"] input, [data-testid="stSelectbox"] [data-baseweb="select"] * {
  font-weight: 600; color: var(--ink); }
[data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within,
[data-testid="stSelectbox"] .react-aria-ComboBox > [role="group"]:focus-within {
  box-shadow: var(--focus-ring); border-color: var(--ink-3); }

/* speed: older (baseweb) and newer (react-aria radiogroup) markup */
[data-baseweb="button-group"],
[data-testid="stButtonGroup"] [role="radiogroup"] {
  display: flex; flex-wrap: nowrap; gap: 2px; padding: 3px; border-radius: 9px;
  background: var(--fill); border: 1px solid var(--line); }
[data-baseweb="button-group"] button,
[data-testid="stButtonGroup"] [role="radiogroup"] button {
  flex: 1 1 0; min-width: 0; min-height: 2.1rem; padding: 0.2rem 0.5rem; margin: 0;
  border: 1px solid transparent; border-radius: 7px; background: transparent;
  color: var(--ink-2); font-weight: 600; box-shadow: none; }
[data-baseweb="button-group"] button:hover,
[data-testid="stButtonGroup"] [role="radiogroup"] button:hover {
  background: rgba(255, 255, 255, 0.6); color: var(--ink); border-color: transparent; }
[data-baseweb="button-group"] button:focus-visible,
[data-testid="stButtonGroup"] [role="radiogroup"] button:focus-visible {
  outline: none; box-shadow: var(--focus-ring); }
[data-baseweb="button-group"] button[kind="segmented_controlActive"],
[data-baseweb="button-group"] button[data-testid="stBaseButton-segmented_controlActive"],
[data-testid="stButtonGroup"] [role="radiogroup"] button[aria-checked="true"] {
  background: var(--surface); color: var(--ink); border-color: var(--line-strong);
  box-shadow: 0 1px 2px rgba(15, 42, 51, 0.10); }
[data-baseweb="button-group"] button p,
[data-testid="stButtonGroup"] [role="radiogroup"] button p { font-size: 0.88rem; color: inherit; }

/* ---------- section heads ---------- */
.sec { display: flex; justify-content: space-between; align-items: baseline; gap: 1rem;
       margin: 1.5rem 0 0.55rem 0; }
.sec-title { font-size: 0.95rem; font-weight: 700; color: var(--ink); }
.sec-legend { font-size: 0.82rem; color: var(--ink-3); text-align: right; }

/* ---------- status vocabulary ---------- */
.s-ok     { --status: transparent;   --status-text: var(--ok);     --wash: transparent; }
.s-watch  { --status: var(--watch);  --status-text: var(--watch);  --wash: var(--watch-wash); }
.s-breach { --status: var(--breach); --status-text: var(--breach); --wash: var(--breach-wash); }
.s-over   { --status: var(--over);   --status-text: var(--over);   --wash: var(--breach-wash); }

/* ---------- pathway: one connected route ---------- */
.route { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1.3fr) minmax(0, 1fr);
         background: var(--surface); border: 1px solid var(--line); border-radius: 12px;
         overflow: hidden; }
.route > * { position: relative; border-left: 1px solid var(--line); }
.route > :first-child { border-left: none; }
/* small arrowhead on each divider: patients move left to right */
.route > :not(:first-child)::before {
  content: ""; position: absolute; left: -1px; top: 50%; transform: translateY(-50%); z-index: 1;
  border-top: 6px solid transparent; border-bottom: 6px solid transparent;
  border-left: 6px solid var(--line-strong); }
.branch { display: grid; grid-template-rows: 1fr 1fr; }
.stop { position: relative; display: flex; flex-direction: column; gap: 0.2rem; min-width: 0;
        padding: 0.85rem 0.95rem 1.05rem 1.05rem; background: var(--wash-focus, transparent); }
.stop.is-focus { --wash-focus: var(--wash); }
.stop::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 4px;
               background: var(--status); }
.branch .stop { border-left: none; padding: 0.6rem 0.95rem 0.75rem 1.05rem;
  display: grid; grid-template-columns: auto minmax(0, 1fr) auto; column-gap: 0.6rem; row-gap: 0.15rem;
  grid-template-areas: "name name status" "wait trend trend"; align-items: baseline; align-content: center; }
.branch .stop-name { grid-area: name; }
.branch .stop-status { grid-area: status; justify-self: end; margin-top: 0; }
.branch .stop-wait { grid-area: wait; }
.branch .stop-trend { grid-area: trend; font-size: 0.76rem; }
.branch .stop + .stop { border-top: 1px solid var(--line); }
.branch .stop::after { height: 3px; }
.stop-name { font-size: 0.84rem; font-weight: 600; color: var(--ink-2);
             white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.stop-wait { display: flex; align-items: baseline; gap: 0.25rem; }
.stop-wait .num { font-size: 2.1rem; font-weight: 700; line-height: 1.05; letter-spacing: -0.02em;
                  color: var(--ink); }
.stop.is-branch .stop-wait .num { font-size: 1.5rem; }
.stop-wait .unit { font-size: 0.82rem; font-weight: 500; color: var(--ink-3); }
.stop-trend { font-size: 0.78rem; line-height: 1.3; color: var(--ink-3);
              font-variant-numeric: tabular-nums; }
.stop-status { display: inline-flex; align-items: center; gap: 0.35rem; margin-top: 0.15rem;
               font-size: 0.8rem; font-weight: 700; color: var(--status-text); }
.stop-status::before { content: ""; width: 0.5rem; height: 0.5rem; border-radius: 50%;
                       background: currentColor; flex: 0 0 auto; }

/* ---------- the action card: the one loud element ---------- */
.st-key-action_card {
  background: var(--surface); border: 1px solid var(--line-strong); border-radius: 12px;
  overflow: hidden; padding: 0 1.4rem 0.6rem 1.4rem; margin-top: 1.25rem; gap: 0.8rem;
  box-shadow: 0 10px 28px -16px rgba(15, 42, 51, 0.35); }
.band { display: flex; justify-content: space-between; align-items: center; gap: 1rem;
        margin: 0 -1.4rem; padding: 0.7rem 1.4rem; color: #FFFFFF; }
.band.tone-urgent { background: var(--breach); }
.band.tone-warn { background: var(--watch); }
.band-label { font-size: 0.95rem; font-weight: 700; }
.band-deadline { display: inline-flex; align-items: center; gap: 0.4rem; white-space: nowrap;
                 font-size: 0.9rem; font-weight: 700; padding: 0.25rem 0.65rem; border-radius: 6px;
                 background: rgba(255, 255, 255, 0.16); }
.band-deadline svg { width: 15px; height: 15px; }
.action-title { font-size: clamp(1.45rem, 3.2vw, 1.95rem); font-weight: 700; line-height: 1.18;
                letter-spacing: -0.015em; color: var(--ink); max-width: 34ch;
                margin: 1rem 0 0.35rem 0; }
.st-key-action_card .stButton { margin-top: 0.4rem; }
[data-testid="stMarkdownContainer"] p.card-body { margin: 0 0 0.35rem 0; max-width: 66ch; font-size: 1.02rem;
  line-height: 1.55; color: var(--ink-2); }
[data-testid="stMarkdownContainer"] p.card-body strong { color: var(--ink); font-weight: 700; }
.inset { background: var(--fill); border-radius: 8px; padding: 0.75rem 1rem; }
.inset-label { font-size: 0.82rem; font-weight: 700; color: var(--ink); margin-bottom: 0.2rem; }
[data-testid="stMarkdownContainer"] .inset p { margin: 0; font-size: 0.97rem; line-height: 1.5;
  color: var(--ink); max-width: 68ch; }
.inset.warn { background: var(--watch-wash); }
.inset.warn .inset-label { color: var(--watch); }
.st-key-action_card [data-testid="stExpander"] details {
  border: none; border-top: 1px solid var(--line); border-radius: 0; background: transparent; }
.st-key-action_card [data-testid="stExpander"] summary { padding-left: 0; padding-right: 0;
  background: transparent; }
.st-key-action_card [data-testid="stExpander"] [data-testid="stExpanderDetails"] { padding-left: 0;
  padding-right: 0; }

/* ---------- expanders ---------- */
[data-testid="stExpander"] details { border: 1px solid var(--line); border-radius: 10px;
                                     background: var(--surface); box-shadow: none; }
[data-testid="stExpander"] summary { font-weight: 600; color: var(--ink); }
[data-testid="stExpander"] summary:hover,
[data-testid="stExpander"] summary:hover span,
[data-testid="stExpander"] summary:hover svg { color: var(--ink-2); }
[data-testid="stExpander"] summary:focus-visible { outline: none; box-shadow: var(--focus-ring);
                                                    border-radius: 6px; }
[data-testid="stMarkdownContainer"] ul.whatif, [data-testid="stMarkdownContainer"] ul.trust {
  list-style: none; padding: 0; margin: 0; }
[data-testid="stMarkdownContainer"] ul.whatif li, [data-testid="stMarkdownContainer"] ul.trust li {
  margin: 0; padding-left: 0; }
.whatif { list-style: none; padding: 0; margin: 0; }
.whatif li { padding: 0.6rem 0; border-top: 1px solid var(--line); font-size: 0.95rem;
             line-height: 1.45; color: var(--ink-2); }
.whatif li:first-child { border-top: none; padding-top: 0.1rem; }
.whatif strong { color: var(--ink); font-weight: 700; }

/* ---------- calm, watch and closed notes ---------- */
.note { display: flex; gap: 0.95rem; align-items: flex-start; margin-top: 1.25rem;
        background: var(--surface); border: 1px solid var(--line); border-radius: 12px;
        padding: 1.1rem 1.3rem; }
.note-icon { flex: 0 0 auto; width: 38px; height: 38px; border-radius: 50%;
             display: flex; align-items: center; justify-content: center; }
.note-icon svg { width: 20px; height: 20px; }
.note.s-ok .note-icon { color: var(--ok); background: var(--ok-wash); }
.note.s-watch .note-icon { color: var(--watch); background: var(--watch-wash); }
.note.s-closed .note-icon { color: var(--ink-2); background: var(--fill); }
.note-title { font-size: 1.25rem; font-weight: 700; line-height: 1.25; color: var(--ink); }
.note-body { font-size: 0.98rem; line-height: 1.5; color: var(--ink-2); margin-top: 0.15rem;
             max-width: 64ch; }

/* ---------- applied move and its effect on the day ---------- */
.applied { margin-top: 0.8rem; background: var(--surface); border: 1px solid var(--line);
           border-radius: 12px; padding: 0.9rem 1.25rem; }
.applied-line { display: flex; gap: 0.6rem; align-items: center; font-size: 0.95rem;
                line-height: 1.45; color: var(--ink-2); }
.applied-line strong { color: var(--ink); }
.applied-icon { flex: 0 0 auto; width: 24px; height: 24px; border-radius: 50%; color: var(--ok);
                background: var(--ok-wash); display: flex; align-items: center; justify-content: center; }
.applied-icon svg { width: 14px; height: 14px; }
.compare { display: flex; align-items: flex-end; gap: 1.75rem; flex-wrap: wrap; margin-top: 0.8rem;
           padding-top: 0.8rem; border-top: 1px solid var(--line); }
.compare-label { flex: 1 1 14rem; font-size: 0.88rem; line-height: 1.4; color: var(--ink-2);
                 align-self: center; }
.cmp { text-align: right; }
.cmp-num { font-size: 1.65rem; font-weight: 700; line-height: 1; letter-spacing: -0.02em; }
.cmp-num.before { color: var(--ink-3); }
.cmp-num.after { color: var(--ok); }
.cmp-cap { margin-top: 0.25rem; font-size: 0.75rem; color: var(--ink-3); }

/* ---------- also watching: one list, a status dot per row ---------- */
.st-key-watching { gap: 0; background: var(--surface); border: 1px solid var(--line);
                   border-radius: 12px; overflow: hidden; }
[class*="st-key-wrow_"] { gap: 0; --dot: var(--watch); }
[class*="st-key-wrow_breach"] { --dot: var(--breach); }
.st-key-watching .stButton button {
  position: relative; width: 100%; min-height: 3rem; justify-content: flex-start; text-align: left;
  border: none; border-top: 1px solid var(--line); border-radius: 0; background: transparent;
  padding: 0.75rem 2.25rem 0.75rem 2.2rem; font-weight: 500; }
.st-key-watching > :first-child .stButton button { border-top: none; }
.st-key-watching .stButton button::before {
  content: ""; position: absolute; left: 1rem; top: 50%; transform: translateY(-50%);
  width: 0.6rem; height: 0.6rem; border-radius: 50%; background: var(--dot); }
.st-key-watching .stButton button::after {
  content: "\\203A"; position: absolute; right: 1rem; top: 50%; transform: translateY(-52%);
  font-size: 1.35rem; line-height: 1; color: var(--ink-3); }
.st-key-watching .stButton button > div { justify-content: flex-start; width: 100%; }
.st-key-watching .stButton button p { text-align: left; }
.st-key-watching .stButton button:hover { background: var(--fill); }
.st-key-watching .stButton button:focus-visible { box-shadow: inset 0 0 0 3px rgba(15, 42, 51, 0.28); }

/* ---------- trust ---------- */
.trust { list-style: none; padding: 0; margin: 0; }
.trust li { padding: 0.65rem 0; border-top: 1px solid var(--line); font-size: 0.98rem;
            line-height: 1.5; color: var(--ink); }
.trust li:first-child { border-top: none; padding-top: 0.1rem; }
[data-testid="stMarkdownContainer"] p.fineprint { margin: 0.3rem 0 0 0; font-size: 0.82rem;
  line-height: 1.5; color: var(--ink-3); }
[data-testid="stMarkdownContainer"] p.footnote { margin-top: 1.5rem; text-align: center;
  font-size: 0.8rem; color: var(--ink-3); }

/* ---------- narrow screens: the route becomes a list ---------- */
@media (max-width: 640px) {
  .block-container, [data-testid="stMainBlockContainer"] { padding: 1.25rem 0.85rem 3rem 0.85rem; }
  .hd { flex-direction: column; align-items: flex-start; gap: 0.75rem; }
  .hd-clock { flex-direction: row; align-items: baseline; gap: 0.7rem; }
  .hd-time { font-size: 2.1rem; }
  .hd-mode { margin-top: 0; }
  .sec-legend { display: none; }

  .route { grid-template-columns: 1fr; }
  .route > * { border-left: none; border-top: 1px solid var(--line); }
  .route > :first-child { border-top: none; }
  .route > :not(:first-child)::before { display: none; }
  .branch { display: block; }
  .stop, .branch .stop {
    display: grid; grid-template-columns: minmax(0, 1fr) auto; column-gap: 0.75rem; row-gap: 0.1rem;
    grid-template-areas: "name wait" "trend status"; align-items: baseline;
    padding: 0.7rem 0.95rem 0.7rem 1.1rem; }
  .branch .stop { padding-left: 2rem; grid-template-columns: minmax(0, 1fr) auto;
                  grid-template-areas: "name wait" "trend status"; }
  .stop::after, .branch .stop::after { top: 0; bottom: 0; right: auto; width: 4px; height: auto; }
  .stop-name { grid-area: name; font-size: 0.95rem; color: var(--ink); }
  .stop-wait { grid-area: wait; justify-self: end; }
  .stop-wait .num, .stop.is-branch .stop-wait .num { font-size: 1.5rem; }
  .stop-trend { grid-area: trend; }
  .stop-status { grid-area: status; justify-self: end; margin-top: 0; }

  .st-key-action_card { padding: 0 1.05rem 0.5rem 1.05rem; }
  .band { margin: 0 -1.05rem; padding: 0.65rem 1.05rem; }
  .compare { gap: 1.25rem; }
}

/* ---------- accessibility preferences ---------- */
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}
@media (prefers-contrast: more) {
  :root { --line: #8A9DA3; --line-strong: #5E737A; --ink-2: #1F363E; --ink-3: #2F464E; }
}
</style>
"""


def inject():
    st.html(CSS)
