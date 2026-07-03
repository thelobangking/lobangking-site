#!/usr/bin/env python3
"""
check_stock.py — auto-flag deals that are sold out / fully redeemed
===================================================================

Visits each deal's source URL and looks for DEFINITIVE "gone" signals — schema.org
availability (OutOfStock / SoldOut / Discontinued) or clear phrases like "sold out",
"fully redeemed", "promotion has ended". When found it sets the deal's
status = "claimed" (it is NOT deleted) so the card and the deal page show a tasteful
"Fully claimed" state instead of a dead link.

Conservative by design: only strong signals flip a deal, transient errors never do,
and the daily aggregator resets statuses — so a false positive self-corrects within a
day. Runs daily (needs network → CI). Dependency-free.
"""
import re
import json
import pathlib
import urllib.request
import urllib.error
import concurrent.futures

import build_pages

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "deals.json"
UA = "LobangKingBot/1.0 (+https://lobangking.sg; availability checker)"

SIGNALS = re.compile("|".join([
    r"schema\.org/(?:OutOfStock|SoldOut|Discontinued)",
    r'"availability"\s*:\s*"[^"]*(?:OutOfStock|SoldOut|Discontinued)',
    r"\bout\s+of\s+stock\b",
    r"\bsold\s+out\b",
    r"\bfully\s+redeemed\b",
    r"\bfully\s+claimed\b",
    r"\bno\s+longer\s+available\b",
    r"\bpromotion\s+has\s+ended\b",
    r"\bthis\s+(?:deal|offer|promotion)\s+has\s+ended\b",
]), re.I)


def claimed_status(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")[:300000]
        return bool(SIGNALS.search(html))
    except urllib.error.HTTPError as e:
        return e.code in (404, 410)           # page gone → treat as claimed
    except Exception:  # noqa: BLE001 — transient → do NOT flip
        return False


def main():
    doc = json.loads(DATA.read_text(encoding="utf-8"))
    deals = doc.get("deals", [])

    def check(d):
        u = d.get("url", "")
        return (d["id"], claimed_status(u) if u.startswith("http") else False)

    flags = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for did, gone in ex.map(check, deals):
            flags[did] = gone

    changed = 0
    for d in deals:
        if flags.get(d["id"]) and d.get("status") != "claimed":
            d["status"] = "claimed"
            changed += 1

    if changed:
        DATA.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
        build_pages.main()
    print(f"Stock check: {changed} deal(s) marked fully claimed.")


if __name__ == "__main__":
    main()
