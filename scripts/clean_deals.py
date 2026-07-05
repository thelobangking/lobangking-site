#!/usr/bin/env python3
"""Remove outdated lobangs immediately — no retention window, no archiving.

This is a STRICTER companion to prune_pages.py. Where prune_pages.py keeps a
deal until it has been expired for RETENTION_DAYS, this script removes a deal
the moment it stops qualifying, and it does NOT store the removed entries
anywhere (no history/archive) — they are simply dropped.

A deal is KEPT only when ALL of the following hold:
  1. It is a real offer, not news/reporting (reuses looks_like_news()).
  2. Its expiry text yields a concrete end date (reuses parse_expiry()).
  3. That end date has not passed (end >= TODAY).

So a deal is REMOVED when it is news, OR its end date cannot be identified from
the source ("Ongoing", "Every Tuesday", "7 hours left", …), OR it has expired.
The definition of "expired"/"undated" is the single source of truth shared with
the rest of the pipeline (aggregate_deals.parse_expiry), so this stays perfectly
consistent with build_pages.is_active — only stricter about undated items.

Both the live catalogue (data/deals.json) AND the curated seed
(scripts/manual_deals.json) are cleaned, so nothing outdated lingers in storage
to be re-added on the next aggregator run.

Usage:
    python scripts/clean_deals.py            # clean + rebuild pages
    python scripts/clean_deals.py --dry-run  # report only, change nothing
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Single source of truth for expiry + news detection.
from aggregate_deals import parse_expiry, looks_like_news, TODAY

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_FILE = ROOT / "data" / "deals.json"
MANUAL_FILE = HERE / "manual_deals.json"


def classify(d: dict) -> tuple[str, object]:
    """Return (verdict, end_date). verdict is 'keep', 'news', 'undated' or 'expired'."""
    title = d.get("title", "")
    summary = f"{d.get('desc', '')} {d.get('expiry', '')}"
    if looks_like_news(title, summary):
        return ("news", None)
    blob = f"{title} {d.get('desc', '')} {d.get('expiry', '')}"
    _, end = parse_expiry(blob)
    if end is None:
        return ("undated", None)
    if end < TODAY:
        return ("expired", end)
    return ("keep", end)


def split(deals: list) -> tuple[list, dict]:
    """Partition deals into kept + a {reason: [deals]} map of removed."""
    kept, removed = [], {"news": [], "undated": [], "expired": []}
    for d in deals:
        verdict, _ = classify(d)
        if verdict == "keep":
            kept.append(d)
        else:
            removed[verdict].append(d)
    return kept, removed


def report(label: str, removed: dict) -> None:
    total = sum(len(v) for v in removed.values())
    if not total:
        print(f"  {label}: nothing to remove — all entries are current & dated.")
        return
    print(f"  {label}: removing {total} —")
    for reason in ("expired", "undated", "news"):
        for d in removed[reason]:
            why = {"expired": "expired", "undated": "no end date in source",
                   "news": "not a real offer"}[reason]
            print(f"    - [{reason}] {d.get('id', '?')} · {d.get('store', '')} "
                  f"· \"{d.get('expiry', '')}\" ({why})")


def fix_spotlight(kept: list, removed_any: bool) -> None:
    """Ensure exactly one spotlight survives (mirrors prune_pages.py)."""
    if not kept:
        return
    if not any(d.get("spotlight") for d in kept):
        for d in kept:
            d.pop("spotlight", None)
        kept[0]["spotlight"] = True


def main() -> int:
    dry = "--dry-run" in sys.argv
    print(f"clean_deals — today is {TODAY.isoformat()}"
          + (" (DRY RUN — no changes written)" if dry else ""))

    changed = False

    # ---- live catalogue -----------------------------------------------------
    doc = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    deals = doc.get("deals", [])
    kept, removed = split(deals)
    report("data/deals.json", removed)
    if len(kept) != len(deals):
        changed = True
        fix_spotlight(kept, True)
        doc["deals"] = kept
        if not dry:
            DATA_FILE.write_text(json.dumps(doc, indent=2, ensure_ascii=False),
                                 encoding="utf-8")
    print(f"  data/deals.json: {len(deals)} → {len(kept)} deals kept")

    # ---- curated seed -------------------------------------------------------
    if MANUAL_FILE.exists():
        man = json.loads(MANUAL_FILE.read_text(encoding="utf-8"))
        man_deals = man.get("deals", []) if isinstance(man, dict) else man
        mkept, mremoved = split(man_deals)
        report("scripts/manual_deals.json", mremoved)
        if len(mkept) != len(man_deals):
            changed = True
            if isinstance(man, dict):
                man["deals"] = mkept
            else:
                man = mkept
            if not dry:
                MANUAL_FILE.write_text(json.dumps(man, indent=2, ensure_ascii=False),
                                       encoding="utf-8")
        print(f"  scripts/manual_deals.json: {len(man_deals)} → {len(mkept)} deals kept")

    # ---- rebuild derived pages ---------------------------------------------
    if dry:
        print("Dry run complete — no files changed, no rebuild.")
        return 0
    if not changed:
        print("Everything already current — no rebuild needed.")
        return 0
    import build_pages
    build_pages.main()
    print("Rebuilt pages, feed and sitemap from the cleaned catalogue.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
