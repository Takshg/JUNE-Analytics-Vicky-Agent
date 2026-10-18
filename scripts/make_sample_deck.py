"""Build the sample Tidewell pitch decks used to test and demo the pitch simulator.

    uv run python scripts/make_sample_deck.py

Writes two 12-slide PDFs to assets/sample_deck/:
- tidewell_deck_draft.pdf      the founders' draft: the 9 Appendix A claims verbatim, flaws included
- tidewell_deck_corrected.pdf  the same deck with each claim replaced by the claim checker's suggested fix

Tidewell is fictional and all figures are synthetic (case pack). Slide text is kept one claim per line so
vicky.deck extracts it cleanly.
"""
from pathlib import Path

import pymupdf

OUT = Path(__file__).resolve().parent.parent / "assets" / "sample_deck"
W, H = 960, 540
INK = (0.07, 0.07, 0.07)
MUTED = (0.42, 0.42, 0.42)
ACCENT = (0.05, 0.47, 0.47)  # Tidewell teal
PANEL = (0.95, 0.96, 0.96)

# Each slide: title, optional kicker, and either bullets or stats [(big value, caption)].
# Where draft and corrected differ, the value is {"draft": ..., "corrected": ...}.
SLIDES = [
    {"title": "Tidewell Dispatch", "kicker": "Scheduling and dispatch for the trades",
     "bullets": ["Seed round, target close January 2027", "Jennifer (CEO) and Craig (CTO)", "Toronto, Canada"],
     "cover": True},
    {"title": "The problem", "kicker": "Trades businesses run their day from a whiteboard",
     "bullets": ["A 12-technician HVAC shop in Mississauga booked every job on a whiteboard and a group chat",
                 "Missed appointments, double-booked technicians, invoices sent days late",
                 "Teams with 3 to 30 technicians are underserved: tools are built for solo operators or "
                 "enterprise fleets"]},
    {"title": "The product", "kicker": "Tidewell Dispatch",
     "bullets": ["Job booking and technician routing", "Quotes and invoices from the field",
                 "Automatic customer texts: \"your technician is 20 minutes away\"",
                 "$45 per technician seat per month"]},
    {"title": "Traction",
     "stats": {"draft": [("$1.37M ARR", "Annual recurring revenue"),
                         ("Growing 10% month over month", "Revenue growth"),
                         ("211 customers", "2,493 seats, September 2026")],
               "corrected": [("$1.29M ARR", "September 2026 MRR x 12. Onboarding fees of $109K (last 12 "
                                            "months) shown separately"),
                             ("MRR grew ~9% a month", "Compounded over the last 12 months; 4.9% over the "
                                                      "last 3 months"),
                             ("211 customers", "2,493 seats, September 2026")]}},
    {"title": "Unit economics",
     "bullets": {"draft": ["92% gross margin",
                           "$970 customer acquisition cost, paid back in under 3 months"],
                 "corrected": ["74% gross margin with customer success in cost of revenue (92% as booked)",
                               "Fully loaded customer acquisition cost about $3,200",
                               "Paid back in about 9 to 10 months"]}},
    {"title": "Retention",
     "bullets": {"draft": ["Monthly logo churn around 1%", "Net revenue retention above 110%",
                           "Customers love the product"],
                 "corrected": ["Monthly logo churn 2.0% over the last 12 months, 1.6% over the last 6",
                               "Net revenue retention about 88%, gross revenue retention about 81%",
                               "Churn is highest in a customer's first 6 months: new onboarding programme "
                               "targets that window"]}},
    {"title": "Market",
     "bullets": {"draft": ["$2B total addressable market in North America",
                           "HVAC, plumbing, electrical, landscaping, pest control, appliance repair"],
                 "corrected": ["Bottom-up market sizing in progress: trades businesses with 3 to 30 "
                               "technicians (Statistics Canada, US Census Bureau) x seats x price",
                               "HVAC, plumbing, electrical, landscaping, pest control, appliance repair"]}},
    {"title": "Our largest customer", "kicker": "Northern Comfort Group",
     "bullets": {"draft": ["31-location HVAC franchise network", "260 seats, signed March 2026",
                           "Northern Comfort Group is expanding to 600 seats next year"],
                 "corrected": ["31-location HVAC franchise network", "260 seats today, 9.7% of MRR",
                               "Renews March 2027",
                               "A 600-seat expansion has been discussed verbally: upside, not in our base plan"]}},
    {"title": "Competition",
     "bullets": ["Jobber and Housecall Pro: built for small crews",
                 "ServiceTitan: built for large enterprises",
                 "Spreadsheets, paper and group chats",
                 "Why we win: built for teams of 3 to 30 technicians, with partner referrals from a plumbing "
                 "and HVAC supply distributor"]},
    {"title": "Team", "kicker": "14 people",
     "bullets": ["Jennifer (CEO): sales and fundraising", "Craig (CTO): product and engineering",
                 "6 software engineers, 2 account executives, 1 marketing manager, 3 customer success",
                 "Both founders were software engineers at a large Canadian software company"]},
    {"title": "The ask", "kicker": "$4M seed round",
     "bullets": {"draft": ["$4M gives us 24 months of runway and gets us to $5M ARR",
                           "Product and engineering 45%, sales and marketing 40%, G&A 10%, reserve 5%",
                           "Looking for a Canadian seed fund to lead"],
                 "corrected": ["About 22 months of runway on our plan, about 17 if growth stays at historical "
                               "rates",
                               "Our plan reaches $5.11M ARR by March 2028 (forecast)",
                               "Product and engineering 45%, sales and marketing 40%, G&A 10%, reserve 5%",
                               "Looking for a Canadian seed fund to lead"]}},
    {"title": "Thank you", "kicker": "Tidewell Systems Inc.",
     "bullets": ["Jennifer, CEO", "Craig, CTO", "Toronto, Canada"], "cover": True},
]


def _pick(value, version: str):
    return value[version] if isinstance(value, dict) else value


def _footer(page, n: int, version: str):
    page.draw_line((48, H - 40), (W - 48, H - 40), color=(0.85, 0.85, 0.85), width=0.6)
    label = "Draft deck" if version == "draft" else "Corrected deck"
    page.insert_text((48, H - 22), f"Tidewell Systems (fictional company, synthetic data) | Sample deck for the "
                                   f"Vicky demo | {label}", fontsize=9, fontname="helv", color=MUTED)
    page.insert_text((W - 80, H - 22), f"{n} / {len(SLIDES)}", fontsize=9, fontname="helv", color=MUTED)


def _cover(page, slide: dict):
    page.draw_rect(pymupdf.Rect(0, 0, W, H), color=None, fill=INK)
    page.draw_rect(pymupdf.Rect(48, 150, 56, 300), color=None, fill=ACCENT)
    page.insert_text((76, 200), slide["title"], fontsize=44, fontname="hebo", color=(1, 1, 1))
    page.insert_text((76, 240), slide.get("kicker", ""), fontsize=20, fontname="helv", color=(0.8, 0.9, 0.9))
    y = 290
    for line in slide["bullets"]:
        page.insert_text((76, y), line, fontsize=15, fontname="helv", color=(0.85, 0.85, 0.85))
        y += 24


def _content(page, slide: dict, version: str):
    page.draw_rect(pymupdf.Rect(0, 0, W, 8), color=None, fill=ACCENT)
    page.insert_text((48, 78), slide["title"], fontsize=32, fontname="hebo", color=INK)
    top = 100
    if slide.get("kicker"):
        page.insert_text((48, 112), slide["kicker"], fontsize=16, fontname="helv", color=ACCENT)
        top = 130
    if "stats" in slide:
        stats = _pick(slide["stats"], version)
        gap, width = 20, (W - 96 - 2 * 20) / 3
        for i, (value, caption) in enumerate(stats):
            x = 48 + i * (width + gap)
            box = pymupdf.Rect(x, top + 20, x + width, top + 300)
            page.draw_rect(box, color=None, fill=PANEL)
            page.draw_rect(pymupdf.Rect(x, top + 20, x + 5, top + 300), color=None, fill=ACCENT)
            page.insert_textbox(pymupdf.Rect(x + 20, top + 45, x + width - 14, top + 170), value, fontsize=24,
                                fontname="hebo", color=INK)
            page.insert_textbox(pymupdf.Rect(x + 20, top + 175, x + width - 14, top + 290), caption, fontsize=13,
                                fontname="helv", color=MUTED)
        return
    y = top + 20
    for line in _pick(slide["bullets"], version):
        page.draw_rect(pymupdf.Rect(48, y + 6, 56, y + 14), color=None, fill=ACCENT)
        rect = pymupdf.Rect(72, y, W - 60, y + 80)
        spare = page.insert_textbox(rect, line, fontsize=19, fontname="helv", color=INK)
        y += 80 - spare + 16  # spare = unused height in the box


def build(version: str) -> bytes:
    doc = pymupdf.open()
    doc.set_metadata({"title": f"Tidewell Dispatch seed deck ({version}, sample)", "author": "Vicky demo (fictional)"})
    for n, slide in enumerate(SLIDES, 1):
        page = doc.new_page(width=W, height=H)
        if slide.get("cover"):
            _cover(page, slide)
        else:
            _content(page, slide, version)
        _footer(page, n, version)
    return doc.tobytes(garbage=3, deflate=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for version in ("draft", "corrected"):
        path = OUT / f"tidewell_deck_{version}.pdf"
        path.write_bytes(build(version))
        print(f"wrote {path.relative_to(OUT.parent.parent)}")


if __name__ == "__main__":
    main()
