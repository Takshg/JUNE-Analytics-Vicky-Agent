# Vicky: AI venture capitalist (June Analytics challenge, Catalyst 2026)

Vicky gets the founders ready for their $4M seed round. She shows them **where they
stand**, **what's in the way** and **how to get where they want to be**, then has them **practise until
they're confident**.

> June told us: founders are stressed, information overload is the failure mode, and the coach should
> build confidence without being a yes-man. So Vicky is a guided journey, one step at a time.

## What we're doing

June Analytics gives startups an AI finance team (Franco the CFO, Rocco the CRO). Our challenge was to add
**Vicky, an AI venture capitalist**: an agent that thinks like the investors a founder is about to pitch,
and gets the founders ready before they walk into the room.

Our test case is **Tidewell Systems**, a fictional Canadian SaaS company raising a $4M seed round. Its
founders are engineers, not finance people. Their deck has numbers that won't survive a first meeting, and
their plan has problems they haven't spotted. Vicky reads the company's data pack, finds what an investor
would find, and walks the founders from "where do we stand?" to answering a partner panel with confidence.

Three rules shape everything:

1. **Every number is computed in code, never by the AI.** The AI explains and coaches. A separate
   rule-based audit checks every figure it writes against the data before the founder sees it.
2. **Vicky coaches, she doesn't decide.** She never suggests a valuation or which offer to take.
   Valuation, legal and tax questions go to a June CPA or a startup lawyer.
3. **It always works.** Every step that scores or reacts has a rule-based fallback, so the app keeps
   working with no API key, a rate limit or a timeout.

## Features at a glance

| Feature                                 | What it does                                                                                                                                                                                                                        |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Readiness in plain words**      | Instead of a score out of 100, the founder sees *Getting ready → Almost there → Ready for the partner meeting*, with a breakdown: strengths, claims to fix, and how many of their top 3 answers they've practised.              |
| **Your fix path**                 | A five-step domino chain (survive the raise → fix the deck numbers → explain the growth slowdown → fix the forecast → partner meeting). Each tile shows one figure and its source. Steps turn "Fixed" as the founder practises. |
| **Practise**                      | One investor question at a time, scored out of 5 with coaching, then retried until it's strong. Founder answers are fact-checked in code.                                                                                           |
| **Investor Q&A with deck upload** | A one-on-one with one of five investor personas. Upload a PDF deck, point at a slide while answering, and Vicky flags where the slide and the answer disagree.                                                                      |
| **Partner meeting**               | Three investors, a clock, and walk-outs when an answer hits a deal-breaker.                                                                                                                                                         |
| **Offer round**                   | Investors make bounded offers. The founder has 90 seconds to accept, counter or walk away, then sees how the investors respond and an audited debrief.                                                                              |
| **Ask Vicky**                     | Finance Q&A through a hierarchical decision model (policy gate → question type → validated tool plan), with a visible decision trace, reasoning, evidence and a timer.                                                            |
| **Financials and Scenario lab**   | Every number with its formula and source, the deck claim check, what-if scenarios (e.g. the round slips to April) and an audited investor prep pack.                                                                                |
| **Blind spots**                   | Problems the founders don't know about, found in the data (see below).                                                                                                                                                              |
| **Learning and access**           | Glossary pop-ups that grow with the founder, read-aloud and voice answers, Canadian French, larger text, high contrast and reduced motion.                                                                                          |

## The journey

The look follows June's own platform (designed as a Lovable mock, rebuilt in Streamlit): black and white with June purple `#502EF6` as an accent, the logo's "/" as a motif, Outfit / Source Serif 4 / Public Sans, and Vicky shown in the sidebar alongside June's other agents, Franco (CFO) and Rocco (CRO), as part of "Your AI finance team".

| Step                                                | What the founder sees                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| --------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Start here**                                | June's snapshot format: **readiness in plain words** (*Getting ready*, *Almost there*, *Ready for the partner meeting*) with three rows (strengths, claims to fix, top 3 answers practised) and a "View breakdown" dialog, Vicky's one-line verdict, and **Your fix path**: five domino steps, each with one figure and its source and a "Practise this →" button for the next step (`vicky/journey.py`). Then a Path Map (where you are → top 3 roadblocks → $5M ARR) and cards for Top 3 questions, Strengths, Weaknesses, Next actions and the Deck check. Every card opens a Finding / Figure / Source table.                                                                                                                                                                                                           |
| **Practise**                                  | One roadblock at a time: understand it in plain language → answer the investor's question → get scored → retry → watch the score go up. An answer scoring 4 or more marks that step of the fix path "Fixed" and moves the readiness level.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| **Investor Q&A**                              | One investor (5 personas from Appendix E) with follow-up questions and a debrief. Founders can **upload their pitch deck (PDF)** and point at a slide while answering: code checks the slide and flags where the slide and the spoken answer disagree, and the debrief lists the slides to fix (`vicky/deck.py`; sample decks in `assets/sample_deck/`).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| **Partner meeting** (Vicky's Partner Meeting) | Three investors, six questions, a 45-second clock. Each investor walks out when an answer trips their deal-breaker. The scorecard says why, and links to practise the weakest answer. (In a real raise, the partner meeting is the final step.)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| **Offer round**                               | The founder sets their own ask (Vicky never suggests a valuation), then up to four investors each make an offer: less money, more equity, or a condition like a board seat. Code keeps every offer inside the investor's cheque size (Appendix E) and a range anchored on Tidewell's SAFE caps, and computes what each one means (pre- and post-money valuation, vs the ask, share of the $4M). The founder has 90 seconds to accept, counter or walk away. The investors' responses are decided in code from each archetype's flexibility (accept, meet halfway, hold firm or withdraw; the government fund co-invests beside a signed lead); the AI only writes their words. Vicky's audited debrief separates money agreed from offers still on the table and explains the trade-offs without saying which offer to take (`vicky/offers.py`). |
| **Ask Vicky**                                 | Founder asks finance questions. A hierarchical decision model (`vicky/decision.py`): a code-only policy gate → the AI picks the question type → code validates and runs the tool plan. The answer shows its decision trace, numbered reasoning and evidence, and is audited before display.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| **Financials**                                | Every number with its calculation, the deck claim check, the scenario lab and the investor prep pack.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |

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

| Principle (Appendix G)                   | How Vicky does it                                                                                                                                                                                                                                                                                                                             |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Numbers come from data, not the model    | `vicky/metrics.py` computes every figure with its formula, inputs and provenance. Tests reproduce Appendix H.                                                                                                                                                                                                                               |
| Say where every figure came from         | Every number carries a label: Historical / Forecast / Founder claim / Reported in pack                                                                                                                                                                                                                                                        |
| A separate check                         | `vicky/audit.py` is rule-based. Each issue comes with the exact fix the reviser must apply, and the loop stops if a revision makes no progress. It ties every $, %, x and months figure the AI writes to the data, and flags founder claims stated as fact, valuation advice and unsourced benchmarks. A failed audit sends the draft back. |
| Missing is a valid answer                | NRR, GRR and cohort churn can't be recomputed from the files provided, so they're labelled "reported in pack". Missing data (CRM, win/loss, TAM) is listed.                                                                                                                                                                                   |
| Realistic investors                      | Five Appendix E personas, each with its own questions, follow-up depth, scoring weights and deal-breakers. Includes second-raise questions (SAFE conversion, whether existing angels are investing again).                                                                                                                                    |
| Founder answers are fact-checked in code | A wrong number caps the accuracy score, whatever the AI thinks.                                                                                                                                                                                                                                                                               |
| Plain language                           | Plain labels on screen. The jargon is underlined with a hover definition from the glossary, so founders learn the terms over time.                                                                                                                                                                                                            |
| Human in the loop                        | `vicky/handoff.py` routes valuation, term-sheet, legal and tax questions to a June CPA and a startup lawyer. Stages 6 and 7 of the journey are marked 👤.                                                                                                                                                                                   |
| Never stalls                             | Practise and Vicky's Partner Meeting score with the AI when it's available and fall back to a transparent rule-based scorer when it isn't (no key, rate limit, timeout).                                                                                                                                                                      |

## Architecture

```
data/ (CSV 01 + PDF tables encoded in data/pack/)
  └─ metrics.py ─ claims.py ─ forecast.py ─ journey.py     deterministic engine (no LLM)
        ├─ practice.py   score an answer: fact check → AI evaluator, or the rule-based fallback
        ├─ hotseat.py    Vicky's Partner Meeting: 3-investor panel, clock, deal-breakers, scorecard
        ├─ offers.py     Offer round: bounded offers, terms and investor responses in code, audited debrief
        ├─ deck.py       pitch deck PDF: slide text, claim check, slide vs answer contradictions
        ├─ audit.py      rule-based check of every figure and claim the AI writes
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
cp .env.example .env          # add a free Google AI Studio (Gemini) or OpenRouter key, see below
uv sync
uv run pytest -q              # 198 tests: engine, decision model, deck checks, glossary, readiness and fix path, offers, scoring, hand-off, partner meeting, French, avatars
uv run streamlit run app.py
```

**Windows:** if you see `UnicodeDecodeError`, pull the latest code (all file reads are now UTF-8), or run
`$env:PYTHONUTF8=1` first.

Start here, Practise, Vicky's Partner Meeting, the Offer round and the Financials work with **no API key**, using the rule-based scorer (the Offer round falls back to rule-based offers, replies and debrief). Investor Q&A
and Ask Vicky need the AI.

**Which AI:** any OpenAI-compatible endpoint works. We use **Google AI Studio's free tier** (default model
`gemini-3.5-flash-lite`, about 500 requests/day, replies in about 3s; falls back to `gemini-3.1-flash-lite`,
then `gemma-4-26b-a4b-it`). In `.env`:

```bash
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_API_KEY=your-gemini-key
```

Without `LLM_BASE_URL` the app uses OpenRouter (free tier: 50 requests/day until you've bought $10 of
credits). Each coach answer is 1–3 calls; each pitch turn or AI-scored practice answer is 1. Keep
`LLM_CACHE=1`, and use the sidebar "AI feedback" toggle to switch to instant rule-based scoring if you're
near the limit. The sidebar **Test AI connection** button checks the key and model.

## Deploy (Streamlit Community Cloud, free)

1. Push this repo to GitHub.
2. Go to share.streamlit.io → **Create app** → choose the repo, branch `main`, main file `app.py`.
3. **Advanced settings:** Python **3.12**. Under **Secrets**, paste:
   ```toml
   LLM_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
   LLM_API_KEY = "your-gemini-key"
   # Or OpenRouter instead: leave out LLM_BASE_URL and set OPENROUTER_API_KEY = "sk-or-..."
   SEO_URL = "https://your-guide.lovable.app"   # optional: the public 10-Minute Test page
   ```

   `vicky/llm.py` copies these secrets into the environment at start-up (there's no `.env` on the server).
   Set `LLM_BASE_URL` along with a Gemini key, otherwise the key goes to OpenRouter and fails with a 401.
   The deployed app starts with an empty response cache and shares one free quota across every visitor.
4. Deploy. Dependencies install from `requirements.txt` (regenerate it with
   `uv export --no-hashes --no-dev --format requirements-txt -o requirements.txt` after changing dependencies).

Never commit `.env`. Only `.env.example`, with a placeholder, belongs in the repo.

## 2-minute table demo

1. **Start here:** "June told us founders don't need more numbers. They need to know where they stand, what's in the way, and how to get there." Point to the readiness level, the fix path, and the cash-runs-out-before-$5M line.
2. **Practise this** on step 1 of the fix path. Type a weak answer ("It won't. We have strong interest."): about 1.6/5, with specific coaching.
3. **Try again** with real numbers: about 5/5 with AI feedback (4.3 rule-based), the fact check passes, and back on Start here step 1 is "Fixed". Copy-paste answers are in `assets/sample_deck/DEMO_SCRIPT.md`.
4. **Vicky's Partner Meeting:** let a judge answer. Bluff once and watch the lead seed fund walk out, with the reason.
5. **Ask Vicky:** "What valuation should we raise at?" She explains SAFE conversion, declines to name a number, and hands off to a CPA and lawyer.

## Team

**Taksh Girdhar** (engine, data, decision model, glossary and deck upload), **Ronald** (AI agents), **Areej Tariq** (UI/UX design and June branding, Vicky avatar, accessibility, French mode and voice, investor personas, SEO site, pitch).
Tidewell Systems is fictional and every figure is synthetic (CAD). Vicky gives no investment or valuation advice.
