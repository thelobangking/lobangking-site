#!/usr/bin/env python3
"""
fetch_images.py — attach each deal's real source image (with a 5-day cache)
===========================================================================

For every deal it reads the source page's **share image** (og:image / twitter:image
— the picture the publisher explicitly publishes for link previews), downloads it,
self-hosts it under images/deals/<id>.jpg, and points the deal at that local copy.
This makes the cards image-rich and seamless, and self-hosting means the picture
never goes missing from the site.

Retention: images are kept for 5 days; anything older than that, or belonging to a
deal that's gone, is deleted (the deal then falls back to the branded image and is
re-fetched fresh on the next run).

IMPORTANT (copyright): this ONLY uses the share-intended og:image/twitter:image and
always keeps the "via <source>" attribution + link on the card. It does NOT remove
watermarks or copyright marks — that would be infringement.

Runs in the daily pipeline (needs network → CI). Dependency-free.
"""
import json
import time
import pathlib
import urllib.request
import urllib.error
import concurrent.futures
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "deals.json"
IMGDIR = ROOT / "images" / "deals"
RETAIN_DAYS = 5
UA = "LobangKingBot/1.0 (+https://lobangking.sg; link-preview image fetcher)"
OG_KEYS = ("og:image", "og:image:url", "og:image:secure_url", "twitter:image", "twitter:image:src")


class OGParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.image = None

    def handle_starttag(self, tag, attrs):
        if tag != "meta" or self.image:
            return
        a = {k.lower(): (v or "") for k, v in attrs}
        key = (a.get("property") or a.get("name") or "").lower()
        if key in OG_KEYS and a.get("content", "").startswith("http"):
            self.image = a["content"]


def og_image(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")[:200000]
    except Exception:  # noqa: BLE001
        return None
    p = OGParser()
    try:
        p.feed(html)
    except Exception:  # noqa: BLE001
        return None
    return p.image


def download(img_url, dest):
    try:
        req = urllib.request.Request(img_url, headers={"User-Agent": UA})
        data = urllib.request.urlopen(req, timeout=25).read()
        if len(data) < 1500:          # too small to be a real hero image
            return False
        dest.write_bytes(data)
        return True
    except Exception:  # noqa: BLE001
        return False


def _process(d):
    local = IMGDIR / f"{d['id']}.jpg"
    if d.get("image") and local.exists():
        return (d["id"], d["image"])          # already have it
    url = d.get("url") or (d.get("source") or {}).get("url")
    if not url or not url.startswith("http"):
        return (d["id"], None)
    og = og_image(url)
    if not og:
        return (d["id"], None)
    return (d["id"], f"images/deals/{d['id']}.jpg") if download(og, local) else (d["id"], None)


def main():
    doc = json.loads(DATA.read_text(encoding="utf-8"))
    deals = doc.get("deals", [])
    IMGDIR.mkdir(parents=True, exist_ok=True)

    todo = [d for d in deals if not (d.get("image") and (IMGDIR / f"{d['id']}.jpg").exists())]
    got = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for did, path in ex.map(_process, todo):
            got[did] = path

    changed = 0
    for d in deals:
        p = got.get(d["id"])
        if p and d.get("image") != p:
            d["image"] = p
            changed += 1

    # 5-day retention: drop images that are orphaned or older than the window
    keep = {d["id"] for d in deals}
    now = time.time()
    pruned = 0
    for f in IMGDIR.glob("*.jpg"):
        stale = (now - f.stat().st_mtime) > RETAIN_DAYS * 86400
        if f.stem not in keep or stale:
            f.unlink()
            pruned += 1
            for d in deals:
                if d["id"] == f.stem:
                    d.pop("image", None)      # fall back / re-fetch next run

    if changed or pruned:
        DATA.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Images: fetched {changed}, pruned {pruned} (>{RETAIN_DAYS} days or orphaned).")


if __name__ == "__main__":
    main()
