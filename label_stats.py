"""
label_stats.py — sanity-check your labeled CSV before training.

Run this whenever you want to see how labeling is going. It tells you:
  - how many rows are still unlabeled
  - the count per label, and whether each is in the 70-90 target band
  - any labels that don't match your taxonomy (typos like "tactial")
  - the smallest class (the one that caps your stratified split)

It does NOT change your CSV — read-only.

Usage
-----
    python3 label_stats.py                  # defaults to candidates.csv
    python3 label_stats.py mydata.csv       # any CSV path
"""

import csv
import sys
from collections import Counter

# Your taxonomy from planning.md / Section 1 of the notebook (2-label scheme).
VALID_LABELS = {"hot_take", "banter"}
TARGET_MIN = 90    # per-class target so a 2-class set still clears ~200 total
TARGET_MAX = 130
GRAND_MIN = 200   # project minimum total labeled examples


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "candidates.csv"
    try:
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        sys.exit(f"No file at {path!r}. Run collect_reddit.py first, or pass a path.")

    if "label" not in (rows[0].keys() if rows else []):
        sys.exit("CSV has no `label` column.")

    total = len(rows)
    labels = [(r.get("label") or "").strip() for r in rows]
    labeled = [l for l in labels if l]
    blank = total - len(labeled)
    counts = Counter(labeled)

    print(f"File: {path}")
    print(f"Total rows:      {total}")
    print(f"Labeled:         {len(labeled)}")
    print(f"Still blank:     {blank}")
    print()

    # Unknown labels (typos / stray values).
    unknown = {l: c for l, c in counts.items() if l not in VALID_LABELS}
    if unknown:
        print("⚠️  Labels not in your taxonomy (fix these typos):")
        for l, c in sorted(unknown.items()):
            print(f"     {l!r}: {c}")
        print()

    # Per-class counts vs. the target band.
    print(f"Per-label counts (target {TARGET_MIN}-{TARGET_MAX} each):")
    for label in sorted(VALID_LABELS):
        c = counts.get(label, 0)
        if c < TARGET_MIN:
            flag = f"⬇  need {TARGET_MIN - c} more"
        elif c > TARGET_MAX:
            flag = f"⬆  {c - TARGET_MAX} over (fine, or trim for balance)"
        else:
            flag = "✅ in band"
        print(f"     {label:<10} {c:>4}   {flag}")
    print()

    # Bottom line: is it ready to train?
    in_band = all(
        counts.get(l, 0) >= TARGET_MIN for l in VALID_LABELS
    )
    smallest = min((counts.get(l, 0) for l in VALID_LABELS), default=0)
    print(f"Smallest class:  {smallest}  (caps your stratified test split)")

    if len(labeled) < GRAND_MIN:
        print(f"\n❌ Not ready: only {len(labeled)}/{GRAND_MIN} labeled.")
    elif unknown:
        print("\n❌ Not ready: fix the unknown labels above first.")
    elif not in_band:
        print(f"\n⚠️  Over {GRAND_MIN} labeled, but at least one class is under "
              f"{TARGET_MIN}. Collect more of the thin class (see planning §4 "
              f"fallback) or accept the imbalance knowingly.")
    else:
        print("\n✅ Ready to train: 200+ labeled and every class in band.")
        print("   Drop the helper columns if you like, keep `text` and `label`,")
        print("   and upload to Section 1 of the notebook.")


if __name__ == "__main__":
    main()
