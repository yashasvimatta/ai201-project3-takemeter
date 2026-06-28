# TakeMeter — planning.md

**Project:** A discourse classifier for r/soccer · AI201 Project 3 · dm853@cornell.edu

---

## 1. Community

**r/soccer** — a ~4M-member, almost entirely text-driven community. During a
tournament a single goal spawns, in one thread, a reasoned breakdown, a bold
dismissal, and a wall of caps-lock celebration. That spread of quality is what
makes classification non-trivial, the "is this a real take or just noise?" split is
native to how the sub talks about itself, and match/post-match/discussion threads
make collecting 200+ public comments trivial.

## 2. Labels

Two labels, on the axis **is the post a take, or just noise?**

**`hot_take`** — an evaluative claim, opinion, or analysis about players, teams, or
tactics (reasoned *or* unsupported; both count as making a claim).
- "Ronaldo at 50 is a better footballer than 99% of r/soccer, don't get the hate."
- "Arteta is no protégé of Pep — he's the new Mourinho with these park-the-bus tactics."

**`banter`** — an emotional reaction, celebration, joke, or in-the-moment vibe with
no real claim being made.
- "GREAT FIRST HALF! 45 MORE MINUTES AND WE'RE IN!"
- "What is the keeper doing lmao."

## 3. Hard edge cases

The genuine ambiguity is **`hot_take` vs `banter`** for emotional posts that *imply*
a judgment, e.g. *"City bottled it again 🤡"*.

**Decision rule:** if an evaluative claim is being made — even implicitly ("they're
chokers") — it's `hot_take`. If it's pure emotion, mockery, or a joke with no claim,
it's `banter`. When genuinely 50/50, default to `banter` so `hot_take` stays a clean
"there is an actual take here" class. ("City bottled it again" asserts a recurring
failing → `hot_take`; a bare "🤡😭" → `banter`.)

**Difficult cases I actually hit while labeling (and what I decided):**

1. *"Tuchelissimo ball is unwatchable. Love the man but there's a reason why he
   finished 3rd with Bayern."* — Could be `banter` (a dismissive jab) or `hot_take`
   (a real evaluative claim). **Decided `hot_take`**: "unwatchable" is a judgment and
   it's backed with a reason (the 3rd-place stat), so a take is clearly being made.

2. *"If Panama don't score in the remaining 25 mins they'll be the only team to go
   out without a goal. Sad day for Panama and the Thomas Christiansen Fanclub (me)."*
   — A prediction wrapped in a self-deprecating joke. **Decided `banter`**: no quality
   judgment about a player/team is being argued; it's an emotional, jokey reaction.

3. *"Emma Hayes' analysis in the water breaks is great — nice to hear someone who
   actually knows tactics rather than general sporting platitudes."* — Praise, which
   sits between appreciation (`banter`) and an evaluative take. **Decided `hot_take`**:
   it's a comparative quality judgment ("knows tactics" vs "platitudes"), i.e. a claim.

4. *"The Uruguay and Algeria keepers are going band for band to see who is worse —
   both of them are shite."* — **Decided `banter`**: in-the-moment mockery/hyperbole
   rather than a reasoned claim, so it falls on the noise side of the boundary.

## 4. Data collection plan

- **Where:** r/soccer post-match threads, live match threads, and the daily
  discussion thread. Reddit blocks anonymous scraping, so I collected **manually**
  (copy-paste into a CSV) — allowed by the project and keeps me close to the data.
- **How many:** ~100+ per label (≥ 200 total) so each split (70/15/15) has a usable
  test set.
- **What actually happened:** first pass = **150** comments. Labeling showed **29
  (19%)** were news/standings-math/trivia that fit no label — dropped them. It also
  showed the on-pitch-analysis class I originally planned had only ~10 examples, far
  too few to train. **Underrepresented-class fallback (executed):** I merged that
  class into `hot_take`, giving a clean 2-label scheme — now **121 rows** (hot_take
  51, banter 70). Next pass collects ~80 more (both classes common in match threads)
  to clear 200+.

## 5. Evaluation metrics

Accuracy alone is misleading because the classes are imbalanced — `banter` is the
most common comment type, so a model that always guesses `banter` could score high
accuracy while being useless at the thing that matters (finding real takes). So:

- **Macro-F1 (primary)** — averages both classes equally, so it can't be gamed by the
  majority class.
- **`hot_take` precision and recall** — the deployment use is a "surface the actual
  discussion" filter, so precision (when it says *take*, it's right) matters most;
  recall second.
- **Confusion matrix** — to see *which* way errors go (takes lost to banter vs. banter
  promoted to takes).
- **Baseline parse rate** — for the Groq zero-shot baseline, report accuracy only on
  parseable label outputs, so the comparison is honest.

## 6. Definition of success

Concrete, checkable bar:
- **Macro-F1 ≥ 0.75** on the held-out test set (fine-tuned model).
- **Both classes ≥ 0.70 F1** — proves it learned `hot_take`, not just the majority.
- **`hot_take` precision ≥ 0.75** — when it flags a take, it's right ~3 of 4 times.
- **Fine-tuned beats the Groq zero-shot baseline by ≥ 0.05 macro-F1** — otherwise
  fine-tuning wasn't worth it.

**Deployable?** I'd ship a *take-highlighter* (surfacing substantive comments in busy
threads) at macro-F1 ≥ 0.75 and `hot_take` precision ≥ 0.75 — good enough as a filter
a human still skims, not an autonomous moderator. I would not ship it for anything
punitive (auto-removing posts) at any accuracy this project can reach.

*Specific enough to grade myself?* Yes — every bar is one number printed directly by
Sections 4 & 6 of the notebook (`classification_report` macro-F1, per-class F1,
`hot_take` precision, baseline-vs-finetuned delta). I read each off and check the box.

## 7. AI Tool Plan

No code to generate here, so AI helps at three points:

- **Label stress-testing (before annotating):** give Claude my §2/§3 definitions and
  ask for 5–10 posts that sit on the `hot_take`/`banter` boundary. Any I can't
  classify cleanly mean the definitions need tightening — done *before* labeling at
  scale.
- **Annotation assistance:** I used an LLM to **pre-label an initial
  batch** of comments, which I then reviewed and corrected myself; the remaining
  examples I labeled by hand from scratch. The final labels are my judgment — the AI
  only gave a first pass on part of the set. Disclosed in my AI-usage section.
- **Failure analysis (after evaluation):** paste the wrong-predictions list (text /
  true / predicted) into Claude to cluster errors into patterns (e.g. "sarcastic
  takes read as banter"). I **verify each pattern against the actual examples** before
  it goes in the README.