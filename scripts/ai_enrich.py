#!/usr/bin/env python3
"""
ai_enrich.py — OPTIONAL 2026 AI enhancement for the deal aggregator
===================================================================

Uses a Large Language Model to POLISH the deals the aggregator already fetched:
it cleans up titles, writes a tidy one-line summary, and double-checks the
category — working ONLY from the real text that was fetched.

Hard guarantee against "fake news": the model is explicitly instructed never to
invent prices, dates, discounts, codes or store names. If the API isn't
configured or anything goes wrong, the original (rule-based) deals are returned
unchanged. Dependency-free (standard library only).

Provider-agnostic — works with any OpenAI-compatible chat endpoint. Free options
in 2026 include:
  • GitHub Models   AI_API_URL=https://models.github.ai/inference   (key: a GitHub token)
  • Groq            AI_API_URL=https://api.groq.com/openai/v1
  • Google Gemini   AI_API_URL=https://generativelanguage.googleapis.com/v1beta/openai
Set AI_API_URL, AI_API_KEY and AI_MODEL as environment variables / GitHub Secrets.
"""
import os
import re
import json
import urllib.request

VALID_CATEGORIES = ["food", "electronics", "home", "travel", "transport",
                    "fashion", "entertainment", "finance", "online"]

SYSTEM_PROMPT = (
    "You are a meticulous editor for a Singapore deals website. You rewrite ONLY using "
    "the information provided. You MUST NOT invent or change any fact — no prices, dates, "
    "percentages, discount amounts, promo codes, or store names that are not already in the "
    "input. If you are unsure, keep the original text. Never add hype or clickbait. "
    "Return STRICT JSON only."
)


def _chat(url, key, model, messages, timeout=45):
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    req = urllib.request.Request(
        url.rstrip("/") + "/chat/completions", data=body,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key,
                 "User-Agent": "LobangKingBot/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"]


def _parse_json(text):
    text = re.sub(r"^```[a-z]*\s*|\s*```$", "", text.strip(), flags=re.I)
    return json.loads(text)


def _enrich_batch(batch, url, key, model):
    payload = [{"id": d["id"], "title": d.get("title", ""), "desc": d.get("desc", ""),
                "category": (d.get("categories") or ["online"])[0]} for d in batch]
    user = (
        "Improve these deals. For each, return: id (unchanged), title (<=80 chars, clear, no hype), "
        "desc (<=140 chars, factual, drawn ONLY from the given title/desc), and category "
        "(exactly one of: " + ", ".join(VALID_CATEGORIES) + "). Do not invent facts.\n"
        'Return JSON shaped {"deals":[{"id":...,"title":...,"desc":...,"category":...}, ...]}.\n\n'
        + json.dumps(payload, ensure_ascii=False))
    out = _parse_json(_chat(url, key, model,
                            [{"role": "system", "content": SYSTEM_PROMPT},
                             {"role": "user", "content": user}]))
    by_id = {}
    for it in (out.get("deals") if isinstance(out, dict) else out) or []:
        if isinstance(it, dict) and it.get("id"):
            by_id[it["id"]] = it
    return by_id


def enrich(deals, cfg=None):
    cfg = cfg or {}
    url = os.environ.get("AI_API_URL", "")
    key = os.environ.get("AI_API_KEY", "")
    model = os.environ.get("AI_MODEL", cfg.get("model", ""))
    if not (cfg.get("enabled") and url and key and model):
        return deals  # AI disabled or not configured → use the original deals untouched

    size = int(cfg.get("batch_size", 12))
    improved = 0
    for i in range(0, len(deals), size):
        batch = deals[i:i + size]
        try:
            patches = _enrich_batch(batch, url, key, model)
        except Exception as e:  # noqa: BLE001
            print(f"  ! AI enrich batch {i // size}: {type(e).__name__}: {e}")
            continue
        for d in batch:
            p = patches.get(d["id"])
            if not p:
                continue
            t = str(p.get("title", "")).strip()
            ds = str(p.get("desc", "")).strip()
            c = str(p.get("category", "")).strip().lower()
            if 4 <= len(t) <= 120:
                d["title"] = t
            if 4 <= len(ds) <= 220:
                d["desc"] = ds
            if c in VALID_CATEGORIES:
                d["categories"] = [c]
            improved += 1
    print(f"  ✓ AI enrich: polished {improved} deals")
    return deals
