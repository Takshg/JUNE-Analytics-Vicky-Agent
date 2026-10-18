# Pitch simulator demo: copy-paste answers

**Setup:** Pitch simulator tab → upload `assets/sample_deck/tidewell_deck_draft.pdf` → keep **The lead seed fund** → Questions **2** → **Start meeting**.

For each question: pick the slide in **Slide you're referencing**, paste the answer, press Enter.

> Live AI runs on Google's free tier (gemini-3.5-flash-lite, about 500 requests/day, with backups 3.1-flash-lite and gemma-4-26b): about 3s per answer.
> The investor words questions differently each time, so match on the topic. Answers you've sent before replay instantly from the cache.

---

## 1. "What's your ARR and how do you calculate it?" → **Slide 4**

```
ARR is $1.29M: September MRR of $107,189 times 12. Our old deck said $1.37M because it included one-time onboarding fees, about $109K over the last year. We now show those separately.
```

## 2. "How fast are you growing?" → **Slide 4**

```
MRR grew about 9% a month compounded over the last 12 months, 8.1% without Northern Comfort. The last three months slowed to 4.9%. I don't have the breakdown between new customers and expansion yet; I'll send it.
```

## 3. "What's your churn?" / "What's your net revenue retention?" → **Slide 6**

```
Monthly logo churn is 2.0% over 12 months and 1.6% over the last six. Net revenue retention is about 88%. Most churn happens in a customer's first six months, so our onboarding programme targets that window.
```

## 4. "What does it cost to win a customer?" / "What's your payback?" → **Slide 5**

```
Fully loaded CAC is $3,209 with payback of about 9 to 10 months. Marketing-only it's $969, which is what our old deck used.
```

## 5. "How dependent are you on Northern Comfort?" → **Slide 8**

```
Northern Comfort is 260 seats, 9.7% of MRR, and renews in March 2027. The 600-seat expansion is verbal, so it's upside, not in our plan.
```

## 6. "Why $4M, and how long does it last?" / "What if the round slips?" → **Slide 11**

```
About 22 months on our plan, about 17 if growth stays at historical rates. If the round slips we'd hold hiring until it closes.
```

## 7. "Where does the $2B TAM come from?" → **Slide 7**

```
We removed the $2B figure. We're building it bottom-up from Statistics Canada and US Census counts of trades businesses with 3 to 30 technicians.
```

## Any question you don't have data for → **No slide**

```
I don't have that data yet. We'll start tracking it in a CRM this quarter and share it before the next meeting.
```

---

## Bad answers: show the investor catching mistakes

Paste one of these instead of the good answer. Each was tested against the app's fact check. When the check flags
a figure, **accuracy is capped at 2/5** whatever the AI thinks, the **Feedback** shows the fact-check error, and the
investor usually pushes back with a follow-up. Point at the slide shown.

### 1. Repeating the deck's inflated claims (flagged: "founder claim stated as fact")

| Investor asks about | Slide | Paste this |
|---|---|---|
| ARR | 4 | `Our ARR is $1.37M.` |
| Growth | 4 | `We're growing 10% month over month.` |
| Churn / NRR | 6 | `Churn is around 1% a month and net revenue retention is above 110%.` |
| Gross margin | 5 | `Our gross margin is 92%.` |
| CAC / payback | 5 | `Our CAC is $970 and we earn it back in under 3 months.` |
| Northern Comfort | 8 | `Northern Comfort Group is expanding to 600 seats next year, so concentration isn't a risk.` |
| Runway / the $4M | 11 | `$4M gives us 24 months of runway and gets us to $5M ARR.` |
| TAM | 7 | `It's a $2B total addressable market in North America.` |

### 2. Making up a number (flagged: "figure doesn't tie to the data")

| Investor asks about | Slide | Paste this |
|---|---|---|
| ARR | 4 | `We have about $2.5M in ARR.` |

### 3. Quoting a benchmark with no source (flagged: "benchmarks must name a public source")

| Investor asks about | Slide | Paste this |
|---|---|---|
| Churn | 6 | `Our churn is better than the industry average for SaaS.` |
| Burn / efficiency | 11 | `Our burn multiple is best-in-class.` |

### 4. Talking valuation (flagged: unsupported figure and valuation language)

| Investor asks about | Slide | Paste this |
|---|---|---|
| The raise | 11 | `We're valued at $20M, so this round is a bargain for you.` |

### 5. Bluffing with no numbers (no figure to check, so Feedback says "Investors expect a number")

These aren't caught by the fact check. The AI evaluator scores them low on evidence and candour, and the investor
asks for the number.

| Investor asks about | Slide | Paste this |
|---|---|---|
| Growth | No slide | `Growth is strong and we're confident it will keep going. Customers love us.` |
| Churn | No slide | `Churn won't be a problem. Our customers love the product.` |
| Any number | No slide | `Honestly, we're growing fast. I'd have to check the exact number.` |

**Tips**
- **Don't add "it's on the slide" or "the deck says".** The fact check treats those words as attribution (the
  founder is quoting the deck), so the inflated figure isn't flagged.
- **The lead seed fund asks up to 2 follow-ups**, and bad answers trigger them, so a run of bad answers makes the
  meeting longer. Mix one bad answer with good ones for a short demo.
- **A strong demo arc:** paste a bad answer (accuracy capped, investor pushes back), then paste the good answer to
  the follow-up and watch the score recover.

**What to point out:** the correct answers given on the *draft* deck trigger "Slide N vs your answer" warnings in **Feedback**, because the slide still shows the old claim. The debrief then lists **Slides to fix before the real meeting**. To show a clean run, upload `tidewell_deck_corrected.pdf` instead.
