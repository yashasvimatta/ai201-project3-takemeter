"""
collect_reddit.py — gather candidate r/soccer comments for TakeMeter labeling.

Uses Reddit's official API via PRAW in READ-ONLY mode (application-only OAuth),
because Reddit blocks anonymous JSON scraping. It does the boring part — pull
public comments, clean them, drop junk, dedupe — and writes a CSV. It does NOT
assign labels: you read each row and fill in the `label` column yourself
(tactical / hot_take / banter). Staying close to the data is the point.

Setup (one time)
----------------
1. Create a free Reddit "script" app at https://www.reddit.com/prefs/apps
   ("create another app" -> type: script -> redirect uri: http://localhost:8080).
2. Note the client ID (under the app name) and the secret.
3. Install PRAW and export your credentials:

       pip install praw
       export REDDIT_CLIENT_ID="your_client_id"
       export REDDIT_CLIENT_SECRET="your_secret"
       export REDDIT_USERNAME="your_reddit_username"   # only used in the UA string

   (Or paste them into the CONFIG block below — but don't commit real secrets.)

Usage
-----
    python3 collect_reddit.py               # auto-discovers recent threads
    python3 collect_reddit.py --target 280  # how many candidate rows to keep
    python3 collect_reddit.py --urls urls.txt   # use your own thread URLs/IDs

Output
------
    candidates.csv  with columns: text, label, thread_type, score, permalink
    The `label` column is empty — that's your job. Open it in a spreadsheet and
    label each row using your planning.md definitions.
"""

import argparse
import csv
import html
import os
import random
import re
import sys
import time
from collections import Counter

# ── CONFIG ────────────────────────────────────────────────────────────────────
# Prefer environment variables; fall back to these constants if you'd rather
# paste them (do NOT commit real secrets to git).
CLIENT_ID     = os.environ.get("REDDIT_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
USERNAME      = os.environ.get("REDDIT_USERNAME", "anon")
SUBREDDIT     = "soccer"

# Keep comments roughly tweet-to-paragraph length. Too short = no signal; too
# long = usually copypasta or a multi-topic essay that's hard to label cleanly.
MIN_CHARS = 15
MAX_CHARS = 600
BOT_AUTHORS = {"automoderator", "sportsbot", "soccer-bot"}

# Title keywords that map a discovered thread to one of our thread types.
THREAD_TITLE_HINTS = {
    "post_match": ["post match thread", "post-match thread"],
    "match":      ["match thread"],          # checked after post_match
    "tactical":   ["daily discussion", "tactical"],
}
# ──────────────────────────────────────────────────────────────────────────────


def get_reddit():
    """Build a read-only PRAW client, or exit with setup instructions."""
    try:
        import praw
    except ImportError:
        sys.exit("PRAW not installed. Run:  pip install praw")

    if not CLIENT_ID or not CLIENT_SECRET:
        sys.exit(
            "Missing Reddit credentials. Create a 'script' app at "
            "https://www.reddit.com/prefs/apps and export:\n"
            "  export REDDIT_CLIENT_ID=...\n"
            "  export REDDIT_CLIENT_SECRET=...\n"
            "  export REDDIT_USERNAME=...   (your reddit username)\n"
        )

    reddit = praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        user_agent=f"macos:takemeter-ai201:1.0 (by /u/{USERNAME})",
    )
    reddit.read_only = True
    return reddit


def classify_title(title):
    """Map a thread title to one of our thread types, or None if not relevant."""
    t = title.lower()
    if any(k in t for k in THREAD_TITLE_HINTS["post_match"]):
        return "post_match"
    if any(k in t for k in THREAD_TITLE_HINTS["match"]):
        return "match"
    if any(k in t for k in THREAD_TITLE_HINTS["tactical"]):
        return "tactical"
    return None


def discover_submissions(reddit, per_type=4):
    """
    Scan the subreddit's hot + new listings and return submissions classified by
    title, capped per type so one busy type doesn't crowd out the others.
    """
    chosen = {"post_match": [], "match": [], "tactical": []}
    sub = reddit.subreddit(SUBREDDIT)
    seen_ids = set()
    for listing in (sub.hot(limit=100), sub.new(limit=100)):
        for submission in listing:
            if submission.id in seen_ids:
                continue
            seen_ids.add(submission.id)
            ttype = classify_title(submission.title or "")
            if ttype and len(chosen[ttype]) < per_type:
                chosen[ttype].append(submission)
    out = []
    for ttype, subs in chosen.items():
        out.extend((ttype, s) for s in subs)
    return out


def clean_text(body):
    """Normalize a comment body: unescape, strip markdown links/quotes, collapse."""
    text = html.unescape(body)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1", text)  # [txt](url)->txt
    text = re.sub(r"https?://\S+", " ", text)                        # bare urls
    text = re.sub(r"^>.*$", " ", text, flags=re.MULTILINE)           # quote lines
    text = re.sub(r"\s+", " ", text).strip()
    return text


def comments_from(submission):
    """Yield (raw_body, score, permalink) for usable comments in a submission."""
    submission.comments.replace_more(limit=0)   # drop the "load more" stubs
    for c in submission.comments.list():
        author = (str(c.author) if c.author else "").lower()
        body = c.body or ""
        if author in BOT_AUTHORS or body in ("[deleted]", "[removed]", ""):
            continue
        yield body, c.score, f"https://reddit.com{c.permalink}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=280,
                    help="number of candidate rows to keep")
    ap.add_argument("--urls", type=str, default=None,
                    help="text file of reddit thread URLs or IDs (one per line)")
    ap.add_argument("--out", type=str, default="candidates.csv")
    args = ap.parse_args()

    reddit = get_reddit()

    # Build the list of (thread_type, submission).
    if args.urls:
        jobs = []
        with open(args.urls) as f:
            for line in f:
                u = line.strip()
                if not u:
                    continue
                try:
                    sub = (reddit.submission(url=u) if u.startswith("http")
                           else reddit.submission(id=u))
                    jobs.append(("manual", sub))
                except Exception as e:
                    print(f"  ! couldn't load {u}: {e}", file=sys.stderr)
    else:
        print(f"Auto-discovering recent r/{SUBREDDIT} threads...")
        jobs = discover_submissions(reddit)
        by_type = Counter(t for t, _ in jobs)
        print(f"  found: {dict(by_type) or 'nothing'}")

    if not jobs:
        sys.exit("No threads to scrape. Pass --urls with a few thread URLs.")

    # Pull, clean, filter, dedupe.
    seen = set()
    rows = []
    for ttype, submission in jobs:
        try:
            title = submission.title
        except Exception as e:
            print(f"  ! skipping a thread ({e})", file=sys.stderr)
            continue
        print(f"Fetching [{ttype}] {title[:70]}")
        for body, score, permalink in comments_from(submission):
            text = clean_text(body)
            if not (MIN_CHARS <= len(text) <= MAX_CHARS):
                continue
            key = re.sub(r"[^a-z0-9]", "", text.lower())[:120]
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "text": text,
                "label": "",                # <-- you fill this in by hand
                "thread_type": ttype,
                "score": score,
                "permalink": permalink,
            })
        time.sleep(1.0)   # be polite between threads

    if not rows:
        sys.exit("Collected 0 usable comments. Try --urls with active threads.")

    # Shuffle (so you don't label one thread at a time) then trim to target.
    random.seed(42)
    random.shuffle(rows)
    rows = rows[:args.target]

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["text", "label", "thread_type", "score", "permalink"]
        )
        writer.writeheader()
        writer.writerows(rows)

    by_type = Counter(r["thread_type"] for r in rows)
    print(f"\nWrote {len(rows)} candidate rows to {args.out}")
    print(f"By thread type: {dict(by_type)}")
    print("\nNext: open candidates.csv in a spreadsheet and fill in the `label`")
    print("column (tactical / hot_take / banter) using your planning.md rules.")
    print("Aim for 70-90 per label; delete rows you can't label cleanly.")
    print("Check progress any time with:  python3 label_stats.py candidates.csv")


if __name__ == "__main__":
    main()
