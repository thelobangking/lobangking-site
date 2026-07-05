#!/usr/bin/env python3
"""One-off: add EverydayOnSales active + upcoming lobangs and reclassify Giant
Durian as upcoming. Writes to both data/deals.json (built artifact the client
reads) and scripts/manual_deals.json (pipeline source so daily rebuilds keep
them). Idempotent: re-running updates in place, never duplicates."""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEALS = ROOT / "data" / "deals.json"
MANUAL = ROOT / "scripts" / "manual_deals.json"

EOS_UP = "https://sg.everydayonsales.com/sales-period/upcoming-sales/"
EOS_PROMO = "https://sg.everydayonsales.com/promotions-freebies/"
EOS_WH = "https://sg.everydayonsales.com/warehouse-sale/"
SRC = lambda u: {"name": "EverydayOnSales", "url": u}

# ---- UPCOMING lobangs (haven't started as of 2026-07-05) -------------------
UPCOMING = [
    {
        "id": "sushiro-myvillage-opening",
        "title": "1-for-1 sushi + grand-opening gifts",
        "store": "SUSHIRO · myVillage @ Serangoon Garden",
        "brand": "SUSHIRO", "categories": ["food"], "icon": "🍣",
        "badges": [{"type": "discount", "label": "1-FOR-1 SUSHI"}],
        "access": {"type": "easy", "label": "Dine-in — new outlet launch"},
        "desc": "SUSHIRO's newest outlet opens at myVillage @ Serangoon Garden with two weeks of 1-for-1 sushi — Bluefin Fatty Tuna, Fresh Salmon and Medium Fatty Tuna included — plus opening-day gifts and launch rewards.",
        "expiry": "7–20 Jul", "expires_at": "2026-07-20", "starts_at": "2026-07-07",
        "heat": 372, "url": EOS_UP, "source": SRC(EOS_UP),
        "image": "images/up-sushiro.jpg",
    },
    {
        "id": "popeyes-heartbeat-bucket",
        "title": "$11.50 4pc chicken + drink, every Tuesday",
        "store": "Popeyes · Islandwide",
        "brand": "Popeyes", "categories": ["food"], "icon": "🍗",
        "badges": [{"type": "discount", "label": "$11.50 TUESDAYS"}],
        "access": {"type": "easy", "label": "Selected Tuesdays · 11am–10pm"},
        "desc": "Popeyes' Singapore Heartbeat Bucket Set: 4 pieces of Signature Chicken with a Large Drink for only $11.50 every selected Tuesday — a National-Day-season treat that runs all the way to 25 August.",
        "expiry": "Tuesdays till 25 Aug", "expires_at": "2026-08-25", "starts_at": "2026-07-07",
        "heat": 340, "url": EOS_UP, "source": SRC(EOS_UP),
        "image": "images/up-popeyes-heartbeat.jpg",
    },
    {
        "id": "tangs-sulwhasoo-candle",
        "title": "Sulwhasoo candle workshop + $100 voucher",
        "store": "TANGS × Sulwhasoo · Tang Plaza",
        "brand": "TANGS", "categories": ["fashion"], "icon": "🕯️",
        "badges": [{"type": "free", "label": "$152 IN GIFTS"}],
        "access": {"type": "signup", "label": "Book a workshop slot"},
        "desc": "Craft a bespoke scented candle at the Sulwhasoo Candle Making Workshop (10–12 & 24–26 Jul) at TANGS Tang Plaza, and walk away with a $100 Sulwhasoo voucher plus a complimentary 3-piece gift worth $52.",
        "expiry": "10–26 Jul", "expires_at": "2026-07-26", "starts_at": "2026-07-10",
        "heat": 300, "url": EOS_UP, "source": SRC(EOS_UP),
        "image": "images/up-tangs-sulwhasoo.jpg",
    },
    {
        "id": "refash-go-green-market",
        "title": "Turn preloved fashion into eVouchers",
        "store": "REFASH · West Mall",
        "brand": "REFASH", "categories": ["fashion"], "icon": "♻️",
        "badges": [{"type": "free", "label": "EARN eVOUCHERS"}],
        "access": {"type": "easy", "label": "Walk-in — no appointment"},
        "desc": "Declutter your wardrobe at the REFASH Go Green Market — bring eligible preloved clothing, bags and wallets and receive West Mall eVouchers in return. Walk-in, no appointment needed, sustainable fashion for the win.",
        "expiry": "10–11 Jul", "expires_at": "2026-07-11", "starts_at": "2026-07-10",
        "heat": 286, "url": EOS_UP, "source": SRC(EOS_UP),
        "image": "images/up-refash.jpg",
    },
    {
        "id": "toysrus-football-sale",
        "title": "Up to 80% off toys + Panini trading",
        "store": "Toys“R”Us · Islandwide",
        "brand": "Toys“R”Us", "categories": ["entertainment"], "icon": "⚽",
        "badges": [{"type": "discount", "label": "UP TO 80% OFF"}],
        "access": {"type": "easy", "label": "In-store & online"},
        "desc": "The Toys“R”Us Football Sale brings up to 80% off selected toys plus a live Panini sticker trading event — a goal for parents, kids and collectors alike.",
        "expiry": "6–12 Jul", "expires_at": "2026-07-12", "starts_at": "2026-07-06",
        "heat": 312, "url": EOS_UP, "source": SRC(EOS_UP),
        "image": "images/up-toysrus.jpg",
    },
    {
        "id": "punggol-harmony-carnival",
        "title": "Free open-top bus tour + carnival fun",
        "store": "Punggol GRC · Punggol 21 CC",
        "brand": "Punggol GRC", "categories": ["entertainment"], "icon": "🎪",
        "badges": [{"type": "free", "label": "FREE ADMISSION"}],
        "access": {"type": "easy", "label": "Free entry — one day only"},
        "desc": "The Inter-Racial & Religious Harmony Carnival brings a FREE open-top bus Punggol tour, multicultural performances, kampong games, snacks and getai — a full, free family day out on 19 July.",
        "expiry": "19 Jul only", "expires_at": "2026-07-19", "starts_at": "2026-07-19",
        "heat": 268, "url": EOS_UP, "source": SRC(EOS_UP),
        "image": "images/up-punggol-carnival.jpg",
    },
    {
        "id": "orchard-hotel-nationalday-drinks",
        "title": "Local-inspired drinks from $6.10",
        "store": "Orchard Hotel Singapore",
        "brand": "Orchard Hotel", "categories": ["food"], "icon": "🥂",
        "badges": [{"type": "discount", "label": "FROM $6.10"}],
        "access": {"type": "easy", "label": "Available through August"},
        "desc": "Celebrate National Day at Orchard Hotel Singapore with a series of local-inspired drinks priced from $6.10 all through August — a nostalgic, wallet-friendly way to toast SG61.",
        "expiry": "Aug 2026", "expires_at": "2026-08-31", "starts_at": "2026-08-01",
        "heat": 258, "url": EOS_UP, "source": SRC(EOS_UP),
        "image": "images/up-orchard-hotel.jpg",
    },
]

# ---- NEW ACTIVE lobangs (already running) ----------------------------------
ACTIVE = [
    {
        "id": "goldlion-moving-out",
        "title": "Moving-out sale + free $10 voucher",
        "store": "GOLDLION · Moving-out sale",
        "brand": "GOLDLION", "categories": ["fashion"], "icon": "👔",
        "badges": [{"type": "free", "label": "FREE $10 VOUCHER"}],
        "access": {"type": "easy", "label": "In-store · no min spend voucher"},
        "desc": "GOLDLION's moving-out sale pairs a Spend-More-Save-More deal with a $10 cash voucher (no minimum spend) — quality menswear, leather goods and accessories before the store closes.",
        "expiry": "Ends 31 Jul", "expires_at": "2026-07-31", "starts_at": "",
        "heat": 244, "url": EOS_WH, "source": SRC(EOS_WH),
    },
    {
        "id": "moley-apparels-closing",
        "title": "30% off storewide — closing after 15 years",
        "store": "Moley Apparels · HarbourFront Centre",
        "brand": "Moley Apparels", "categories": ["fashion"], "icon": "🏷️",
        "badges": [{"type": "discount", "label": "30% OFF ALL"}],
        "access": {"type": "easy", "label": "In-store while it lasts"},
        "desc": "Moley Apparels bids farewell to its very first HarbourFront Centre store after 15 years — 30% off storewide during the moving-out sale before the doors close for good.",
        "expiry": "Ends 26 Jul", "expires_at": "2026-07-26", "starts_at": "",
        "heat": 230, "url": EOS_WH, "source": SRC(EOS_WH),
    },
    {
        "id": "kei-kaisendon-premium-set",
        "title": "Premium Kaisendon set from $22.95++",
        "store": "Kei Kaisendon",
        "brand": "Kei Kaisendon", "categories": ["food"], "icon": "🍥",
        "badges": [{"type": "discount", "label": "FROM $22.95++"}],
        "access": {"type": "easy", "label": "Dine-in"},
        "desc": "Kei Kaisendon's Premium Set Meal: an authentic Japanese kaisendon served with side dishes and a drink for $22.95++ (usual $24.95++) — a worthwhile treat for seafood lovers.",
        "expiry": "While stocks last", "expires_at": "", "starts_at": "",
        "heat": 210, "url": EOS_PROMO, "source": SRC(EOS_PROMO),
    },
]

FIRST_SEEN = "2026-07-05"


def normalise(d, upcoming):
    d = dict(d)
    d.setdefault("first_seen", FIRST_SEEN)
    d["upcoming"] = upcoming
    d.setdefault("starts_at", "")
    return d


def merge(store_deals):
    by_id = {d["id"]: i for i, d in enumerate(store_deals)}
    # Reclassify existing Giant Durian → upcoming, give it a unique image.
    if "giant-durian-buffet" in by_id:
        g = store_deals[by_id["giant-durian-buffet"]]
        g["upcoming"] = True
        g["starts_at"] = "2026-07-18"
        g["expiry"] = "18–19 Jul"
        g["expires_at"] = "2026-07-19"
        g["image"] = "images/up-giant-durian.jpg"
    for d in UPCOMING:
        nd = normalise(d, True)
        if d["id"] in by_id:
            store_deals[by_id[d["id"]]] = nd
        else:
            store_deals.append(nd)
    for d in ACTIVE:
        nd = normalise(d, False)
        if d["id"] in by_id:
            store_deals[by_id[d["id"]]] = nd
        else:
            store_deals.append(nd)
    return store_deals


# data/deals.json — dict with "deals" list
dj = json.loads(DEALS.read_text(encoding="utf-8"))
dj["deals"] = merge(dj["deals"])
# refresh brands_today / brands_tracked lightly
brands = sorted({d["brand"] for d in dj["deals"] if d.get("brand")})
dj["brands_today"] = brands
tracked = set(dj.get("brands_tracked") or [])
tracked.update(brands)
dj["brands_tracked"] = sorted(tracked)
DEALS.write_text(json.dumps(dj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# scripts/manual_deals.json — dict with "deals" list
mj = json.loads(MANUAL.read_text(encoding="utf-8"))
mj["deals"] = merge(mj["deals"])
MANUAL.write_text(json.dumps(mj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

up = [d for d in dj["deals"] if d.get("upcoming")]
print(f"deals.json now {len(dj['deals'])} deals · {len(up)} upcoming")
for d in up:
    print("  ↑", d["id"], "starts", d["starts_at"], "→", d["expires_at"])
