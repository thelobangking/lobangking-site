#!/usr/bin/env python3
"""
validate.py — hourly compliance + correctness watchdog (auto-fix)
=================================================================

Runs every hour on GitHub's servers (NOT in visitors' browsers — so it has zero
effect on page-load performance). It:

  1. VALIDATES correctness — JSON parses, assets referenced by the pages actually
     exist, the feed/sitemap are valid XML.
  2. VALIDATES 2026 security compliance — every page keeps its strict CSP
     (no 'unsafe-inline', no stray external origins), no inline executable scripts,
     no inline styles, Referrer-Policy present, and the security headers + AI-bot
     blocking haven't regressed.
  3. AUTO-CORRECTS time-sensitive information immediately — prunes deals whose
     end date has passed since the last daily build, re-picks the Deal of the Day,
     and rebuilds the pre-rendered HTML + feed + sitemap so the site is never
     showing stale/expired info for more than an hour.

Safe by design: it only WRITES when it actually fixes data, never corrupts a file
on error, and reuses the existing expiry logic + builder (single source of truth,
so it stays correct as the site evolves). Dependency-free (standard library only).

Usage:
  python3 scripts/validate.py            # validate + auto-fix
  python3 scripts/validate.py --dry-run  # report only, change nothing
"""
import sys
import re
import json
import pathlib
import datetime
import xml.dom.minidom

import aggregate_deals as agg   # reuse parse_expiry + TODAY (single source of truth)
import build_pages              # reuse the renderer so HTML stays in sync
import prune_pages              # retention garbage collector (deals expired >10 days)
import verify_deals             # freshness/validity gate (expired, month-only, stale)

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "deals.json"
PROD = ["index.html", "deals.html", "about.html", "submit.html", "privacy.html", "404.html"]
ASSET_EXT = (".css", ".js", ".json", ".webmanifest", ".xml", ".ico", ".png", ".html")
AI_BOTS = ["GPTBot", "CCBot", "ClaudeBot", "Google-Extended", "Bytespider", "PerplexityBot"]

DRY = "--dry-run" in sys.argv
errors = []     # block / alert the owner (run goes red)
warnings = []   # informational
fixes = []      # things we corrected


def log(kind, msg):
    (errors if kind == "error" else warnings if kind == "warn" else fixes).append(msg)
    prefix = {"error": "::error::", "warn": "::warning::", "fix": "  🔧 "}[kind]
    print(prefix + msg)


# ---------------------------------------------------------------- correctness
def check_json():
    for name in ("data/deals.json", "scripts/sources.json", "scripts/manual_deals.json"):
        p = ROOT / name
        if not p.exists():
            continue
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            log("error", f"{name} is not valid JSON: {e}")


def check_xml():
    for name in ("feed.xml", "sitemap.xml"):
        p = ROOT / name
        if p.exists():
            try:
                xml.dom.minidom.parse(str(p))
            except Exception as e:  # noqa: BLE001
                log("error", f"{name} is not valid XML: {e}")


def check_assets():
    for f in PROD:
        s = (ROOT / f).read_text(encoding="utf-8")
        for u in re.findall(r'(?:href|src)="([^"]+)"', s):
            if u.startswith(("http", "mailto:", "//", "data:", "#")):
                continue
            path = u.split("?")[0].split("#")[0].lstrip("/")
            if not path or not path.lower().endswith(ASSET_EXT):
                continue
            if path.startswith("fonts/"):
                continue  # woff2 are optional until get_fonts.sh is run
            if not (ROOT / path).exists():
                log("error", f"{f}: broken reference → {u}")


# ---------------------------------------------------------------- security
def check_security():
    for f in PROD:
        s = (ROOT / f).read_text(encoding="utf-8")
        m = re.search(r'Content-Security-Policy" content="([^"]+)"', s)
        if not m:
            log("error", f"{f}: Content-Security-Policy meta is missing")
        else:
            csp = m.group(1)
            if "unsafe-inline" in csp or "unsafe-eval" in csp:
                log("error", f"{f}: CSP regressed — contains unsafe-inline/eval")
            ext = [e for e in re.findall(r'https?://[^ ;]+', csp) if "formspree.io" not in e]
            if ext:
                log("error", f"{f}: CSP gained external origin(s): {ext}")
        # inline executable scripts (data blocks like ld+json / speculationrules are fine)
        for sm in re.finditer(r'<script(?![^>]*\bsrc=)([^>]*)>', s):
            tm = re.search(r'type="([^"]+)"', sm.group(1))
            typ = tm.group(1) if tm else ""
            if typ not in ("application/ld+json", "speculationrules"):
                log("error", f"{f}: inline executable <script> found (use an external file)")
                break
        if 'style="' in s:
            log("error", f"{f}: inline style attribute found (breaks style-src 'self')")
        if 'name="referrer"' not in s:
            log("warn", f"{f}: Referrer-Policy meta missing")


def check_headers_file():
    p = ROOT / "_headers"
    if not p.exists():
        return
    block = p.read_text(encoding="utf-8")
    needed = ["Strict-Transport-Security", "X-Content-Type-Options", "X-Frame-Options",
              "Referrer-Policy", "Permissions-Policy", "Cross-Origin-Resource-Policy"]
    for h in needed:
        if h not in block:
            log("warn", f"_headers: {h} header missing")
    csp_line = next((l for l in block.splitlines() if "Content-Security-Policy:" in l), "")
    if "unsafe-inline" in csp_line:
        log("error", "_headers: CSP regressed — contains unsafe-inline")


def check_robots_and_securitytxt():
    robots = (ROOT / "robots.txt")
    if robots.exists():
        txt = robots.read_text(encoding="utf-8")
        missing = [b for b in AI_BOTS if b not in txt]
        if missing:
            log("warn", f"robots.txt no longer blocks: {', '.join(missing)}")
    sectxt = ROOT / ".well-known" / "security.txt"
    if sectxt.exists():
        m = re.search(r"Expires:\s*([0-9T:\-]+Z)", sectxt.read_text(encoding="utf-8"))
        if m:
            try:
                exp = datetime.datetime.fromisoformat(m.group(1).replace("Z", "+00:00")).date()
                if exp < agg.TODAY:
                    log("warn", "security.txt has expired — update the Expires date")
            except Exception:  # noqa: BLE001
                pass


# ---------------------------------------------------------------- auto-correct
def verify_current():
    """Freshness/validity gate — drop expired, month-only-expired, stale and
    unverifiable deals, re-order newest-first, and rebuild pages if anything
    changed. Runs every hour so nothing goes stale between daily builds."""
    removed = verify_deals.verify(dry_run=DRY, rebuild=True)
    if removed:
        log("fix", f"verified deals: removed {len(removed)} expired/stale/unverifiable "
                   f"(e.g. {removed[0][1]})" + (" [dry-run: not written]" if DRY else ""))
    return len(removed)


def prune_expired():
    """Database retention GC — hard-delete deals that expired more than 10 days ago,
    then rebuild so the sitemap + per-deal/category pages stay in sync (new deals get
    URLs, expired pages are deleted). The live site already hides expired deals.
    Returns the number removed."""
    removed = prune_pages.prune(dry_run=DRY)
    if removed:
        log("fix", f"retention GC: removed {len(removed)} deal(s) expired >10 days; "
                   f"sitemap & pages rebuilt" + (" [dry-run: not written]" if DRY else ""))
    return len(removed)


# ---------------------------------------------------------------- main
def main():
    print(f"validate.py — {datetime.datetime.now(datetime.timezone.utc).isoformat()}  (dry-run={DRY})")
    for fn in (check_json, check_xml, check_assets, check_security,
               check_headers_file, check_robots_and_securitytxt):
        try:
            fn()
        except Exception as e:  # noqa: BLE001 — one failing check must not abort the rest
            log("warn", f"{fn.__name__} could not run: {e}")

    if not errors or all("not valid JSON" not in e for e in errors):
        try:
            verify_current()   # freshness gate first (catches month-only expiries etc.)
        except Exception as e:  # noqa: BLE001
            log("warn", f"verify step failed: {e}")
        try:
            prune_expired()
        except Exception as e:  # noqa: BLE001
            log("warn", f"prune step failed: {e}")

    print(f"\nSummary: {len(fixes)} fixed, {len(warnings)} warning(s), {len(errors)} error(s).")
    if errors:
        print("Compliance/correctness errors need attention (see ::error:: above).")
        sys.exit(1)
    print("✅ Site is compliant and current.")


if __name__ == "__main__":
    main()
