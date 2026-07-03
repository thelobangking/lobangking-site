# 🔒 Security, reliability & performance

This document explains how LobangKing.sg is protected, what those protections do
and don't cover, and the free steps to make them strongest. It's written to be
honest — no security theatre.

---

## The honest threat model

LobangKing.sg is a **static site** (plain HTML/CSS/JS) on GitHub Pages. That's a
security advantage: **there is no server, database, login, or server-side code to
break into.** Most classic "hacks" (SQL injection, admin-panel takeover, server
RCE) simply don't apply here.

Two things people often ask for that are **not possible for any public website**,
and why we don't fake them:

- **"Make the data impossible to copy."** Anything a browser displays can be
  viewed and saved — that's how the web works. Tricks like disabling right-click
  or obfuscating code are bypassed in seconds and badly hurt your Google ranking
  and accessibility. We don't use them. To *deter bulk scraping*, the real lever
  is Cloudflare bot management + rate limiting (free — see below).
- **"Make the site unhackable."** Nothing is 100% unhackable. What we *can* do is
  shrink the attack surface to almost nothing and add strong, layered defences.

So we focus on what genuinely matters: **integrity** (nobody can inject or tamper
with the site), **availability** (bot/DDoS resilience), **no secrets leak**, and
**reliability + speed**.

---

## What's already built in

### 1. No secrets in the browser ✅
The site ships **zero credentials**. The optional affiliate API keys live in
**GitHub Secrets** and are only used by the automation that runs on GitHub's
servers — they are never written into `deals.json` or sent to a visitor's browser.

### 2. Cross-site scripting (XSS) defences ✅
Because deals come from third-party feeds, every value is treated as untrusted:
- All feed text is **HTML-escaped** before it's shown (`esc()` in `js/main.js`).
- All links are **scheme-checked** (`safeUrl()`): only `http(s)`, root-relative or
  anchor links are allowed, so a malicious `javascript:` link in a feed can't run.
  The aggregator drops non-web links too (defence in depth).
- A strict **Content-Security-Policy** is set on every page (`script-src 'self'`),
  so even if something slipped through, the browser won't execute injected script.
  There are **no inline scripts or inline event handlers** anywhere.

### 3. Security headers ✅
Defined in `_headers` (applied by Cloudflare Pages / Netlify, or via Cloudflare —
see below) and, where possible, mirrored as `<meta>` tags so core protection works
even on bare GitHub Pages:
| Header | Protects against |
|---|---|
| `Content-Security-Policy` | XSS, data injection, unwanted third-party loads |
| `X-Frame-Options: DENY` / `frame-ancestors 'none'` | Clickjacking & iframe "replication" |
| `X-Content-Type-Options: nosniff` | MIME-sniffing attacks |
| `Strict-Transport-Security` | Forces HTTPS, blocks downgrade attacks |
| `Referrer-Policy` | Privacy — limits referrer leakage |
| `Permissions-Policy` | Disables camera/mic/geolocation APIs you don't use |

### 4. Anti-bot on forms ✅
The newsletter / submit forms have two silent, free defences (`js/main.js`):
- a **honeypot** field hidden from humans — bots fill it and get rejected;
- a **time trap** — submissions faster than 1.5s are treated as automated.

When you connect a real form backend, add **Cloudflare Turnstile** (free, below)
for a proper CAPTCHA-grade gate, and prefer a provider with built-in spam filtering
such as Formspree.

### 5. Reliability & performance ✅
- A **service worker** (`sw.js`) caches the site so it loads instantly on repeat
  visits and **keeps working offline**. Deals use a *network-first* strategy so
  they stay fresh; everything else is *cache-first* for speed.
- The automation has a **safety net**: a transient feed outage will never wipe your
  live deals (it keeps the last good `deals.json`).
- **Zero third-party requests** — fonts are **self-hosted** and there's no external
  analytics call, so the CSP is locked to `'self'` with **no outside origins at all**.
  No build dependencies means nothing to compromise in a supply-chain attack.
- **Handles traffic spikes:** large deal lists render in pages ("load more") with
  CSS `content-visibility`, so the browser stays smooth even with hundreds of deals;
  and static hosting behind a CDN (GitHub Pages / Cloudflare) absorbs high volume.
- Long-cache headers for static assets; short cache for the daily deals file.

### 6. Responsible disclosure ✅
`/.well-known/security.txt` (RFC 9116) tells researchers how to report issues.
**Update the contact email** in that file to one you monitor.

---

## 🟧 Do this for the strongest free protection: put Cloudflare in front

GitHub Pages can't run a firewall or set every header. Routing your domain through
**Cloudflare's free plan** adds enterprise-grade defences at no cost:

1. Create a free account at [cloudflare.com](https://www.cloudflare.com) and add
   your domain `lobangking.sg`.
2. Update your domain's nameservers to the two Cloudflare gives you.
3. Add a `CNAME` record pointing to `<your-username>.github.io` (proxied — orange
   cloud ON).
4. In the Cloudflare dashboard, turn on:
   - **SSL/TLS → Full (strict)** and **Always Use HTTPS**.
   - **Security → Bots → Bot Fight Mode** (free automated-bot blocking).
   - **Security → DDoS** (on by default — absorbs volumetric attacks).
   - **Security → WAF → Managed Rules** (free managed ruleset).
   - **Rules → Rate limiting** — e.g. cap requests per IP to deter scrapers.
   - **Rules → Transform Rules → HTTP Response Headers** — add the headers from
     `_headers` so they apply on GitHub Pages too.
5. Optional: **Under Attack Mode** is one click if you're ever targeted.

That single step gives you a real WAF, DDoS protection, bot mitigation and full
security headers — all free.

### Cloudflare Turnstile (free CAPTCHA) for forms
When you wire up the newsletter/submit forms to a backend, add
[**Turnstile**](https://www.cloudflare.com/products/turnstile/) — a free, privacy-
friendly CAPTCHA. Drop its widget into the form and verify the token server-side
(Formspree and most form services support it). This stops automated form spam cold.

---

## 🛡️ Making your content harder to copy

**Honest reality first:** you cannot make a public website un-copyable. Anything a
browser renders can be saved, and aggressive tricks (disabling right-click
site-wide, dev-tools blockers, heavy JS obfuscation) are bypassed in seconds and
badly hurt your SEO, speed and accessibility. So we add the measures that *actually*
deter copycats without hurting you:

1. **Your real moat — daily freshness.** The site rebuilds itself every morning, so
   a scraped clone is **out of date within 24 hours**. A static copy can't keep up
   with your automation. This is your strongest, zero-cost protection.
2. **AI/scraper blocking** (`robots.txt`) — known content-harvesters and AI-training
   crawlers (GPTBot, CCBot, ClaudeBot, Google-Extended, Bytespider, PerplexityBot,
   Diffbot, etc.) are disallowed, while search engines stay welcome.
3. **Content canary + console notice** (`js/protect.js`) — an invisible, unique
   marker rides along with any verbatim copy (easy to prove a clone), plus a
   copyright notice in the dev console. Image drag/right-click is discouraged
   (images only — text stays selectable for real users and SEO).
4. **Minified CSS** (`scripts/minify.py`, run by the build) — smaller *and* harder
   to read than the source.
5. **No hotlinking / no embedding** — `Cross-Origin-Resource-Policy: same-origin`
   stops other sites loading your images/assets, and `frame-ancestors 'none'`
   stops them iframing your pages. (Both come from `_headers` / Cloudflare.)
6. **Cloudflare anti-scrape (free, strongest lever):** once your domain is proxied,
   turn on **Bot Fight Mode**, **rate limiting** (cap requests per IP), and
   **Hotlink Protection** (Scrape Shield). This blocks the bulk-scraping that a
   copycat would need to clone you at scale. **AI Scrapers & Crawlers** can be
   blocked in one click under Security → Bots.
7. **Legal backstop:** your Terms (in `privacy.html`) prohibit wholesale copying;
   with the canary as evidence you can file a DMCA/host takedown against a clone.

What we deliberately did **not** add: site-wide right-click disabling and dev-tools
detection. They don't stop a determined copier, they punish legitimate users, and
they hurt your search ranking — a bad trade.

## 🔬 Advanced 2026 layers (added) + what's still lacking

After researching current (2026) best practice, here's what was added and the one
honest gap that remains.

**Added in this pass:**
- **Trusted Types–ready code** — every place the site writes HTML to the DOM now
  goes through one audited sink (`setHTML` in `js/main.js`). This is the strongest
  defence against DOM-based XSS (Baseline 2026). It's shipped in **report-only**
  mode via `Content-Security-Policy-Report-Only: require-trusted-types-for 'script'`
  so it can't break anything. **To enforce it** (after a quick browser test), move
  `require-trusted-types-for 'script'; trusted-types lk-sanitizer` into the main CSP.
- **CSP violation reporting** — `report-to` + `Reporting-Endpoints` in `_headers`.
  Point it at a free **report-uri.com** account (replace `YOUR_SUBDOMAIN`) to get
  alerted the moment anything tries to violate your policy.
- **Speculation Rules API** — pages **prerender on hover**, so internal navigation
  feels instant. Progressive: ignored by browsers that don't support it.
- **Font preloading** — the primary fonts are preloaded to cut LCP (the main Core
  Web Vitals load metric).
- **Free uptime monitoring** — `.github/workflows/health-check.yml` pings the site
  every 30 min and fails (emailing you) if it's down. For a full status page with
  history + Slack/Telegram alerts, add **[Upptime](https://upptime.js.org)** (free).

**⚠️ The one real gap that remains: `style-src 'unsafe-inline'`.**
Your script CSP is already locked to `'self'` (no `unsafe-inline` on scripts — the
important one). But `style-src` still allows `'unsafe-inline'`, only because the
pages use a handful of inline `style="…"` attributes. Security scanners
(securityheaders.com, Mozilla Observatory) will flag this as the one thing between
you and an A+. **The fix:** move those inline `style="…"` attributes into CSS
classes, then change `style-src 'self' 'unsafe-inline'` → `style-src 'self'`. It's a
mechanical change with no functional risk — worth doing, but it touches several
files, so it's best done as its own focused pass. Style injection can't execute
code, so this is a polish item, not an open door.

## 🔄 Self-refreshing content protection + weekly auto-patch

The AI-crawler landscape changes almost weekly, so the anti-scraping policy is built
to **stay current on its own**:

- **`scripts/content_protection.py`** regenerates `robots.txt`, `ai.txt` and the
  `X-Robots-Tag: noai, noimageai` header. It blocks a comprehensive list of
  AI-training crawlers and content-harvesters (GPTBot, ClaudeBot, CCBot,
  Google-Extended, Bytespider, PerplexityBot, Meta-ExternalAgent, Applebot-Extended,
  and ~45 more), emits **Content Signals** (`search=yes, ai-input=no, ai-train=no`),
  and adds a **TDM (text-&-data-mining) reservation** in `ai.txt` — while keeping real
  search engines welcome.
- **Constant-patch stance:** each run also pulls the newest crawlers from the
  community-maintained [`ai-robots-txt/ai.robots.txt`](https://github.com/ai-robots-txt/ai.robots.txt)
  project (auto-updated from Dark Visitors) and merges them in — so new bots are
  blocked as they appear. If the fetch fails, the built-in list is used.
- **`scripts/auto_patch.py` + `.github/workflows/auto-patch.yml` (weekly):** refreshes
  the block list, **renews `security.txt`** (+1 year, so it never lapses), **verifies
  the security-header baseline** (all headers present, CSP has no `unsafe-inline`) and
  **flags any drift for review**, then runs the **test suite as a guard** before
  committing. It only auto-updates *policy/config and time-sensitive values* — it does
  **not** autonomously rewrite core security *logic* (auto-editing your own code weekly
  is itself a risk), so anything non-trivial is surfaced as an alert, not silently
  changed. Action version bumps are handled by Dependabot.

**Enforcement (honest):** robots/ai.txt/headers are honoured by *well-behaved*
crawlers; bad actors ignore them. The real teeth are **Cloudflare's AI Crawl Control /
AI Labyrinth / pay-per-crawl** (2025–2026) — free, one toggle once your domain is on
Cloudflare, and it blocks or challenges AI bots at the edge regardless of what they
claim to be. Turn it on under **Security → Bots → AI Crawl Control**.

## Optional hardening

- **Self-hosted fonts — already done.** Run `bash scripts/get_fonts.sh` once to fetch
  the woff2 files into `/fonts`; the CSP already has no external origins
  (`font-src 'self'`). Until you run it, the site falls back to system fonts.
- **Even stricter CSP (optional):** drop `'unsafe-inline'` from `style-src` by moving
  the handful of inline `style=""` attributes into CSS classes. Style injection can't
  execute code, so this is a low-risk final polish rather than a real gap.
- **Enable Dependabot / secret scanning** in your GitHub repo settings (free) so
  you're alerted if a credential is ever committed by mistake.
- **Branch protection** on `main` so only reviewed changes ship.

---

## Reporting a problem
Found a security issue? Email the address in
[`/.well-known/security.txt`](.well-known/security.txt). Please don't open a public
issue for anything sensitive.
