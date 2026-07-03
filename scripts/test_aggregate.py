#!/usr/bin/env python3
"""
Offline sanity test for aggregate_deals.py — no network required.
Feeds a small sample RSS document (mirroring real Singapore deal feeds)
through the parser and checks categorisation, expiry-dropping, badges and
de-duplication. Run with:  python3 scripts/test_aggregate.py
"""
import datetime
import aggregate_deals as agg

# Pin "today" so the expiry test is deterministic.
agg.TODAY = datetime.date(2026, 6, 30)

SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>Sample Deals</title>
  <item>
    <title>Mr Bean S'pore 1-for-1 Soy Drinks Promotion on Sunday, 28 June 2026</title>
    <link>https://singpromos.com/dining-restaurants-food/mr-bean-1for1-303731/</link>
    <description>Two refreshing soy drinks for the price of one [ Read more at SINGPROMOS.COM ]</description>
    <category>Dining</category>
  </item>
  <item>
    <title>Popeyes S'pore 1-for-1 Midnight Crunch Combo Meal from 29 Jun - 3 Jul 2026</title>
    <link>https://singpromos.com/dining-restaurants-food/popeyes-303721/</link>
    <description>A value-packed late-night chicken feast</description>
  </item>
  <item>
    <title>Steam Summer Sale 2026 now on till 9 Jul 2026</title>
    <link>https://singpromos.com/video-games/steam-summer-sale-303701/</link>
    <description>Score massive savings on blockbuster PC games</description>
  </item>
  <item>
    <title>RHB Bank Singapore FD Promo Rates now up to 1.55% p.a. from 25 Jun 2026</title>
    <link>https://singpromos.com/banks-credit-cards/rhb-fd-303677/</link>
    <description>Higher short-term SGD fixed deposit rates with a S$20,000 minimum placement.</description>
  </item>
  <item>
    <title>Grab S'pore $5 Off 3 Rides with code GOKING till 5 Jul 2026</title>
    <link>https://singpromos.com/motor-vehicles/grab-303600/</link>
    <description>Enter promo code GOKING in the Grab app.</description>
  </item>
  <item>
    <title>Scoot S'pore $99 Return Flights to Bangkok till 5 Jul 2026</title>
    <link>https://singpromos.com/travel/scoot-bangkok-303500/</link>
    <description>All-in return fares on selected dates.</description>
  </item>
  <item>
    <title>Popeyes S'pore 1-for-1 Midnight Crunch Combo Meal from 29 Jun - 3 Jul 2026</title>
    <link>https://singpromos.com/dining-restaurants-food/popeyes-DUP/</link>
    <description>Duplicate of the Popeyes deal — should be removed.</description>
  </item>
</channel></rss>"""

records = agg.parse_feed(SAMPLE.encode())
assert len(records) == 7, f"expected 7 raw records, got {len(records)}"

deals = [d for d in (agg.deal_from_record(r, "SINGPromos") for r in records) if d]

# Expired Mr Bean (28 Jun < 30 Jun) must be dropped -> 6 remain (incl. duplicate)
titles = [d["title"] for d in deals]
assert not any("Mr Bean" in t for t in titles), "expired deal was not dropped"

# De-dup by title
seen, unique = set(), []
for d in deals:
    k = "".join(ch for ch in d["title"].lower() if ch.isalnum())[:50]
    if k not in seen:
        seen.add(k); unique.append(d)
assert sum("Popeyes" in d["title"] for d in unique) == 1, "duplicate not removed"

by_store = {d["store"]: d for d in unique}
checks = {
    "Popeyes": "food",
    "Steam Summer Sale 2026 now on": "entertainment",
    "RHB Bank": "finance",
    "Grab": "transport",
    "Scoot": "travel",
}

print("Parsed deals:")
for d in unique:
    print(f"  [{d['categories'][0]:13}] {d['store']:28} | {d['expiry']:16} | "
          f"{', '.join(b['label'] for b in d['badges'])}")

# Category assertions
cat_by_store = {d["store"]: d["categories"][0] for d in unique}
problems = []
for store_frag, expect in checks.items():
    match = next((c for s, c in cat_by_store.items() if store_frag.split()[0] in s), None)
    if match != expect:
        problems.append(f"{store_frag}: expected {expect}, got {match}")

# Grab deal should carry the promo code + a code badge
grab = next((d for d in unique if "Grab" in d["store"]), None)
assert grab and grab.get("code") == "GOKING", "promo code not extracted"
assert any(b["type"] == "discount" and "1-FOR-1" in b["label"]
           for d in unique if "Popeyes" in d["store"] for b in d["badges"]), "1-for-1 badge missing"

if problems:
    print("\nFAIL:")
    for p in problems:
        print("  -", p)
    raise SystemExit(1)

# Brand detection across the watchlist
brand_cases = {
    "IKEA Singapore kids eat free this July": "IKEA",
    "Don Don Donki opens new outlet with opening deals": "Don Don Donki",
    "Uniqlo Singapore AIRism sale up to 40% off": "Uniqlo",
    "McDonald's S'pore $9.90 chicken deal": "McDonald's",
    "Charles & Keith bags 30% off online": "Charles & Keith",
    "Universal Studios Singapore ticket promo": "Universal Studios Singapore",
    "Singapore Zoo family pass discount": "Singapore Zoo",
    "A random restaurant promo with no tracked brand": None,
}
bproblems = []
for text, expect in brand_cases.items():
    got = agg.detect_brand(text)
    if got != expect:
        bproblems.append(f"{text!r}: expected {expect}, got {got}")
# false-positive guard: 'pineapple tart' must not match Apple
if agg.detect_brand("pineapple tart promotion"):
    bproblems.append("'pineapple' wrongly matched a brand")

if bproblems:
    print("\nBRAND FAIL:")
    for p in bproblems:
        print("  -", p)
    raise SystemExit(1)

# AI enrichment must be a safe no-op when not configured (no API creds in env)
import ai_enrich
_sample = [{"id": "x", "title": "T", "desc": "D", "categories": ["food"]}]
assert ai_enrich.enrich(_sample, {"enabled": True}) == _sample, "AI enrich must not alter deals when unconfigured"
assert ai_enrich.enrich(_sample, {}) == _sample, "AI enrich must no-op when disabled"

print("\n✅ All checks passed: parsing, expiry-drop, dedupe, categories, code, badges, brand detection & AI no-op.")
