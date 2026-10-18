"""Vicky, June Analytics' AI venture capitalist. Run: uv run streamlit run app.py

A guided journey, one step at a time (June: "information overload" is the failure mode):
  Start here -> Practise -> Investor Q&A -> Vicky's Partner Meeting, with Ask Vicky and Financials.
Vicky (an original illustrated avatar) guides every step. Jargon appears progressively, with pop-ups.
"""
import html
import json
import os
import random
import re
import time

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from langchain_core.messages import AIMessage, HumanMessage

from vicky import avatar, claims, data, forecast, handoff, hotseat, i18n, journey, lingo, llm, metrics, practice
from vicky.audit import audit
from vicky.glossary import escape_dollars, glossify, glossify_sections

st.set_page_config(page_title="Vicky · AI VC by June", page_icon="assets/june_logo.png", layout="wide")

# Design tokens from the June mock (HANDOFF.md): black on white, purple as an accent only.
PURPLE, INK, MUTED, BORDER, LAVENDER, STONE = "#502EF6", "#161616", "#66635D", "#E3E1DD", "#EFECFE", "#F3F2EE"
PURPLE_DARK, PURPLE_LIGHT = "#3A1BB0", LAVENDER
PROV = {  # (label, text colour, background)
    "historical": ("Historical", "#161616", "#E9E8E4"),
    "forecast": ("Forecast", "#502EF6", "#ECE9FE"),
    "founder_claim": ("Founder claim", "#B46D10", "#F8ECDB"),
    "reported_in_pack": ("Reported in pack", "#3D4A5C", "#E6EAF0"),
    "public_source": ("Public source", "#007277", "#DDF1F1"),
}
STATUS_COLOR = {claims.FIX: "#9b1c1c", claims.REWORD: "#8a5a00", claims.REMOVE: "#9b1c1c",
                claims.UPSIDE: "#3b4a9b", claims.OK: "#1f7a4d"}
DIM_LABEL = {"accuracy": "Accuracy", "evidence": "Shows the math", "candor": "Honesty", "clarity": "Clarity"}
# The public SEO guide (built in Lovable). Set SEO_URL in .env or in Streamlit Cloud Secrets.
SEO_URL = os.getenv("SEO_URL", "").strip()
SEO_TITLE = "The 10-Minute Test: 6 numbers seed investors check first"
PANEL_NAME = "Vicky's Partner Meeting"  # was "Hot Seat": the real final step of a VC raise, hosted by Vicky
NAV = ["Start here", "Practise", "Investor Q&A", "Partner meeting", "Ask Vicky", "Financials"]
PATH_SUB = "Where you are, what's in the way, and where you want to be."
TOP3_TITLE = "Top 3 questions you'll be asked"
PAGE_TITLES = {"Start here": "Start here", "Practise": "Practise", "Investor Q&A": "Investor Q&A",
               "Partner meeting": PANEL_NAME, "Ask Vicky": "Ask Vicky", "Financials": "Financials"}

st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@500;700;800&family=Public+Sans:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=swap');
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp td, .stApp th,
.stApp [data-testid="stMarkdownContainer"] {{font-family:'Public Sans',ui-sans-serif,sans-serif}}
.stApp {{color:{INK};background:#fff}}
.stApp h1, .stApp h2, .stApp h3, .disp {{font-family:'Outfit',ui-sans-serif,sans-serif !important;font-weight:800;letter-spacing:-0.02em;color:{INK}}}
.stApp h1 {{font-size:2rem}} .stApp h3 {{font-size:1.15rem}}
.serif {{font-family:'Source Serif 4',Georgia,serif}}
.num {{font-family:'Outfit',ui-sans-serif,system-ui,sans-serif;font-weight:700;font-variant-numeric:tabular-nums}}
.sl::before {{content:"/ ";color:{PURPLE};font-weight:800}}
.eyebrow {{font-size:0.72rem;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;color:{MUTED}}}
.small {{font-size:0.84rem;color:{MUTED}}}
/* sidebar like the mock: white, hairline border, team list */
[data-testid="stSidebar"] {{background:#fff;border-right:1px solid {BORDER}}}
.team-row {{display:flex;gap:10px;align-items:center;padding:9px 10px;border-radius:8px;margin-bottom:4px}}
.team-row.off {{opacity:.6}}
.team-row.on {{background:{LAVENDER};border-left:2px solid {PURPLE}}}
.team-ico {{width:34px;height:34px;border-radius:50%;background:{STONE};display:grid;place-items:center;
  font-family:'Outfit',ui-sans-serif,system-ui,sans-serif;font-weight:700;font-size:.9rem;flex:0 0 auto}}
.team-row .n {{font-weight:600;font-size:.9rem;line-height:1.2}} .team-row .r {{font-size:.75rem;color:{MUTED}}}
.team-row.on .r {{color:{PURPLE_DARK}}}
.soon {{font-size:.62rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:{MUTED}}}
/* header */
.topbar {{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}}
.pill {{display:inline-flex;gap:8px;align-items:center;border:1px solid {BORDER};border-radius:6px;padding:5px 11px;
  font-size:.75rem;font-weight:600}}
.dot {{width:7px;height:7px;border-radius:50%;background:#007277;display:inline-block}}
.ptitle {{font-family:'Outfit',ui-sans-serif,system-ui,sans-serif;font-weight:800;font-size:2rem;letter-spacing:-0.02em;margin:2px 0 6px}}
.ptitle::before {{content:"/ ";color:{PURPLE}}}
/* tabs: segmented control restyled as underline tabs */
div[data-testid="stButtonGroup"] > div {{width:100%}}
div[data-testid="stButtonGroup"] {{border-bottom:1px solid {BORDER};gap:0}}
div[data-testid="stButtonGroup"] button {{background:transparent !important;border:none !important;border-radius:0 !important;
  box-shadow:none !important;color:{MUTED} !important;padding:6px 2px 12px !important;margin-right:26px;min-height:0}}
div[data-testid="stButtonGroup"] button:hover {{color:{INK} !important}}
div[data-testid="stButtonGroup"] button[aria-checked="true"] {{color:{INK} !important;
  border-bottom:2px solid {INK} !important}}
div[data-testid="stButtonGroup"] button[aria-checked="true"] p::before {{content:"/ ";color:{PURPLE};font-weight:800}}
/* cards */
div[data-testid="stVerticalBlockBorderWrapper"] {{border-color:{BORDER} !important;border-radius:10px !important}}
.ctitle {{font-family:'Outfit',ui-sans-serif,system-ui,sans-serif;font-weight:800;font-size:1.1rem;letter-spacing:-0.01em;margin:0}}
.ctitle::before {{content:"/ ";color:{PURPLE}}}
.csub {{font-size:.88rem;color:{MUTED};margin:2px 0 8px}}
.row {{display:flex;justify-content:space-between;align-items:center;gap:14px;padding:10px 0;border-top:1px solid {BORDER};font-size:.92rem}}
.row:first-of-type {{border-top:none}}
.row .fig {{display:flex;align-items:center;gap:8px;flex:0 0 auto}}
.badge {{display:inline-block;padding:2px 6px;border-radius:4px;font-size:.62rem;font-weight:700;letter-spacing:.06em;
  text-transform:uppercase;white-space:nowrap;margin-left:4px}}
.blind {{display:inline-block;background:{INK};color:#fff;font-size:.62rem;font-weight:700;padding:2px 7px;border-radius:4px;
  margin-left:6px;letter-spacing:.06em;vertical-align:middle}}
.divider {{display:flex;align-items:center;gap:12px;margin:18px 0 10px}}
.divider::after {{content:"";flex:1;border-top:1px solid {BORDER}}}
/* readiness card + quote panel */
.ready {{background:{INK};color:#fff;border-radius:10px;padding:26px 26px 22px;height:100%}}
.ready .eyebrow {{color:rgba(255,255,255,.7)}}
.ready .big {{font-family:'Outfit',ui-sans-serif,system-ui,sans-serif;font-weight:800;font-size:3.6rem;line-height:1;margin:14px 0 6px}}
.ready .big span {{font-size:1.4rem;opacity:.6}}
.bar {{height:6px;border-radius:6px;background:rgba(255,255,255,.15);margin-top:16px}}
.bar > div {{height:100%;border-radius:6px;background:{PURPLE}}}
.vicky {{display:flex;gap:18px;align-items:center;background:{LAVENDER};border-radius:10px;padding:20px 24px;margin:2px 0 8px}}
.vicky .q {{font-family:'Source Serif 4',Georgia,serif;font-weight:600;font-size:1.18rem;line-height:1.45;color:{INK}}}
.vicky .who {{font-size:.86rem;color:{PURPLE_DARK};margin-top:6px}}
@keyframes hop{{0%,100%{{transform:translateY(0)}} 50%{{transform:translateY(-6px)}}}}
img.char.talking{{animation:hop .45s ease-in-out 4}}
@media (prefers-reduced-motion: reduce){{img.char.talking{{animation:none}}}}
.qbox {{display:flex;gap:14px;align-items:center;border:1px solid {BORDER};border-radius:10px;padding:14px 18px;background:#fff}}
.qbox .qt {{font-family:'Source Serif 4',Georgia,serif;font-weight:600;font-size:1.15rem}}
/* path map */
.path {{display:flex;gap:10px;align-items:stretch;flex-wrap:wrap}}
.pcol {{flex:1 1 200px;border-radius:8px;padding:12px 14px;background:{STONE}}}
.pcol.goal {{background:{LAVENDER}}}
.pnum {{font-family:'Outfit',ui-sans-serif,system-ui,sans-serif;font-weight:700;font-size:1.25rem;font-variant-numeric:tabular-nums}}
.plabel {{font-size:.78rem;color:{MUTED};margin-bottom:8px}}
.parrow {{display:flex;align-items:center;color:#aaa;font-size:1.4rem}}
.pchip {{display:block;font-size:.84rem;padding:6px 8px;background:#fff;border:1px solid {BORDER};border-radius:6px;margin-bottom:6px}}
.stages {{display:flex;gap:4px;flex-wrap:wrap;margin-top:10px}}
.stage {{flex:1 1 100px;font-size:.7rem;padding:5px 6px;border-radius:5px;background:{STONE};color:{MUTED};text-align:center}}
.stage.done {{background:#E9E8E4;color:{INK}}} .stage.here {{background:{INK};color:#fff;font-weight:700}}
/* jargon pop-ups */
.term{{position:relative;border-bottom:2px dotted {PURPLE};cursor:help;outline:none}}
.term .tip{{visibility:hidden;opacity:0;position:absolute;left:0;top:calc(100% + 6px);z-index:1000;width:min(290px,78vw);
  background:{INK};color:#fff;padding:9px 11px;border-radius:8px;font-size:0.8rem;line-height:1.4;font-weight:400;
  text-transform:none;letter-spacing:0;text-align:left;box-shadow:0 8px 24px rgba(0,0,0,.2);transition:opacity .12s}}
.term:hover .tip, .term:focus .tip{{visibility:visible;opacity:1}}
.term:focus-visible{{outline:3px solid {PURPLE};outline-offset:2px;border-radius:3px}}
*:focus-visible{{outline-color:{PURPLE} !important}}
.gl{{position:relative;border-bottom:2px dotted {PURPLE};cursor:help;outline:none}}
.gl .gl-tip{{visibility:hidden;opacity:0;position:absolute;left:0;top:calc(100% + 6px);z-index:1000;width:min(290px,78vw);
  background:{INK};color:#fff;padding:9px 11px;border-radius:8px;font-size:0.8rem;line-height:1.4;font-weight:400;
  font-style:normal;text-transform:none;letter-spacing:0;text-align:left;white-space:normal;
  box-shadow:0 8px 24px rgba(0,0,0,.2);transition:opacity .12s;pointer-events:none}}
.gl .gl-tip b{{color:#fff}} .gl .gl-tip .gl-ex{{display:block;margin-top:5px;color:#cfcfcf}}
.gl:hover .gl-tip,.gl:focus .gl-tip{{visibility:visible;opacity:1}}
.gl:focus-visible{{outline:3px solid {PURPLE};outline-offset:2px;border-radius:3px}}
.chip{{display:inline-block;padding:3px 8px;border-radius:4px;font-size:.66rem;font-weight:700;letter-spacing:.06em;
  text-transform:uppercase;margin:0 6px 4px 0}}
.trace{{display:grid;grid-template-columns:auto auto 1fr;gap:6px 12px;align-items:baseline;font-size:.88rem}}
/* other screens */
.kpi{{border:1px solid {BORDER};border-radius:10px;padding:12px 14px;background:#fff;height:100%}}
.kpi .v{{font-family:'Outfit',ui-sans-serif,system-ui,sans-serif;font-size:1.55rem;font-weight:800;margin:2px 0}}
.kpi .l{{font-size:0.82rem;color:{MUTED}}}
.claim{{border-left:3px solid;padding:8px 14px;margin-bottom:10px;background:#fff;border-radius:4px;border-top:1px solid {BORDER};
  border-right:1px solid {BORDER};border-bottom:1px solid {BORDER}}}
.card{{border:1px solid {BORDER};border-radius:10px;padding:14px 16px;background:#fff;margin-bottom:6px}}
.seat{{border:1px solid {BORDER};border-radius:10px;padding:10px;text-align:center;background:#fff}}
.seat.speaking{{border:2px solid {PURPLE};box-shadow:0 0 0 4px {LAVENDER}}}
.seat.out{{opacity:0.45;filter:grayscale(1)}}
.seat img{{display:block;margin:0 auto 6px}}
.timer{{font-family:'Outfit',ui-sans-serif,system-ui,sans-serif;font-size:1.6rem;font-weight:800;text-align:center}}
.dtable{{width:100%;border-collapse:collapse;font-size:.9rem}}
.dtable th{{background:{STONE};text-align:left;font-size:.7rem;letter-spacing:.08em;text-transform:uppercase;color:{MUTED};
  padding:8px 10px;font-weight:600}}
.dtable td{{padding:11px 10px;border-top:1px solid {BORDER};vertical-align:top}}
.footer-line{{position:fixed;left:0;right:0;bottom:0;z-index:50;background:rgba(255,255,255,.96);border-top:1px solid {BORDER};
  padding:9px 24px 9px 0;text-align:center;font-size:.75rem;color:{MUTED}}}
.block-container{{padding-bottom:70px}}
@media (max-width: 760px) {{ .parrow{{display:none}} .ready .big{{font-size:2.8rem}} }}
</style>""", unsafe_allow_html=True)


# ---------------------------------------------------------------- helpers
def LANG() -> str:
    return "fr" if st.session_state.get("lang_fr") else "en"


def T(text: str, **kw) -> str:
    """On-screen text in the founder's language (vicky/i18n.py). Numbers are never translated."""
    return i18n.tr(text, LANG(), **kw)


def low(text: str) -> str:
    """Lower-case a title inside a sentence (English only: French keeps "5 M$" and proper nouns intact)."""
    return text if LANG() == "fr" else text.lower()


def month(m: str) -> str:
    """'March 2028' in the founder's language."""
    name = journey._month_name(m)
    if LANG() == "fr":
        for en, fr in i18n.MONTHS_FR.items():
            name = name.replace(en, fr)
    return name


def lang_wrap(question: str) -> str:
    return question + i18n.ai_instruction(LANG())


def badge(prov: str) -> str:
    label, fg, bg = PROV.get(prov, (prov, "#555", "#eee"))
    label = T(label)
    return f'<span class="badge" style="color:{fg};background:{bg}">{label}</span>'


def learned() -> set:
    return st.session_state.setdefault("learned", set())


LINGO_MODES = ["Auto (grows with you)", "Plain English", "Mixed", "Investor-speak"]


def lingo_level() -> int:
    mode = st.session_state.get("lingo_mode", LINGO_MODES[0])
    return lingo.auto_level(len(learned())) if mode == LINGO_MODES[0] else LINGO_MODES.index(mode)


def term(text: str, key: str, label: bool = False) -> str:
    """Jargon pop-up. Hover, tap or Tab to it. The amount of investor-speak grows as the founder learns."""
    shown, tip = lingo.display_text(text, key, lingo_level(), label=label)
    if not tip:
        return esc(text)
    return (f'<span class="term" tabindex="0" aria-label="{esc(shown)}. {esc(tip)}">{esc(shown)}'
            f'<span class="tip" role="tooltip">{esc(tip)}</span></span>')


def reduce_motion() -> bool:
    return st.session_state.get("a11y_motion", False)


def face(key: str, mood: str = "happy", talking: bool = False, size: int = 56) -> str:
    still = reduce_motion()
    return avatar.img(key, mood, talking=talking and not still, still=still, size=size)


def person(key: str) -> str:
    """Investors are named by role, like real archetypes: 'The lead seed fund'."""
    return T(data.investor_profiles()[key]["name"])


def plain(html_text: str) -> str:
    return html.unescape(re.sub(r"<span class=\"tip\".*?</span></span>", "</span>", html_text)
                         .replace("<br>", " ")).replace("&#36;", "$") if html_text else ""


def read_aloud(text: str, label: str | None = None):
    """Browser text-to-speech (no API). An accessibility option for every Vicky message and investor question."""
    label = label or ("🔊 Lire à voix haute" if LANG() == "fr" else "🔊 Read aloud")
    clean = re.sub(r"<[^>]+>", "", plain(text))
    components.html(
        f"""<button id="b" aria-label="Read aloud" style="font:600 13px system-ui,sans-serif;padding:5px 12px;
        border-radius:16px;border:1.5px solid #d9ccff;background:#fff;color:#3A1BB0;cursor:pointer">{label}</button>
        <script>document.getElementById('b').onclick=()=>{{const s=window.speechSynthesis;s.cancel();
        const u=new SpeechSynthesisUtterance({json.dumps(clean)});u.lang='{i18n.SPEECH_LANG[LANG()]}';u.rate=1;s.speak(u);}};</script>""",
        height=38)


def vicky_says(text_html: str, mood: str = "happy", speak: bool = True, source: str = "Vicky"):
    """Vicky's voice: the lavender quote panel from the mock. Her pose matches the moment."""
    st.markdown(f'<div class="vicky">{face("vicky", mood, talking=True, size=104)}'
                f'<div><div class="q" role="status">{text_html}</div><div class="who">— {esc(source)}</div></div></div>',
                unsafe_allow_html=True)
    if speak:
        read_aloud(text_html)


def _add_transcript(target: str, mic_key: str):
    """Append what the founder said to their answer box (runs before the rerun, so the box shows it)."""
    said = st.session_state.get(mic_key + "_output")
    if said:
        before = (st.session_state.get(target) or "").strip()
        st.session_state[target] = f"{before} {said}".strip()
    else:
        st.session_state["voice_failed"] = True


def voice_input(target: str, mic_key: str):
    """🎤 Answer out loud: the browser records, the speech is transcribed into the answer box, then scored like typing."""
    try:
        from streamlit_mic_recorder import speech_to_text
    except ImportError:
        return
    fr = LANG() == "fr"
    c1, c2 = st.columns([1, 3], vertical_alignment="center")
    with c1:
        speech_to_text(start_prompt="🎤 Répondre à voix haute" if fr else "🎤 Answer out loud",
                       stop_prompt="⏹ Terminer" if fr else "⏹ Stop and transcribe",
                       language=i18n.SPEECH_LANG[LANG()], just_once=True, use_container_width=True, key=mic_key,
                       callback=_add_transcript, args=(target, mic_key))
    if st.session_state.pop("voice_failed", False):
        c2.caption("Je n'ai pas compris. Réessayez ou tapez votre réponse." if fr
                   else "I couldn't catch that. Try again, or type your answer.")
    else:
        c2.caption("Parlez, puis vérifiez le texte avant de l'envoyer." if fr
                   else "Speak, then check the text before you send it. Your words are transcribed into the box.")


def investor_says(key: str, text: str, mood: str = "thinking", speak: bool = True):
    text = T(text)
    st.markdown(f'<div class="qbox">{face(key, mood, talking=True, size=56)}<div><div class="eyebrow">'
                f'{esc(person(key))}</div><div class="qt">“{esc(text)}”</div></div></div>', unsafe_allow_html=True)
    if speak:
        read_aloud(text, "🔊 Écouter la question" if LANG() == "fr" else "🔊 Hear the question")


def term_check(key: str, ctx: str):
    """Vicky's quick check: one multiple-choice question on a term. Passing it moves the founder up a level."""
    if not lingo.entry(key):
        return
    q = lingo.quiz(key)
    e = lingo.entry(key)
    st.markdown(f"<div class='vicky'>{face('vicky', 'learning', size=64)}<div style='padding-top:14px'>"
                f"<b>🧠 Vicky's quick check:</b> what does <b>{esc(q['short'])}</b> mean?</div></div>",
                unsafe_allow_html=True)
    choice = st.radio("Pick one", q["options"], index=None, key=f"quiz_{ctx}_{key}", label_visibility="collapsed")
    if choice is None:
        return
    if choice == q["answer"]:
        if key not in learned():
            learned().add(key)
            st.rerun()
        st.success(f"Yes! You'll hear **{esc(q['short'])}** a lot. " + (f"Think of it as: {esc(e['analogy'])}" if e["analogy"] else ""))
    else:
        st.warning(f"Not quite. **{esc(q['short'])}**: {esc(q['answer'])}")


def esc(s: str) -> str:
    """Escape for st.markdown: HTML-safe, and '$' must not trigger LaTeX math."""
    return html.escape(str(s)).replace("$", "&#36;")


def show_metric(m: metrics.Metric):
    st.markdown(f"**{m.label}** = **{m.display()}** {badge(m.provenance)}", unsafe_allow_html=True)
    st.markdown(f"Formula: {esc(m.formula)}")
    if m.inputs:
        st.json({k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.inputs.items()})
    st.caption(f"Source: {m.ref}")
    if m.note:
        st.info(m.note.replace("$", "\\$"))


def kpi(key: str, label: str, sub: str = "", term_key: str | None = None):
    m = metrics.get(key)
    lab = term(label, term_key, label=True) if term_key else esc(label)
    st.markdown(f'<div class="kpi"><div class="l">{lab}{badge(m.provenance)}</div>'
                f'<div class="v">{m.display()}</div><div class="small">{sub}</div></div>', unsafe_allow_html=True)
    with st.popover("Show calculation", width="stretch"):
        show_metric(m)


def render_audit(entries: list[dict], title="Audit notes"):
    with st.expander(f"🔎 {title}: {entries[-1]['summary']}", expanded=not entries[-1]["passed"]):
        for e in entries:
            label = f"Round {e['round']}: " if "round" in e else ""
            st.markdown(f"**{label}{e['summary']}**")
            for i in e["issues"]:
                st.markdown(f"- `{i['type']}` **{i['text']}**: {i['detail']}  \n  <span class='small'>“{esc(i['sentence'][:220])}”</span>",
                            unsafe_allow_html=True)
        if len(entries) > 1:
            st.success("Issues found by the audit were sent back to Vicky and fixed before you saw this.")


def human_box(h: dict | None):
    if h:
        st.info(f"👤 **Bring in a human here: {h['who']}.** {h['why']}")


def go(page: str, **state):
    """Button callback: jump to another step (and remember what to open there)."""
    st.session_state.nav = page
    st.session_state.update(state)


def use_ai() -> bool:
    return llm.configured() and st.session_state.get("use_ai", True)


def best_scores() -> dict:
    return st.session_state.setdefault("best", {})


def record(rid: str | None, score: float):
    if rid:
        b = best_scores()
        b[rid] = max(score, b.get(rid, 0))


def feedback(turn: dict, previous: float | None = None, show_strong: bool = True):
    """Scores, what went well, what to fix, fact check, and a stronger answer."""
    delta = None if previous is None else round(turn["weighted"] - previous, 1)
    c = st.columns(5)
    c[0].metric("Overall", f"{turn['weighted']:.1f}/5", None if delta is None else f"{delta:+.1f} vs last try")
    for col, d in zip(c[1:], practice.DIMENSIONS):
        col.metric(DIM_LABEL[d], f"{turn['scores'][d]}/5")
    fc = turn["fact_check"]
    if fc["issues"]:
        st.error("**Fact check:** " + "; ".join(f"**{esc(i['text'])}**: {i['detail']}" for i in fc["issues"]))
    elif fc["numbers_checked"]:
        st.success(f"**Fact check:** {fc['summary']}")
    else:
        st.info("**Fact check:** no figures the audit could check. Investors expect a number.")
    seen = set()  # one glossary pop-up per term across this feedback block
    if turn.get("went_well"):
        st.markdown(f"✅ **Went well:** {glossify(esc(turn['went_well']), seen)}", unsafe_allow_html=True)
    st.markdown(f"🛠️ **Improve:** {glossify(esc(turn['improve']), seen)}", unsafe_allow_html=True)
    if show_strong:
        with st.expander("See a stronger answer (try again yourself first)"):
            st.markdown(f"> {glossify(esc(turn['stronger_answer']), seen)}", unsafe_allow_html=True)
    how = "Vicky's AI feedback" if turn["method"] == "ai" else "Quick check (rule-based, no AI)"
    if turn.get("fallback_reason"):
        how += " · the AI was unavailable, so this used the rule-based check"
    st.caption(f"Scored by: {how}. Numbers are always checked in code, never by the AI.")


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.image("assets/june_logo_wide.png", width=110)
    st.markdown(f"""<div class="eyebrow" style="margin:18px 0 10px"><span style="color:{PURPLE}">/</span> {T("Your AI finance team")}</div>
<div class="team-row off" aria-disabled="true"><div class="team-ico">F</div><div><div class="n">Franco</div>
<div class="r">{T("AI Finance Officer (CFO) · forecasts")}</div><div class="soon">{T("Coming from June")}</div></div></div>
<div class="team-row off" aria-disabled="true"><div class="team-ico">R</div><div><div class="n">Rocco</div>
<div class="r">{T("AI Risk Officer (CRO) · monthly checks")}</div><div class="soon">{T("Coming from June")}</div></div></div>
<div class="team-row on">{face("vicky", "happy", size=36)}<div><div class="n">Vicky</div>
<div class="r">{T("AI VC · seed meeting prep")}</div></div></div>""", unsafe_allow_html=True)
    st.toggle("🇨🇦 Français", key="lang_fr", help="Canada has two official languages. Vicky's messages, investor "
              "questions, AI feedback and read-aloud switch to Canadian French. Numbers stay exactly as computed.")
    rs = journey.readiness_score(best_scores())
    r = journey.readiness(best_scores())
    st.markdown(f'<div class="eyebrow" style="margin-top:18px">{T("Readiness")}</div>'
                f'<div class="num" style="font-size:1.6rem">{rs["score"]}<span class="small">/100</span></div>',
                unsafe_allow_html=True)
    st.progress(rs["score"] / 100)
    st.caption(T("{ready} of {total} roadblocks you can answer well", ready=r["ready"], total=r["total"]))
    if SEO_URL:
        st.link_button(T("📖 Take the free 10-Minute Test"), SEO_URL, width="stretch")
    with st.expander(T("🧠 Learn the lingo")):
        g = data.glossary()
        st.progress(len(learned()) / len(g))
        st.caption(f"{len(learned())} of {len(g)} terms learned · Vicky talks in **{lingo.LEVELS[lingo_level()]}**")
        st.selectbox("How should Vicky talk?", LINGO_MODES, key="lingo_mode",
                     help="Auto starts in plain English and uses more investor jargon as you learn terms.")
        nxt_term = lingo.next_term(learned(), prefer=[r_.term for r_ in journey.top_three()])
        if nxt_term:
            term_check(nxt_term, "sidebar")
        pick = st.selectbox("Look up a term", list(g), index=None, placeholder="e.g. Burn multiple")
        if pick:
            e = lingo.entry(pick)
            st.markdown(f"**{esc(pick)}**: {esc(e['means'])}  \n*Tidewell:* {esc(e['example'])}"
                        + (f"  \n*Think of it as:* {esc(e['analogy'])}" if e["analogy"] else ""))
    with st.expander(T("♿ Accessibility")):
        st.toggle(T("Larger text"), key="a11y_large")
        st.toggle(T("High contrast"), key="a11y_contrast")
        st.toggle(T("Reduce motion"), key="a11y_motion", help="Stops avatar animations.")
        st.caption("Every Vicky message and investor question has a 🔊 Read aloud button. Hover, tap or Tab to any "
                   "dotted-underlined word for its meaning.")
    with st.expander(T("⚙️ AI settings")):
        if llm.configured():
            st.toggle("AI feedback", value=True, key="use_ai",
                      help="Off = instant rule-based scoring with no API calls. It is used automatically if the AI is unavailable.")
            st.caption(f"Model: `{llm.model_name()}`. Calculations never come from the AI.")
            if st.button("Test AI connection", width="stretch"):
                with st.spinner("Asking the model to say OK…"):
                    ok, msg = llm.check_connection()
                (st.success if ok else st.error)(msg)
        else:
            st.caption(f"AI not configured: Practise and {PANEL_NAME} use the rule-based scorer.")
    co = data.company()
    st.markdown(f'<div style="border-top:1px solid {BORDER};margin-top:18px;padding-top:12px" class="small">'
                f'<b style="color:{INK}">{esc(co["name"])}</b><br>{T("Books synced 30 Sep 2026 · CAD")}<br>'
                f'{T("Fictional company, synthetic data")}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- header + navigation
extra = []
if st.session_state.get("a11y_large"):
    extra.append(".stApp{zoom:1.15}")
if st.session_state.get("a11y_contrast"):
    extra.append(".small,.plabel,.kpi .l,.stage,.csub,.eyebrow,[data-testid=stCaptionContainer]{color:#111 !important}"
                 ".card,.kpi,.qbox,.seat,div[data-testid=stVerticalBlockBorderWrapper]{border-color:#111 !important}"
                 ".term{border-bottom-color:#111}")
if st.session_state.get("a11y_motion"):
    extra.append("*{animation:none !important;transition:none !important}")
if extra:
    st.markdown("<style>" + "".join(extra) + "</style>", unsafe_allow_html=True)
if st.session_state.get("nav") not in NAV:
    st.session_state.nav = NAV[0]
st.markdown(f'<div class="topbar"><div class="eyebrow">{T("Vicky · Seed readiness")}</div>'
            f'<span class="pill"><span class="dot"></span>{T("Connected books: Oct 2024 to Sep 2026")}</span></div>'
            f'<div class="ptitle">{esc(T(PAGE_TITLES.get(st.session_state.nav, "Start here")))}</div>', unsafe_allow_html=True)
page = st.segmented_control("Step", NAV, key="nav", required=True, label_visibility="collapsed", format_func=T)
st.markdown(f'<div class="footer-line">{T("Numbers come from your books, not the AI. Vicky gives no investment or valuation advice.")}'
            '</div>', unsafe_allow_html=True)
st.write("")


# ================================================================ 1. START HERE
@st.dialog("Details", width="large")
def detail(title: str, summary: str, rows: list[dict], practise: str | None = None):
    """The mock's right-hand detail panel: every finding with its figure and source."""
    st.markdown(f'<div class="serif" style="font-size:1.9rem;font-weight:700;line-height:1.2">{esc(title)}</div>'
                f'<div class="small" style="font-size:1rem;margin:6px 0 16px">{esc(summary)}</div>', unsafe_allow_html=True)
    body = "".join(f'<tr><td>{esc(T(r_["text"]))}<div class="small">{esc(r_.get("ref", ""))}</div></td>'
                   f'<td class="num">{esc(r_.get("figure") or "—")}</td><td>{badge(r_["prov"])}</td></tr>' for r_ in rows)
    st.markdown(f'<table class="dtable"><thead><tr><th>{T("Finding")}</th><th>{T("Figure")}</th><th>{T("Source")}</th></tr></thead>'
                f'<tbody>{body}</tbody></table>', unsafe_allow_html=True)
    if practise:
        st.button("Practise this now →", type="primary", on_click=go, args=(NAV[1],),
                  kwargs={"practice_rb": practise, "practice_text": ""})
    st.caption("Tidewell Systems is fictional. All figures come from the June challenge data pack, calculated in code.")


def rows_html(rows: list[dict]) -> str:
    return "".join(f'<div class="row"><span>{r_["html"] if "html" in r_ else esc(T(r_["text"]))}</span><span class="fig">'
                   f'{"<span class=num>" + esc(r_["figure"]) + "</span>" if r_.get("figure") else ""}{badge(r_["prov"])}'
                   f'</span></div>' for r_ in rows)


def snapshot_card(title: str, summary: str, rows: list[dict], key: str, detail_rows: list[dict] | None = None,
                  practise: str | None = None):
    with st.container(border=True):
        st.markdown(f'<div class="ctitle">{esc(title)}</div><div class="csub">{esc(summary)}</div>{rows_html(rows)}',
                    unsafe_allow_html=True)
        if st.button(T("Open with sources →"), key=f"open_{key}", type="tertiary"):
            detail(title, summary, detail_rows or rows, practise)


def page_start():
    rs = journey.readiness_score(best_scores())
    r = journey.readiness(best_scores())
    top = journey.top_three()
    nxt = next((rb for rb in journey.roadblocks() if best_scores().get(rb.id, 0) < 4), None)

    # --- readiness card + Vicky's quote (the mock's top row)
    c1, c2 = st.columns([1, 2], gap="medium")
    with c1:
        if rs["score"] < rs["with_top3"]:
            msg = T("Not seed-ready yet. Practising your top 3 moves you to {n}.", n=rs["with_top3"])
        elif nxt:
            msg = T("Getting there. Next up: {next}.", next=low(T(nxt.title)))
        else:
            msg = T("Every roadblock answered well. The last points come from fixing the deck itself.")
        st.markdown(f'<div class="ready"><div class="eyebrow"><span style="color:{PURPLE}">/</span> {T("Readiness")}</div>'
                    f'<div class="big">{rs["score"]}<span>/100</span></div><div style="font-size:.92rem;opacity:.85">'
                    f'{esc(msg)}</div><div class="bar"><div style="width:{rs["score"]}%"></div></div></div>',
                    unsafe_allow_html=True)
        if st.button(T("View breakdown →"), type="tertiary", key="rd_break"):
            detail("Readiness breakdown", "How your score out of 100 is built. Every point traces to the data or to your practice.", [
                {"text": "Deck claims that survive a first meeting", "figure": f"{rs['deck_points']}/30 pts",
                 "prov": "historical", "ref": "Deck claim check: 3 of 9 hold up (2 reword, 1 upside)"},
                {"text": "Roadblocks you can answer well (4+/5 in practice)", "figure": f"{rs['practice_points']}/70 pts",
                 "prov": "historical", "ref": f"{r['ready']} of {r['total']} roadblocks; the top 3 count double"},
                {"text": "Fix the deck itself (update the 6 failing claims)", "figure": "+20 pts",
                 "prov": "founder_claim", "ref": "A real-world fix: edit the slides, then re-run the check"},
            ])
    with c2:
        if r["percent"] == 0:
            quote = esc(T("“Your growth is real and your burn is efficient. Lead with that. But fix three things before "
                          "your first meeting, and one of them isn't in your deck.”"))
        elif nxt:
            quote = esc(T("“Good progress. Next, get ready for this: {next}.”", next=low(T(nxt.title))))
        else:
            quote = esc(T("“You can answer everything they'll ask. Time for my partner meeting.”"))
        vicky_says(quote, "thinking" if r["percent"] == 0 else "proud",
                   source=T("Vicky, from a review of 24 months of your books and 9 deck claims"))
        if nxt:
            st.button(T("Practise roadblock {rank}: {title} →", rank=nxt.rank, title=T(nxt.title)), type="primary",
                      on_click=go, args=(NAV[1],), kwargs={"practice_rb": nxt.id, "practice_text": ""})
        else:
            st.button(T("Enter {panel} →", panel=T(PANEL_NAME)), type="primary", on_click=go, args=(NAV[3],))

    st.markdown(f'<div class="divider"><span class="eyebrow"><span style="color:{PURPLE}">/</span> {T("Snapshot")}</span></div>',
                unsafe_allow_html=True)

    # --- path map: where you are -> what's in the way -> where you want to be
    nums = journey.where_you_are()
    g = journey.goal()
    with st.container(border=True):
        st.markdown(f'<div class="ctitle">{T("Your path to a Series A")}</div><div class="csub">'
                    f'{T(PATH_SUB)}</div>', unsafe_allow_html=True)
        now_html = "".join(f'<div class="pnum">{n["display"]}</div><div class="plabel">'
                           f'{term(T(n["label"]), n["term"], label=True)}{badge(n["provenance"])}</div>' for n in nums)
        blind = f'<span class=blind>{T("BLIND SPOT")}</span>'
        block_html = "".join(f'<span class="pchip"><b>{rb.rank}.</b> {esc(T(rb.title))}'
                             f'{blind if rb.blind_spot else ""}</span>' for rb in top)
        stages = "".join(f'<div class="stage {"here" if i_ == r["stage"] else "done" if i_ < r["stage"] else ""}">'
                         f'{i_ + 1}. {T(s_["name"])}{" 👤" if s_["human"] else ""}</div>' for i_, s_ in enumerate(journey.STAGES))
        st.markdown(f"""<div class="path">
          <div class="pcol"><div class="eyebrow">{T("Where you are · Sep 2026")}</div>{now_html}</div>
          <div class="parrow">→</div>
          <div class="pcol"><div class="eyebrow">{T("What's in the way")}</div>{block_html}</div>
          <div class="parrow">→</div>
          <div class="pcol goal"><div class="eyebrow">{T("Where you want to be")}</div><div class="pnum">$5M ARR</div>
            <div class="plabel">{T("Series A")} {badge("founder_claim")}</div>
            <div class="small">{T("Your plan gets there in")} <b>{month(g["plan_month"])}</b> {badge("forecast")}<br>
            {T("At the growth you've actually had, cash runs out in")} <b>{month(g["historical_cash_out"])}</b>,
            {T("before you get there")} {badge("forecast")}</div></div>
        </div><div class="stages">{stages}</div>
        <div class="small" style="margin-top:6px">{T("👤 = bring in a human: a June CPA and a startup lawyer.")}</div>""",
                    unsafe_allow_html=True)

    # --- top 3 questions, each with a practise button
    with st.container(border=True):
        st.markdown(f'<div class="ctitle">{T(TOP3_TITLE)}</div>'
                    f'<div class="csub">{T("Prepare crisp, sourced answers before the first call.")}</div>', unsafe_allow_html=True)
        for rb in top:
            q = practice.question(rb.practice_qid)
            best = best_scores().get(rb.id)
            status = " ✅" if best is not None and best >= 4 else ""
            a_, b_, c_ = st.columns([6, 3, 2], vertical_alignment="center")
            a_.markdown(f'{esc(T(q["text"]))}{status}<div class="small">{rb.rank}. {esc(T(rb.title))}'
                        f'{blind if rb.blind_spot else ""}</div>', unsafe_allow_html=True)
            b_.markdown(f'<div style="text-align:right"><span class="num">{esc(rb.figure)}</span>{badge(rb.figure_prov)}</div>',
                        unsafe_allow_html=True)
            c_.button(T("Practise →"), key=f"go_{rb.id}", on_click=go, args=(NAV[1],),
                      kwargs={"practice_rb": rb.id, "practice_text": ""}, width="stretch")
        if st.button(T("Open with sources →"), key="open_q", type="tertiary"):
            rows = [{"text": practice.question(rb.practice_qid)["text"], "figure": rb.figure, "prov": rb.figure_prov,
                     "ref": "; ".join(f.text for f in rb.facts[:2])} for rb in top]
            detail(T("Top 3 questions you'll be asked"), T("Prepare crisp, sourced answers before the first call."), rows,
                   practise=top[0].id)

    # --- strengths / weaknesses
    a_, b_ = st.columns(2, gap="medium")
    with a_:
        st_rows = [{"text": s_["label"], "figure": s_["figure"], "prov": s_["provenance"], "ref": s_["ref"]}
                   for s_ in journey.strengths()]
        snapshot_card(T("Strengths"), T("{n} signals investors will like.", n=len(st_rows)), st_rows, "s")
    with b_:
        w_rows = journey.weaknesses()
        snapshot_card(T("Weaknesses"), T("{n} areas likely to draw scrutiny.", n=len(w_rows)), w_rows, "w")

    # --- next actions / deck check (the audit card)
    a_, b_ = st.columns(2, gap="medium")
    with a_:
        acts = journey.next_actions()
        snapshot_card(T("Next actions"), T("Do these before you send the deck."), acts[:4], "n", detail_rows=acts)
    with b_:
        cs = claims.check_all()
        failing = [c for c in cs if c["status"] in (claims.FIX, claims.REMOVE)]
        audit_rows = []
        for c in failing:
            ev = c["evidence"]
            fig = ""
            if c["id"] == "arr":
                fig = "$1.37M → " + metrics.get("arr").display()
            elif c["id"] == "gross_margin":
                fig = "92% → " + metrics.get("gross_margin_incl_cs").display()
            elif c["id"] == "churn":
                fig = "1% → " + metrics.get("logo_churn_12m").display()
            elif c["id"] == "nrr":
                fig = "110% → " + metrics.get("nrr").display()
            elif c["id"] == "cac":
                fig = "$970 → " + metrics.get("cac_fully_loaded").display()
            elif c["id"] == "tam":
                fig = "$2B, no source"
            audit_rows.append({"text": c["claim"].strip('"'), "figure": fig,
                               "prov": "reported_in_pack" if c["id"] == "nrr" else "founder_claim" if c["id"] == "tam" else "historical",
                               "ref": c["data_shows"]})
        snapshot_card(T("Deck check: {n} of {total} claims need fixing", n=len(failing), total=len(cs)),
                      T("Every claim tested against your books. No AI involved."), audit_rows[:4], "a", detail_rows=audit_rows)

    with st.expander(T("{n} more things investors may raise", n=len(journey.roadblocks()) - 3)):
        for rb in journey.roadblocks()[3:]:
            roadblock_card(rb)

    st.markdown('<div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:6px" class="small">'
                '<span style="margin-right:auto">Tidewell Systems is fictional; all data is synthetic (June challenge pack).</span>'
                f'<b>{T("Source key:")}</b>' + "".join(badge(k) for k in PROV) + '</div>', unsafe_allow_html=True)


def roadblock_card(rb: journey.Roadblock, top_card: bool = False):
    best = best_scores().get(rb.id)
    status = ("✅ Ready" if best is not None and best >= 4 else f"Best try {best:.1f}/5" if best is not None
              else "Not practised yet")
    with st.container(border=True):
        a_, b_ = st.columns([5, 2], vertical_alignment="center")
        a_.markdown(f'<b>{rb.rank}. {esc(T(rb.title))}</b>{"<span class=blind>" + T("BLIND SPOT") + "</span>" if rb.blind_spot else ""}'
                    f'<div class="small">{esc(rb.impact)} · {status} · {term("the term investors use", rb.term)}</div>',
                    unsafe_allow_html=True)
        b_.markdown(f'<div style="text-align:right"><span class="num">{esc(rb.figure)}</span>{badge(rb.figure_prov)}</div>',
                    unsafe_allow_html=True)
        c1, c2 = st.columns([1, 1])
        if c1.button(T("Open with sources →"), key=f"src_{rb.id}", type="tertiary"):
            detail(rb.title, rb.impact, [{"text": f.text, "prov": f.provenance, "ref": f.ref} for f in rb.facts]
                   + [{"text": "What to do: " + a, "prov": "forecast", "ref": ""} for a in rb.what_to_do], practise=rb.id)
        c2.button(T("Practise this →"), key=f"go_{rb.id}", on_click=go, args=(NAV[1],),
                  kwargs={"practice_rb": rb.id, "practice_text": ""})


# ================================================================ 2. PRACTISE
def page_practise():
    rbs = journey.roadblocks()
    ids = [r_.id for r_ in rbs]
    st.session_state.setdefault("practice_rb", ids[0])
    c1, c2 = st.columns([3, 2])
    rid = c1.selectbox(T("Roadblock to practise"), ids, key="practice_rb",
                       format_func=lambda i: f"{journey.roadblock(i).rank}. {T(journey.roadblock(i).title)}"
                       + ("  ✅" if best_scores().get(i, 0) >= 4 else ""))
    profiles = data.investor_profiles()
    persona = c2.selectbox(T("Who's asking"), list(profiles), key="practice_persona", format_func=person)
    rb = journey.roadblock(rid)
    q = practice.question(rb.practice_qid)
    attempts = st.session_state.get("attempts", {}).get(rid, [])
    if not attempts:
        vicky_says(T("Let's work on <b>{title}</b>. Read the numbers first, then answer like you're in the room. "
                     "I'll check every figure you say against your books.", title=esc(low(T(rb.title)))), "numbers")
    else:
        w = attempts[-1]["weighted"]
        tip = esc(attempts[-1]["improve"].split(". ")[0].rstrip(".")) + "."
        if w >= 4:
            vicky_says(T("<b>That's an answer a lead investor writes down.</b> {w} out of 5. Readiness is now {score}/100.",
                         w=f"{w:.1f}", score=journey.readiness_score(best_scores())["score"]), "proud")
        elif w >= 3:
            vicky_says(T("Close: {w} out of 5. One thing to fix: {tip} Try again?", w=f"{w:.1f}", tip=tip), "happy")
        else:
            vicky_says(T("That one would hurt in the room ({w} out of 5), and that's why we practise here first. "
                         "Start with this: {tip}", w=f"{w:.1f}", tip=tip), "thinking")

    with st.expander(T("First, understand it: {title}", title=T(rb.title)), expanded=not st.session_state.get("attempts", {}).get(rid)):
        st.markdown(f"**Why it matters:** {esc(rb.impact)}")
        for f in rb.facts:
            st.markdown(f"- {esc(f.text)} {badge(f.provenance)}", unsafe_allow_html=True)
        st.markdown(f"**What the investor is listening for:** {esc(q['why'])}")
        st.markdown(f"<span class='small'>Jargon you'll hear: {term(rb.term, rb.term)}</span>", unsafe_allow_html=True)

    investor_says(persona, q["text"])
    st.caption(T("A strong answer has four parts: the number, how you got it, the weak spot, and what you're doing about it."))
    voice_input("practice_text", f"mic_practice_{rid}")
    answer = st.text_area(T("Your answer"), key="practice_text", height=130,
                          placeholder="Answer as you would in the room. Use your real numbers.")
    if st.button(T("Get feedback"), type="primary") and answer.strip():
        with st.spinner("Checking your numbers and scoring your answer…"):
            turn = practice.score(q, answer, persona, use_ai=use_ai(), lang=LANG())
        st.session_state.setdefault("attempts", {}).setdefault(rid, []).append(turn)
        record(rid, turn["weighted"])
        st.rerun()

    if attempts:
        last = attempts[-1]
        prev = attempts[-2]["weighted"] if len(attempts) > 1 else None
        st.subheader(T("Attempt {n}", n=len(attempts)))
        if last.get("investor_reply"):
            st.markdown(f"<div class='vicky'>{face(persona, 'happy' if last['weighted'] >= 3 else 'stern', size=44)}"
                        f"<div class='small' style='padding-top:10px'><i>{esc(last['investor_reply'])}</i></div></div>",
                        unsafe_allow_html=True)
        feedback(last, prev)
        if len(attempts) > 1:
            trend = " → ".join(f"{a['weighted']:.1f}" for a in attempts)
            st.markdown(f"**Your progress on this question:** {trend}")
        if rb.term not in learned():
            with st.container(border=True):
                term_check(rb.term, f"practice_{rid}")
        b1, b2 = st.columns(2)
        b1.button(T("Try again"), on_click=lambda: st.session_state.update(practice_text=""), width="stretch")
        nxt = next((i for i in ids if best_scores().get(i, 0) < 4 and i != rid), None)
        if last["weighted"] >= 4 and nxt:
            b2.button(f"Next roadblock: {journey.roadblock(nxt).title} →", type="primary", width="stretch",
                      on_click=go, args=(NAV[1],), kwargs={"practice_rb": nxt, "practice_text": ""})
        elif last["weighted"] >= 4:
            b2.button(f"You're ready for {PANEL_NAME} 🔥", type="primary", width="stretch", on_click=go, args=(NAV[3],))


def deck_uploader() -> dict | None:
    """Taksh Girdhar's deck upload: an optional PDF the founder can point at during the meeting. Parsed once per file."""
    from vicky import deck as decks
    f = st.file_uploader("Your pitch deck (PDF, optional)", type=["pdf"],
                         help="Export from PowerPoint, Keynote or Google Slides as PDF. During the meeting you pick "
                              "the slide you're pointing at; the investor reads it with your answer, and code checks it.")
    st.caption("No deck handy? Try `assets/sample_deck/tidewell_deck_draft.pdf` from the repo.")
    if not f:
        st.session_state.pop("deck_upload", None)
        return None
    cached = st.session_state.get("deck_upload")
    if not cached or cached["file_id"] != f.file_id:
        try:
            cached = {"file_id": f.file_id, "deck": decks.load(f.getvalue(), f.name), "error": None}
        except decks.DeckError as e:
            cached = {"file_id": f.file_id, "deck": None, "error": str(e)}
        st.session_state.deck_upload = cached
    if cached["error"]:
        st.error(cached["error"])
        return None
    d = cached["deck"]
    blank = [s_["n"] for s_ in d["slides"] if not s_["text"]]
    st.caption(f"📎 {d['name']}: {len(d['slides'])} slides loaded."
               + (f" Only the first {len(d['slides'])} are used." if d["truncated"] else "")
               + (f" Slides {', '.join(map(str, blank))} have no text (image only), so the investor can't read them."
                  if blank else ""))
    return d


def slide_viewer(deck: dict) -> int | None:
    """Slide picker + image. Returns the slide the founder is pointing at (None = no slide)."""
    options = [None] + [s_["n"] for s_ in deck["slides"]]
    slide = st.selectbox("Slide you're referencing", options, key="pitch_slide",
                         format_func=lambda n: "No slide" if n is None else f"{n} · {deck['slides'][n - 1]['title']}")
    if slide:
        st.image(deck["images"][slide - 1], width="stretch")
        st.caption("The investor sees this slide's text with your next answer, and code checks it against the data.")
    else:
        st.caption("Pick a slide to point at it in your next answer.")
    return slide


def slide_feedback(turn: dict):
    """Taksh Girdhar's slide check, shown inside the answer's feedback."""
    slide = turn.get("slide")
    if not slide:
        return
    for c in slide["contradictions"]:
        st.warning(escape_dollars(f"Slide {slide['n']} vs your answer: {c}"))
    if slide["check"]["issues"]:
        st.warning(escape_dollars(f"Slide {slide['n']} check: " + "; ".join(
            f"**{i['text']}**: {i['detail']}" for i in slide["check"]["issues"])))
    elif not slide["contradictions"]:
        st.caption(f"Slide {slide['n']}: {slide['check']['summary']}")


def tidy(text: str) -> str:
    """Collapse stray whitespace from copy-paste (it also makes identical answers hit the AI cache)."""
    return " ".join((text or "").split())


# ================================================================ 3. MOCK MEETING (Ronald's pitch simulator)
def page_mock():
    st.caption("One investor, follow-up questions, and a debrief at the end.")
    if not llm.configured():
        vicky_says(f"The 1:1 chat needs my AI connection, which isn't set up here. Practise and {PANEL_NAME} work "
                   f"without it.", "concerned", speak=False)
        return
    profiles = data.investor_profiles()
    sess = st.session_state.get("pitch")
    if not sess:
        cols = st.columns(len(profiles))
        for col, (key, p) in zip(cols, profiles.items()):
            with col:
                st.markdown(f"{face(key, 'happy', size=64)}<br><b>{esc(person(key))}</b>", unsafe_allow_html=True)
                st.caption(p["who"])
                st.markdown(f"<span class='small'><b>Cares about:</b> {', '.join(p['cares_about'])}<br>"
                            f"<b>Says no when:</b> {', '.join(p['says_no_when'])}</span>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([2, 1, 1])
        choice = c1.selectbox("Investor", list(profiles), format_func=person)
        n_q = c2.slider("Questions", 2, 5, 3)
        if c3.button("🎲 Random investor"):
            st.session_state.random_choice = random.choice(list(profiles))
        choice = st.session_state.pop("random_choice", choice)
        deck = deck_uploader()
        if st.button("Start meeting", type="primary"):
            from vicky.graphs.pitch import PitchSession
            with st.spinner("The investor is taking a seat…"):
                try:
                    st.session_state.pitch = PitchSession(choice, n_q, deck=deck)
                    st.session_state.pitch_persona = choice
                    st.session_state.pitch_deck = deck
                    st.session_state.pop("pitch_slide", None)
                except Exception as e:  # keep the message across the rerun, or it flashes and disappears
                    st.session_state.pitch_error = (f"{llm.explain_error(e)} Practise and {PANEL_NAME} still work "
                                                    "with the rule-based scorer.")
            st.rerun()
        if st.session_state.get("pitch_error"):
            st.error(st.session_state.pop("pitch_error"))
        st.caption("Investor types are archetypes from the data pack (Appendix E), not real firms or people.")
        return
    p = profiles[st.session_state.pitch_persona]
    state = sess.state
    pkey = st.session_state.pitch_persona
    st.markdown(f"**In the room:** {esc(person(pkey))}. {esc(p['style'])}")
    deck = st.session_state.get("pitch_deck")
    slide = None
    chat_col, slide_col = st.columns([3, 2], gap="medium") if deck else (st.container(), None)
    if deck:
        with slide_col:
            slide = slide_viewer(deck)
    with chat_col:
        turns = iter(state.get("turns", []))
        for t in state["transcript"]:
            if t["role"] == "investor":
                with st.chat_message("investor", avatar=avatar.data_uri(pkey)):
                    st.markdown(glossify(t["text"]), unsafe_allow_html=True)
            else:
                with st.chat_message("founder", avatar="🧑‍💻"):
                    if t.get("slide") and deck:
                        st.caption(f"📎 Pointing at slide {t['slide']}: {deck['slides'][t['slide'] - 1]['title']}")
                    st.markdown(escape_dollars(t["text"]))
                turn = next(turns, None)
                if turn:
                    with st.expander(f"Feedback: {turn['weighted']:.1f}/5 (weighted for this investor)"):
                        slide_feedback(turn)
                        feedback({**turn, "method": "ai"}, show_strong=True)
    if sess.finished:
        d = state["debrief"]
        st.divider()
        st.subheader(f"Debrief: {d['verdict']}")
        cols = st.columns(5)
        cols[0].metric("Overall (weighted)", f"{d['overall']:.1f}/5")
        for col, (k, val) in zip(cols[1:], d["averages"].items()):
            col.metric(DIM_LABEL[k], f"{val}/5")
        st.markdown(f"Weakest: **{DIM_LABEL[d['weakest']]}**. Figures flagged by the fact check: **{d['flagged_figures']}**.")
        if d.get("slides_flagged"):
            st.markdown("**Slides to fix before the real meeting:**")
            for s_ in d["slides_flagged"]:
                st.markdown(escape_dollars(f"- **Slide {s_['n']}: {s_['title']}**: " + "; ".join(s_["problems"])))
        elif deck:
            st.success("No problems found on the slides you pointed at.")
    else:
        if err := st.session_state.pop("pitch_error", None):
            st.error(err)
        ans = st.chat_input("Your answer…" if not slide else f"Your answer (pointing at slide {slide})…")
        if ans:
            with st.spinner("The investor is thinking…"):
                try:
                    sess.answer(tidy(ans), slide=slide)
                except Exception as e:  # shown after the rerun; the answer can simply be sent again
                    st.session_state.pitch_error = llm.explain_error(e) + " Nothing was lost: send the answer again."
            st.rerun()
    if st.button("End / new meeting"):
        del st.session_state["pitch"]
        st.session_state.pop("pitch_deck", None)
        st.rerun()


# ================================================================ 4. HOT SEAT
def page_hotseat():
    profiles = data.investor_profiles()
    hs = st.session_state.get("hs")
    if not hs:
        vicky_says(T("Welcome to my partner meeting. In a real raise, this is the last step: you pitch the whole "
                     "partnership at once. A lead seed fund partner, an angel investor and the skeptical partner will ask "
                     "six questions, <b>{secs} seconds</b> each. Every partner has one thing that makes them walk out. "
                     "It's the hardest version of the meeting, so the real one feels easier.",
                     secs=hotseat.TIME_LIMIT_SECONDS), "happy")
        cols = st.columns(3)
        for col, key in zip(cols, hotseat.PANEL):
            p = profiles[key]
            col.markdown(f'<div class="seat">{face(key, "happy", size=84)}<b>{esc(person(key))}</b><br>'
                         f'<span class="small">{T("Walks out when")}: {esc(", ".join(p["says_no_when"]).lower())}</span></div>',
                         unsafe_allow_html=True)
        st.write("")
        if st.button(T("Start the partner meeting"), type="primary"):
            st.session_state.hs = hotseat.new_session()
            st.session_state.hs_started = time.time()
            st.rerun()
        return

    cur = hotseat.current(hs)
    cols = st.columns(3)
    for col, key in zip(cols, hotseat.PANEL):
        p = profiles[key]
        cls = "out" if key in hs["out"] else "speaking" if cur and cur["persona"] == key else ""
        status = T("OUT") if key in hs["out"] else T("speaking") if cls == "speaking" else T("listening")
        mood = "stern" if cls == "out" else "thinking" if cls == "speaking" else "happy"
        col.markdown(f'<div class="seat {cls}">{face(key, mood, talking=cls == "speaking", size=84)}'
                     f'<b>{esc(person(key))}</b><br><span class="small">{status}</span></div>', unsafe_allow_html=True)

    if hs["turns"]:
        last = hs["turns"][-1]
        p = profiles[last["persona"]]
        msg = f"**{person(last['persona'])}:** {last['reaction']}"
        (st.error if last["walked_out"] else st.success)(msg + (f"  \n*Why:* {hs['out'][last['persona']]}"
                                                                   if last["walked_out"] else ""))

    if cur:
        investor_says(cur["persona"], cur["question"]["text"])
        started = st.session_state.get("hs_started", time.time())

        @st.fragment(run_every=1)
        def clock():
            left = hotseat.TIME_LIMIT_SECONDS - int(time.time() - started)
            color = "#c0392b" if left <= 10 else "#111"
            st.markdown(f"<div class='timer' style='color:{color}'>⏱ {max(left, 0)}s"
                        f"{' · over time' if left < 0 else ''}</div>", unsafe_allow_html=True)
        clock()
        voice_input(f"hs_ans_{len(hs['turns'])}", f"mic_hs_{len(hs['turns'])}")
        with st.form(f"hs_form_{len(hs['turns'])}", clear_on_submit=True):
            ans = st.text_area(T("Your answer"), key=f"hs_ans_{len(hs['turns'])}", height=110, placeholder="The number, how you got it, the weak spot, the fix.")
            sent = st.form_submit_button(T("Answer"), type="primary")
        if sent and ans.strip():
            with st.spinner("The panel is conferring…"):
                turn = hotseat.submit(hs, ans, time.time() - started, use_ai=use_ai(), lang=LANG())
            rid = next((r_.id for r_ in journey.roadblocks() if r_.practice_qid == turn.get("qid")), None)
            record(rid, turn.get("weighted", 0))  # partner meeting answers count toward readiness too
            st.session_state.hs_started = time.time()
            st.rerun()
        return

    # --- scorecard
    card = hotseat.scorecard(hs)
    n_in = len(card["still_in"])
    vicky_says({3: "All three partners want a second meeting. That's what confident sounds like.",
                0: "Everyone walked out, and that's fine: better here than in the real room. Your weakest answer is "
                   "below. Fix that one first and come back."}.get(
        n_in, f"You kept {n_in} of 3 partners. Look at why the others left: each reason is one specific fix."),
        "proud" if n_in == 3 else "concerned" if n_in == 0 else "happy")
    st.subheader(f"Scorecard: {card['verdict']}")
    c1, c2 = st.columns(2)
    c1.metric("Investors still in", f"{len(card['still_in'])} of 3")
    c2.metric("Average answer", f"{card['average']:.1f}/5")
    for w in card["walked_out"]:
        key = next(k for k in hotseat.PANEL if profiles[k]["name"] == w["name"])
        st.markdown(f"<div class='vicky'>{face(key, 'stern', size=40)}<div style='padding-top:8px'><b>{esc(person(key))}"
                    f"</b> walked out: {esc(w['reason'])}</div></div>", unsafe_allow_html=True)
    for name in card["still_in"]:
        key = next(k for k in hotseat.PANEL if profiles[k]["name"] == name)
        st.markdown(f"<div class='vicky'>{face(key, 'proud', size=40)}<div style='padding-top:8px'>✅ <b>"
                    f"{esc(person(key))}</b> wants a second meeting</div></div>", unsafe_allow_html=True)
    for t in hs["turns"]:
        p = profiles[t["persona"]]
        icon = "🚪" if t["walked_out"] else "✅"
        with st.expander(f"{icon} {person(t['persona']).split(',')[0]}: {t['question']} · {t['weighted']:.1f}/5 · {t['seconds']}s"):
            st.markdown(f"**You said:** {esc(t['answer'])}")
            feedback(t)
    if card["weakest"]:
        w = card["weakest"]
        rid = next((r_.id for r_ in journey.roadblocks() if r_.practice_qid == w["qid"]), None)
        if rid:
            st.button(f"Practise your weakest answer: “{w['question']}” →", type="primary", on_click=go,
                      args=(NAV[1],), kwargs={"practice_rb": rid, "practice_text": ""})
    if st.button("Go again"):
        st.session_state.hs = hotseat.new_session()
        st.session_state.hs_started = time.time()
        st.rerun()


# ================================================================ 5. ASK VICKY (Ronald's coach)
INTENT_LABEL = {  # Taksh Girdhar's decision model: the question type Vicky chose
    "explain_metric": ("Explain a metric", "#007277", "#DDF1F1"),
    "challenge_claim": ("Challenge a claim", "#B46D10", "#F8ECDB"),
    "what_if": ("What-if scenario", PURPLE, "#ECE9FE"),
    "concept": ("Concept", "#3D4A5C", "#E6EAF0"),
    "investor_prep": ("Investor prep", PURPLE, "#ECE9FE"),
    "missing_data": ("Missing data", "#66635D", "#E9E8E4"),
    "policy_boundary": ("Policy boundary", "#9B1C1C", "#FBE4E4"),
    "general": ("General", "#66635D", "#E9E8E4"),
}
BY_COLOR = {"code": ("#007277", "#DDF1F1"), "llm": (PURPLE, "#ECE9FE")}


def chip(text: str, fg: str, bg: str) -> str:
    return f'<span class="chip" style="color:{fg};background:{bg}">{esc(text)}</span>'


def render_coach_header(meta: dict):
    chips = [chip(*INTENT_LABEL.get(meta.get("intent"), INTENT_LABEL["general"]))]
    if meta.get("policy"):
        chips.append(chip(f"gate: {meta['policy']['rule'].replace('_', ' ')}", "#9B1C1C", "#FBE4E4"))
    if meta.get("revised"):
        chips.append(chip("revised after audit", "#B46D10", "#F8ECDB"))
    if meta.get("audit", {}).get("passed"):
        chips.append(chip("audited: every figure checked", "#007277", "#DDF1F1"))
    st.markdown(" ".join(chips), unsafe_allow_html=True)


def render_coach_details(meta: dict):
    if meta.get("decision_trace"):
        with st.expander("🧭 How Vicky decided"):
            rows = "".join(f'<b>{esc(t["level"])}</b>{chip(t["by"], *BY_COLOR.get(t["by"], ("#B46D10", "#F8ECDB")))}'
                           f'<span>{esc(t["decision"])}</span>' for t in meta["decision_trace"])
            st.markdown(f'<div class="trace">{rows}</div>', unsafe_allow_html=True)
            st.caption("Level 1 is a code-only policy check. Level 2 is the AI planner (with a keyword fallback). "
                       "Level 3 is checked and run in code.")
    if meta.get("reasoning"):
        with st.expander("🧠 How Vicky reasoned"):
            st.markdown(glossify("\n".join(f"{n}. {s_}" for n, s_ in enumerate(meta["reasoning"], 1))),
                        unsafe_allow_html=True)
    if meta.get("evidence"):
        n = len(meta["evidence"])
        with st.expander(f"🧰 Evidence ({n} tool result{'s' if n != 1 else ''})"):
            for e in meta["evidence"]:
                args = ", ".join(f"{k}={v!r}" for k, v in e["args"].items())
                st.markdown(f"`{e['name']}({args})`" + ("" if e.get("ok", True) else " ⚠️ failed"))
                st.code(e["preview"] + ("…" if len(e["preview"]) >= 600 else ""), language="json")
    elif meta.get("tool_calls"):
        st.caption("Tools used: " + ", ".join(f"`{t['name']}`" for t in meta["tool_calls"]))
    if meta.get("timings"):
        steps = " · ".join(f"{t['step']} {t['seconds']:.1f}s" for t in meta["timings"] if t["seconds"] >= 0.05)
        st.caption(f"⏱️ {meta['seconds']:.1f}s total" + (f" ({steps})" if steps else ""))


def page_ask():
    if not llm.configured():
        vicky_says(T("I need my AI connection to chat, and it isn't set up here. Every number, with its calculation, "
                     "is in Financials."), "concerned", speak=False)
        return
    st.session_state.setdefault("chat", [])
    if not st.session_state.chat:
        vicky_says(T("Ask me anything about your numbers, like 'explain burn multiple like I'm an engineer'. I look "
                     "everything up in your books, and an independent check reviews my answer before you see it."), speak=False)
    st.caption("Vicky decides in levels (policy check → question type → tool plan), runs the tools in code, reasons "
               "step by step, and an independent audit checks every figure before you see it.")
    examples = ["What's our real ARR and why isn't it $1.37M?", "Explain burn multiple like I'm an engineer",
                "What if churn stays at 2% and reps take 3 months to ramp?", "What valuation should we raise at?",
                "Why will we beat Jobber?"]
    picked = None
    for col, ex in zip(st.columns(len(examples)), examples):
        if col.button(ex, width="stretch"):
            picked = ex
    for t in st.session_state.chat:
        with st.chat_message(t["role"], avatar=avatar.data_uri("vicky") if t["role"] == "assistant" else None):
            meta = t.get("meta")
            if meta:
                render_coach_header(meta)
            if t["role"] == "assistant":
                st.markdown(glossify(t["content"]), unsafe_allow_html=True)
            else:
                st.markdown(escape_dollars(t["content"]), unsafe_allow_html=True)
            human_box(t.get("handoff"))
            if meta:
                render_coach_details(meta)
                render_audit([{**a, "round": i_ + 1} for i_, a in enumerate(meta["audit_history"])], "Answer audit")
    q = tidy(st.chat_input("Ask about ARR, churn, runway, CAC, SAFEs…") or picked or "")
    if q:
        from vicky.graphs import coach
        st.session_state.chat.append({"role": "user", "content": q})
        history = [HumanMessage(t["content"]) if t["role"] == "user" else AIMessage(t["content"])
                   for t in st.session_state.chat[:-1][-8:]]
        with st.spinner("Vicky is checking the numbers…", show_time=True):
            try:
                res = coach.ask(history, lang_wrap(q))
                st.session_state.chat.append({"role": "assistant", "content": res["answer"], "meta": res,
                                              "handoff": handoff.needs_human(q)})
            except Exception as e:
                st.session_state.chat.append({"role": "assistant", "handoff": handoff.needs_human(q),
                                              "content": f"⚠️ {llm.explain_error(e)} The Financials tab has every "
                                                         "number with its calculation."})
        st.rerun()
    if st.session_state.chat and st.button("Clear chat"):
        st.session_state.chat = []
        st.rerun()


# ================================================================ 6. DEEP DIVE (Taksh Girdhar's engine)
def page_deep():
    vicky_says("Everything here shows its math. Tap <b>Show calculation</b> on any number to see the formula and "
               "where it came from.", "numbers", speak=False)
    t = st.tabs(["📊 Numbers", "🧾 Deck claim check", "🧪 Scenario lab", "📋 Investor prep pack"])
    with t[0]:
        deep_numbers()
    with t[1]:
        deep_claims()
    with t[2]:
        deep_scenarios()
    with t[3]:
        deep_pack()


def deep_numbers():
    st.subheader("Snapshot at September 30, 2026")
    r1 = st.columns(4)
    with r1[0]:
        kpi("arr", "Recurring revenue per year", "MRR × 12, no one-time fees", "ARR (annual recurring revenue)")
    with r1[1]:
        kpi("cmgr_12m", "Monthly growth (12 months)", f"Last 3 months: {metrics.get('cmgr_3m').display()}",
            "CMGR (compound monthly growth rate)")
    with r1[2]:
        kpi("gross_margin_incl_cs", "Profit on each sale, incl. support",
            f"As booked: {metrics.get('gross_margin_booked').display()}", "Gross margin")
    with r1[3]:
        kpi("logo_churn_12m", "Customers lost per month", f"Last 6 months: {metrics.get('logo_churn_6m').display()}",
            "Churn (logo)")
    r2 = st.columns(4)
    with r2[0]:
        kpi("cac_fully_loaded", "Cost to win a customer", f"Earned back in ≈ {metrics.get('cac_payback_months').value:.1f} months",
            "CAC (customer acquisition cost)")
    with r2[1]:
        kpi("burn_monthly", "Cash burned per month", "Apr–Sep 2026, excl. SR&ED", "Burn rate")
    with r2[2]:
        kpi("runway_months", "Months of cash left", f"Cash {metrics.get('cash').display()}", "Runway")
    with r2[3]:
        kpi("burn_multiple", "Burn per $1 of new revenue", f"Excl. SR&ED: {metrics.get('burn_multiple_ex_sred').display()}",
            "Burn multiple")
    r3 = st.columns(4)
    with r3[0]:
        kpi("nrr", "Revenue kept from last year's customers", "Not recomputable from the files provided",
            "Net revenue retention (NRR)")
    with r3[1]:
        kpi("ncg_share_of_mrr", "Largest customer's share", "Northern Comfort, renews Mar 2027", "Logo")
    with r3[2]:
        kpi("plan_runway_after_close", "Months of cash after the raise (plan)", "Deck says 24 months", "Runway")
    with r3[3]:
        kpi("plan_arr_end", "ARR in March 2028 (plan)", "Founders' forecast", "Forecast")

    st.subheader("Monthly recurring revenue: actuals vs the founders' plan vs historical drivers")
    hist = data.income_statement()["subscription_revenue"].rename("MRR").to_frame()
    hist["series"] = "Actual (historical)"
    fp = forecast.run(forecast.founders_plan()).loc[:"2028-03", ["mrr"]].rename(columns={"mrr": "MRR"})
    fp["series"] = "Founders' plan (forecast)"
    hd = forecast.run(forecast.historical_drivers()).loc[:"2028-03", ["mrr"]].rename(columns={"mrr": "MRR"})
    hd["series"] = "Historical drivers (forecast)"
    chart_df = pd.concat([hist, fp, hd]).reset_index(names="month")
    chart_df["month"] = pd.to_datetime(chart_df["month"])
    chart = alt.Chart(chart_df).mark_line(point=alt.OverlayMarkDef(size=18)).encode(
        x=alt.X("month:T", title=None),
        y=alt.Y("MRR:Q", title="MRR (CAD)", axis=alt.Axis(format="$,.0s")),
        color=alt.Color("series:N", title=None, scale=alt.Scale(
            domain=["Actual (historical)", "Founders' plan (forecast)", "Historical drivers (forecast)"],
            range=["#111111", "#d08c00", PURPLE]), legend=alt.Legend(orient="top")),
        strokeDash=alt.condition(alt.datum.series == "Actual (historical)", alt.value([1, 0]), alt.value([5, 4])),
        tooltip=["series", alt.Tooltip("month:T", format="%b %Y"), alt.Tooltip("MRR:Q", format="$,.0f")],
    ).properties(height=320)
    st.altair_chart(chart, width="stretch")
    st.caption("Historical drivers: 2% churn, 3-month rep ramp, 4.5 deals per rep, Northern Comfort flat at 260 seats, "
               "price rise phased in. Spending follows the founders' plan in both forecasts.")
    with st.expander("All metrics, with formulas and sources"):
        tbl = pd.DataFrame(metrics.as_table())[["label", "display", "provenance", "formula", "ref", "note"]]
        st.dataframe(tbl, hide_index=True, width="stretch")
    with st.expander("What's missing from the data (and what would fill the gap)"):
        for item in data.company()["missing_data"]:
            st.markdown(f"- {esc(item)}")


def deep_claims():
    st.subheader("Would your deck survive a first meeting?")
    cs = claims.check_all()
    failing = sum(c["status"] in (claims.FIX, claims.REMOVE) for c in cs)
    st.markdown(f"**{failing} of {len(cs)} claims need fixing** and the rest need rewording or reframing. "
                "This check is deterministic: no AI involved, every figure traces to the data.")
    for c in cs:
        color = STATUS_COLOR[c["status"]]
        seen_c = set()
        st.markdown(
            f'<div class="claim" style="border-color:{color}"><b>“{esc(c["claim"])}”</b>{badge("founder_claim")} '
            f'<span class="badge" style="color:#fff;background:{color}">{c["status"]}</span><br>'
            f'<b>What the data shows:</b> {glossify(esc(c["data_shows"]), seen_c)}<br><b>Say instead:</b> '
            f'{glossify(esc(c["suggested_fix"]), seen_c)}<br><span class="small"><b>Why investors care:</b> '
            f'{glossify(esc(c["why_investors_care"]), seen_c)}</span></div>',
            unsafe_allow_html=True)
        if c["evidence"]:
            with st.popover("Evidence"):
                for e in c["evidence"]:
                    show_metric(metrics.get(e["key"]))


def deep_pack():
    st.subheader("Investor prep pack")
    st.caption("Pipeline: compute metrics and checks in code → Vicky drafts the pack → independent audit checks every "
               "figure, claim and benchmark → Vicky revises (up to 2 rounds) → you see the result plus the audit notes.")
    c1, c2 = st.columns([1, 3])
    run_llm = c1.button("Generate with Vicky", type="primary", disabled=not llm.configured())
    run_det = c2.button("Generate without AI (deterministic)")
    if run_llm:
        from vicky.graphs import prep_pack
        with st.status("Building your pack…", expanded=True) as status:
            st.write("Computing metrics, claim checks and scenarios…")
            try:
                st.session_state.pack = prep_pack.run()
                status.update(label="Pack ready", state="complete")
            except Exception as e:
                status.update(label="The AI is unavailable; showing the deterministic pack", state="error")
                st.caption(f"{type(e).__name__}: {str(e)[:160]}")
                st.session_state.pack = prep_pack.deterministic()
    if run_det:
        from vicky.graphs import prep_pack
        st.session_state.pack = prep_pack.deterministic()
    pack = st.session_state.get("pack")
    if pack:
        st.markdown(glossify_sections(pack["markdown"].replace("$", "&#36;")), unsafe_allow_html=True)
        render_audit(pack["audit_log"])
        st.download_button("Download pack (.md)", pack["markdown"], file_name="tidewell_investor_prep_pack.md")


def deep_scenarios():
    st.subheader("Scenario lab: stress-test the forecast")
    st.caption("Everything here is FORECAST. Revenue is rebuilt from drivers; spending follows the founders' plan. "
               "The model reproduces the founders' plan to within about 1% of MRR each quarter.")
    preset = st.radio("Start from", list(forecast.PRESETS), horizontal=True)
    base = forecast.PRESETS[preset]()
    c1, c2, c3 = st.columns(3)
    churn = c1.slider("Customers lost per month (churn)", 0.005, 0.04, base.monthly_churn, 0.0025, format="%.4f",
                      help="Historical: 2.0% (12 mo), 1.6% (6 mo). Plan: 1.0%")
    ramp = c1.slider("Months for a new salesperson to ramp", 1, 6, base.ae_ramp_months, help="Historical ≈ 3. Plan: 1")
    deals = c2.slider("Deals per ramped salesperson / month", 2.0, 7.0, float(base.ae_new_per_month), 0.5,
                      help="Historical: 4 to 5")
    ncg_seats = c2.select_slider("Northern Comfort seats at renewal", [0, 260, 400, 600], base.ncg_renewal_seats,
                                 help="0 = they leave. Nothing is signed.")
    uptake = c3.slider("Share of customers repriced in Jan 2027", 0.0, 1.0, base.price_increase_uptake, 0.05)
    months = ["2027-01", "2027-02", "2027-03", "2027-04", "2027-06"]
    seed_month = c3.selectbox("Seed round lands", months, index=months.index(base.seed_month))
    hold = c3.toggle("Hold spending until the round lands", value=base.hold_spend_until_close)
    custom = forecast.with_overrides(base, name="Your scenario", monthly_churn=churn, ae_ramp_months=ramp,
                                     ae_new_per_month=deals, ncg_renewal_seats=ncg_seats, price_increase_uptake=uptake,
                                     seed_month=seed_month, hold_spend_until_close=hold)
    plan, mine = forecast.compare(forecast.founders_plan(), custom)
    k = st.columns(4)
    k[0].metric("ARR at Mar 2028", f"${mine['arr_mar_2028'] / 1e6:.2f}M",
                f"{(mine['arr_mar_2028'] - plan['arr_mar_2028']) / 1e6:+.2f}M vs plan")
    k[1].metric("Cash at Mar 2028", f"${mine['cash_mar_2028'] / 1e6:.2f}M",
                f"{(mine['cash_mar_2028'] - plan['cash_mar_2028']) / 1e6:+.2f}M vs plan")
    k[2].metric("Cash runs out", mine["cash_out_month"] or "after 2030")
    rw = mine["runway_after_close_months"]
    k[3].metric("Runway after close", f"{rw} months" if rw and rw > 0 else "—",
                None if not (rw and plan["runway_after_close_months"]) else f"{rw - plan['runway_after_close_months']:+d} vs plan")
    if mine["cash_out_before_close"]:
        st.error(f"⚠️ Cash runs out in {mine['cash_out_month']}, before the round lands in {seed_month}. "
                 "Try holding spending until the term sheet is signed.")
    if mine["arr_mar_2028"] < 5_000_000:
        st.warning(f"ARR at March 2028 is ${mine['arr_mar_2028'] / 1e6:.2f}M, short of the \"$5M ARR Series A\" goal.")
    sim = forecast.run(custom).loc[:"2029-06"]
    pl = forecast.run(forecast.founders_plan()).loc[:"2029-06"]
    cdf = pd.concat([pl[["cash"]].assign(series="Founders' plan"), sim[["cash"]].assign(series="Your scenario")]).reset_index(names="month")
    cdf["month"] = pd.to_datetime(cdf["month"])
    cash_chart = alt.Chart(cdf).mark_line().encode(
        x=alt.X("month:T", title=None), y=alt.Y("cash:Q", title="Cash (CAD)", axis=alt.Axis(format="$,.2s")),
        color=alt.Color("series:N", title=None, scale=alt.Scale(range=["#d08c00", PURPLE]), legend=alt.Legend(orient="top")),
        tooltip=["series", alt.Tooltip("month:T", format="%b %Y"), alt.Tooltip("cash:Q", format="$,.0f")])
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#9b1c1c", strokeDash=[4, 4]).encode(y="y:Q")
    st.altair_chart((cash_chart + zero).properties(height=300), width="stretch")
    st.caption("After March 2028 the burn is held at its final-quarter level, as in the data pack's runway figures.")


# ---------------------------------------------------------------- router
{NAV[0]: page_start, NAV[1]: page_practise, NAV[2]: page_mock, NAV[3]: page_hotseat,
 NAV[4]: page_ask, NAV[5]: page_deep}[page]()
