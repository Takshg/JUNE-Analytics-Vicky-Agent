# Vicky: AI venture capitalist (June Analytics challenge, Catalyst 2026)

Vicky gets the founders of Tidewell Systems ready for their $4M seed round. She shows them **where they
stand**, **what's in the way** and **how to get where they want to be**, then has them **practise until
they're confident**.

> June told us: founders are stressed, information overload is the failure mode, and the coach should
> build confidence without being a yes-man. So Vicky is a guided journey, one step at a time.

## The journey

The look follows June's own platform (designed as a Lovable mock, rebuilt in Streamlit): black and white with June purple `#502EF6` as an accent, the logo's "/" as a motif, Outfit / Source Serif 4 / Public Sans, and Vicky shown in the sidebar alongside June's other agents, Franco (CFO) and Rocco (CRO), as part of "Your AI finance team".

| Step | What the founder sees |
|---|---|
| **Start here** | June's snapshot format: a **Readiness score /100** (with breakdown), Vicky's one-line verdict, a Path Map (where you are → top 3 roadblocks → $5M ARR), then cards for Top 3 questions, Strengths, Weaknesses, Next actions and the Deck check. Every card opens a Finding / Figure / Source table. |
| **Practise** | One roadblock at a time: understand it in plain language → answer the investor's question → get scored → retry → watch the score go up. Readiness rises as answers improve. |
| **Investor Q&A** | One investor (5 personas from Appendix E) with follow-up questions and a debrief. Founders can **upload their pitch deck (PDF)** and point at a slide while answering: code checks the slide and flags where the slide and the spoken answer disagree, and the debrief lists the slides to fix (`vicky/deck.py`; sample decks in `assets/sample_deck/`). |
| **Partner meeting** (Vicky's Partner Meeting) | Three investors, six questions, a 45-second clock. Each investor walks out when an answer trips their deal-breaker. The scorecard says why, and links to practise the weakest answer. (In a real raise, the partner meeting is the final step.) |
| **Ask Vicky** | Founder asks finance questions. A hierarchical decision model (`vicky/decision.py`): a code-only policy gate → the AI picks the question type → code validates and runs the tool plan. The answer shows its decision trace, numbered reasoning and evidence, and is audited before display. |
| **Financials** | Every number with its calculation, the deck claim check, the scenario lab and the investor prep pack. |

### Vicky, the avatar, and a friendlier experience

- **Vicky is a snowy owl:** curious, sharp-eyed and Canadian. Our illustrated poses (`assets/characters/`) match each moment: waving hello, a magnifying glass while she checks your numbers, a calculator in the Deep dive, a book for jargon checks, a growth chart on Start here, and cheering when you nail an answer. She hops when she speaks.
- **The investors are professional archetypes** (Appendix E), drawn at the event: the lead seed fund, the angel operator, the skeptical partner, the strategic investor and the government-backed fund. Each is named by role so practice feels like a real meeting. In the Partner Meeting the speaker lights up, and anyone who walks out greys out.
- **Jargon pop-ups that grow with you** (`vicky/lingo.py`). Hover, tap or Tab to any dotted-underlined word to see its plain meaning, Tidewell's number, and an analogy for engineers ("churn is a memory leak"). Vicky starts in **Plain English**, moves to **Mixed** after 3 terms, and to **Investor-speak** after 8. Founders learn terms through quick checks in Practise and the sidebar. They can also pick the level by hand.
- **Accessibility:** a 🔊 Read aloud button on every Vicky message and investor question (browser speech, no API), plus Larger text, High contrast and Reduce motion toggles. Keyboard focus outlines everywhere, and it works on mobile.
- **Voice in and out:** 🎤 *Answer out loud* in Practise and the Partner Meeting records the founder's spoken answer and transcribes it into the answer box (English or French) with Google's free speech recognition, so it's checked and scored like a typed answer. Audio goes to Google for transcription; founders can always type instead. 🔊 Read aloud uses the browser's own speech.
- **Français:** a 🇨🇦 toggle in the sidebar switches the interface, Vicky's messages, investor questions, AI feedback and read-aloud to Canadian French (`vicky/i18n.py`). Numbers stay exactly as the engine computes them, so the audit still checks them.
- **Glossary pop-ups in AI text** (`vicky/glossary.py`): every glossary term in Ask Vicky answers, the prep pack, feedback and claim cards gets a hover/tap/focus definition with Tidewell's number.
- **SEO link:** set `SEO_URL` and the app links to the public "10-Minute Test" guide built in Lovable (prompt in `docs/lovable_prompt.md`). The guide links back to the app.

### Blind spots: problems the founders don't know about

The deck and the founders' plan don't mention these. Vicky finds them in the data:

- **Cash could run out before the round closes.** The plan raises monthly spend from $154K to $178K in October, before the money lands. If the round slips to April 2027, cash runs out in March 2027.
- **The forecast counts revenue as cash.** $181K of deferred revenue (prepaid annual plans) will be recognised without new cash.
- **A $240K SR&ED refund that isn't filed.** Without it, runway after a January close is about 21 months instead of 22.
- **The 20% price rise hits customers who can't be repriced yet** (45 annual-prepay customers, 59 on the legacy price).

Plus the slowdown the founders will be asked about first: growth fell from 9.0% a month (12 months) to 4.9% (last 3). At the growth they've actually had, cash runs out in June 2028, before they reach $5M ARR.

## Why this isn't a one-shot chatbot

| Principle (Appendix G) | How Vicky does it |
|---|---|
| Numbers come from data, not the model | `vicky/metrics.py` computes every figure with its formula, inputs and provenance. Tests reproduce Appendix H. |
| Say where every figure came from | Every number carries a label: Historical / Forecast / Founder claim / Reported in pack |
| A separate check | `vicky/audit.py` is rule-based. Each issue comes with the exact fix the reviser must apply, and the loop stops if a revision makes no progress. It ties every $, %, x and months figure the AI writes to the data, and flags founder claims stated as fact, valuation advice and unsourced benchmarks. A failed audit sends the draft back. |
| Missing is a valid answer | NRR, GRR and cohort churn can't be recomputed from the files provided, so they're labelled "reported in pack". Missing data (CRM, win/loss, TAM) is listed. |
| Realistic investors | Five Appendix E personas, each with its own questions, follow-up depth, scoring weights and deal-breakers. Includes second-raise questions (SAFE conversion, whether existing angels are investing again). |
| Founder answers are fact-checked in code | A wrong number caps the accuracy score, whatever the AI thinks. |
| Plain language | Plain labels on screen. The jargon is underlined with a hover definition from the glossary, so founders learn the terms over time. |
| Human in the loop | `vicky/handoff.py` routes valuation, term-sheet, legal and tax questions to a June CPA and a startup lawyer. Stages 6 and 7 of the journey are marked 👤. |
| Never stalls | Practise and Vicky's Partner Meeting score with the AI when it's available and fall back to a transparent rule-based scorer when it isn't (no key, rate limit, timeout). |

## Architecture

```
data/ (CSV 01 + PDF tables encoded in data/pack/)
  └─ metrics.py ─ claims.py ─ forecast.py ─ journey.py     deterministic engine (no LLM)
        ├─ practice.py   score an answer: fact check → AI evaluator, or the rule-based fallback
        ├─ hotseat.py    Vicky's Partner Meeting: 3-investor panel, clock, deal-breakers, scorecard
        ├─ avatar.py     original SVG avatars with moods and talking animation
        ├─ lingo.py      progressive jargon levels, pop-up text, term quizzes
        ├─ handoff.py    when to bring in a human (backed by decision.gate)
        ├─ decision.py   Ask Vicky's policy gate → intent → validated tool plan
        ├─ glossary.py   pop-up definitions inside AI-written text
        ├─ i18n.py       Français: on-screen text, AI language, fr-CA speech
        └─ tools.py (LangChain tools)
              ├─ graphs/coach.py      agent ⇄ tools → audit → revise      (Ask Vicky)
              ├─ graphs/prep_pack.py  compute → draft → audit → revise ×2   (Prep pack)
              └─ graphs/pitch.py      persona → [answer ⏸ → fact-check → score → follow-up]* → debrief
app.py (Streamlit)
```

## Run it locally

```bash
cp .env.example .env          # add your OpenRouter key (free at https://openrouter.ai/keys)
uv sync
uv run pytest -q              # 181 tests: engine, decision model, deck checks, glossary, journey, scoring, hand-off, partner meeting, French, avatars
uv run streamlit run app.py
```

**Windows:** if you see `UnicodeDecodeError`, pull the latest code (all file reads are now UTF-8), or run
`$env:PYTHONUTF8=1` first.

Start here, Practise, Vicky's Partner Meeting and the Financials work with **no API key**, using the rule-based scorer. Investor Q&A
and Ask Vicky need the AI.

**OpenRouter free tier:** 50 requests/day until you've bought $10 of credits, then 1,000/day. Each coach
answer is 1–3 calls; each pitch turn or AI-scored practice answer is 1. Keep `LLM_CACHE=1`, and use the
sidebar "AI feedback" toggle to switch to instant rule-based scoring if you're near the limit.

## Deploy (Streamlit Community Cloud, free)

1. Push this repo to GitHub.
2. Go to share.streamlit.io → **Create app** → choose the repo, branch `main`, main file `app.py`.
3. **Advanced settings:** Python **3.12**. Under **Secrets**, paste:
   ```toml
   OPENROUTER_API_KEY = "sk-or-..."
   # Or Google Gemini instead of OpenRouter (free tier, faster):
   # LLM_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
   # LLM_API_KEY = "your-gemini-key"
   # LLM_MODEL = "gemini-3.5-flash-lite"
   SEO_URL = "https://your-guide.lovable.app"   # optional: the public 10-Minute Test page
   ```
4. Deploy. Dependencies install from `requirements.txt` (regenerate it with
   `uv export --no-hashes --no-dev --format requirements-txt -o requirements.txt` after changing dependencies).

Never commit `.env`. Only `.env.example`, with a placeholder, belongs in the repo.

## 2-minute table demo

1. **Start here:** "June told us founders don't need more numbers. They need to know where they stand, what's in the way, and how to get there." Point to the Path Map, the blind spot, and the cash-runs-out-before-$5M line.
2. **Practise this** on roadblock 1. Type a weak answer ("It won't. We have strong interest."): about 1.6/5, with specific coaching.
3. **Try again** with real numbers: about 4.3/5, the fact check passes, and readiness goes up.
4. **Vicky's Partner Meeting:** let a judge answer. Bluff once and watch the lead seed fund walk out, with the reason.
5. **Ask Vicky:** "What valuation should we raise at?" She explains SAFE conversion, declines to name a number, and hands off to a CPA and lawyer.

## Team

**Taksh Girdhar** (engine, data, decision model, glossary and deck upload), **Ronald** (AI agents), **Areej Tariq** (UI/UX design and June branding, Vicky avatar, accessibility, French mode and voice, investor personas, SEO site, pitch).
Tidewell Systems is fictional and every figure is synthetic (CAD). Vicky gives no investment or valuation advice.
