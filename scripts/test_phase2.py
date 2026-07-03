#!/usr/bin/env python3
"""Offline tests for the Phase-2 scripts — no network needed.
Run: python3 scripts/test_phase2.py"""
import fetch_images
import check_stock
import build_pages

# --- og:image parser (handles attribute order + fallbacks) ---
p = fetch_images.OGParser()
p.feed('<head><meta property="og:image" content="https://x.com/a.jpg">'
       '<meta name="twitter:image" content="https://x.com/b.jpg"></head>')
assert p.image == "https://x.com/a.jpg", p.image

p2 = fetch_images.OGParser()
p2.feed('<meta content="https://x.com/c.jpg" property="og:image">')   # reversed order
assert p2.image == "https://x.com/c.jpg", p2.image

p3 = fetch_images.OGParser()
p3.feed('<meta name="twitter:image" content="https://x.com/t.jpg">')  # twitter fallback
assert p3.image == "https://x.com/t.jpg", p3.image

p4 = fetch_images.OGParser()
p4.feed('<meta name="description" content="no image here">')
assert p4.image is None

# --- out-of-stock detection (conservative) ---
assert check_stock.SIGNALS.search("Sorry, this item is Out of Stock")
assert check_stock.SIGNALS.search('"availability":"https://schema.org/SoldOut"')
assert check_stock.SIGNALS.search("This promotion has ended.")
assert check_stock.SIGNALS.search("fully redeemed")
assert not check_stock.SIGNALS.search("Great deal, in stock now — buy today!")

# --- claimed-state rendering (card + deal page) ---
claimed = {"id": "x", "title": "Test deal", "store": "ACME", "categories": ["food"],
           "expiry": "Ends 5 Jul", "status": "claimed", "badges": [{"type": "free", "label": "FREE"}]}
card = build_pages.card_html(claimed)
assert "is-claimed" in card and "Fully claimed" in card, "card claimed state missing"
page = build_pages.deal_page(claimed, [])
assert "claimed-notice" in page and "fully redeemed" in page, "deal-page claimed notice missing"

# --- image-led card uses a real/fallback image ---
normal = {"id": "y", "title": "Live deal", "store": "Shop", "categories": ["online"],
          "expiry": "Ends 9 Jul", "image": "images/deals/y.jpg"}
assert 'src="images/deals/y.jpg"' in build_pages.card_html(normal)
assert 'images/deal-fallback.jpg' in build_pages.card_html({"id": "z", "title": "T", "store": "S", "categories": ["home"]})

print("✅ Phase 2 tests passed: og:image parse, out-of-stock detection, claimed rendering, image-led cards.")
