"""Hover definitions for Appendix I glossary terms.

glossify(text) wraps the first mention of each glossary term in a tooltip span (definition + Tidewell
example). It works on Markdown or HTML and leaves code, HTML tags and link targets alone.
The app injects CSS (below) once so the tooltip shows on hover, tap or keyboard focus.
"""
import html
import re
from functools import lru_cache

from . import data

# Names that find each entry in text. Default: the name before " (" plus the bracketed acronym.
ALIASES = {
    "Churn (logo)": ["logo churn", "churn"],
    "Churn (revenue)": ["revenue churn"],
    "Cost of revenue (COGS)": ["cost of revenue", "COGS"],
    "TAM, SAM, SOM": ["TAM", "SAM", "SOM"],
    "Historical (actuals)": ["actuals"],
    "Gross margin": ["gross margin"],
    "Burn rate": ["burn rate", "monthly burn", "net burn"],
}
# Everyday words that would underline half the app ("Forecast" badges, the June logo, seat counts)
SKIP = {"Forecast", "Logo", "Seat"}

CSS = """
.gl{border-bottom:1px dotted currentColor;cursor:help;position:relative;outline:none}
.gl .gl-tip{visibility:hidden;opacity:0;position:absolute;left:0;top:calc(100% + 6px);z-index:9999;width:280px;
  max-width:80vw;background:#1c1c1c;color:#f5f5f5;padding:9px 11px;border-radius:8px;font-size:0.8rem;
  font-weight:400;font-style:normal;line-height:1.4;text-align:left;white-space:normal;text-transform:none;
  letter-spacing:normal;box-shadow:0 4px 14px rgba(0,0,0,.25);transition:opacity .12s;pointer-events:none}
.gl .gl-tip b{color:#fff}
.gl .gl-tip .gl-ex{display:block;margin-top:5px;color:#c9c9c9;font-style:normal}
.gl:hover .gl-tip,.gl:focus .gl-tip{visibility:visible;opacity:1}
"""

# Left alone: fenced and inline code, HTML tags, Markdown link targets, and tooltips already added
PROTECTED = re.compile(r"```.*?```|`[^`\n]*`|<span class=\"gl\".*?</span></span>|<[^>]+>|\]\([^)]*\)", re.S)


def _names(entry: str) -> list[str]:
    if entry in ALIASES:
        return ALIASES[entry]
    names = [entry.split(" (")[0]]
    acronym = re.search(r"\(([^)]+)\)", entry)
    if acronym:
        names.append(acronym.group(1))
    return names


def _is_acronym(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Z&]{2,}", name))


@lru_cache
def _index() -> tuple[re.Pattern, dict]:
    """One regex over every name (longest first, so 'CAC payback' wins over 'CAC') and name -> entry."""
    lookup, parts = {}, []
    for entry in data.glossary():
        if entry in SKIP:
            continue
        for name in _names(entry):
            lookup[name.lower()] = entry
            # acronyms are case-sensitive so "safe" the adjective isn't a SAFE; words allow a plural
            body = re.escape(name) if _is_acronym(name) else f"(?i:{re.escape(name)})"
            parts.append((len(name), rf"(?<![\w&]){body}(?:e?s)?(?![\w&])"))
    parts.sort(key=lambda p: -p[0])
    return re.compile("|".join(p for _, p in parts)), lookup


def _entry_for(match: str) -> str | None:
    _, lookup = _index()
    word = match.lower()
    for candidate in (word, re.sub(r"es$", "", word), re.sub(r"s$", "", word)):
        if candidate in lookup:
            return lookup[candidate]
    return None


def _escape(text: str) -> str:
    # &#36; keeps Streamlit from reading "$58K ... $3,200" as LaTeX
    return html.escape(text).replace("$", "&#36;")


def tooltip(match: str, entry: str) -> str:
    g = data.glossary()[entry]
    tip = f"<b>{_escape(entry)}</b><br>{_escape(g['means'])}"
    if g.get("example"):
        tip += f"<em class=\"gl-ex\">Tidewell: {_escape(str(g['example']))}</em>"
    return f'<span class="gl" tabindex="0">{match}<span class="gl-tip">{tip}</span></span>'


def glossify(text: str, seen: set | None = None) -> str:
    """Add hover definitions to the first mention of each glossary term.

    Pass the same `seen` set across several calls to treat them as one block (e.g. one claim card).
    """
    if not text:
        return text
    pattern, _ = _index()
    seen = set() if seen is None else seen

    def wrap(m: re.Match) -> str:
        entry = _entry_for(m.group(0))
        if not entry or entry in seen:
            return m.group(0)
        seen.add(entry)
        return tooltip(m.group(0), entry)

    out, pos = [], 0
    for p in PROTECTED.finditer(text):
        out.append(pattern.sub(wrap, text[pos:p.start()]))
        out.append(p.group(0))
        pos = p.end()
    out.append(pattern.sub(wrap, text[pos:]))
    return "".join(out)


def glossify_sections(markdown: str) -> str:
    """glossify per Markdown section, so each heading's section gets its own first mentions."""
    parts = re.split(r"(?m)^(?=#{1,6} )", markdown or "")
    return "".join(glossify(part) for part in parts)
