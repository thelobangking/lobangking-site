#!/usr/bin/env python3
"""
snapshot.py — daily history + change-log for deals.json
=======================================================

Keeps a dated copy of deals.json under history/ (audit trail + one-click rollback)
and writes a small diff of what was added/removed versus the previous snapshot.
Prunes to the most recent KEEP days so the repo doesn't grow forever. Stdlib only.
"""
import json
import pathlib
import datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "deals.json"
HIST = ROOT / "history"
KEEP = 60  # days of history to retain


def main():
    if not DATA.exists():
        return
    HIST.mkdir(exist_ok=True)
    doc = json.loads(DATA.read_text(encoding="utf-8"))
    today = datetime.date.today().isoformat()

    prev = sorted(HIST.glob("deals-*.json"))
    added, removed = [], []
    if prev:
        old = json.loads(prev[-1].read_text(encoding="utf-8"))
        old_t = {d["id"]: d.get("title", "") for d in old.get("deals", [])}
        new_t = {d["id"]: d.get("title", "") for d in doc.get("deals", [])}
        added = [new_t[i] for i in new_t.keys() - old_t.keys()]
        removed = [old_t[i] for i in old_t.keys() - new_t.keys()]

    (HIST / f"deals-{today}.json").write_text(
        json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    (HIST / "changes-latest.json").write_text(
        json.dumps({"date": today, "added": added, "removed": removed},
                   indent=2, ensure_ascii=False), encoding="utf-8")

    snaps = sorted(HIST.glob("deals-*.json"))
    for p in snaps[:-KEEP]:
        p.unlink()
    print(f"Snapshot {today}: +{len(added)} new, -{len(removed)} removed; "
          f"{min(len(snaps), KEEP)} snapshots retained.")


if __name__ == "__main__":
    main()
