#!/usr/bin/env python3
"""
minify.py — conservative CSS minifier (dependency-free).

Strips comments and collapses whitespace into single spaces. It NEVER removes a
semantically-meaningful single space (so values like `calc(100% - 10px)` and
`contain-intrinsic-size:auto 320px` stay valid) — making it safe to run blind.

Benefits: smaller payload (faster loads) AND the deployed CSS is harder for a
copycat to read. Source files stay readable; this writes *.min.css next to them.
Called automatically by build_pages.py.
"""
import re
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def minify_css(src: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", src, flags=re.S)     # remove comments
    s = re.sub(r"[ \t]*\r?\n[ \t]*", " ", s)          # newlines + indentation -> single space
    s = re.sub(r"[ \t]{2,}", " ", s)                  # runs of spaces -> single space
    return s.strip()


def build():
    for name in ("styles.css", "fonts.css"):
        src = ROOT / "css" / name
        if not src.exists():
            continue
        out = ROOT / "css" / name.replace(".css", ".min.css")
        before = len(src.read_text(encoding="utf-8"))
        mini = minify_css(src.read_text(encoding="utf-8"))
        out.write_text(mini, encoding="utf-8")
        print(f"  ✓ minified css/{out.name} ({before}→{len(mini)} bytes)")


if __name__ == "__main__":
    build()
