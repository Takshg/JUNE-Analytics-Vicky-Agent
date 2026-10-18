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

## Optional: show the investor catching a bad answer

Paste one of these instead to show the fact check capping accuracy and the investor pushing back.

**Slide 4:**
```
Our ARR is $1.37M.
```

**Slide 4:**
```
We're growing 10% month over month.
```

**Slide 6:**
```
Churn is around 1% a month and net revenue retention is above 110%.
```

**What to point out:** the correct answers given on the *draft* deck trigger "Slide N vs your answer" warnings in **Feedback**, because the slide still shows the old claim. The debrief then lists **Slides to fix before the real meeting**. To show a clean run, upload `tidewell_deck_corrected.pdf` instead.
