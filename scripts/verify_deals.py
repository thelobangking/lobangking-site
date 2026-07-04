#!/usr/bin/env python3
"""
verify_deals.py — pre-display deal verifier (freshness + validity gate)
=======================================================================

The daily aggregator collects deals; THIS script is the gate that decides which
of them are still trustworthy enough to show. It runs AFTER aggregation and
BEFORE the pages are built, so the site only ever pre-renders verified, current
deals. It also runs hourly (via validate.py) so nothing goes stale between the
daily builds.

Why it exists
-------------
The aggregator only drops a deal when it can parse an explicit DAY + MONTH that
has passed (e.g. "Ends 12 Apr"). Real listings are messier:

  • "IKEA April promotion"  → month only, no day  → the old code gave it NO end
    date, so it was treated as "ongoing" and shown for months after April ended.
  • "Ends 2 Jul" once 2 Jul passes                → expired.
  • A deal with no date at all                     → could linger forever.

verify_deals.py closes all three gaps. For every deal it decides KEEP or DROP:

  1. EXPIRED — an explicit end date (day+month) is in the past.               DROP
  2. MONTH PASSED — the deal names a month (optionally a year) whose last day
     is before today, and it isn't phrased as a start ("from April").         DROP
  3. STALE — the deal has NO usable end date and was first seen more than
     MAX_AGE_DAYS ago (safety net for undated promos that never expire).      DROP
  4. UNVERIFIABLE — no real source link AND no promotional signal at all
     (price / % / 1-for-1 / promo code / free …). Nothing to trust.           DROP
  Otherwise                                                                    KEEP

First-seen memory
-----------------
Deals carry no age of their own and the aggregator rewrites data/deals.json each
run, so we keep a tiny sidecar, data/seen.json  ({deal_id: "YYYY-MM-DD"}), that
survives rewrites and lets rule #3 measure how long a deal has been around.

Reuses aggregate_deals.parse_expiry + PROMO_KEYWORDS + MONTHS (single source of
truth) and build_pages for the optional rebuild. Standard library only.

Usage
-----
  python3 scripts/verify_deals.py                 # verify + write cleaned deals.json
  python3 scripts/verify_deals.py --dry-run       # report only, change nothing
  python3 scripts/verify_deals.py --rebuild       # also rebuild HTML/feed/sitemap
  python3 scripts/verify_deals.py --max-age 45    # override the stale cutoff (days)

Or import and call verify(...) — that's what the hourly validator does.
"""
import sys
import re
import json
import calendar
import pathlib
import datetime

import aggregate_deals as agg   # parse_expiry, PROMO_KEYWORDS, MONTHS, TODAY

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "deals.json"
SEEN = ROOT / "data" / "seen.json"

# A deal with no parseable end date is dropped once it's older than this many
# days (measured from when we first saw it). Long enough for genuine evergreen
# promos to stay, short enough that abandoned listings don't pile up.
MAX_AGE_DAYS = 45
# How long to remember a deal id in seen.json after it disappears (housekeeping).
SEEN_TTL_DAYS = 120

# Month-name → number, reused from the aggregator so the two stay consistent.
_MONTHS = agg.MONTHS
_MONTH_RE = re.compile(
    r"(?<![a-z])(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*(\d{4})?",
    re.I,
)
# Words right before a month that mean it's a START, not an expiry ("from April").
_START_BEFORE = re.compile(
    r"(from|since|starting|start|effective|launched?|launching|begins?|began|"
    r"available\s+from|valid\s+from|fr\.?|w\.e\.f\.?)\s*$",
    re.I,
)


def _last_day(year: int, month: int) -> datetime.date:
    return datetime.date(year, month, calendar.monthrange(year, month)[1])


def month_only_expiry(text: str, ref: datetime.date):
    """Latest end-of-month implied by a MONTH-ONLY reference (no explicit day).

    Anchored to `ref` (the date we first saw the deal): a bare month resolves to
    the occurrence nearest that date, so "April" seen in Apr 2026 → 30 Apr 2026.
    References phrased as a start ("from April") are ignored. Returns a date or
    None. The LATEST qualifying month wins (most lenient), so a deal valid
    "through September" isn't killed by an earlier month it also mentions.
    """
    best = None
    for m in _MONTH_RE.finditer(text):
        mon = _MONTHS.get(m.group(1).lower()[:3])
        if not mon:
            continue
        # Skip if this reads as a start date rather than an end date.
        if _START_BEFORE.search(text[:m.start()]):
            continue
        yr = m.group(2)
        if yr:
            end = _last_day(int(yr), mon)
        else:
            # No year given: resolve to the FIRST occurrence of this month on or
            # after (ref - 45d). This anchors a bare month to the promo's active
            # window and biases toward keeping — we never resolve to a month that
            # passed long before we saw the deal (which would drop it wrongly).
            anchor = ref - datetime.timedelta(days=45)
            end = _last_day(anchor.year, mon)
            if end < anchor:
                end = _last_day(anchor.year + 1, mon)
        if best is None or end > best:
            best = end
    return best


def effective_end(deal: dict, first_seen: datetime.date):
    """The deal's real end date, or None if it's genuinely open-ended.

    Tries the shared day+month parser first; falls back to a month-only match.
    """
    blob = f"{deal.get('title','')} {deal.get('desc','')} {deal.get('expiry','')}"
    _, end = agg.parse_expiry(blob)
    if end:
        return end
    return month_only_expiry(blob, first_seen)


def has_deal_signal(deal: dict) -> bool:
    """Does the deal carry any promotional signal we can stand behind?"""
    blob = f"{deal.get('title','')} {deal.get('desc','')}".lower()
    if any(k in blob for k in agg.PROMO_KEYWORDS):
        return True
    # A badge other than the generic NEW/brand tag also counts as a signal.
    for b in deal.get("badges", []):
        if b.get("type") in ("discount", "free", "code"):
            return True
    return False


def has_real_link(deal: dict) -> bool:
    url = str(deal.get("url", "") or deal.get("source", {}).get("url", ""))
    return bool(re.match(r"^https?://", url, re.I)) and url not in ("#", "")


def _load_seen() -> dict:
    if SEEN.exists():
        try:
            return json.loads(SEEN.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — corrupt sidecar must never break a build
            return {}
    return {}


def _iso(d: datetime.date) -> str:
    return d.isoformat()


def _parse_iso(s: str, fallback: datetime.date) -> datetime.date:
    try:
        return datetime.date.fromisoformat(s[:10])
    except Exception:  # noqa: BLE001
        return fallback


def verify(dry_run: bool = False, rebuild: bool = False,
           max_age: int = MAX_AGE_DAYS, editors_exempt: bool = True):
    """Filter data/deals.json down to verified, current deals.

    Returns a list of (title, reason) for every deal removed. Writes the cleaned
    deals.json (and updates seen.json) unless dry_run. When rebuild=True and
    something changed, regenerates the HTML/feed/sitemap so pages stay in sync.
    """
    if not DATA.exists():
        return []
    doc = json.loads(DATA.read_text(encoding="utf-8"))
    deals = doc.get("deals", [])
    today = agg.TODAY

    seen = _load_seen()
    kept, removed = [], []

    for d in deals:
        did = str(d.get("id") or "")
        first_seen = _parse_iso(seen.get(did, ""), today) if did in seen else today
        if did:
            seen[did] = _iso(first_seen)          # remember first sighting
        d["first_seen"] = _iso(first_seen)         # stamp onto the deal for transparency

        is_editor = editors_exempt and (d.get("source", {}) or {}).get("name") == "Editor's pick"
        end = effective_end(d, first_seen)
        age = (today - first_seen).days
        src = d.get("source", {}) or {}
        blob = f"{d.get('title','')} {d.get('desc','')} {d.get('expiry','')}"

        reason = None
        # Blocked publisher (setlui, alvinology, …) — shared list with the aggregator.
        if agg.is_blocked_source(src.get("name"), src.get("url"), d.get("url")) and not is_editor:
            reason = f"blocked source — {src.get('name','?')}"
        # Present-year gate: drop anything dated to a previous year.
        elif end and end.year < agg.CURRENT_YEAR:
            reason = f"expired — ended {end.day} {end.strftime('%b %Y')}"
        elif agg.mentions_past_year(blob) and not is_editor:
            reason = "past year — copy references a bygone year"
        elif end and end < today:
            reason = f"expired — ended {end.day} {end.strftime('%b %Y')}"
        elif end is None and age > max_age and not is_editor:
            reason = f"stale — no end date and unseen-fresh for {age} days"
        elif not has_real_link(d) and not has_deal_signal(d) and not is_editor:
            reason = "unverifiable — no source link and no deal signal"

        if reason:
            removed.append((d.get("title", did or "?"), reason))
        else:
            kept.append(d)

    # Order newest-first. first_seen is day-granular, so equal-day deals keep the
    # aggregator's order (a stable sort) as the within-day tiebreak. This makes
    # "most recent" the site's natural order and puts the latest deal on top.
    kept.sort(key=lambda d: d.get("first_seen", ""), reverse=True)

    # The single spotlight is now simply the newest deal (not a curated pick).
    for d in kept:
        d.pop("spotlight", None)
    if kept:
        kept[0]["spotlight"] = True
    doc["deals"] = kept
    doc["brands_today"] = sorted({d["brand"] for d in kept if d.get("brand")})
    doc["updated"] = _iso(today)

    # Housekeeping: forget ids we haven't seen in a long time so seen.json stays small.
    live_ids = {str(d.get("id")) for d in kept}
    cutoff = today - datetime.timedelta(days=SEEN_TTL_DAYS)
    seen = {k: v for k, v in seen.items()
            if k in live_ids or _parse_iso(v, today) >= cutoff}

    if not dry_run:
        # Always rewrite: even with nothing removed we persist first_seen, the
        # newest-first ordering, and the refreshed spotlight/summary fields.
        DATA.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
        SEEN.parent.mkdir(parents=True, exist_ok=True)
        SEEN.write_text(json.dumps(seen, indent=2, ensure_ascii=False), encoding="utf-8")
        if rebuild and removed:
            try:
                import build_pages
                build_pages.main()
            except Exception as e:  # noqa: BLE001 — never let a rebuild error lose the data fix
                print(f"  ! rebuild skipped: {type(e).__name__}: {e}")

    return removed


def main():
    dry = "--dry-run" in sys.argv
    rebuild = "--rebuild" in sys.argv
    max_age = MAX_AGE_DAYS
    if "--max-age" in sys.argv:
        try:
            max_age = int(sys.argv[sys.argv.index("--max-age") + 1])
        except (ValueError, IndexError):
            pass

    print(f"verify_deals.py — {agg.TODAY.isoformat()}  "
          f"(dry-run={dry}, rebuild={rebuild}, max-age={max_age}d)")
    removed = verify(dry_run=dry, rebuild=rebuild, max_age=max_age)
    if removed:
        print(f"Removed {len(removed)} unverified/expired deal(s):")
        for title, reason in removed:
            print(f"  ✗ {title[:60]}  —  {reason}")
    else:
        print("All deals verified current. Nothing removed.")
    print(f"{'[dry-run] ' if dry else ''}done.")


if __name__ == "__main__":
    main()
