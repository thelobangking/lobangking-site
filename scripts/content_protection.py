#!/usr/bin/env python3
"""
content_protection.py — comprehensive, self-refreshing anti-scraping policy
===========================================================================

The AI-crawler landscape changes almost weekly, so this file is built to stay
CURRENT. It regenerates:

  • robots.txt  — search engines welcome; AI-training crawlers & content-harvesters
                  blocked; plus a Content Signals line (search=yes, ai-train=no).
  • ai.txt      — an explicit AI-usage / TDM (text-&-data-mining) reservation.
  • _headers    — ensures `X-Robots-Tag: noai, noimageai` is present.

Constant-patch stance: on each run it pulls the latest bot list from the
community-maintained project github.com/ai-robots-txt/ai.robots.txt (auto-updated
from Dark Visitors) and MERGES it with the built-in list — so new crawlers are
blocked as they appear. If the fetch fails (offline), the built-in list is used.

HONEST NOTE: robots/ai.txt/headers are honored by *well-behaved* crawlers. Bad
actors ignore them — real enforcement needs Cloudflare's AI Crawl Control / bot
management (free; see SECURITY.md). This file makes your intent explicit and legally
useful, and keeps the block list current. Stdlib only.
"""
import re
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://lobangking.sg"
UA = "LobangKingBot/1.0 (+https://lobangking.sg; content-protection updater)"
UPSTREAM = "https://raw.githubusercontent.com/ai-robots-txt/ai.robots.txt/main/robots.txt"

# Content Signals (Cloudflare-led 2025 standard): allow search, refuse AI use.
CONTENT_SIGNAL = "search=yes, ai-input=no, ai-train=no"

# Built-in fallback list of AI-training / harvesting crawlers (kept broad; the
# weekly refresh from ai.robots.txt adds any newcomers on top of these).
BUILTIN_BOTS = [
    "AI2Bot", "Ai2Bot-Dolma", "Amazonbot", "anthropic-ai", "Applebot-Extended",
    "Brightbot 1.0", "Bytespider", "CCBot", "ChatGPT-User", "Claude-Web", "Claude-User",
    "Claude-SearchBot", "ClaudeBot", "cohere-ai", "cohere-training-data-crawler",
    "Crawlspace", "DeepSeekBot", "Diffbot", "DuckAssistBot", "FacebookBot",
    "FriendlyCrawler", "Google-Extended", "GoogleOther", "GoogleOther-Image",
    "GoogleOther-Video", "GPTBot", "iaskspider/2.0", "ICC-Crawler", "ImagesiftBot",
    "img2dataset", "ISSCyberRiskCrawler", "Kangaroo Bot", "Meta-ExternalAgent",
    "Meta-ExternalFetcher", "OAI-SearchBot", "omgili", "omgilibot", "PanguBot",
    "Perplexity-User", "PerplexityBot", "PetalBot", "Scrapy", "SemrushBot-OCOB",
    "Sidetrade indexer bot", "Timpibot", "TurnitinBot", "VelenPublicWebCrawler",
    "Webzio-Extended", "YouBot", "magpie-crawler", "DataForSeoBot",
]


def fetch_upstream():
    """Pull the latest User-agent list from the community project (best effort)."""
    try:
        req = urllib.request.Request(UPSTREAM, headers={"User-Agent": UA})
        text = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
    except Exception:  # noqa: BLE001 — offline/unreachable → use built-in
        return []
    bots = re.findall(r"^\s*User-agent:\s*(.+?)\s*$", text, re.M | re.I)
    # sanitise: only accept plausible, safe user-agent tokens (avoid injecting junk)
    return [b for b in bots if b and b != "*" and len(b) <= 60
            and re.match(r"^[A-Za-z0-9 _\-\./+:;()]+$", b)]


def build_bot_list():
    bots = set(BUILTIN_BOTS)
    bots.update(fetch_upstream())
    return sorted(bots, key=str.lower)


def write_robots(bots):
    out = [
        "# LobangKing.sg — robots policy.",
        "# Search engines are welcome. AI-training crawlers & content-harvesters are",
        "# blocked. Block list auto-refreshed (incl. community data from",
        "# github.com/ai-robots-txt/ai.robots.txt) by scripts/content_protection.py.",
        "",
        "User-agent: *",
        f"Content-Signal: {CONTENT_SIGNAL}",
        "Allow: /",
        "Disallow: /privacy.html",
        "",
        f"# --- AI / scraper crawlers ({len(bots)}): full block ---",
    ]
    out += [f"User-agent: {b}" for b in bots]
    out += ["Disallow: /", "", f"Sitemap: {SITE}/sitemap.xml", ""]
    (ROOT / "robots.txt").write_text("\n".join(out), encoding="utf-8")


def write_ai_txt(bots):
    out = [
        "# ai.txt — AI usage policy for LobangKing.sg",
        "# We RESERVE this site's content from AI training and AI input (TDM reservation).",
        "# Content may not be used to train, fine-tune or ground AI models, or be ingested",
        "# as AI input, without prior written permission.",
        "",
        f"Content-Signal: {CONTENT_SIGNAL}",
        "User-Agent: *",
        "Disallow: /",
        "",
        "# Explicitly named AI crawlers (also blocked in robots.txt):",
    ]
    out += [f"# - {b}" for b in bots]
    (ROOT / "ai.txt").write_text("\n".join(out) + "\n", encoding="utf-8")


def ensure_header():
    """Make sure X-Robots-Tag: noai, noimageai is present in _headers."""
    p = ROOT / "_headers"
    if not p.exists():
        return False
    s = p.read_text(encoding="utf-8")
    if "X-Robots-Tag" in s:
        return False
    s = s.replace("  X-Content-Type-Options: nosniff",
                  "  X-Content-Type-Options: nosniff\n  X-Robots-Tag: noai, noimageai", 1)
    p.write_text(s, encoding="utf-8")
    return True


def main():
    bots = build_bot_list()
    write_robots(bots)
    write_ai_txt(bots)
    added_header = ensure_header()
    print(f"Content protection refreshed: {len(bots)} AI/scraper bots blocked"
          + (" (+X-Robots-Tag header)" if added_header else "") + ".")
    return len(bots)


if __name__ == "__main__":
    main()
