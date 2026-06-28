# TakeMeter — Classifying Discourse Quality on r/soccer

A fine-tuned `distilbert-base-uncased` classifier that separates **takes** from
**noise** in r/soccer comments (`hot_take` vs `banter`), compared to a zero-shot
`llama-3.3-70b-versatile` (Groq) baseline.

## Community

**r/soccer** — a ~4M-member, almost entirely text-driven football community. The same
event (a goal, a red card) produces, in one thread, a reasoned breakdown, a bold
dismissal, and a wall of caps-lock celebration. That spread of quality is what makes
classification interesting, and the "is this a real take or just noise?" distinction
is native to how the sub talks about itself. Volume makes collecting 200+ public
comments easy.

## Label taxonomy

Two labels on one axis — **is the comment making a take, or just noise?**

**`hot_take`** — an evaluative claim, opinion, or analysis about players, teams,
managers, or tactics (reasoned *or* unsupported; both count as a claim).
- *"Ronaldo at 50 is a better footballer than 99% of r/soccer, don't get the hate."*
- *"Arteta is no protégé of Pep — he's the new Mourinho with these park-the-bus tactics."*

**`banter`** — an emotional reaction, celebration, joke, or in-the-moment vibe with no
real claim being made.
- *"GREAT FIRST HALF! 45 MORE MINUTES AND WE'RE IN!"*
- *"What is the keeper doing lmao."*

## Data

**Source.** Public r/soccer comments — post-match threads, live match threads, and the
daily discussion thread. Reddit blocks anonymous scraping, so I collected **manually**
(copy-paste into a CSV).

**Labeling process.** I used an LLM to pre-label an initial batch, then reviewed and
corrected every row myself against the definitions above; later comments I labeled by
hand. I dropped 29 of the original 150 comments that fit no label (news, standings
math, trivia), and merged an originally-planned `tactical` class into `hot_take` after
it proved too rare to train on — leaving a 2-label set.

**Label distribution** (121 labeled rows):

| Label | Count | Share |
|---|---|---|
| `banter` | 70 | 57.9% |
| `hot_take` | 51 | 42.1% |

**3 difficult-to-label examples and decisions:**

1. *"Tuchelissimo ball is unwatchable. Love the man but there's a reason why he
   finished 3rd with Bayern."* → **`hot_take`**: "unwatchable" is a judgment, backed
   with a reason — a take, not just a jab.
2. *"If Panama don't score they'll be the only team to go out without a goal. Sad day
   for Panama and the Thomas Christiansen Fanclub (me)."* → **`banter`**: a prediction
   wrapped in a self-deprecating joke; no quality judgment is argued.
3. *"Emma Hayes' analysis in the water breaks is great — someone who actually knows
   tactics rather than general platitudes."* → **`hot_take`**: a comparative quality
   judgment, so a claim is being made.

## Fine-tuning approach

- **Base model:** `distilbert-base-uncased` with a 2-label classification head.
- **Training setup:** 3 epochs, learning rate `2e-5`, batch size 16, weight decay 0.01,
  50 warmup steps, max length 256, on a Colab T4 GPU. Stratified 70/15/15 split; best
  model chosen by validation accuracy.
- **Hyperparameter decision:** kept epochs at **3** rather than increasing them. With
  only ~85 training examples, more epochs risk overfitting (memorizing the training
  set) instead of learning the take-vs-noise boundary; 3 epochs at `2e-5` is the
  standard low-overfit starting point for BERT-family models on small data.

## Baseline (zero-shot Groq)

Zero-shot `llama-3.3-70b-versatile`, no training. The system prompt gives the task,
both label definitions, one example per label, and a tie-breaker, and instructs the
model to output only the label name; each test comment is sent at `temperature=0`.
Results were collected by running every test comment through the model and matching its
output to a label string, reporting accuracy over parseable responses.

```
You are classifying comments from r/soccer.
Assign each to exactly ONE category: is it making a TAKE, or just NOISE?

hot_take: an evaluative claim/opinion/analysis about players, teams, or tactics.
  Example: "Arteta is the new Mourinho with park-the-bus tactics."
banter: emotional reaction, celebration, joke, or vibe with no claim.
  Example: "GREAT FIRST HALF! 45 MORE MINUTES AND WE'RE IN!"

Tie-breaker: emotional but implies a judgment ("they bottled it again") -> hot_take.
Respond with ONLY the label name.
```

## Evaluation report

Test set: **19 examples** (8 `hot_take`, 11 `banter`).

**Accuracy:**

| Model | Accuracy |
|---|---|
| Zero-shot baseline (Groq) | 0.579 |
| Fine-tuned DistilBERT | **0.632** |

**Per-class — baseline:**

| Label | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| `hot_take` | 0.50 | 1.00 | 0.67 | 8 |
| `banter` | 1.00 | 0.27 | 0.43 | 11 |

**Per-class — fine-tuned** (macro-F1 0.63):

| Label | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| `hot_take` | 0.54 | 0.88 | 0.67 | 8 |
| `banter` | 0.83 | 0.45 | 0.59 | 11 |

**Confusion matrix — fine-tuned** (rows = true, cols = predicted):

| true \ pred | hot_take | banter |
|---|---|---|
| **hot_take** | 7 | 1 |
| **banter** | 6 | 5 |

The dominant error is **`banter` → `hot_take`** (6 of 11): the model over-predicts
`hot_take` (recall 0.88) and misses nearly half of `banter` (recall 0.45). It is more
balanced than the baseline (which barely predicted `banter` at all), but it leans toward
calling things takes. (See the confidence note below — predictions are near coin-flip
throughout.)

**3 wrong predictions, analyzed:**

1. *"Only Roberto can make a portugal vs Colombia game look boring. Fraud of the
   highest order. He's lost the locker room."* — True **hot_take**, Predicted
   **banter** (conf 0.50). This is a clear take ("fraud", "lost the locker room"), but
   the sarcastic opener reads like a joke, so the model leaned on *tone* instead of the
   *claim*. The one false-negative for `hot_take`.
2. *"It wouldn't be a World Cup without a video of Japanese fans tidying up."* — True
   **banter**, Predicted **hot_take** (conf 0.50). A wry cultural observation with no
   evaluative claim, but its confident declarative shape looks take-like to the model.
3. *"As a Scotland fan I can only dream that one day we too will make it to the last 16
   and be knocked out by Iceland."* — True **banter**, Predicted **hot_take** (conf
   0.50). A self-deprecating joke the model misreads as a judgment. (A fourth error,
   the "Mokoena is a shithouser… regen Adebayor" comment, is arguably a genuine
   `hot_take` itself — a reminder the boundary is inherently fuzzy.)

**Sample classifications:**

| Comment | Predicted | Confidence | Correct? |
|---|---|---|---|
| "What build up play? Ronaldo touched the ball like 4 times. The free kick and two shots that got blocked." | hot_take | 0.50 | ✅ |
| "We went from all WC games being free on national television, to having to pay to watch ALL of them." | hot_take | 0.52 | ✅ |
| "Only Roberto can make a portugal vs Colombia game look boring. Fraud of the highest order." | banter | 0.50 | ❌ (true `hot_take`) |
| "It wouldn't be a World Cup without a video of Japanese fans tidying up." | hot_take | 0.50 | ❌ (true `banter`) |
| "As a Scotland fan I can only dream… knocked out by Iceland." | hot_take | 0.50 | ❌ (true `banter`) |

**One correct example explained:** *"What build up play? Ronaldo touched the ball like
4 times…"* → `hot_take` (0.50). This is a genuine evaluative rebuttal backed with
specifics, exactly the signal the `hot_take` label is meant to capture — the model got
it right. But the **0.50 confidence is the real story:** even its correct calls are
made at coin-flip certainty.

**Confidence is uninformative.** Across the whole test set, every prediction — correct
or wrong — landed between **0.50 and 0.53**. The model never commits; the 0.63 accuracy
comes from tiny margins, not confident discrimination. With ~85 training examples this
is expected, and it's the clearest evidence that the dataset is too small for the model
to learn a sharp boundary.

## Reflection — what the model learned vs. intended

I intended a classifier that detects whether a comment makes an evaluative *claim*. On
this small dataset it learned a weaker proxy — surface cues like player/manager names
and words such as "overrated"/"fraud" — rather than truly detecting an argument, which
is why sarcastic takes (the "Roberto… fraud" comment) and joking non-takes (the Scotland
and Japan comments) both trip it up. The +5-point gain over zero-shot shows it learned
something real, but every prediction sits at 0.50–0.53 confidence: it never commits.
The honest conclusion is that ~120 examples is too few to learn a sharp take-vs-noise
boundary — promising signal, not yet reliable.

## Spec reflection

- **How the spec helped:** planning.md pre-committed an "if a class is underrepresented"
  fallback, so when `tactical` turned out too rare I executed the planned merge to 2
  labels instead of improvising.
- **Where implementation diverged:** the spec assumed 3 labels and PRAW scraping;
  Reddit blocked anonymous scraping (forcing manual collection) and `tactical` was too
  rare (forcing the 2-label merge). Both were data-driven corrections.

## AI usage

1. **Label / spec design.** I directed the AI to draft the taxonomy and planning.md from
   the brief. I overrode its initial 3-label scheme, merging `tactical` into `hot_take`
   after labeling showed `tactical` was too rare.
2. **Annotation assistance (disclosed).** I used the LLM to pre-label an initial batch
   of comments, then reviewed and corrected every label myself against my definitions
   — the final labels are my judgment, not the AI's.
