#!/usr/bin/env python3
"""
check_links.py — remove deals whose outbound link is definitively dead
======================================================================

Runs in CI (it needs network). For every deal it requests the `url`; if the link
returns a DEFINITIVE dead status (404 / 410 / 451) the deal is removed and the site
rebuilt. Transient problems (timeouts, connection resets, 403/429/5xx) are IGNORED
— we never delete a real deal because of a temporary blip. Dependency-free.
"""
import json
import pathlib
import urllib.request
import urllib.error
import concurrent.futures

import build_pages

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "deals.json"
DEAD = {404, 410, 451}                      # only these mean "gone for good"
UA = "LobangKingBot/1.0 (+https://lobangking.sg; link checker)"


def status(url):
    if not url or not url.startswith("http"):
        return None                          # nothing to check (#, mailto, etc.)
    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:                        # noqa: BLE001 — transient → keep the deal
        return None


def main():
    doc = json.loads(DATA.read_text(encoding="utf-8"))
    deals = doc.get("deals", [])
    urls = [d.get("url", "") for d in deals]
    codes = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        for u, c in zip(urls, ex.map(status, urls)):
            codes[u] = c

    kept = [d for d in deals if codes.get(d.get("url", "")) not in DEAD]
    removed = len(deals) - len(kept)
    if removed:
        for d in kept:
            d.pop("spotlight", None)
        if kept:
            kept[0]["spotlight"] = True
        doc["deals"] = kept
        DATA.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
        build_pages.main()
    print(f"Link check: removed {removed} dead-linked deal(s); {len(kept)} live.")


if __name__ == "__main__":
    main()
