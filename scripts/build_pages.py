#!/usr/bin/env python3
"""
build_pages.py — LobangKing.sg static site builder
===================================================

Two jobs, both dependency-free (standard library only):

1. SHARED CHROME (DRY): the canonical site header and footer live HERE, in one
   place. This script writes them into every content page, so you edit the nav,
   logo or social links once instead of in six files.

2. SEO PRE-RENDER: it bakes the current deals from data/deals.json directly into
   the HTML of index.html and deals.html (between <!--DEALS:START/END--> markers)
   and emits ItemList JSON-LD. That means search engines and link previews see
   the real deal text without running JavaScript. The site's JS still hydrates
   the same content for interactivity.

Run order in the GitHub Action:  aggregate_deals.py  →  build_pages.py  → commit.
Run locally any time:            python3 scripts/build_pages.py
"""

import re
import json
import html
import pathlib
import datetime
import minify
from aggregate_deals import CATEGORIES, parse_expiry, TODAY, is_upcoming  # single source of truth

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_FILE = ROOT / "data" / "deals.json"

# ---- Site config (single source of truth) ----------------------------------
SITE_URL = "https://lobangking.sg"
# Social channels are not live yet — shown as "coming soon" in the footer.
SOCIALS_SOON = [("Facebook", "📘"), ("TikTok", "🎵"), ("Instagram", "📸"), ("X", "𝕏")]
CONTACT_EMAIL = "thelobangkingsg@gmail.com"

# Which pages get the shared chrome, and their active nav key
PAGES = {
    "index.html": "home",
    "deals.html": "deals",
    "about.html": "about",
    "submit.html": "submit",
    "privacy.html": None,
}
NAV = [("home", "index.html", "Home"), ("deals", "deals.html", "All Lobangs"),
       ("about", "about.html", "About"), ("submit", "submit.html", "Submit a Lobang")]


def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def safe_url(u):
    u = ("" if u is None else str(u)).strip() or "#"
    if u[:1] in ("#", "/"):
        return u
    return u if re.match(r"^https?://", u, re.I) else "#"


# ---- Shared header / footer -------------------------------------------------
def header(active):
    sub = "#subscribe" if active == "home" else "index.html#subscribe"
    links = "\n".join(
        f'      <a class="nav__link{" nav__link--active" if k == active else ""}" href="{href}">{label}</a>'
        for k, href, label in NAV)
    mobile = "\n".join(f'      <a href="{href}">{label}</a>' for _, href, label in NAV)
    site_bg = '<div class="site-bg" aria-hidden="true"><div class="site-bg__img"></div><div class="site-bg__scrim"></div></div>'
    skip = '<a class="skip-link" href="#main">Skip to content</a>'
    return skip + site_bg + ICON_SPRITE + f'''
<header class="site-header">
  <div class="container nav">
    <a class="nav__logo" href="index.html" aria-label="LobangKing.sg home">
      <img class="nav__logo-img" src="images/icon-192.png" alt="" width="40" height="40" decoding="async" fetchpriority="high">
      <span class="wordmark">lobang<b>king</b></span>
    </a>
    <nav class="nav__links" aria-label="Primary">
{links}
    </nav>
    <div class="nav__actions">
      <button class="icon-btn theme-toggle" type="button" aria-label="Toggle light and dark mode"><span class="moon">{icon("i-moon")}</span><span class="sun">{icon("i-sun")}</span></button>
      <a class="btn btn--gold nav__cta-desktop" href="{sub}">Subscribe free</a>
      <button class="icon-btn menu-toggle" type="button" aria-label="Open menu" aria-expanded="false">{icon("i-menu")}</button>
    </div>
  </div>
  <div class="container">
    <nav class="mobile-menu" id="mobileMenu" aria-label="Mobile">
{mobile}
      <a href="{sub}">Subscribe free</a>
    </nav>
  </div>
</header>'''


def footer():
    social_chips = "\n".join(
        f'          <span class="social__chip" title="{n} — coming soon" aria-label="{n} — coming soon">{ic}</span>'
        for n, ic in SOCIALS_SOON)
    return f'''<footer class="site-footer">
  <div class="container">
    <div class="footer__grid">
      <div class="footer__brand">
        <a class="nav__logo mb-14" href="index.html">
          <img class="nav__logo-img" src="images/icon-192.png" alt="" loading="lazy" decoding="async">
          <span class="wordmark">lobang<b>king</b></span>
        </a>
        <p>Singapore's friendliest lobang site. We hand-check every promo so you can save without the scrolling. Always free.</p>
        <div class="social social--soon" aria-label="Social channels — coming soon">
{social_chips}
          <span class="social__soon-label">Coming soon</span>
        </div>
        <p class="footer__contact">📧 <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></p>
      </div>
      <div class="footer__col"><h4>Browse</h4>
        <a href="deals.html">All Lobangs</a><a href="deals.html?cat=food">Food &amp; Drinks</a>
        <a href="deals.html?cat=electronics">Electronics</a><a href="deals.html?cat=travel">Travel</a></div>
      <div class="footer__col"><h4>Site</h4>
        <a href="about.html">About Us</a><a href="submit.html">Submit a Lobang</a>
        <a href="index.html#subscribe">Subscribe</a><a href="about.html#advertise">Advertise</a></div>
      <div class="footer__col"><h4>Legal</h4>
        <a href="privacy.html">Privacy Policy</a><a href="privacy.html#terms">Terms of Use</a>
        <a href="privacy.html#disclaimer">Disclaimer</a></div>
    </div>
    <div class="footer__bottom">
      <span>© 2026 LobangKing.sg — Every Lobang in Singapore 👑 · All rights reserved</span>
      <nav><a href="about.html">About</a><a href="submit.html">Submit</a><a href="privacy.html">Privacy</a></nav>
    </div>
  </div>
</footer>'''


# ---- Professional SVG icon set (replaces emojis) ----------------------------
CAT_ICON = {"all": "i-all", "food": "i-food", "electronics": "i-electronics", "home": "i-home",
            "travel": "i-travel", "transport": "i-transport", "fashion": "i-fashion",
            "entertainment": "i-fun", "finance": "i-finance", "online": "i-online"}

ICON_SPRITE = ('<svg class="icon-sprite" aria-hidden="true" focusable="false"><defs>'
    '<symbol id="i-all" viewBox="0 0 24 24"><path d="M12 3l1.8 6 6 1.8-6 1.8L12 21l-1.8-6-6-1.8 6-1.8z"/></symbol>'
    '<symbol id="i-food" viewBox="0 0 24 24"><path d="M4 11h16a8 8 0 0 1-16 0zM4 11h16M9 3v3M12 3v3M15 3v3"/></symbol>'
    '<symbol id="i-electronics" viewBox="0 0 24 24"><path d="M3 5h18v11H3zM9 20h6M12 16v4"/></symbol>'
    '<symbol id="i-home" viewBox="0 0 24 24"><path d="M4 11l8-6 8 6M6 10v9h12v-9"/></symbol>'
    '<symbol id="i-travel" viewBox="0 0 24 24"><path d="M21 4L3 11l6 2 2 6z"/></symbol>'
    '<symbol id="i-transport" viewBox="0 0 24 24"><path d="M5 12l1.6-4h10.8L19 12M4 12h16v4H4zM7 16v2M17 16v2"/></symbol>'
    '<symbol id="i-fashion" viewBox="0 0 24 24"><path d="M6 8h12l1 12H5zM9 8a3 3 0 0 1 6 0"/></symbol>'
    '<symbol id="i-fun" viewBox="0 0 24 24"><path d="M4 8h16v3a2 2 0 0 0 0 4v1H4v-1a2 2 0 0 0 0-4zM12 8v8"/></symbol>'
    '<symbol id="i-finance" viewBox="0 0 24 24"><path d="M3 6h18v12H3zM3 10h18"/></symbol>'
    '<symbol id="i-online" viewBox="0 0 24 24"><path d="M4 5h2l2 10h9l2-7H7"/><circle cx="9" cy="19" r="1"/><circle cx="17" cy="19" r="1"/></symbol>'
    '<symbol id="i-search" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></symbol>'
    '<symbol id="i-share" viewBox="0 0 24 24"><circle cx="17" cy="6" r="2.5"/><circle cx="6" cy="12" r="2.5"/><circle cx="17" cy="18" r="2.5"/><path d="M8.3 10.8l6.4-3.6M8.3 13.2l6.4 3.6"/></symbol>'
    '<symbol id="i-arrow" viewBox="0 0 24 24"><path d="M5 12h13M13 6l6 6-6 6"/></symbol>'
    '<symbol id="i-menu" viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h16"/></symbol>'
    '<symbol id="i-sun" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4.5"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M19 5l-1.5 1.5M6.5 17.5L5 19"/></symbol>'
    '<symbol id="i-moon" viewBox="0 0 24 24"><path d="M20 14a8 8 0 1 1-10-10 6.5 6.5 0 0 0 10 10z"/></symbol>'
    '<symbol id="i-clock" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/></symbol>'
    '<symbol id="i-tag" viewBox="0 0 24 24"><path d="M4 4h7l9 9-7 7-9-9z"/><circle cx="8" cy="8" r="1"/></symbol>'
    '<symbol id="i-bolt" viewBox="0 0 24 24"><path d="M13 3L5 13h6l-2 8 8-11h-6z"/></symbol>'
    '</defs></svg>')


def icon(name):
    return f'<svg class="ic" aria-hidden="true"><use href="#{name}"></use></svg>'


# Inline bookmark glyph — drawn with its own <path> (not the sprite) so the
# "Chope" save button renders on every page, including the sprite-less 404.
BOOKMARK_SVG = ('<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">'
                '<path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z"/></svg>')


def chope_btn():
    """The 'Chope' (Singlish: reserve/save) button on every card. Saving is
    100% client-side (localStorage) in js/main.js — this is just initial markup."""
    return ('<button class="deal-chope" type="button" data-chope '
            'aria-label="Save this lobang" aria-pressed="false" '
            f'title="Chope (save) this lobang">{BOOKMARK_SVG}</button>')


def time_chip(d):
    """Expiry chip carrying a machine-readable end date so js/main.js can run a
    live countdown, plus a best-effort urgency colour computed at build time."""
    ex = d.get("expires_at") or ""
    cls = "deal-card__time"
    if ex:
        try:
            days = (datetime.date.fromisoformat(ex) - TODAY).days
            cls += " is-expired" if days < 0 else " is-urgent" if days <= 2 else " is-soon" if days <= 6 else ""
        except ValueError:
            pass
    label = d.get("expiry", "")
    attr = f' data-expires="{esc(ex)}"' if ex else ""
    return (f'<span class="{cls}"{attr} data-label="{esc(label)}">{icon("i-clock")}'
            f'<span class="tc-text">{esc(label)}</span></span>')


# ---- Image-led deal card (mirrors js/main.js) -------------------------------
def card_html(d):
    cat = (d.get("categories") or ["online"])[0]
    url = esc(safe_url(d.get("url")))
    img = esc(d.get("image") or "images/deal-fallback.jpg")
    claimed = d.get("status") == "claimed"
    badges = d.get("badges") or []
    primary = next((b for b in badges if b.get("type") in ("free", "discount", "code")), None)
    overlay = (f'<span class="deal-badge deal-badge--{esc(primary["type"])}">{esc(primary["label"])}</span>'
               if primary and not claimed else "")
    claim = '<span class="deal-claimed">Fully claimed</span>' if claimed else ""
    code = (f'<button class="code-pill" data-code="{esc(d["code"])}" type="button">{icon("i-tag")}{esc(d["code"])}</button>'
            if d.get("code") and not claimed else "")
    s = d.get("source")
    # Compact "mini source link" (mirrors js/main.js) — the publisher name is no
    # longer the visible hyperlink; a small labelled Source chip carries the link.
    src = (f' · <a class="deal-card__src" href="{esc(safe_url(s.get("url")))}" target="_blank" rel="noopener nofollow" title="Source: {esc(s.get("name","source"))}">{icon("i-arrow")}Source</a>'
           if s and safe_url(s.get("url")) != "#" else "")
    # Share button — hidden until the card is hovered/focused (see styles.css).
    share = f'<button class="deal-share" type="button" data-share-open aria-label="Share this lobang">{icon("i-share")}</button>'
    chope = chope_btn()   # always-visible save button (mirrors js/main.js)
    cta = ('<span class="deal-card__cta is-disabled">Fully claimed</span>' if claimed
           else f'<a class="deal-card__cta" href="{url}" rel="noopener">View lobang {icon("i-arrow")}</a>')
    return (
        f'<article class="deal-card{" is-claimed" if claimed else ""}" data-id="{esc(d.get("id",""))}" '
        f'data-cats="{esc(",".join(d.get("categories") or []))}" data-title="{esc(d.get("title",""))}" '
        f'data-store="{esc(d.get("store",""))}" data-url="{url}" data-img="{img}" data-expires="{esc(d.get("expires_at",""))}">'
        f'<a class="deal-card__media" href="{url}" rel="noopener" tabindex="-1" aria-hidden="true">'
        f'<img src="{img}" alt="" loading="lazy" decoding="async">'
        f'<span class="deal-card__cat">{icon(CAT_ICON.get(cat,"i-tag"))}{esc(CAT_LABELS.get(cat,""))}</span>'
        f'{overlay}{claim}</a>{chope}{share}'
        f'<div class="deal-card__body">'
        f'<div class="deal-card__store">{esc(d.get("store",""))}{src}</div>'
        f'<h3 class="deal-card__title"><a href="{url}" rel="noopener">{esc(d.get("title",""))}</a></h3>'
        + (f'<p class="deal-card__take">{esc(d.get("desc",""))}</p>' if d.get("desc") else "")
        + code
        + f'<div class="deal-card__foot">{time_chip(d)}{cta}</div>'
        f'</div></article>'
    )


def launch_label(starts_at, ref=None):
    """(css-suffix, text) for an Upcoming card's launch pill. Mirrors
    launchLabel() in js/main.js so the server-rendered label matches the live one
    js re-computes on load."""
    ref = ref or TODAY
    try:
        start = datetime.date.fromisoformat(starts_at) if starts_at else None
    except ValueError:
        start = None
    if not start:
        return ("", "Coming soon")
    d = (start - ref).days
    if d < 0:
        return ("is-live", "Live now")
    if d == 0:
        return ("is-imminent", "Launches today")
    if d == 1:
        return ("is-imminent", "Launches tomorrow")
    if d <= 6:
        return ("is-soon", f"Launches in {d} days")
    return ("", f"Launches {start.day} {start.strftime('%b')}")


def upcoming_card_html(d):
    """Immersive 'Upcoming Lobang' poster card — a deliberately different, richer
    treatment than the standard grid card: a full-bleed hero image with a gradient
    veil, a glowing live launch-countdown pill, an eyebrow, and a sliding info
    drawer that expands the description on hover/focus. Carries the same data-*
    attributes as card_html so Chope (save) + Share work unchanged. Kept byte-for
    -byte in step with upcomingCard() in js/main.js."""
    cat = (d.get("categories") or ["online"])[0]
    url = esc(safe_url(d.get("url")))
    img = esc(d.get("image") or "images/deal-fallback.jpg")
    badges = d.get("badges") or []
    primary = next((b for b in badges if b.get("type") in ("free", "discount", "code")), None)
    badge = (f'<span class="up-card__badge up-card__badge--{esc(primary["type"])}">{esc(primary["label"])}</span>'
             if primary else "")
    s = d.get("source")
    src = (f'<a class="up-card__src" href="{esc(safe_url(s.get("url")))}" target="_blank" rel="noopener nofollow" '
           f'title="Source: {esc(s.get("name","source"))}">{icon("i-arrow")}Source</a>'
           if s and safe_url(s.get("url")) != "#" else "")
    lcls, ltext = launch_label(d.get("starts_at") or "")
    launch = (f'<span class="up-card__count {lcls}" data-starts="{esc(d.get("starts_at") or "")}">'
              f'{icon("i-clock")}<span class="uc-text">{esc(ltext)}</span></span>')
    share = f'<button class="deal-share" type="button" data-share-open aria-label="Share this lobang">{icon("i-share")}</button>'
    eyebrow = f'<span class="up-card__eyebrow"><span class="up-card__emoji" aria-hidden="true">{esc(d.get("icon") or "✨")}</span>Upcoming lobang</span>'
    return (
        f'<article class="up-card reveal" data-id="{esc(d.get("id",""))}" '
        f'data-cats="{esc(",".join(d.get("categories") or []))}" data-title="{esc(d.get("title",""))}" '
        f'data-store="{esc(d.get("store",""))}" data-url="{url}" data-img="{img}" data-expires="{esc(d.get("expires_at",""))}">'
        f'<div class="up-card__poster">'
        f'<img class="up-card__img" src="{img}" alt="" loading="lazy" decoding="async">'
        f'<span class="up-card__veil" aria-hidden="true"></span>'
        f'<span class="up-card__sheen" aria-hidden="true"></span>'
        f'<span class="up-card__cat">{icon(CAT_ICON.get(cat,"i-tag"))}{esc(CAT_LABELS.get(cat,""))}</span>'
        f'{launch}{chope_btn()}{share}'
        f'<div class="up-card__head">{eyebrow}'
        f'<div class="up-card__store">{esc(d.get("store",""))}</div>'
        f'<h3 class="up-card__title"><a href="{url}" rel="noopener">{esc(d.get("title",""))}</a></h3>'
        f'</div></div>'
        f'<div class="up-card__drawer">'
        f'<div class="up-card__row">{badge}{src}</div>'
        + (f'<p class="up-card__desc">{esc(d.get("desc",""))}</p>' if d.get("desc") else "")
        + f'<div class="up-card__foot">{time_chip(d)}'
        f'<a class="up-card__cta" href="{url}" rel="noopener">Sneak peek {icon("i-arrow")}</a>'
        f'</div></div></article>'
    )


def spotlight_html(d):
    url = esc(safe_url(d.get("url")))
    img = esc(d.get("image") or "images/deal-fallback.jpg")
    code = (f'<button class="code-pill" data-code="{esc(d["code"])}" type="button">{icon("i-tag")}{esc(d["code"])}</button>'
            if d.get("code") else "")
    return (
        f'<div class="spotlight-card" data-id="{esc(d.get("id",""))}" data-title="{esc(d.get("title",""))}" '
        f'data-store="{esc(d.get("store",""))}" data-url="{url}" data-img="{img}" data-expires="{esc(d.get("expires_at",""))}">'
        f'<a class="spotlight__media" href="{url}" rel="noopener" tabindex="-1" aria-hidden="true"><img src="{img}" alt="" loading="lazy" decoding="async"></a>'
        f'{chope_btn()}'
        f'<div class="spotlight__body"><span class="spotlight__kicker">{icon("i-bolt")}Latest Lobang</span>'
        f'<div class="spotlight__store">{esc(d.get("store",""))}</div>'
        f'<h2 class="spotlight__title">{esc(d.get("title",""))}</h2>'
        + (f'<p class="spotlight__desc">{esc(d.get("desc",""))}</p>' if d.get("desc") else "")
        + code
        + f'<div class="spotlight__foot">{time_chip(d)}'
        f'<a class="btn btn--gold btn--lg" href="{url}" rel="noopener">View this lobang {icon("i-arrow")}</a></div>'
        f'</div></div>'
    )


def itemlist_jsonld(deals, page_url):
    items = []
    for i, d in enumerate(deals[:20], 1):
        items.append({
            "@type": "ListItem", "position": i,
            "item": {"@type": "Offer", "name": d.get("title", ""), "category": (d.get("categories") or [""])[0],
                     "seller": {"@type": "Organization", "name": d.get("store", "")},
                     "url": safe_url(d.get("url"))}})
    data = {"@context": "https://schema.org", "@type": "ItemList", "name": "Singapore Lobangs",
            "url": page_url, "numberOfItems": len(items), "itemListElement": items}
    return '<script type="application/ld+json">\n' + json.dumps(data, ensure_ascii=False) + '\n</script>'


def org_jsonld():
    data = {"@context": "https://schema.org", "@type": "Organization", "name": "LobangKing.sg",
            "url": SITE_URL + "/", "logo": SITE_URL + "/images/icon-512.png",
            "description": "Singapore's #1 lobang site — verified daily promos, freebies and discounts.",
            "email": CONTACT_EMAIL}
    return '<script type="application/ld+json">\n' + json.dumps(data, ensure_ascii=False) + '\n</script>'


def write_feed(deals):
    items = []
    for d in deals[:30]:
        items.append(
            "<item>"
            f"<title>{esc(d.get('title',''))}</title>"
            f"<link>{esc(safe_url(d.get('url')))}</link>"
            f"<description>{esc(d.get('desc',''))}</description>"
            f"<category>{esc((d.get('categories') or [''])[0])}</category>"
            f'<guid isPermaLink="false">{esc(d.get("id",""))}</guid>'
            "</item>")
    feed = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<rss version="2.0"><channel>'
            '<title>LobangKing.sg — Singapore Lobangs</title>'
            f'<link>{SITE_URL}/</link>'
            '<description>Verified daily promos, freebies and discounts across Singapore.</description>'
            '<language>en-SG</language>'
            + "".join(items) + '</channel></rss>')
    (ROOT / "feed.xml").write_text(feed, encoding="utf-8")
    print("  ✓ wrote feed.xml")


def write_sitemap(extra=None):
    today = datetime.date.today().isoformat()
    pages = [("/", "1.0", "daily"), ("/deals.html", "0.9", "daily"),
             ("/about.html", "0.6", "monthly"), ("/submit.html", "0.6", "monthly")]
    pages += list(extra or [])
    body = "".join(
        f"<url><loc>{SITE_URL}{p}</loc><lastmod>{today}</lastmod>"
        f"<changefreq>{cf}</changefreq><priority>{pr}</priority></url>" for p, pr, cf in pages)
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + body + '</urlset>',
        encoding="utf-8")
    print("  ✓ wrote sitemap.xml (lastmod " + today + ")")


def replace_region(s, start, end, content):
    pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    return pat.sub(lambda m: start + content + end, s, count=1)


def strip_accumulated_chrome(s):
    """Fix a long-standing build bug: header() prepends the skip-link, background
    and icon-sprite before <header>, but the header swap only replaced <header>
    itself — so every rebuild left the previous copies behind and pages piled up
    duplicates (13 sprites, 10 backgrounds, 8 skip-links each ≈ 26 KB of bloat).
    Remove every occurrence here; header() then re-injects exactly one fresh set."""
    s = re.sub(r'<a class="skip-link"[^>]*>.*?</a>', '', s, flags=re.S)
    s = re.sub(r'<div class="site-bg"[^>]*>.*?</div></div>', '', s, flags=re.S)
    s = re.sub(r'<svg class="icon-sprite".*?</svg>', '', s, flags=re.S)
    return s


# ---- SEO: per-deal + category pages (more indexable pages = more search traffic) ----
CAT_LABELS = {c["id"]: c["label"] for c in CATEGORIES}
DEFAULT_LABEL = "Lobangs"


def is_active(d):
    """A deal is shown only while it hasn't expired (ongoing deals always show)."""
    blob = f"{d.get('title','')} {d.get('desc','')} {d.get('expiry','')}"
    _, end = parse_expiry(blob)
    return end is None or end >= TODAY
SPEC_RULES = ('<script type="speculationrules">\n'
              '  {"prerender":[{"where":{"href_matches":"/*"},"eagerness":"moderate"}],'
              '"prefetch":[{"where":{"href_matches":"/*"},"eagerness":"moderate"}]}\n  </script>')


def full_page(title, desc, canonical, jsonld, body, og_image=None):
    og_image = og_image or (SITE_URL + "/images/og-image.png")
    head = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="copyright" content="© 2026 LobangKing.sg. All rights reserved.">
  <meta name="author" content="LobangKing.sg">
  <meta name="rights" content="All rights reserved — reproduction or replication of this site's design, code or curated content is prohibited.">
  <link rel="license" href="/LICENSE.txt">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; manifest-src 'self'; worker-src 'self'; form-action 'self' https://formspree.io; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; upgrade-insecure-requests">
  <meta name="referrer" content="strict-origin-when-cross-origin">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}">
  <meta name="theme-color" content="#ffffff">
  <link rel="canonical" href="{esc(canonical)}">
  <link rel="icon" href="images/favicon.ico" sizes="any">
  <link rel="icon" type="image/png" sizes="32x32" href="images/favicon-32.png">
  <link rel="apple-touch-icon" href="images/apple-touch-icon.png">
  <link rel="manifest" href="manifest.webmanifest">
  <link rel="alternate" type="application/rss+xml" title="LobangKing.sg lobangs" href="feed.xml">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:image" content="{esc(og_image)}">
  <meta property="og:url" content="{esc(canonical)}">
  <meta name="twitter:card" content="summary_large_image">
  <script src="js/theme.js?v=13"></script>
  <link rel="preload" as="font" type="font/woff2" href="fonts/dmsans-400.woff2?v=13" crossorigin>
  <link rel="preload" as="font" type="font/woff2" href="fonts/sora-700.woff2?v=13" crossorigin>
  <link rel="stylesheet" href="css/fonts.min.css?v=13">
  <link rel="stylesheet" href="css/styles.min.css?v=13">
  {jsonld}
  {SPEC_RULES}
</head>
<body>
'''
    tail = ('<button class="back-to-top" id="backToTop" type="button" aria-label="Back to top">↑</button>\n'
            '<script src="js/consent.js?v=13" defer></script>\n'
            '<script src="js/protect.js?v=13" defer></script>\n'
            '<script src="js/vitals.js?v=13" defer></script>\n'
            '<script src="js/engagement.js?v=13" defer></script>\n'
            '<script src="js/translate.js?v=13" defer></script>\n'
            '<script src="js/a11y.js?v=13" defer></script>\n'
            '<script src="js/main.js?v=13" defer></script>\n</body>\n</html>\n')
    return head + header(None) + '<main id="main" tabindex="-1">\n' + body + "\n</main>\n" + footer() + "\n" + tail


def deal_page(d, all_deals):
    cat = (d.get("categories") or ["online"])[0]
    label = CAT_LABELS.get(cat, DEFAULT_LABEL)
    title = f"{d.get('title', 'Lobang')} — {d.get('store', '')} | LobangKing.sg"
    desc = (d.get("desc") or d.get("title", ""))[:155]
    canonical = f"{SITE_URL}/deal-{d['id']}.html"
    claimed = d.get("status") == "claimed"
    offer = {"@context": "https://schema.org", "@type": "Offer", "name": d.get("title", ""),
             "category": cat, "url": safe_url(d.get("url")),
             "seller": {"@type": "Organization", "name": d.get("store", "")},
             "availability": "https://schema.org/" + ("SoldOut" if claimed else "InStock")}
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL + "/"},
        {"@type": "ListItem", "position": 2, "name": "Lobangs", "item": SITE_URL + "/deals.html"},
        {"@type": "ListItem", "position": 3, "name": d.get("title", "Deal")}]}
    jsonld = ('<script type="application/ld+json">' + json.dumps(offer, ensure_ascii=False) + '</script>'
              '<script type="application/ld+json">' + json.dumps(crumbs, ensure_ascii=False) + '</script>')
    related = [x for x in all_deals if x.get("id") != d.get("id") and cat in (x.get("categories") or [])][:6]
    if claimed:
        cta_block = ('<div class="claimed-notice"><span class="claimed-notice__tag">Fully claimed</span>'
                     '<h2>This lobang has been fully redeemed</h2>'
                     '<p>Sorry — this lobang has been fully claimed or is out of stock. The good news: '
                     'there are plenty more below, hand-verified and refreshed every morning.</p>'
                     f'<a class="btn btn--gold btn--lg" href="deals.html">Browse live {esc(label.lower())} lobangs {icon("i-arrow")}</a></div>')
    else:
        cta_block = (f'<div class="center-cta"><a class="btn btn--gold btn--lg" '
                     f'href="{esc(safe_url(d.get("url")))}" rel="noopener">Get this lobang {icon("i-arrow")}</a></div>')
    body = (
        '<section class="page-hero"><div class="container page-hero__inner">'
        f'<p class="muted"><a class="link-gold" href="deals.html">← All lobangs</a> · {esc(label)}</p>'
        f'<h1>{esc(d.get("title", ""))}</h1>'
        f'<p>{esc(d.get("store", ""))} · {esc(d.get("expiry", ""))}</p>'
        '</div></section>'
        '<section class="section"><div class="container">'
        f'<div class="deal-grid">{card_html(d)}</div>'
        f'{cta_block}'
        '</div></section>')
    if related:
        body += ('<section class="section"><div class="container">'
                 f'<div class="section__head"><h2 class="section__title">More {esc(label)} lobangs</h2>'
                 '<a class="section__link" href="deals.html">See all →</a></div>'
                 f'<div class="deal-grid">{"".join(card_html(x) for x in related)}</div>'
                 '</div></section>')
    return full_page(title, desc, canonical, jsonld, body)


def category_page(cat, deals):
    label = CAT_LABELS.get(cat, "Deals")
    title = f"Best {label} Deals in Singapore | LobangKing.sg"
    desc = f"Hand-verified {label.lower()} promos, discounts and freebies in Singapore — updated daily."
    canonical = f"{SITE_URL}/cat-{cat}.html"
    jsonld = ('<script type="application/ld+json">' + json.dumps(
        {"@context": "https://schema.org", "@type": "CollectionPage", "name": title, "url": canonical},
        ensure_ascii=False) + '</script>' + itemlist_jsonld(deals, canonical))
    body = (
        '<section class="page-hero"><div class="container page-hero__inner">'
        f'<h1>Best {esc(label)} Lobangs in Singapore</h1>'
        f'<p>{len(deals)} hand-verified {esc(label.lower())} promos, updated daily.</p>'
        '</div></section>'
        '<section class="section"><div class="container">'
        f'<div class="deal-grid">{"".join(card_html(x) for x in deals)}</div>'
        '<div class="center-cta"><a class="btn btn--ghost btn--lg" href="deals.html">Browse all categories →</a></div>'
        '</div></section>')
    return full_page(title, desc, canonical, jsonld, body)


def generate_seo_pages(deals):
    extra, current = [], set()
    for d in deals:
        fn = f"deal-{d['id']}.html"
        current.add(fn)
        (ROOT / fn).write_text(deal_page(d, deals), encoding="utf-8")
        extra.append((f"/{fn}", "0.7", "weekly"))
    for c in CATEGORIES:
        if c["id"] == "all":
            continue
        ds = [d for d in deals if c["id"] in (d.get("categories") or [])]
        if not ds:
            continue
        fn = f"cat-{c['id']}.html"
        current.add(fn)
        (ROOT / fn).write_text(category_page(c["id"], ds), encoding="utf-8")
        extra.append((f"/{fn}", "0.8", "daily"))
    pruned = 0
    for p in list(ROOT.glob("deal-*.html")) + list(ROOT.glob("cat-*.html")):
        if p.name not in current:
            p.unlink()
            pruned += 1
    print(f"  ✓ generated {len(extra)} SEO pages (per-deal + category), pruned {pruned} orphan(s)")
    return extra


def main():
    minify.build()  # refresh css/*.min.css from source
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    active_deals = [d for d in data.get("deals", []) if is_active(d)]  # non-expired only
    # Split live deals from ones that haven't started yet — the latter go into a
    # separate "Upcoming" section instead of the main grid.
    def _is_up(d):
        return bool(d.get("upcoming")) or is_upcoming(d)[0]
    upcoming = [d for d in active_deals if _is_up(d)]
    # Sort upcoming by soonest launch first so the anticipation builds top-down.
    upcoming.sort(key=lambda d: d.get("starts_at") or "9999-12-31")
    deals = [d for d in active_deals if not _is_up(d)]             # "current" deals for the live grid
    upcoming_cards = "".join(upcoming_card_html(d) for d in upcoming)
    spot = next((d for d in deals if d.get("spotlight")), deals[0] if deals else None)
    non_spot = [d for d in deals if not d.get("spotlight")]

    def set_upcoming(s):
        """Fill the Upcoming section's cards and show/hide it based on content."""
        s = replace_region(s, "<!--UPCOMING:START-->", "<!--UPCOMING:END-->", upcoming_cards)
        # Toggle the `hidden` attribute on the section wrapper.
        if upcoming:
            s = re.sub(r'(<section[^>]*id="upcomingSection"[^>]*?)\s+hidden(\s|>)', r"\1\2", s, count=1)
        elif 'id="upcomingSection" hidden' not in s and 'id="upcomingSection"' in s:
            s = re.sub(r'(<section[^>]*id="upcomingSection")(?![^>]*\shidden)', r"\1 hidden", s, count=1)
        return s

    for page, active in PAGES.items():
        p = ROOT / page
        if not p.exists():
            continue
        s = p.read_text(encoding="utf-8")
        orig = s
        # DRY chrome — first clear any duplicate chrome earlier builds left behind,
        # then re-inject exactly one fresh header (which carries skip-link + bg + sprite).
        s = strip_accumulated_chrome(s)
        s = re.sub(r'<header class="site-header">.*?</header>', lambda m: header(active), s, count=1, flags=re.S)
        s = re.sub(r'<footer class="site-footer">.*?</footer>', lambda m: footer(), s, count=1, flags=re.S)
        # Pre-render deals
        if page == "index.html":
            if spot:
                s = replace_region(s, "<!--SPOT:START-->", "<!--SPOT:END-->", spotlight_html(spot))
            s = replace_region(s, "<!--DEALS:START-->", "<!--DEALS:END-->",
                               "".join(card_html(d) for d in non_spot[:9]))
            s = set_upcoming(s)
            s = replace_region(s, "<!--JSONLD:START-->", "<!--JSONLD:END-->",
                               org_jsonld() + itemlist_jsonld(deals, SITE_URL + "/"))
        elif page == "deals.html":
            s = replace_region(s, "<!--DEALS:START-->", "<!--DEALS:END-->",
                               "".join(card_html(d) for d in deals[:24]))
            s = set_upcoming(s)
            s = replace_region(s, "<!--JSONLD:START-->", "<!--JSONLD:END-->",
                               itemlist_jsonld(deals, SITE_URL + "/deals.html"))
        # Serve minified CSS in production (smaller + harder to read for copycats)
        s = s.replace("css/styles.css?v=", "css/styles.min.css?v=").replace("css/fonts.css?v=", "css/fonts.min.css?v=")
        if s != orig:
            p.write_text(s, encoding="utf-8")
            print(f"  ✓ built {page}")
    seo = generate_seo_pages(deals)
    write_feed(deals)
    write_sitemap(seo)
    print(f"Pre-rendered {len(deals)} deals into the HTML.")


if __name__ == "__main__":
    main()
