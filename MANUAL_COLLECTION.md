# Manual collection workflow — TakeMeter

Goal: ~240 labeled comments, **70–90 per label** (`tactical` / `hot_take` / `banter`),
ending at **200+** clean rows. Budget ~1–2 hours. You stay close to the data — which
is the whole point.

## Setup (1 minute)

1. Open **`candidates.csv`** (in this folder) in **Google Sheets** (recommended) or
   Excel/Numbers. It has 3 example rows showing the format — **delete those 3 rows**
   before you start.
2. Columns: `text`, `label`, `thread_type`, `source`. You only *must* fill `text`
   and `label`; the other two are handy notes (which thread, the comment link).

> **Google Sheets paste tip:** to paste a comment into a single cell (not split
> across columns), **double-click the cell first** to enter edit mode, then paste.
> Or paste into the formula bar at the top.

## Where to collect (for class balance)

Open these on **old.reddit.com/r/soccer** (cleaner to read) and pull from all three
so every label is represented:

| Thread | Find it by | Mostly gives you |
|---|---|---|
| **Post Match Thread** | search "Post Match Thread", sort New | `tactical` + `hot_take` |
| **Match Thread** (live) | search "Match Thread" during/after a game | `banter` |
| **Daily Discussion** | pinned at top of the sub | `tactical` + `hot_take` |

Tip: in post-match threads, sort comments by **Top** to find the reasoned
breakdowns; scroll **Match Threads** for the caps-lock emotion.

## The loop (repeat ~240 times — it's fast)

For each comment:
1. Read it. Decide the label using the rules below.
2. Copy the comment text → paste into the `text` cell (double-click cell first).
3. Type the label in the `label` cell: `tactical`, `hot_take`, or `banter`.
4. (Optional) note `thread_type` and paste the comment's link in `source`.
5. **Skip** anything you can't label cleanly — don't force it. Skip images-only,
   one-word replies, and non-English comments.

## Labeling rules (from planning.md)

- **`tactical`** — explains HOW/WHY with specific, verifiable detail (formation,
  movement, stats, match events). Remove the opinion and reasoning remains.
- **`hot_take`** — a bold evaluative opinion with NO real supporting evidence.
- **`banter`** — emotion / joke / celebration, no analytical claim.

**Decision rule for the hard case** (a take with one stat, e.g. *"Haaland is
overrated — 0 goals in his last 4 UCL knockouts"*): if the evidence would still
support the claim with the opinion stripped out → `tactical`; if it's cherry-picked
/ decorative → `hot_take`. When genuinely 50/50, pick the **lower** tier
(banter < hot_take < tactical) so `tactical` stays clean.

## Keeping balance

Every ~50 comments, check your counts so one label doesn't run away:

```bash
python3 label_stats.py candidates.csv
```

It prints per-label counts vs. the 70–90 target and tells you which class to chase.
`tactical` is usually the one that lags → spend extra time in post-match and daily
discussion threads.

## When you're done

`label_stats.py` prints **"✅ Ready to train"** once you have 200+ and every class is
in band. Then:
- Keep the `text` and `label` columns (extra columns are fine — the notebook ignores
  them).
- File → Download → **CSV** (if in Google Sheets), save as `candidates.csv`.
- Upload it in **Section 1** of the notebook.
