# Vicky: AI venture capitalist (June Analytics challenge)

Vicky prepares the founders of Tidewell Systems for their $4M seed round. She **analyzes the numbers**,
**prepares the founder** and **simulates the pitch**.

## Why this isn't a one-shot chatbot
| Principle (Appendix G) | How Vicky does it |
|---|---|
| Numbers come from data, not the model | `vicky/metrics.py` computes every figure with its formula, inputs and provenance. 33 tests reproduce Appendix H. |
| Say where every figure came from | Badges: Historical / Forecast / Founder claim / Reported in pack |
| A separate check | `vicky/audit.py` pulls every $, %, x and months figure out of the LLM's text and ties it to the data. It also flags founder claims stated as fact, valuation advice and unsourced benchmarks. A failed audit sends the draft back for revision, and the audit notes are shown. |
| Missing is a valid answer | NRR, GRR and cohort churn can't be recomputed from the files provided. They are labelled "reported in pack". Missing data (CRM, win/loss, TAM) is listed. |
| Realistic investors | Five Appendix E personas, each with its own questions, follow-up depth and scoring weights. Founder answers are fact-checked in code before the LLM scores them. |
| Stress-test the forecast | `vicky/forecast.py` rebuilds the founders' plan from drivers (to within about 1% of MRR each quarter). It reruns the plan with historical drivers, giving 22 → 17 months of runway, and with a round slipping to April, which runs out of cash in March 2027. |

## Architecture
```
data/ (CSV 01 + PDF tables encoded in data/pack/)
  └─ metrics.py ─ claims.py ─ forecast.py      deterministic engine (no LLM)
        └─ tools.py (LangChain tools)
              ├─ graphs/coach.py      agent ⇄ tools → audit → revise      (Ask Vicky)
              ├─ graphs/prep_pack.py  compute → draft → audit → revise ×2   (Prep pack)
              └─ graphs/pitch.py      persona → [founder answer ⏸ interrupt → fact-check → score → follow-up]* → debrief
app.py (Streamlit)
```
LangGraph is the orchestrator. The LLM is any OpenAI-compatible endpoint (OpenRouter free models by
default) and costs $0. Responses are cached in SQLite.

## Run
```bash
cp .env.example .env          # add a free OPENROUTER_API_KEY from https://openrouter.ai/keys
uv sync
uv run pytest -q              # engine reproduces the data pack's figures
uv run streamlit run app.py
```
The Numbers, Deck claim check and Scenario lab tabs, plus the deterministic prep pack, work with no key.

OpenRouter free tier: about 20 requests/min and 50/day without credits. Each coach answer is 1–3 calls; each
pitch turn is 1 call. Keep `LLM_CACHE=1` and rehearse the demo path once to warm the cache. A Groq free key
works as a drop-in backup (see `.env.example`).

## 3-minute demo script
1. **Numbers**: ARR $1.29M (not $1.37M), with the calculation popover. Chart: plan vs historical drivers.
2. **Deck claim check**: 9 claims, 7 need fixing. Every figure has evidence.
3. **Pitch simulator → Skeptical partner**: answer "churn is around 1%". The fact check catches it, accuracy is
   capped, and the investor pushes back. Then answer with real numbers and the score improves.
4. **Ask Vicky**: "What valuation should we raise at?" She declines and explains how the SAFE caps work.
   "Why will we beat Jobber?" She says there's no win/loss data and how to get it.
5. **Scenario lab**: slip the round to April. Cash runs out in March 2027. Toggle "hold spending" to fix it.
6. **Prep pack**: show the audit notes. The audit caught and fixed problems before the founder saw the pack.
