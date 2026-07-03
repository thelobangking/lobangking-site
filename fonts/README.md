# Self-hosted fonts

The site uses **Sora** (headings) and **DM Sans** (body), self-hosted here so there
are **no external font requests**. That lets the Content-Security-Policy stay locked
to `'self'`, and makes the site faster and more reliable (no dependency on Google's
servers).

## Get the font files (one-time)

From the repo root, run:

```bash
bash scripts/get_fonts.sh
```

This downloads the exact `woff2` files into this folder with these names:

```
sora-600.woff2   sora-700.woff2   sora-800.woff2
dmsans-400.woff2 dmsans-500.woff2 dmsans-600.woff2 dmsans-700.woff2
```

**No terminal?** Go to <https://gwfh.mranftl.com>, pick **Sora** (weights 600/700/800)
and **DM Sans** (weights 400/500/600/700), download the woff2 files, and rename them
to the names above.

> Until these files exist, the site automatically falls back to clean system fonts,
> so nothing breaks — it simply upgrades to the brand fonts once they're present.

The `@font-face` rules that point at these files live in [`../css/fonts.css`](../css/fonts.css).
