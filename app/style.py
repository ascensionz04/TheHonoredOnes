"""Visual style for the single screen (DESIGN.md section 6).

Light grey page, white cards, one translucent sticky toolbar. Colour carries
status only; the action blue marks the one thing to do. Motion is limited to
instant press feedback, because the replay re-renders every tick.
"""

import streamlit as st

TOKENS = {
    "bg": "#F3F6F7",
    "card": "#FFFFFF",
    "fill": "#EEF3F4",
    "text": "#0F2A33",
    "secondary": "#3D5359",
    "tertiary": "#5B6F74",
    "hairline": "rgba(15, 42, 51, 0.10)",
    "action": "#0F2A33",
    "action_hover": "#1C4250",
    "ok": "#1E7B3E",
    "watch": "#A34F00",
    "breach": "#C4161C",
    "over": "#8E0F14",
}

CSS = """
<style>
:root {
  --bg: %(bg)s; --card: %(card)s; --fill: %(fill)s;
  --text: %(text)s; --secondary: %(secondary)s; --tertiary: %(tertiary)s;
  --hairline: %(hairline)s; --action: %(action)s; --action-hover: %(action_hover)s;
  --ok: %(ok)s; --watch: %(watch)s; --breach: %(breach)s; --over: %(over)s;
  --font: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI Variable Text",
          "Segoe UI", Inter, system-ui, sans-serif;
  --font-display: -apple-system, BlinkMacSystemFont, "SF Pro Display",
          "Segoe UI Variable Display", "Segoe UI", Inter, system-ui, sans-serif;
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.04), 0 1px 1px rgba(0,0,0,0.03);
  --shadow-md: 0 1px 2px rgba(0,0,0,0.04), 0 6px 20px rgba(0,0,0,0.06);
  --shadow-lg: 0 2px 4px rgba(0,0,0,0.04), 0 12px 32px rgba(0,0,0,0.08);
}

/* ---------- page ---------- */
.stApp { background: var(--bg); font-family: var(--font); color: var(--text);
         -webkit-font-smoothing: antialiased; }
.stApp p, .stApp li { font-family: var(--font); }
[data-testid="stHeader"], [data-testid="stDecoration"] { display: none; }
.block-container { max-width: 860px; padding: 2.25rem 1rem 4rem 1rem; }
/* The replay re-renders every tick; never dim stale elements. */
[data-stale="true"] { opacity: 1 !important; transition: none !important; }

/* ---------- type ---------- */
.eyebrow { font-size: 0.72rem; font-weight: 600; letter-spacing: 0.06em;
           text-transform: uppercase; color: var(--tertiary); line-height: 1.3; }
.title { font-family: var(--font-display); font-size: clamp(1.75rem, 4vw, 2.25rem);
         font-weight: 700; letter-spacing: -0.025em; line-height: 1.08;
         color: var(--text); margin: 0.3rem 0 0.4rem 0; }
[data-testid="stMarkdownContainer"] p.subtitle { font-size: 1.02rem; line-height: 1.5; color: var(--secondary);
            letter-spacing: -0.005em; max-width: 40rem; margin: 0; }
.section-head { display: flex; justify-content: space-between; align-items: baseline;
                margin: 1.6rem 0 0.55rem 0.15rem; }
.section-head .legend { font-size: 0.8rem; color: var(--tertiary); }
.num { font-variant-numeric: tabular-nums; }

/* ---------- toolbar: translucent material, sticky ---------- */
[data-testid="stLayoutWrapper"]:has(> .st-key-toolbar) {
  position: sticky; top: 0.75rem; z-index: 100; }
.st-key-toolbar {
  background: rgba(255, 255, 255, 0.72);
  -webkit-backdrop-filter: saturate(180%%) blur(20px);
  backdrop-filter: saturate(180%%) blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.7);
  box-shadow: 0 0 0 1px var(--hairline), var(--shadow-md);
  border-radius: 18px; padding: 0.55rem 0.75rem; margin-top: 1.25rem; }
.st-key-toolbar [data-testid="stHorizontalBlock"] { gap: 0.6rem; }
.clock { text-align: right; line-height: 1; }
.clock .eyebrow { display: block; margin-bottom: 0.2rem; }
.clock-time { font-family: var(--font-display); font-size: 1.7rem; font-weight: 600;
              letter-spacing: -0.02em; font-variant-numeric: tabular-nums; color: var(--text); }

/* ---------- controls ---------- */
.stButton button, [data-testid="stBaseButton-secondary"] {
  border-radius: 980px; font-weight: 600; letter-spacing: -0.01em;
  background: var(--card); color: var(--text); border: 1px solid var(--hairline);
  box-shadow: var(--shadow-sm);
  transition: transform 100ms ease-out, background-color 150ms ease, box-shadow 150ms ease; }
.stButton button:hover { background: #F7FAFA; border-color: rgba(0,0,0,0.14); color: var(--text); }
.stButton button:active { transform: scale(0.97); }
.stButton button:focus-visible { outline: 3px solid rgba(15,42,51,0.30); outline-offset: 2px; }
.stButton button[data-testid="stBaseButton-primary"] {
  background: var(--action); color: #FFFFFF; border: none; padding: 0.6rem 1.5rem;
  font-size: 1.02rem; box-shadow: 0 1px 2px rgba(0,0,0,0.08), 0 4px 14px rgba(15,42,51,0.22); }
.stButton button[data-testid="stBaseButton-primary"]:hover { background: var(--action-hover); color: #FFFFFF; }
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
  border-radius: 12px; background: var(--card); border-color: var(--hairline);
  box-shadow: var(--shadow-sm); font-weight: 500; }
[data-baseweb="button-group"] { background: #E1E9EB; padding: 3px; border-radius: 12px;
                                flex-wrap: nowrap; gap: 2px; }
[data-baseweb="button-group"] button {
  flex: 1 1 0; min-width: 0; min-height: 2.15rem; padding: 0.2rem 0.55rem; border: none;
  border-radius: 9px; background: transparent; color: var(--secondary); font-weight: 500;
  box-shadow: none; transition: background-color 150ms ease, transform 100ms ease-out; }
[data-baseweb="button-group"] button:hover { background: rgba(255,255,255,0.5); color: var(--text); }
[data-baseweb="button-group"] button:active { transform: scale(0.97); }
[data-baseweb="button-group"] button[kind="segmented_controlActive"] {
  background: var(--card); color: var(--text); font-weight: 600;
  box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 0 0 0.5px rgba(0,0,0,0.04); }
[data-baseweb="button-group"] button p { font-size: 0.88rem; }

/* ---------- patient flow strip ---------- */
.flow { display: grid; align-items: stretch; gap: 0;
        grid-template-columns: 1fr 18px 1fr 18px 1fr 18px 1fr 18px 1fr; }
.chev { display: flex; align-items: center; justify-content: center; color: #B5C3C6; }
.chev svg { width: 12px; height: 12px; }
.chev.branch { font-size: 0.7rem; font-weight: 600; color: var(--tertiary); }
.tile { position: relative; overflow: hidden; background: var(--card); border-radius: 16px;
        padding: 0.85rem 0.8rem 0.8rem 0.8rem; box-shadow: 0 0 0 1px var(--hairline), var(--shadow-sm);
        display: flex; flex-direction: column; gap: 0.3rem; min-width: 0; }
.tile::before { content: ""; position: absolute; inset: 0 0 auto 0; height: 3px;
                background: var(--status-colour, transparent); }
.tile.focus { box-shadow: 0 0 0 2px var(--action), var(--shadow-md); }
.tile-name { font-size: 0.8rem; font-weight: 600; color: var(--secondary);
             letter-spacing: -0.005em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tile-wait { display: flex; align-items: baseline; gap: 0.2rem; }
.tile-wait .num { font-family: var(--font-display); font-size: 1.85rem; font-weight: 650;
                  letter-spacing: -0.03em; line-height: 1; color: var(--text); }
.tile-wait .unit { font-size: 0.8rem; color: var(--tertiary); font-weight: 500; }
.tile-next { font-size: 0.76rem; color: var(--tertiary); font-variant-numeric: tabular-nums;
             white-space: nowrap; }
.pill { display: inline-flex; align-items: center; gap: 0.3rem; align-self: flex-start;
        font-size: 0.72rem; font-weight: 650; letter-spacing: 0.01em; line-height: 1;
        padding: 0.28rem 0.5rem; border-radius: 980px; white-space: nowrap; }
.pill::before { content: ""; width: 6px; height: 6px; border-radius: 50%%; background: currentColor; }
.s-ok    { --status-colour: transparent; }
.s-watch { --status-colour: var(--watch); }
.s-breach{ --status-colour: var(--breach); }
.s-over  { --status-colour: var(--over); }
.pill.s-ok     { color: var(--ok);     background: rgba(30,123,62,0.10); }
.pill.s-watch  { color: var(--watch);  background: rgba(163,79,0,0.10); }
.pill.s-breach { color: var(--breach); background: rgba(196,22,28,0.10); }
.pill.s-over   { color: #FFFFFF;       background: var(--over); }
.pill.s-over::before { background: #FFFFFF; }

/* ---------- action card ---------- */
.st-key-action_card {
  background: var(--card); border-radius: 22px; padding: 1.4rem 1.5rem 1.1rem 1.5rem;
  box-shadow: 0 0 0 1.5px var(--action), var(--shadow-lg); margin-top: 1.4rem; gap: 0.75rem; }
.st-key-action_card .stButton { margin: 0.15rem 0 0.1rem 0; }
.card-head { display: flex; justify-content: space-between; align-items: center; gap: 0.75rem; }
.eyebrow.action { color: var(--action); }
.deadline { display: inline-flex; align-items: center; gap: 0.35rem; font-size: 0.82rem;
            font-weight: 650; color: var(--breach); background: rgba(196,22,28,0.08);
            padding: 0.32rem 0.65rem; border-radius: 980px; white-space: nowrap; }
.deadline svg { width: 14px; height: 14px; }
.action-title { font-family: var(--font-display); font-size: clamp(1.5rem, 3.4vw, 2.05rem);
                font-weight: 700; letter-spacing: -0.022em; line-height: 1.14;
                color: var(--text); margin: 0.55rem 0 0.15rem 0; }
[data-testid="stMarkdownContainer"] p.card-body { font-size: 1.04rem; line-height: 1.55; color: var(--secondary);
             letter-spacing: -0.005em; margin: 0.35rem 0 0.4rem 0; }
[data-testid="stMarkdownContainer"] p.card-body strong { color: var(--text); font-weight: 600; }
.inset { background: var(--fill); border-radius: 14px; padding: 0.8rem 1rem; }
.inset .eyebrow { margin-bottom: 0.25rem; }
[data-testid="stMarkdownContainer"] .inset p { margin: 0; font-size: 0.97rem; line-height: 1.5; color: var(--text); }
.inset.warn { background: rgba(163,79,0,0.08); }
.inset.warn .eyebrow { color: var(--watch); }
.st-key-action_card [data-testid="stExpander"] details {
  box-shadow: none; border: none; border-top: 1px solid var(--hairline); border-radius: 0; background: transparent; }
.st-key-action_card [data-testid="stExpander"] summary { padding-left: 0.1rem; padding-right: 0.1rem; }

/* ---------- expanders ---------- */
[data-testid="stExpander"] details { border-radius: 16px; border: none; background: var(--card);
                                     box-shadow: 0 0 0 1px var(--hairline), var(--shadow-sm); }
[data-testid="stExpander"] summary { font-weight: 600; letter-spacing: -0.01em; }
[data-testid="stExpander"] summary:hover { color: var(--action); }
[data-testid="stExpander"] summary:hover svg, [data-testid="stExpander"] summary:hover span { color: var(--action); }
.whatif { list-style: none; padding: 0; margin: 0; }
.whatif li { padding: 0.6rem 0; border-top: 1px solid var(--hairline); font-size: 0.95rem;
             line-height: 1.45; color: var(--secondary); }
.whatif li:first-child { border-top: none; padding-top: 0.1rem; }
.whatif strong { color: var(--text); font-weight: 600; }

/* ---------- state cards ---------- */
.state { display: flex; gap: 1rem; align-items: center; background: var(--card);
         border-radius: 22px; padding: 1.25rem 1.4rem; margin-top: 1.4rem;
         box-shadow: 0 0 0 1px var(--hairline), var(--shadow-md); }
.state-icon { flex: 0 0 auto; width: 44px; height: 44px; border-radius: 50%%;
              display: flex; align-items: center; justify-content: center; }
.state-icon svg { width: 22px; height: 22px; }
.state-icon.s-ok { color: var(--ok); background: rgba(30,123,62,0.12); }
.state-icon.s-watch { color: var(--watch); background: rgba(163,79,0,0.12); }
.state-icon.s-closed { color: var(--secondary); background: var(--fill); }
.state-title { font-family: var(--font-display); font-size: 1.3rem; font-weight: 700;
               letter-spacing: -0.02em; line-height: 1.2; color: var(--text); }
.state-body { font-size: 0.98rem; line-height: 1.5; color: var(--secondary); margin-top: 0.15rem; }

/* ---------- applied / outcome ---------- */
.applied { background: var(--card); border-radius: 20px; padding: 1.1rem 1.3rem; margin-top: 0.9rem;
           box-shadow: 0 0 0 1px var(--hairline), var(--shadow-sm); }
.applied-head { display: flex; gap: 0.7rem; align-items: center; }
.applied-head .state-icon { width: 30px; height: 30px; }
.applied-head .state-icon svg { width: 16px; height: 16px; }
.applied-title { font-weight: 650; font-size: 0.98rem; letter-spacing: -0.01em; }
.applied-sub { font-size: 0.9rem; color: var(--tertiary); }
.compare { display: flex; align-items: center; gap: 1.25rem; margin-top: 0.9rem;
           padding-top: 0.85rem; border-top: 1px solid var(--hairline); flex-wrap: wrap; }
.compare-label { font-size: 0.85rem; color: var(--secondary); flex: 1 1 12rem; line-height: 1.4; }
.stat { text-align: right; }
.stat-num { font-family: var(--font-display); font-size: 1.6rem; font-weight: 650;
            letter-spacing: -0.025em; line-height: 1; font-variant-numeric: tabular-nums; }
.stat-num.before { color: var(--tertiary); }
.stat-num.after { color: var(--ok); }
.stat-cap { font-size: 0.72rem; color: var(--tertiary); margin-top: 0.2rem; }
.compare .to { color: #B5C3C6; }

/* ---------- also watching: grouped list ---------- */
.st-key-watching { gap: 0; background: var(--card); border-radius: 16px; overflow: hidden;
                   box-shadow: 0 0 0 1px var(--hairline), var(--shadow-sm); }
.st-key-watching .stButton button {
  width: 100%%; justify-content: flex-start; text-align: left; border: none; border-radius: 0;
  box-shadow: none; background: transparent; padding: 0.85rem 1rem; font-weight: 500;
  border-top: 1px solid var(--hairline); }
.st-key-watching [data-testid="stElementContainer"]:first-child .stButton button { border-top: none; }
.st-key-watching .stButton button > div { justify-content: flex-start; width: 100%%; }
.st-key-watching .stButton button p { text-align: left; }
.st-key-watching .stButton button::after { content: "\\203A"; margin-left: auto; padding-left: 0.75rem;
                                           font-size: 1.35rem; line-height: 1; color: #B5C3C6; }
.st-key-watching .stButton button:hover { background: #F7FAFA; }
.st-key-watching .stButton button:active { transform: none; background: var(--fill); }

/* ---------- trust ---------- */
.trust { list-style: none; padding: 0; margin: 0; }
.trust li { padding: 0.7rem 0; border-top: 1px solid var(--hairline); font-size: 0.98rem;
            line-height: 1.5; color: var(--text); }
.trust li:first-child { border-top: none; padding-top: 0.1rem; }
[data-testid="stMarkdownContainer"] p.fineprint { font-size: 0.8rem; color: var(--tertiary); line-height: 1.5; margin: 0.3rem 0 0 0; }
[data-testid="stMarkdownContainer"] p.footnote { text-align: center; font-size: 0.78rem; color: var(--tertiary); margin-top: 1.5rem; }

/* ---------- narrow screens ---------- */
@media (max-width: 640px) {
  .flow { grid-template-columns: 1fr 1fr; gap: 0.6rem; }
  .chev { display: none; }
  .st-key-action_card { padding: 1.1rem 1.1rem 0.9rem 1.1rem; }
  .clock { text-align: left; }
}

/* ---------- accessibility preferences ---------- */
@media (prefers-reduced-motion: reduce) {
  .stButton button, .stButton button:active { transition: none; transform: none; }
}
@media (prefers-reduced-transparency: reduce) {
  .st-key-toolbar { background: var(--card); -webkit-backdrop-filter: none; backdrop-filter: none; }
}
@media (prefers-contrast: more) {
  :root { --hairline: rgba(0,0,0,0.45); --tertiary: #2E4248; --secondary: #0F2A33; }
  .st-key-toolbar { background: var(--card); }
}
</style>
""" % TOKENS


def inject():
    st.html(CSS)
