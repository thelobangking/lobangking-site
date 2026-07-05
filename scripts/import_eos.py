#!/usr/bin/env python3
"""One-off importer: review current EverydayOnSales promotions and add the
non-expired, non-duplicate ones into the curated deal set.

Source page: https://sg.everydayonsales.com/promotions-freebies/ (fetched 2026-07-05)

The script "reviews each post": it re-parses every candidate's validity dates
through the SAME parse_expiry the site uses, DROPS anything already expired,
DROPS anything that duplicates a deal already on the site, and writes the
survivors into BOTH scripts/manual_deals.json (persistent curated source) and
data/deals.json (the live build input) without touching the deals already there.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from aggregate_deals import parse_expiry, TODAY  # single source of truth

MANUAL_FILE = HERE / "manual_deals.json"
DATA_FILE = ROOT / "data" / "deals.json"
SRC = {"name": "EverydayOnSales", "url": "https://sg.everydayonsales.com/promotions-freebies/"}
PAGE = SRC["url"]

# Candidate posts transcribed from the fetched listing. Descriptions are kept
# free of "DD Month" tokens on purpose; the validity lives only in `expiry` so
# parse_expiry reads exactly one end date (or none, for ongoing offers).
CANDIDATES = [
    {
        "id": "sukiya-shrimp-miso", "title": "Shrimp Ball Miso Soup from $2.90",
        "store": "SUKIYA · All 30 halal outlets", "brand": "SUKIYA",
        "categories": ["food"], "icon": "🍲",
        "badges": [{"type": "discount", "label": "FROM $2.90"}],
        "access": {"type": "easy", "label": "Dine-in at all outlets islandwide"},
        "desc": "New Shrimp Ball Miso Soup for a limited time — order it on its own or upgrade any regular miso soup for just $2.90. Available at all 30 Halal-certified SUKIYA outlets.",
        "expiry": "While stocks last",
    },
    {
        "id": "takagi-ramen-1for1-ndp", "title": "Ultimate 1-for-1 ramen & rice bowls",
        "store": "Takagi Ramen · Delivery & outlets", "brand": "Takagi Ramen",
        "categories": ["food"], "icon": "🍜",
        "badges": [{"type": "discount", "label": "1-FOR-1"}],
        "access": {"type": "app", "label": "GrabFood, Foodpanda or order direct"},
        "desc": "NDP-season Ultimate 1-for-1 on selected ramen and rice bowls — great-value Japanese comfort food via GrabFood, Foodpanda or direct ordering.",
        "expiry": "While stocks last",
    },
    {
        "id": "yellowribbon-hellokitty-plush", "title": "Win a Hello Kitty x Yellow Ribbon 50th plush",
        "store": "Yellow Ribbon Singapore · Giveaway", "brand": "Yellow Ribbon",
        "categories": ["entertainment"], "icon": "🎁",
        "badges": [{"type": "free", "label": "FREE GIVEAWAY"}],
        "access": {"type": "easy", "label": "Share your story to enter"},
        "desc": "For its 50th Anniversary, Yellow Ribbon Singapore is giving away an exclusive Hello Kitty collectible plush. Share a thank-you story to someone who believed in you for a chance to win.",
        "expiry": "Ends 31 Jul",
    },
    {
        "id": "kennyrogers-670-meals", "title": "$6.70 rice or pasta meals islandwide",
        "store": "Kenny Rogers Roasters · Islandwide", "brand": "Kenny Rogers Roasters",
        "categories": ["food"], "icon": "🍗",
        "badges": [{"type": "discount", "label": "$6.70 MEALS"}],
        "access": {"type": "easy", "label": "Selected outlets & online ordering"},
        "desc": "Rice or pasta meals for just $6.70 each — an easy, wallet-friendly lunch or dinner at selected Kenny Rogers Roasters outlets islandwide and via online ordering.",
        "expiry": "While stocks last",
    },
    {
        "id": "welcia-kose-beauty", "title": "Up to 50% off KOSE beauty + free gifts",
        "store": "Welcia · KOSE brands", "brand": "Welcia",
        "categories": ["fashion"], "icon": "💄",
        "badges": [{"type": "discount", "label": "UP TO 50% OFF"}],
        "access": {"type": "easy", "label": "In-store at Welcia outlets"},
        "desc": "Up to 50% off selected KOSE beauty brands including SEKKISEI, ONE BY KOSÉ and FASIO, plus exclusive SEKKISEI x Monchhichi gifts, foldable bags and deluxe samples with qualifying purchases.",
        "expiry": "While stocks last",
    },
    {
        "id": "hp-double7-savings", "title": "Double 7: up to $120 off HP laptops & printers",
        "store": "HP Singapore Online Store", "brand": "HP",
        "categories": ["electronics"], "icon": "💻",
        "badges": [{"type": "discount", "label": "UP TO $120 OFF"}],
        "access": {"type": "easy", "label": "Sitewide vouchers at HP online store"},
        "desc": "HP's Double 7 sale: sitewide vouchers worth up to $120 off selected HP AI laptops, workstations, printers and accessories. Upgrade your tech for less while the offer lasts.",
        "expiry": "While stocks last",
    },
    {
        "id": "giant-durian-buffet", "title": "Unlimited durian buffet at Giant Tampines",
        "store": "Giant · Tampines Hypermarket", "brand": "Giant",
        "categories": ["food"], "icon": "🍈",
        "badges": [{"type": "discount", "label": "EARLY-BIRD DEAL"}],
        "access": {"type": "easy", "label": "Book ahead for early-bird pricing"},
        "desc": "Giant's popular Durian Buffet Party returns to Giant Tampines Hypermarket — unlimited fresh durians with complimentary fresh coconut and tropical fruits. Book ahead to lock in early-bird pricing.",
        "expiry": "Ends 19 Jul",
    },
    {
        "id": "sothys-july-skincare", "title": "10% off + gifts worth up to $106",
        "store": "Sothys Singapore", "brand": "Sothys",
        "categories": ["fashion"], "icon": "🧴",
        "badges": [{"type": "discount", "label": "10% OFF + GIFTS"}],
        "access": {"type": "easy", "label": "In-store & online while stocks last"},
        "desc": "Sothys July skincare offers: the new MultiVit range, complimentary gifts worth up to $106, limited-edition cleansing sets, anti-ageing offers and 10% off selected favourites.",
        "expiry": "While stocks last",
    },
    {
        "id": "harbourfront-summer-popup", "title": "Free selfie-mirror pop-up experience",
        "store": "HarbourFront Centre · Pop-up", "brand": "HarbourFront Centre",
        "categories": ["entertainment"], "icon": "🎡",
        "badges": [{"type": "free", "label": "FREE ACTIVITY"}],
        "access": {"type": "easy", "label": "Drop by the mall pop-up"},
        "desc": "A creative summer pop-up with a fun selfie-mirror personalisation activity — a simple, free, hands-on mall experience for families, shoppers and commuters.",
        "expiry": "Ends 26 Jul",
    },
    {
        "id": "kfc-drivethru-voucher", "title": "Free decal + $5 voucher, no min spend",
        "store": "KFC · Drive-Thru outlets", "brand": "KFC",
        "categories": ["food"], "icon": "🍗",
        "badges": [{"type": "free", "label": "FREE $5 VOUCHER"}],
        "access": {"type": "easy", "label": "Islandwide Drive-Thru, no min spend"},
        "desc": "KFC Drive-Thru freebie: a free decal and a $5 voucher with no minimum spend, at islandwide Drive-Thru outlets while stocks last.",
        "expiry": "While stocks last",
    },
    {
        "id": "zenyum-sonic2-50off", "title": "50% off ZenyumSonic 2.0 (now $59.90)",
        "store": "Zenyum Singapore", "brand": "Zenyum",
        "categories": ["electronics"], "icon": "🪥",
        "badges": [{"type": "discount", "label": "50% OFF"}],
        "access": {"type": "easy", "label": "Online at Zenyum SG"},
        "desc": "Half price on the ZenyumSonic 2.0 smart sonic toothbrush — smarter oral care for just $59.90.",
        "expiry": "Ends 12 Jul",
    },
    {
        "id": "panasonic-grooming-10off", "title": "10% off shavers & hair dryers + extra 5%",
        "store": "Panasonic Singapore · Online", "brand": "Panasonic",
        "categories": ["electronics"], "icon": "🪒",
        "badges": [{"type": "code", "label": "CODE: PANASAF26"}],
        "access": {"type": "easy", "label": "Online — apply code PANASAF26"},
        "desc": "10% off selected Panasonic shavers and hair dryers, with an extra 5% off when you buy more than one. Apply promo code PANASAF26 at checkout.",
        "expiry": "Ends 15 Jul",
    },
]


def norm(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())[:50]


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    manual = load(MANUAL_FILE)
    data = load(DATA_FILE)
    man_deals = manual["deals"]
    live_deals = data["deals"]

    # Build dedup index from EVERYTHING already known.
    known_ids = {d.get("id") for d in man_deals} | {d.get("id") for d in live_deals}
    known_titles = {norm(d.get("title")) for d in man_deals} | {norm(d.get("title")) for d in live_deals}

    added, skipped_dup, skipped_exp = [], [], []
    heat = 372  # slot new deals in the upper cluster, below the #380 spotlight

    for c in CANDIDATES:
        label, end = parse_expiry(f"{c['title']} {c['desc']} {c['expiry']}")
        # 1) reject expired
        if end is not None and end < TODAY:
            skipped_exp.append((c["title"], label))
            continue
        # 2) reject duplicates already on the site
        if c["id"] in known_ids or norm(c["title"]) in known_titles:
            skipped_dup.append(c["title"])
            continue
        deal = dict(c)
        deal["heat"] = 0
        deal["url"] = PAGE
        deal["source"] = dict(SRC)
        deal["first_seen"] = TODAY.isoformat()
        deal["expires_at"] = end.isoformat() if end else ""

        man_deals.append(dict(deal))                 # persistent copy (heat 0)
        live = dict(deal); live["heat"] = heat; heat -= 3
        live_deals.append(live)                      # live copy with ranking heat

        known_ids.add(c["id"]); known_titles.add(norm(c["title"]))
        added.append((c["title"], deal["expiry"], deal["expires_at"] or "ongoing"))

    # Re-sort the live set by heat so fresh deals interleave properly.
    live_deals.sort(key=lambda d: d.get("heat", 0), reverse=True)
    data["updated"] = TODAY.isoformat()
    # Keep the brand list in sync for any UI that reads it.
    if "brands" in data:
        data["brands"] = sorted({d["brand"] for d in live_deals if d.get("brand")})

    MANUAL_FILE.write_text(json.dumps(manual, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Reviewed {len(CANDIDATES)} posts from EverydayOnSales (today = {TODAY.isoformat()})")
    print(f"\n✓ ADDED {len(added)}:")
    for t, exp, ea in added:
        print(f"    + {t}  [{exp} → {ea}]")
    print(f"\n• SKIPPED {len(skipped_dup)} already on site:")
    for t in skipped_dup:
        print(f"    = {t}")
    print(f"\n• SKIPPED {len(skipped_exp)} expired:")
    for t, label in skipped_exp:
        print(f"    ✗ {t}  [{label}]")
    print(f"\nLive deals.json now has {len(live_deals)} deals; manual_deals.json has {len(man_deals)}.")


if __name__ == "__main__":
    main()
