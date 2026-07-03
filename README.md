# 👑 LobangKing.sg — Every Deal in Singapore

A fast, friendly, mobile-first deals website for Singapore. Verified daily promos, freebies and discounts across food, electronics, travel, finance and more.

Built as a **static site** (plain HTML/CSS/JS) — no build step, no framework, no server. Perfect for free hosting on **GitHub Pages**.

---

## ✨ Features

- **Light & dark mode** — auto-detects the visitor's system preference and remembers their choice. Designed to be comfortable for all ages.
- **Fully responsive** — looks great from a small phone to a wide desktop (1-, 2- and 3-column deal grids).
- **Live search & category filter** — instant, no page reload.
- **Sort** deals by hottest, ending soon, or newest.
- **Deal of the Day** spotlight.
- **Upvote ("heat")** and **one-tap sharing** (WhatsApp, Telegram, X, copy link — uses the native share sheet on mobile).
- **Copy-code chips**, expiry timers, and clear "how to claim" labels.
- **Newsletter & submit-a-deal** forms (ready to connect to a form service).
- **Installable PWA** — visitors can "Add to Home Screen".
- **SEO-ready** — meta tags, Open Graph/social cards, `sitemap.xml`, `robots.txt`, and structured data.
- **Accessible** — keyboard focus styles, reduced-motion support, AA-contrast colours, large tap targets.

---

## 📁 Project structure

```
.
├── index.html              # Homepage (hero, search, spotlight, hot deals)
├── deals.html              # Browse all deals (search + filter + sort)
├── about.html              # About / how it works / advertise
├── submit.html             # Submit-a-deal form
├── privacy.html            # Privacy, terms & disclaimer
├── 404.html                # Friendly not-found page
├── css/
│   └── styles.css          # Full design system (light + dark themes)
├── js/
│   └── main.js             # Theming, search, filter, share, vote, render
├── data/
│   └── deals.json          # ← EDIT THIS to add or change deals
├── images/                 # Logo, favicons, PWA icons, social image
├── manifest.webmanifest    # PWA manifest
├── robots.txt              # SEO
├── sitemap.xml             # SEO
├── .nojekyll               # Tells GitHub Pages to serve files as-is
├── .github/workflows/
│   └── update-deals.yml    # FREE daily scheduler (GitHub Actions)
└── scripts/
    ├── aggregate_deals.py  # Daily deal aggregator (stdlib only)
    ├── sources.json        # Which feeds/APIs to pull from
    ├── manual_deals.json   # Optional always-on curated deals
    └── test_aggregate.py   # Offline self-test
```

---

## 🚀 Deploy to GitHub Pages (free)

1. Create a new repository on GitHub (e.g. `lobangking`).
2. Upload **everything inside this folder** to the repository root (or use `git push`).
3. In the repo, go to **Settings → Pages**.
4. Under *Build and deployment*, set **Source = Deploy from a branch**, **Branch = `main`**, folder **`/ (root)`**, then **Save**.
5. Wait ~1 minute. Your site goes live at `https://<your-username>.github.io/<repo-name>/`.

### Using your own domain (lobangking.sg)
1. Add a file named `CNAME` (no extension) to the repo root containing one line: `lobangking.sg`
2. At your domain registrar, point the domain to GitHub Pages (an `A`/`ALIAS` record to GitHub's IPs, or a `CNAME` record to `<your-username>.github.io`).
3. In **Settings → Pages**, enter the custom domain and enable **Enforce HTTPS**.

> Tip: the `404.html` page uses root-absolute paths (`/css/...`), which is correct for a custom domain or a user/organisation Pages site. If you deploy to a project sub-path (`username.github.io/repo/`), change those `/...` paths in `404.html` to include `/repo/`.

---

## ✏️ How to update deals (no coding needed)

Open **`data/deals.json`** and edit the `deals` array. Each deal looks like this:

```json
{
  "id": "unique-id",
  "title": "FREE Bubble Tea",
  "store": "Gong Cha · Islandwide",
  "categories": ["food"],
  "icon": "🧋",
  "spotlight": false,
  "badges": [{ "type": "free", "label": "FREE" }],
  "access": { "type": "easy", "label": "Walk in — no purchase needed" },
  "code": "OPTIONALCODE",
  "desc": "Short description of the deal and any catch.",
  "expiry": "Ends 5 Jul",
  "heat": 120,
  "url": "https://link-to-the-deal"
}
```

- **`categories`** — any of: `food`, `electronics`, `home`, `travel`, `transport`, `fashion`, `entertainment`, `finance`, `online`.
- **`badges[].type`** — `free`, `discount`, `code`, `ending`, `new`, or `plain` (controls the colour).
- **`access.type`** — `easy` (🟢), `app` (🟡), or `limited` (🔴).
- **`spotlight: true`** — makes it the homepage "Deal of the Day" (set it on one deal).
- **`code`** — optional; shows a tap-to-copy promo code chip.

Save the file, commit, and the site updates automatically.

---

## 🤖 Automate it — fresh deals every day, for free

The site can update itself daily with **no server and no cost**, using **GitHub Actions** (free scheduled jobs) + **GitHub Pages**. Here's the flow:

```
  ┌─ every day at 9am SGT ─────────────────────────────────────────┐
  │  GitHub Action runs scripts/aggregate_deals.py                  │
  │   → fetches verified Singapore deal feeds (+ optional API)      │
  │   → normalises, categorises (all 9 categories), de-duplicates   │
  │   → drops expired deals, keeps a SOURCE LINK on every item      │
  │   → writes data/deals.json → commits → pushes                   │
  │  GitHub Pages redeploys automatically → site shows new deals    │
  └────────────────────────────────────────────────────────────────┘
```

### Why this is legitimate (not "fake news")
- The aggregator **never invents a deal.** Every item comes from a real fetched feed, and each deal keeps a **link back to the original source** (shown on the card and on the "Get Deal" button).
- It pulls from **public RSS feeds** of established Singapore deal publishers, and optionally from **merchant-authorised affiliate feeds** (see below) — not by scraping pages behind logins or paywalls.
- It uses short factual summaries + attribution, and respects each source by linking back. Keep summaries brief and always credit the source.

### Files that power it
| File | What it does |
|------|--------------|
| `.github/workflows/update-deals.yml` | The free daily scheduler (cron). Also has a "Run workflow" button. |
| `scripts/aggregate_deals.py` | The aggregator. **Pure Python standard library — no installs needed.** |
| `scripts/build_pages.py` | Builds the site: single-source header/footer **and** pre-renders deals + JSON-LD into the HTML so Google sees them without JavaScript. Edit nav/footer/social links **here, once**. |
| `scripts/sources.json` | Your list of feeds + settings. Edit this to add/remove sources. |
| `scripts/manual_deals.json` | Optional hand-picked deals that always appear. |
| `scripts/test_aggregate.py` | Offline self-test (`python3 scripts/test_aggregate.py`). |
| `scripts/validate.py` + `.github/workflows/validate.yml` | **Hourly watchdog** — validates JSON/XML, security/CSP compliance, and asset integrity, then **auto-prunes expired deals** and rebuilds. Runs on GitHub's servers (zero impact on visitors). Run locally: `python3 scripts/validate.py --dry-run`. |
| `.github/workflows/health-check.yml` | Pings the live site every 30 min; emails you if it's down. |
| `scripts/check_links.py` + `check-links.yml` | Daily — removes deals whose outbound link has gone dead (404/410/451 only). |
| `scripts/snapshot.py` | Daily — dated `history/` snapshots of deals.json + a change-log, with rollback. |
| `scripts/prune_pages.py` | **Retention GC** — hard-deletes deals expired >10 days, then rebuilds so the sitemap + per-deal pages auto-sync. Runs hourly via the validator. |

**Expiry model:** the live site only ever shows **active** (non-expired) deals — expired ones are hidden immediately and their per-deal pages auto-deleted. The database keeps a recently-expired deal for a **10-day grace window**, then `prune_pages.py` purges it for good.

**🜲 Motherlode (knowledge transfer):** `scripts/motherlode.py` generates a self-updating blueprint of the whole system — **`MOTHERLODE.yaml`** (structured, AI-ingestible), **`MOTHERLODE.md`** (English rebuild playbook), and **`llms.txt`** (LLM index). It scans the repo so the inventory stays current and runs in the daily build. To document a new feature or roadmap item, edit the `BLUEPRINT` dict in the script. Use these files to hand the entire architecture + scripts to another AI to build a different site.

**2026 browser tech (client-side, CSP-safe, all progressive):** on-device **AI translation** (`js/translate.js` — Chrome's built-in Translator into 中文 / Malay / Tamil, runs locally, no API key), smooth cross-page **View Transitions**, and compositor-driven **scroll animations** (replacing JS reveal on supported browsers for a better INP score).
| `lighthouse.yml` · `a11y.yml` · `codeql.yml` · `dependabot.yml` | CI gates: performance/SEO budget, WCAG-AA accessibility, JS security scan, and auto-patched Actions. |

**SEO pages:** every build also generates an indexable page per deal (`deal-<id>.html`) and per category (`cat-<id>.html`) — each with `Offer`/`ItemList` JSON-LD and breadcrumbs — and prunes orphans, so you rank for long-tail searches like "IKEA deal Singapore".

### Turn it on (3 steps)
1. Upload everything (including the `.github` and `scripts` folders) to your repo.
2. Go to **Settings → Pages** and set the source to **Deploy from a branch → `main` / root**. (This is what makes each daily commit publish automatically.)
3. Go to the **Actions** tab, enable workflows if prompted, and click **Update deals daily → Run workflow** once to test. After that it runs on its own every morning.

> The schedule (`cron: "0 1 * * *"` = 9am Singapore) lives in the workflow file. Change it at [crontab.guru](https://crontab.guru). You can also hit **Run workflow** any time for an instant refresh.

### Cover more sources
Two feeds come pre-configured and verified working: **SINGPromos** and **Great Deals Singapore**. To add more, edit `scripts/sources.json`:
- If a deals site publishes an RSS feed (most WordPress sites do — try adding `/feed/` to the URL), add `{ "name": "...", "url": ".../feed/" }` to the `rss` list.
- If a site has **no** native feed, create one free at **[rss.app](https://rss.app)** and paste that URL instead.
- More sources = broader category coverage. The script already sorts items into all 9 categories automatically using the article's tags, URL and keywords.

### Track specific brands (IKEA, Donki, Uniqlo, McDonald's…)
The aggregator watches a **brand list** and pulls Singapore coverage for each one
from **Google News RSS** (free, and every item links back to the original article).
It also tags any deal from the other feeds with its brand and **boosts brand deals**
so they stay near the top. Edit the list under `brand_news.brands` in
`scripts/sources.json`. Shipped with: IKEA, Don Don Donki, Muji, Uniqlo, Adidas,
Nike, Charles & Keith, Ya Kun, McDonald's, Starbucks, Chagee, Apple, Lenovo,
Secretlab, Universal Studios Singapore and Singapore Zoo. Items are filtered to
promotional posts so you get deals, not generic corporate news.

> Note on social media: Instagram/Facebook/TikTok no longer offer free public APIs
> and their terms forbid scraping, so we use Google News (which already indexes most
> brand promos reported from social) plus the deal-publisher feeds. To follow a
> specific brand's social page, generate a free feed for it at rss.app and add it to
> the `rss` list.

### Optional: 2026 AI polish (free)
The aggregator can run fetched deals through an LLM to tidy titles, write cleaner
one-line summaries, and double-check categories — working **only** from the real
fetched text (it's instructed never to invent prices, dates or stores; if anything
fails it falls back to the original). It's **off by default** and provider-agnostic
(any OpenAI-compatible endpoint). Free 2026 options: **GitHub Models**, **Groq**,
**Google Gemini**. To enable: add `AI_API_URL`, `AI_API_KEY`, `AI_MODEL` as GitHub
Secrets and set `ai.enabled: true` in `scripts/sources.json`. See `scripts/ai_enrich.py`.

### Optional: official affiliate feed (earns you money)
For the most authoritative data — and commission on sales — join **[Involve Asia](https://involve.asia)** (free; the leading Southeast-Asia affiliate network, covering Lazada, Shopee, Grab, Klook, Zalora and 500+ merchants). Then:
1. Request a **Publisher API key** (Profile → Tools → API).
2. In your repo: **Settings → Secrets and variables → Actions** → add `INVOLVE_API_KEY` and `INVOLVE_API_SECRET`.
3. In `scripts/sources.json`, set `involve_asia.enabled` to `true` and paste your token/offers endpoints from the Involve Asia API docs.

The aggregator will then include real, merchant-approved offers with your tracking links.

### Honest expectations
- "Scan **all** major deals" isn't something any tool guarantees — your coverage equals the sources you configure. The starter set is solid; add feeds to widen it.
- Auto-categorisation and date parsing are smart heuristics, not perfect. For total control, you can run in **review mode**: keep `manual_deals.json` as your curated, always-on list and treat the feeds as suggestions.
- Everything here stays within **GitHub's free tier** for a public repository.

## 🔌 Connect the forms (optional)

The newsletter and submit forms are already wired to **[Formspree](https://formspree.io)** (free) with a placeholder ID. To start receiving submissions:

1. Create a free Formspree form (takes ~2 minutes) and copy its form ID.
2. Find-and-replace **`YOUR_FORM_ID`** with your real ID across the HTML files.

Each form already includes a spam honeypot (`_gotcha`) that Formspree filters automatically. Until you set a real ID, the form shows a friendly confirmation instead of posting to a dead endpoint. (Prefer Google Forms? Just link the "Submit a Deal" button to it instead.)

**Social links:** the footer/hero icons point at placeholder handles (`lobangkingsg`). Update them in one place — the `SOCIALS` block at the top of `scripts/build_pages.py` — then run `python3 scripts/build_pages.py`.

**Analytics:** the site ships with none (privacy-first). For free, cookieless numbers, enable **Cloudflare Web Analytics** in the Cloudflare dashboard once your domain is proxied — no code change, no CSP change. (If you prefer the JS beacon, add `https://static.cloudflareinsights.com` to `script-src` and `https://cloudflareinsights.com` to `connect-src` in the CSP.)

---

## 🔒 Security, reliability & performance

The site is hardened out of the box — a **locked-down Content-Security-Policy**
(`'self'` only, no external origins), **self-hosted fonts**, escaped feed data + link
sanitisation (XSS-safe), security headers (`_headers`), **anti-bot honeypot** on forms,
an offline-capable **service worker**, and **no secrets in the browser** (affiliate
keys stay in GitHub Secrets). A static site has no server or database to break into,
which removes most classic attack vectors.

**Built for high traffic:** static files behind a CDN scale to large audiences for
free, and the deal list renders in pages ("load more") with CSS `content-visibility`
so the browser never lags — even with hundreds of deals. Run `bash scripts/get_fonts.sh`
once to fetch the self-hosted font files (the site falls back to system fonts until then).

For the **strongest free protection** — a real WAF, DDoS mitigation, bot blocking
and full security headers — route your domain through **Cloudflare's free plan**.
Full details, the honest threat model (including why "uncopyable data" isn't a real
thing), and the Cloudflare + Turnstile setup are in **[`SECURITY.md`](SECURITY.md)**.

## 🎨 Branding

- Colours and fonts live at the top of `css/styles.css` (the `:root` variables) — change `--gold` and `--navy` to rebrand instantly.
- Icons and the social-share image in `images/` were generated from your lion-and-crown logo.

---

© 2026 LobangKing.sg — Every Deal in Singapore 👑
