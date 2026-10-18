"""Characters.

Vicky, the coach, is a snowy owl: curious, sharp-eyed and Canadian. Her illustrated poses live in
assets/characters/vicky_<pose>.png (waving, magnifying glass, calculator, cheering, reading, presenting).
The investors are professional archetypes from Appendix E, drawn in SVG at the event, so practice
feels like a real meeting. Every avatar has moods
(happy, thinking, proud, concerned, stern) and an optional talking animation that respects
"reduce motion" (and the OS-level prefers-reduced-motion setting).

Avatars are returned as data-URI <img> tags so they render anywhere Streamlit accepts HTML.
"""
import base64
from functools import lru_cache
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "characters"
VICKY_POSES = {"happy": "happy", "proud": "proud", "thinking": "thinking", "concerned": "thinking",
               "stern": "thinking", "numbers": "numbers", "learning": "learning", "presenting": "presenting"}


@lru_cache
def _png(name: str) -> str | None:
    f = ASSETS / f"{name}.png"
    return "data:image/png;base64," + base64.b64encode(f.read_bytes()).decode("ascii") if f.exists() else None


def _pose_uri(key: str, mood: str) -> str | None:
    if key != "vicky":
        return _png(f"{key}_{mood}") or _png(key)
    return _png(f"vicky_{VICKY_POSES.get(mood, 'happy')}")

PURPLE = "#5B2EFF"

CHARACTERS = {
    "vicky": {"name": "Vicky the snowy owl", "skin": "#C68863", "hair": "#2B1B17", "style": "bob", "outfit": PURPLE,
              "bg": "#EEE8FF", "glasses": True, "slash": True},
    "lead_seed_fund": {"name": "Morgan", "skin": "#F1C9A5", "hair": "#9AA0A6", "style": "short", "outfit": "#1F2A44",
                       "bg": "#E6ECF7", "tie": "#5B2EFF"},
    "angel_operator": {"name": "Dana", "skin": "#8D5524", "hair": "#1B1B1B", "style": "curly", "outfit": "#E07A5F",
                       "bg": "#FCEDE7"},
    "skeptical_partner": {"name": "Sam", "skin": "#E0AC69", "hair": "#3B3B3B", "style": "buzz", "outfit": "#111111",
                          "bg": "#E9EEF0", "glasses": True, "turtleneck": True},
    "strategic_investor": {"name": "Alex", "skin": "#C68642", "hair": "#4A3222", "style": "short", "outfit": "#2E7D32",
                           "bg": "#E8F5E9", "hardhat": True},
    "government_fund": {"name": "Jordan", "skin": "#FFDBAC", "hair": "#B5651D", "style": "long", "outfit": "#7A1F1F",
                        "bg": "#FBEAEA", "pin": True},
}

MOODS = ["happy", "proud", "thinking", "concerned", "stern"]
MOUTHS = {
    "happy": '<path d="M52 63 Q60 70 68 63" stroke="#5A2A1A" stroke-width="2.4" fill="none" stroke-linecap="round"/>',
    "proud": '<path d="M50 61 Q60 73 70 61 Z" fill="#5A2A1A"/><path d="M53 62 Q60 66 67 62" fill="#fff"/>',
    "thinking": '<path d="M55 65 Q60 64 65 66" stroke="#5A2A1A" stroke-width="2.2" fill="none" stroke-linecap="round"/>',
    "concerned": '<path d="M53 67 Q60 62 67 67" stroke="#5A2A1A" stroke-width="2.2" fill="none" stroke-linecap="round"/>',
    "stern": '<path d="M53 65 L67 65" stroke="#5A2A1A" stroke-width="2.4" stroke-linecap="round"/>',
}
BROWS = {
    "happy": ('M45 44 Q50 41 55 44', 'M65 44 Q70 41 75 44'),
    "proud": ('M45 43 Q50 39 55 43', 'M65 43 Q70 39 75 43'),
    "thinking": ('M45 42 Q50 40 55 43', 'M65 45 Q70 44 75 45'),
    "concerned": ('M46 42 L55 45', 'M65 45 L74 42'),
    "stern": ('M45 43 L55 46', 'M65 46 L75 43'),
}


def _hair(c: dict, back: bool) -> str:
    h, s = c["hair"], c["style"]
    if back:
        if s == "bob":
            return f'<path d="M33 58 Q30 24 60 23 Q90 24 87 58 L88 74 Q80 76 76 70 L44 70 Q40 76 32 74 Z" fill="{h}"/>'
        if s == "long":
            return f'<path d="M34 56 Q32 24 60 24 Q88 24 86 56 L90 92 L30 92 Z" fill="{h}"/>'
        return ""
    if s == "bob":
        return (f'<path d="M36 52 Q38 28 60 28 Q82 28 84 52 Q78 40 66 37 Q60 44 46 42 Q40 46 36 52 Z" fill="{h}"/>'
                f'<path d="M70 30 Q78 33 82 42" stroke="{PURPLE}" stroke-width="2.5" fill="none" stroke-linecap="round"/>')
    if s == "short":
        return f'<path d="M36 48 Q36 27 60 27 Q84 27 84 48 Q78 36 60 35 Q42 36 36 48 Z" fill="{h}"/>'
    if s == "buzz":
        return f'<path d="M37 46 Q38 29 60 29 Q82 29 83 46 Q76 37 60 37 Q44 37 37 46 Z" fill="{h}" opacity="0.85"/>'
    if s == "curly":
        dots = "".join(f'<circle cx="{x}" cy="{y}" r="7.5" fill="{h}"/>' for x, y in
                       [(40, 40), (47, 31), (57, 27), (67, 28), (76, 33), (81, 42), (37, 50), (84, 52)])
        return dots
    if s == "long":
        return f'<path d="M36 50 Q38 27 60 27 Q82 27 84 50 Q74 38 58 38 Q46 40 36 50 Z" fill="{h}"/>'
    return ""


def svg(key: str = "vicky", mood: str = "happy", talking: bool = False, still: bool = False) -> str:
    c = CHARACTERS.get(key, CHARACTERS["vicky"])
    mood = mood if mood in MOUTHS else "happy"
    b1, b2 = BROWS[mood]
    anim = "" if still else f"""
      @keyframes blink {{0%,92%,100%{{transform:scaleY(1)}} 95%{{transform:scaleY(0.1)}}}}
      @keyframes talk {{0%,100%{{transform:scaleY(0.25)}} 50%{{transform:scaleY(1)}}}}
      @keyframes bob {{0%,100%{{transform:translateY(0)}} 50%{{transform:translateY(-1.5px)}}}}
      .eye{{transform-origin:center;transform-box:fill-box;animation:blink 4.5s infinite}}
      .talk{{transform-origin:center;transform-box:fill-box;animation:talk 0.28s ease-in-out 14}}
      .head{{animation:bob 3.2s ease-in-out infinite}}
      @media (prefers-reduced-motion: reduce){{.eye,.talk,.head{{animation:none}}}}"""
    mouth = ('<ellipse class="talk" cx="60" cy="65" rx="5.5" ry="4" fill="#5A2A1A"/>' if talking and not still
             else MOUTHS[mood])
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" role="img" aria-label="{c["name"]}">',
             f"<style>{anim}</style>",
             f'<circle cx="60" cy="60" r="60" fill="{c["bg"]}"/>',
             '<g class="head">',
             _hair(c, back=True),
             f'<path d="M18 122 Q18 90 60 87 Q102 90 102 122 Z" fill="{c["outfit"]}"/>']
    if c.get("turtleneck"):
        parts.append(f'<rect x="49" y="76" width="22" height="14" rx="5" fill="{c["outfit"]}"/>')
    else:
        parts.append(f'<rect x="53" y="74" width="14" height="14" rx="4" fill="{c["skin"]}"/>')
        parts.append('<path d="M47 89 L60 102 L73 89 L66 88 L60 95 L54 88 Z" fill="#ffffff"/>')
    if c.get("tie"):
        parts.append(f'<path d="M57 95 L63 95 L65 112 L60 117 L55 112 Z" fill="{c["tie"]}"/>')
    if c.get("slash"):
        parts.append('<line x1="80" y1="112" x2="88" y2="98" stroke="#ffffff" stroke-width="3.2" stroke-linecap="round"/>')
    if c.get("pin"):
        parts.append('<path d="M82 100 l2 -4 l2 4 l3 -1 l-2 4 l2 1 l-5 2 l-5 -2 l2 -1 l-2 -4 Z" fill="#D52B1E"/>')
    parts += [f'<ellipse cx="60" cy="56" rx="22" ry="24" fill="{c["skin"]}"/>',
              f'<ellipse cx="38" cy="58" rx="3.5" ry="5" fill="{c["skin"]}"/>',
              f'<ellipse cx="82" cy="58" rx="3.5" ry="5" fill="{c["skin"]}"/>',
              _hair(c, back=False),
              f'<path d="{b1}" stroke="#2B1B17" stroke-width="2" fill="none" stroke-linecap="round"/>',
              f'<path d="{b2}" stroke="#2B1B17" stroke-width="2" fill="none" stroke-linecap="round"/>',
              '<ellipse class="eye" cx="50" cy="52" rx="2.6" ry="3" fill="#1d1d1d"/>',
              '<ellipse class="eye" cx="70" cy="52" rx="2.6" ry="3" fill="#1d1d1d"/>',
              '<circle cx="45" cy="60" r="3.2" fill="#ff8a80" opacity="0.35"/>',
              '<circle cx="75" cy="60" r="3.2" fill="#ff8a80" opacity="0.35"/>']
    if c.get("glasses"):
        parts.append('<g stroke="#222" stroke-width="1.8" fill="none"><circle cx="50" cy="52" r="7"/>'
                     '<circle cx="70" cy="52" r="7"/><line x1="57" y1="52" x2="63" y2="52"/></g>')
    if c.get("hardhat"):
        parts.append('<path d="M34 42 Q36 20 60 20 Q84 20 86 42 Z" fill="#F9C80E"/><rect x="31" y="40" width="58" height="5" rx="2" fill="#E0B000"/>')
    parts += [mouth, "</g></svg>"]
    return "".join(parts)


def img(key: str = "vicky", mood: str = "happy", talking: bool = False, still: bool = False, size: int = 72,
        alt: str | None = None) -> str:
    """An <img> tag: Vicky's illustrated pose (PNG) if available, otherwise the SVG drawing."""
    label = alt or CHARACTERS.get(key, CHARACTERS["vicky"])["name"]
    uri = _pose_uri(key, mood)
    cls = "char" + (" talking" if talking and not still else "")
    if uri:
        return (f'<img class="{cls}" src="{uri}" width="{size}" height="{size}" alt="{label}" '
                f'style="flex:0 0 auto;object-fit:contain">')
    data = base64.b64encode(svg(key, mood, talking, still).encode("utf-8")).decode("ascii")
    return (f'<img class="char" src="data:image/svg+xml;base64,{data}" width="{size}" height="{size}" alt="{label}" '
            f'style="border-radius:50%;flex:0 0 auto">')


def data_uri(key: str = "vicky", mood: str = "happy") -> str:
    uri = _pose_uri(key, mood)
    if uri:
        return uri
    return "data:image/svg+xml;base64," + base64.b64encode(svg(key, mood, still=True).encode("utf-8")).decode("ascii")
