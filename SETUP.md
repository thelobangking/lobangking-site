# LobangKing.sg — Setup Guide

Everything to get this site live on GitHub Pages (free hosting) from the
`lobangking-site.zip` archive. Full detail is in `README.md`, `SECURITY.md`, and
the `MOTHERLODE.md` blueprint.

---

## Accounts you'll need

| Account | Cost | Needed? | What it's for |
|---|---|---|---|
| **GitHub** (github.com) | Free | **Required** | Hosting (GitHub Pages) + the automation that updates deals |
| **Cloudflare** (cloudflare.com) | Free | Recommended | Security (WAF, bot blocking), CDN speed, free analytics, custom-domain HTTPS |
| **Domain registrar** (e.g. for `lobangking.sg`) | ~$10–30/yr | Optional | A custom domain instead of the free `*.github.io` URL |
| **Formspree** (formspree.io) | Free | Optional | Actually receive the newsletter / "submit a deal" form entries |
| **Involve Asia** (involve.asia) | Free | Optional | Merchant-approved affiliate deals + earn commission |
| **AI provider** — GitHub Models / Groq / Google Gemini | Free tier | Optional | "Polish" deal text with on-server AI |

> Minimum to go live: **just GitHub**. Everything else can be added later.

---

## 1. Unzip
Extract `lobangking-site.zip` to a folder (e.g. `Documents/lobangking`).
**Confirm the hidden files came through** — you must see a **`.github`** folder and a
**`.nojekyll`** file (enable "Hidden items" on Windows / press ⌘+Shift+. on Mac).

## 2. Install the basics
- **Git** — https://git-scm.com (required to push)
- **GitHub account** — https://github.com (free)
- *(optional)* **Python 3** — https://python.org — only if you want to run the build
  scripts locally; GitHub runs them automatically otherwise.

## 3. Put it on GitHub
Create a new **empty** repo on GitHub (e.g. `lobangking`) — do **not** add a README.

**Option A — command line** (run inside the unzipped folder):
```bash
git init
git add -A
git commit -m "Initial LobangKing.sg site"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/lobangking.git
git push -u origin main
```
**Option B — no terminal:** on the new repo page choose *"uploading an existing file"*
and drag in **all** files and folders (including `.github`), then Commit.

## 4. Turn on GitHub Pages
Repo → **Settings → Pages** → Source: **Deploy from a branch** → Branch: **main / (root)**
→ Save. Live in ~1 min at `https://YOUR-USERNAME.github.io/lobangking/`.

## 5. Allow the automation to run (important)
Repo → **Settings → Actions → General**:
- *Actions permissions:* **Allow all actions**
- *Workflow permissions:* **Read and write permissions** ✅ (lets the bots commit deal updates)

Then **Actions** tab → **"Update deals daily" → Run workflow** once to pull live deals.
After that, all jobs run on schedule automatically.

## 6. Personalize (≈10 min)
- **Forms:** find-and-replace `YOUR_FORM_ID` with a free Formspree (formspree.io) form ID.
- **Social links + contact:** edit `SOCIALS` in `scripts/build_pages.py` and the email in
  `.well-known/security.txt`.
- **Brand fonts (optional):** run `bash scripts/get_fonts.sh` once (system fonts used until then).
- **Optional secrets** (Settings → Secrets and variables → Actions): `INVOLVE_API_KEY`
  (affiliate), `AI_API_URL` / `AI_API_KEY` / `AI_MODEL` (AI polish).
- **Custom domain + Cloudflare (optional):** see `SECURITY.md`.

## 7. Verify
Open the Pages URL — you'll see the demo deals; after the first workflow run they're
replaced with **live Singapore deals**, refreshed daily.

---
*Built with an automated daily pipeline + a full security/SEO/reliability toolchain.
See `MOTHERLODE.yaml` / `MOTHERLODE.md` to understand or rebuild the whole system.*
