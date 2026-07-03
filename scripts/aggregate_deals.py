#!/usr/bin/env python3
"""
aggregate_deals.py — LobangKing.sg automated deal aggregator
============================================================

Pulls deals from CONFIGURED, LEGITIMATE sources and writes data/deals.json.
Run automatically by .github/workflows/update-deals.yml on a daily schedule.

Dependency-free: uses only the Python standard library (no `pip install`).

Sources
-------
1. RSS feeds of established Singapore deal publishers (scripts/sources.json).
2. Per-BRAND Google News RSS — tracks the brands you care about (IKEA, Donki,
   Uniqlo, McDonald's, etc.) across Singapore news & deal coverage. Each item
   links back to the ORIGINAL article (attribution preserved).
3. Optional Involve Asia affiliate API (merchant-authorised; earns commission).

Design principle: the script NEVER fabricates a deal. Every entry comes from a
real fetched item and carries its source URL so it can be verified.
"""

import os
import re
import json
import html
import hashlib
import datetime
import pathlib
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import concurrent.futures
import ai_enrich

# ----------------------------------------------------------------------------
# Paths & constants
# ----------------------------------------------------------------------------
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_FILE = ROOT / "data" / "deals.json"
SOURCES_FILE = HERE / "sources.json"
MANUAL_FILE = HERE / "manual_deals.json"

TODAY = datetime.date.today()
USER_AGENT = "LobangKingBot/1.0 (+https://lobangking.sg; daily deal aggregator)"

CATEGORIES = [
    {"id": "all",           "label": "All Deals",        "icon": "🔥"},
    {"id": "food",          "label": "Food & Drinks",    "icon": "🍜"},
    {"id": "electronics",   "label": "Electronics",      "icon": "💻"},
    {"id": "home",          "label": "Home & Living",    "icon": "🏠"},
    {"id": "travel",        "label": "Travel",           "icon": "✈️"},
    {"id": "transport",     "label": "Transport",        "icon": "🚗"},
    {"id": "fashion",       "label": "Fashion & Beauty", "icon": "👗"},
    {"id": "entertainment", "label": "Fun & Leisure",    "icon": "🎮"},
    {"id": "finance",       "label": "Finance",          "icon": "💳"},
    {"id": "online",        "label": "Online Shopping",  "icon": "🛒"},
]
CATEGORY_ICONS = {c["id"]: c["icon"] for c in CATEGORIES}

# Brands to track. Each canonical name maps to match aliases (word-boundary matched).
# A deal's brand is recorded and used to boost it so brand coverage stays strong.
BRANDS = {
    "IKEA": ["ikea"],
    "Don Don Donki": ["don don donki", "don don donki", "donki", "dondonki"],
    "Muji": ["muji"],
    "Uniqlo": ["uniqlo"],
    "Adidas": ["adidas"],
    "Nike": ["nike"],
    "Charles & Keith": ["charles & keith", "charles and keith", "charles keith", "charleskeith"],
    "Ya Kun": ["ya kun", "yakun"],
    "McDonald's": ["mcdonald", "mcdonald's", "mcdonalds"],
    "Starbucks": ["starbucks"],
    "Chagee": ["chagee", "cha gee"],
    "Apple": ["apple"],
    "Lenovo": ["lenovo"],
    "Secretlab": ["secretlab", "secret lab"],
    "Universal Studios Singapore": ["universal studios", "uss", "rws"],
    "Singapore Zoo": ["singapore zoo", "mandai", "night safari", "river wonders", "bird paradise", "zoo"],
}

# Maps a brand to its most natural category (used when a brand deal is otherwise ambiguous)
BRAND_CATEGORY = {
    "IKEA": "home", "Don Don Donki": "online", "Muji": "home", "Uniqlo": "fashion",
    "Adidas": "fashion", "Nike": "fashion", "Charles & Keith": "fashion", "Ya Kun": "food",
    "McDonald's": "food", "Starbucks": "food", "Chagee": "food", "Apple": "electronics",
    "Lenovo": "electronics", "Secretlab": "home", "Universal Studios Singapore": "entertainment",
    "Singapore Zoo": "entertainment",
}

# Keep brand-news items only if they look promotional (not generic corporate news)
PROMO_KEYWORDS = [
    "deal", "promo", "promotion", "sale", "discount", " off", "offer", "free", "1-for-1",
    "1 for 1", "voucher", "bundle", "launch", "new menu", "giveaway", "%", "cashback",
    "$", "save", "buy 1", "bogo", "members",
]

SLUG_HINTS = {
    "dining-restaurants-food": "food", "food": "food", "groceries": "food", "grocery": "food",
    "supermarket": "food", "dining": "food", "banks-credit-cards": "finance", "banking": "finance",
    "insurance": "finance", "credit-cards": "finance", "motor-vehicles": "transport",
    "transport": "transport", "petrol": "transport", "video-games": "entertainment",
    "movies": "entertainment", "events": "entertainment", "attractions": "entertainment",
    "gaming": "entertainment", "electronics": "electronics", "mobile": "electronics",
    "computers": "electronics", "it-gadgets": "electronics", "travel": "travel", "hotels": "travel",
    "flights": "travel", "health-beauty": "fashion", "beauty": "fashion", "fashion": "fashion",
    "apparel": "fashion", "home": "home", "furniture": "home", "home-living": "home",
    "web-hosting": "online", "shopping": "online", "online": "online", "e-commerce": "online",
}

CATEGORY_RULES = [
    ("finance", ["bank", "dbs", "posb", "ocbc", "uob", "citi", "maybank", "credit card",
                 "cashback", "fixed deposit", " fd ", "time deposit", "p.a.", "interest rate",
                 "insurance", "savings account", "miles", "loan"]),
    ("travel", ["flight", "airline", "scoot", "singapore airlines", " sia ", "klook", "kkday",
                "trip.com", "agoda", "hotel", "staycation", "cruise", "resort", "holiday",
                "getaway", "expedia", "booking.com", "airbnb", "traveloka", "esim", "roaming"]),
    ("transport", ["grab", "gojek", "tada", "taxi", "comfortdelgro", "mrt", "ez-link",
                   "petrol", "fuel", "esso", "shell ", "parking", "ride"]),
    ("entertainment", ["movie", "cinema", "golden village", " gv ", "cathay", "concert",
                       "steam", "playstation", "xbox", "nintendo", "gaming", "universal studios",
                       "aquarium", "zoo", "gardens by the bay", "theme park", "ticket",
                       "festival", "attraction"]),
    ("electronics", ["laptop", "airpods", "headphone", "earbuds", "ssd", "kindle", "lenovo",
                     "samsung", "macbook", "iphone", "ipad", " pc ", "gadget", "charger",
                     "speaker", "camera", "monitor", "router", "smartwatch", "tv "]),
    ("fashion", ["fashion", "apparel", "clothing", "shoe", "sneaker", "uniqlo", "h&m", "zara",
                 "nike", "adidas", "puma", "beauty", "cosmetic", "makeup", "skincare", "sephora",
                 "handbag", "watch", "perfume", "guardian", "watsons", "charles"]),
    ("home", ["ikea", "furniture", "kitchen", "appliance", "mattress", "household", "home ",
              "living", "decor", "dyson", "vitamin", "supplement", "muji", "secretlab"]),
    ("food", ["1-for-1", "1 for 1", "buffet", "burger", "pizza", "chicken", "milk tea",
              "bubble tea", " bbt", "coffee", "cafe", "restaurant", "sushi", "prata", "soy",
              "ice cream", "snack", "bakery", "mcdonald", "kfc", "starbucks", "gong cha",
              "koi", "subway", "breakfast", "meal", "dessert", "cookie", "fairprice", "giant",
              "sheng siong", "dining", "eat", "drink", "grocery", "supermarket", "donki", "ya kun"]),
    ("online", ["shopee", "lazada", "amazon", "qoo10", "redmart", "taobao", "sitewide",
                "voucher", "promo code", "online", "e-commerce", "web hosting"]),
]

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

BOILERPLATE = [
    r"\[?\s*read more at singpromos\.com\s*\]?",
    r"visit great deals singapore for the full post\.?",
    r"the post .*? appeared first on .*?$",
    r"\[\s*…\s*\]", r"read more",
]


# ----------------------------------------------------------------------------
# Text helpers
# ----------------------------------------------------------------------------
def clean_text(raw: str) -> str:
    if not raw:
        return ""
    s = re.sub(r"<[^>]+>", " ", raw)
    s = html.unescape(s)
    for pat in BOILERPLATE:
        s = re.sub(pat, "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip(" -–—|·")
    return s.strip()


def detect_brand(text: str):
    t = text.lower()
    for brand, aliases in BRANDS.items():
        for a in aliases:
            if re.search(r"\b" + re.escape(a) + r"\b", t):
                return brand
    return None


def classify(title: str, summary: str, link: str, rss_cats=None, brand=None) -> str:
    hints = " ".join(rss_cats or []).lower() + " " + (link or "").lower()
    for slug, cat in SLUG_HINTS.items():
        if slug in hints:
            return cat
    text = f" {title} {summary} ".lower()
    for cat, words in CATEGORY_RULES:
        if any(w in text for w in words):
            return cat
    if brand and brand in BRAND_CATEGORY:
        return BRAND_CATEGORY[brand]
    return "online"


_MON = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"


def _build_date(day, mon, year):
    try:
        month = MONTHS[mon.lower()[:3]]
        yr = int(year) if year else TODAY.year
        end = datetime.date(yr, month, int(day))
    except (ValueError, KeyError):
        return None
    if not year and (TODAY - end).days > 60:
        end = datetime.date(yr + 1, month, int(day))
    return end


def parse_expiry(text: str):
    t = text
    end = None
    m = re.search(rf"\d{{1,2}}\s+{_MON}\s*[-–to]+\s*(\d{{1,2}})\s+{_MON}\.?\s*(\d{{4}})?", t, re.I)
    if m:
        end = _build_date(m.group(2), m.group(3), m.group(4))
    if not end:
        m = re.search(rf"(\d{{1,2}})\s*[-–]\s*(\d{{1,2}})\s+{_MON}\.?\s*(\d{{4}})?", t, re.I)
        if m:
            end = _build_date(m.group(2), m.group(3), m.group(4))
    if not end:
        m = re.search(rf"(?:till|until|ends?|thru|through|by|valid\s+till)\s+(\d{{1,2}})\s+{_MON}\.?\s*(\d{{4}})?", t, re.I)
        if m:
            end = _build_date(m.group(1), m.group(2), m.group(3))
    if not end:
        m = re.search(rf"\bon\s+(\d{{1,2}})\s+{_MON}\.?\s*(\d{{4}})?", t, re.I)
        if m:
            end = _build_date(m.group(1), m.group(2), m.group(3))
    if not end and re.search(rf"\bfrom\s+\d{{1,2}}\s+{_MON}", t, re.I):
        return ("Ongoing", None)
    if not end:
        allm = re.findall(rf"(\d{{1,2}})\s+{_MON}\.?\s*(\d{{4}})?", t, re.I)
        if not allm:
            return ("Check link for dates", None)
        end = _build_date(allm[-1][0], allm[-1][1], allm[-1][2])
    if not end:
        return ("Check link for dates", None)
    return ("Ends " + f"{end.day} {end.strftime('%b')}", end)


def make_badges(text: str, brand=None):
    t = text.lower()
    badges = []
    if brand:
        badges.append({"type": "new", "label": brand.upper()})
    if any(k in t for k in ["1-for-1", "1 for 1", "buy 1", "b1g1", "1-1"]):
        badges.append({"type": "discount", "label": "1-FOR-1"})
    if re.search(r"\bfree\b", t) and "free delivery" not in t:
        badges.append({"type": "free", "label": "FREE"})
    m = re.search(r"(\d{1,3})\s*%\s*off", t)
    if m:
        badges.append({"type": "discount", "label": f"{m.group(1)}% OFF"})
    if "promo code" in t or "coupon" in t or re.search(r"\bcode\b", t):
        badges.append({"type": "code", "label": "PROMO CODE"})
    if "cashback" in t:
        badges.append({"type": "discount", "label": "CASHBACK"})
    if not badges:
        badges.append({"type": "new", "label": "NEW"})
    seen, out = set(), []
    for b in badges:
        if b["label"] not in seen:
            seen.add(b["label"]); out.append(b)
    return out[:3]


def detect_access(text: str):
    t = text.lower()
    if any(w in t for w in ["online", "sitewide", "checkout", "website", "promo code", "code", "e-coupon"]):
        return {"type": "easy", "label": "Online — see source link to claim"}
    if any(w in t for w in ["app", "scan", "member", "rewards", "in-app"]):
        return {"type": "app", "label": "App or membership may be needed"}
    return {"type": "easy", "label": "See source for how to redeem"}


def extract_code(text: str):
    m = re.search(r"\bcode[:\s]+([A-Z0-9]{4,15})\b", text)
    return m.group(1) if m else None


def extract_store(title: str, source_name: str) -> str:
    t = re.split(r"\bS(?:ingapore|['’]?pore|G)\b", title, maxsplit=1)[0].strip(" -–—:|")
    if 2 <= len(t) <= 40:
        return t
    words = title.split()
    return " ".join(words[:4]) if words else source_name


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


# ----------------------------------------------------------------------------
# Feed fetching / parsing (stdlib only)
# ----------------------------------------------------------------------------
def fetch_url(url: str, timeout: int = 25) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _local(el) -> str:
    return el.tag.split("}")[-1].lower()


def parse_feed(xml_bytes: bytes):
    root = ET.fromstring(xml_bytes)
    items = [el for el in root.iter() if _local(el) == "item"]
    atom = False
    if not items:
        items = [el for el in root.iter() if _local(el) == "entry"]
        atom = True
    records = []
    for it in items:
        rec = {"title": "", "link": "", "description": "", "categories": [], "publisher": ""}
        for ch in it:
            tag = _local(ch)
            if tag == "title" and not rec["title"]:
                rec["title"] = (ch.text or "").strip()
            elif tag == "link":
                if atom:
                    href = ch.get("href")
                    if href and ch.get("rel") in (None, "alternate"):
                        rec["link"] = href
                elif ch.text:
                    rec["link"] = ch.text.strip()
            elif tag in ("description", "summary", "encoded") and not rec["description"]:
                rec["description"] = ch.text or ""
            elif tag == "category":
                c = (ch.text or ch.get("term") or "").strip()
                if c:
                    rec["categories"].append(c)
            elif tag == "source" and not rec["publisher"]:
                rec["publisher"] = (ch.text or "").strip()
        if rec["title"]:
            records.append(rec)
    return records


def deal_from_record(rec: dict, source_name: str):
    title = clean_text(rec["title"])
    if not title:
        return None
    summary = clean_text(rec["description"]) or title
    link = rec["link"] or "#"
    if link != "#" and not re.match(r"^https?://", link, re.I):
        link = "#"  # only allow real web links into the site (defence-in-depth)

    brand = detect_brand(f"{title} {summary}")
    category = classify(title, summary, link, rec.get("categories"), brand)
    expiry_label, end_date = parse_expiry(f"{title} {summary}")
    if end_date and end_date < TODAY:
        return None

    deal = {
        "id": slugify(title) or hashlib.md5(title.encode()).hexdigest()[:10],
        "title": title[:120],
        "store": brand or extract_store(title, source_name),
        "categories": [category],
        "icon": CATEGORY_ICONS.get(category, "🏷️"),
        "badges": make_badges(f"{title} {summary}", brand),
        "access": detect_access(f"{title} {summary}"),
        "desc": summary[:200].rstrip(),
        "expiry": expiry_label,
        "heat": 0,
        "url": link,
        "source": {"name": source_name, "url": link},
    }
    if brand:
        deal["brand"] = brand
    code = extract_code(f"{title} {summary}")
    if code:
        deal["code"] = code
    return deal


def fetch_rss(source: dict, max_items: int):
    name = source.get("name", "Source")
    url = source["url"]
    try:
        records = parse_feed(fetch_url(url))
    except Exception as e:  # noqa: BLE001
        print(f"  ! {name}: {type(e).__name__}: {e}")
        return []
    deals = [d for d in (deal_from_record(r, name) for r in records[:max_items]) if d]
    print(f"  ✓ {name}: {len(deals)} deals")
    return deals


def _fetch_one_brand(brand: str, cfg: dict):
    suffix = cfg.get("query_suffix", "Singapore (promotion OR deal OR sale OR discount OR offer)")
    hl, gl, ceid = cfg.get("hl", "en-SG"), cfg.get("gl", "SG"), cfg.get("ceid", "SG:en")
    per = int(cfg.get("max_per_brand", 4))
    q = f'"{brand}" {suffix}'
    url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(q) +
           f"&hl={hl}&gl={gl}&ceid={urllib.parse.quote(ceid)}")
    try:
        records = parse_feed(fetch_url(url))
    except Exception as e:  # noqa: BLE001
        print(f"  ! {brand} news: {type(e).__name__}: {e}")
        return []
    out, kept = [], 0
    for rec in records:
        if kept >= per:
            break
        title = clean_text(rec["title"])
        summary = clean_text(rec["description"]) or title
        blob = f"{title} {summary}".lower()
        if not any(k in blob for k in PROMO_KEYWORDS):
            continue
        if not detect_brand(f"{title} {summary}"):
            continue
        d = deal_from_record(rec, rec.get("publisher") or f"{brand} news")
        if not d:
            continue
        d["brand"], d["store"] = brand, brand
        out.append(d)
        kept += 1
    print(f"  ✓ {brand}: {kept} news deals")
    return out


def fetch_brand_news(cfg: dict):
    """Per-brand Google News RSS (Singapore-scoped, promo-filtered). Fetched
    CONCURRENTLY for speed; each item links back to the original publisher."""
    if not cfg.get("enabled"):
        return []
    brands = cfg.get("brands", list(BRANDS.keys()))
    out = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for r in ex.map(lambda b: _fetch_one_brand(b, cfg), brands):
            out.extend(r)
    return out


def fetch_involve_asia(cfg: dict, max_items: int):
    if not cfg.get("enabled"):
        return []
    key = os.environ.get("INVOLVE_API_KEY", "")
    secret = os.environ.get("INVOLVE_API_SECRET", "")
    token_url, offers_url = cfg.get("token_url", ""), cfg.get("offers_url", "")
    if not (key and secret and token_url and offers_url):
        print("  · Involve Asia enabled but credentials/URLs missing — skipping.")
        return []
    try:
        body = urllib.parse.urlencode({"key": key, "secret": secret}).encode()
        tok_req = urllib.request.Request(token_url, data=body, headers={"User-Agent": USER_AGENT})
        tok = json.loads(urllib.request.urlopen(tok_req, timeout=30).read())
        token = (tok.get("data") or {}).get("token") or tok.get("token")
        off_req = urllib.request.Request(f"{offers_url}?limit={max_items}",
                                         headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT})
        res = json.loads(urllib.request.urlopen(off_req, timeout=30).read())
        offers = ((res.get("data") or {}).get("data")) or res.get("data") or []
    except Exception as e:  # noqa: BLE001
        print(f"  ! Involve Asia: {type(e).__name__}: {e}")
        return []
    deals = []
    for o in offers[:max_items]:
        title = clean_text(str(o.get("offer_name") or o.get("title") or ""))
        if not title:
            continue
        link = o.get("tracking_link") or o.get("offer_url") or "#"
        brand = detect_brand(title)
        category = classify(title, clean_text(str(o.get("description", ""))), "", None, brand)
        d = {
            "id": slugify(title), "title": title[:120],
            "store": brand or clean_text(str(o.get("merchant_name") or title)),
            "categories": [category], "icon": CATEGORY_ICONS.get(category, "🏷️"),
            "badges": make_badges(title, brand), "access": {"type": "easy", "label": "Online — via affiliate link"},
            "desc": clean_text(str(o.get("description", "")))[:200], "expiry": "Check link for dates",
            "heat": 0, "url": link, "source": {"name": "Involve Asia", "url": link},
        }
        if brand:
            d["brand"] = brand
        deals.append(d)
    print(f"  ✓ Involve Asia: {len(deals)} offers")
    return deals


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    print(f"LobangKing aggregator — {TODAY.isoformat()}")
    cfg = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    settings = cfg.get("settings", {})
    max_total = int(settings.get("max_deals", 72))
    max_per = int(settings.get("max_per_source", 25))

    collected = []

    if MANUAL_FILE.exists():
        try:
            manual = json.loads(MANUAL_FILE.read_text(encoding="utf-8"))
            man_deals = manual.get("deals", []) if isinstance(manual, dict) else manual
            for d in man_deals:
                d.setdefault("source", {"name": "Editor's pick", "url": d.get("url", "#")})
            collected.extend(man_deals)
            print(f"  ✓ manual_deals.json: {len(man_deals)} curated deals")
        except Exception as e:  # noqa: BLE001
            print(f"  ! manual_deals.json error: {e}")

    rss = cfg.get("rss", []) or []
    if rss:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            for r in ex.map(lambda s: fetch_rss(s, max_per), rss):
                collected.extend(r)

    collected.extend(fetch_brand_news(cfg.get("brand_news", {}) or {}))
    collected.extend(fetch_involve_asia(cfg.get("involve_asia", {}) or {}, max_per))

    # De-duplicate by normalised title
    seen, deduped = set(), []
    for d in collected:
        key = re.sub(r"[^a-z0-9]", "", d["title"].lower())[:50]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(d)

    # OPTIONAL 2026 AI polish (titles/summaries/categories) — only real fetched text,
    # never invents facts. No-op unless configured (see scripts/ai_enrich.py).
    deduped = ai_enrich.enrich(deduped, cfg.get("ai", {}) or {})

    # Rank: brand deals and free/discount deals float up; freshest first otherwise.
    for i, d in enumerate(deduped):
        base = max(30, 320 - i * 5)
        if d.get("brand"):
            base += 40
        if any(b["type"] in ("free", "discount") for b in d.get("badges", [])):
            base += 20
        d["heat"] = base
    deduped.sort(key=lambda d: d["heat"], reverse=True)
    deduped = deduped[:max_total]
    if deduped:
        deduped[0]["spotlight"] = True

    if not deduped and DATA_FILE.exists():
        try:
            prev = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            if prev.get("deals"):
                print("! No deals fetched this run — keeping the previous deals.json.")
                return
        except Exception:  # noqa: BLE001
            pass

    brands_seen = sorted({d["brand"] for d in deduped if d.get("brand")})
    out = {
        "updated": TODAY.isoformat(),
        "categories": CATEGORIES,
        "brands_tracked": list(BRANDS.keys()),
        "brands_today": brands_seen,
        "deals": deduped,
    }
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(deduped)} deals ({len(brands_seen)} brands today) → {DATA_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
