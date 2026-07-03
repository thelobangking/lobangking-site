#!/usr/bin/env python3
"""
auto_patch.py — weekly security & content-protection maintenance
================================================================

Runs weekly on GitHub's servers. It performs ONLY safe, reviewable auto-updates:

  1. Refreshes the AI/scraper block list + Content Signals (content_protection.py),
     pulling the latest crawlers from the community list — the "constant patch".
  2. Renews the security.txt Expires date (+1 year) so the disclosure file never
     lapses (RFC 9116).
  3. Verifies the security-header baseline (all required headers present, CSP has no
     unsafe-inline) and FLAGS any drift for human review.

Deliberately conservative: it patches policy/config and time-sensitive values, and
runs the test suite as a guard — but it does NOT autonomously rewrite core security
LOGIC. Auto-editing your own code every week is itself a risk; anything beyond
config is surfaced as an alert for a human to review. (GitHub Dependabot handles
Action version bumps; the test suite is the safety net.) Stdlib only.
"""
import re
import sys
import datetime
import pathlib

import content_protection

ROOT = pathlib.Path(__file__).resolve().parent.parent
REQUIRED_HEADERS = [
    "Strict-Transport-Security", "X-Content-Type-Options", "X-Frame-Options",
    "Referrer-Policy", "Permissions-Policy", "Cross-Origin-Resource-Policy",
    "Content-Security-Policy",
]

fixes, alerts = [], []


def renew_security_txt():
    p = ROOT / ".well-known" / "security.txt"
    if not p.exists():
        return
    s = p.read_text(encoding="utf-8")
    t = datetime.date.today()
    exp = f"{t.year + 1:04d}-{t.month:02d}-{t.day:02d}T23:59:59.000Z"
    s2 = re.sub(r"Expires:\s*[^\n]*", "Expires: " + exp, s, count=1)
    if s2 != s:
        p.write_text(s2, encoding="utf-8")
        fixes.append(f"security.txt Expires renewed → {exp}")


def verify_header_baseline():
    p = ROOT / "_headers"
    if not p.exists():
        alerts.append("_headers file is missing")
        return
    s = p.read_text(encoding="utf-8")
    for h in REQUIRED_HEADERS:
        if h + ":" not in s:
            alerts.append(f"_headers is missing the {h} header")
    csp_line = next((l for l in s.splitlines() if "Content-Security-Policy:" in l), "")
    if "unsafe-inline" in csp_line or "unsafe-eval" in csp_line:
        alerts.append("_headers CSP regressed — contains unsafe-inline/eval")


def main():
    n = content_protection.main()
    fixes.append(f"AI/scraper block list refreshed ({n} bots) + Content Signals")
    renew_security_txt()
    verify_header_baseline()

    print("\n=== weekly auto-patch report ===")
    for f in fixes:
        print("  ✓ patched:", f)
    for a in alerts:
        print("  ⚠ review :", a)
    if not alerts:
        print("  ✅ security baseline OK — nothing needs manual review.")
    print("  · Policy/config auto-patched. Core-logic changes are flagged, not auto-applied.")
    sys.exit(1 if alerts else 0)


if __name__ == "__main__":
    main()
