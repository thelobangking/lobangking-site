#!/usr/bin/env python3
"""
prune_pages.py — retention garbage collector
============================================

Keeps the database and the generated pages tidy and current:

  • Hard-deletes any deal whose expiry passed more than RETENTION_DAYS (10) days
    ago — so old, dead deals never accumulate in the database.
  • Rebuilds the site afterwards, which AUTOMATICALLY:
      – creates a sitemap URL + per-deal page for every current deal (new deals
        appear the moment they're added), and
      – deletes the per-deal / category pages of deals that are gone (orphans),
        so expired pages are removed and the sitemap stays accurate.

Note on display vs. retention: the site itself only ever shows *active* (non-expired)
deals — build_pages hides expired ones immediately. This GC is the database-level
cleanup that removes them for good after the 10-day grace window.

Reuses the existing expiry parser + builder (single source of truth) and is
dependency-free, so it stays correct long-term. Runs hourly via the validator,
or standalone:  python3 scripts/prune_pages.py [--dry-run]
"""
import sys
import json
import pathlib
import datetime

import aggregate_deals as agg   # parse_expiry + TODAY
import build_pages              # rebuild → sitemap + pages stay in sync

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "deals.json"
RETENTION_DAYS = 10


def expiry_end(deal):
    """The deal's end date (or None if it has no parseable end / is ongoing)."""
    blob = f"{deal.get('title','')} {deal.get('desc','')} {deal.get('expiry','')}"
    _, end = agg.parse_expiry(blob)
    return end


def prune(days=RETENTION_DAYS, dry_run=False):
    """Remove deals expired more than `days` ago. Returns the list of removed titles."""
    if not DATA.exists():
        return []
    doc = json.loads(DATA.read_text(encoding="utf-8"))
    deals = doc.get("deals", [])
    cutoff = agg.TODAY - datetime.timedelta(days=days)

    kept, removed = [], []
    for d in deals:
        end = expiry_end(d)
        if end and end < cutoff:
            removed.append(d.get("title", d.get("id", "?")))
        else:
            kept.append(d)

    if removed and not dry_run:
        for d in kept:
            d.pop("spotlight", None)
        if kept:
            kept[0]["spotlight"] = True
        doc["deals"] = kept
        doc["updated"] = agg.TODAY.isoformat()
        DATA.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
        build_pages.main()   # regenerate sitemap + per-deal/category pages, prune orphans
    return removed


def main():
    dry = "--dry-run" in sys.argv
    removed = prune(dry_run=dry)
    if removed:
        print(f"Retention GC: removed {len(removed)} deal(s) expired >{RETENTION_DAYS} days; "
              f"sitemap & pages rebuilt." + (" [dry-run — nothing written]" if dry else ""))
        for t in removed:
            print(f"   – {t}")
    else:
        print(f"Retention GC: nothing expired more than {RETENTION_DAYS} days ago. ✅")


if __name__ == "__main__":
    main()
