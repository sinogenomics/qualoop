"""Ad-hoc summary of issues.json by status/type for smoke-test."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
with (ROOT / "automation" / "issues.json").open(encoding="utf-8-sig") as f:
    data = json.load(f)

issues = data.get("issues", [])
status_counts = Counter(i.get("status") for i in issues)
print("status:", dict(status_counts))

by_type: dict[str, Counter] = defaultdict(Counter)
for i in issues:
    by_type[i.get("type", "?")][i.get("status", "?")] += 1
print("by_type:")
for t, c in sorted(by_type.items()):
    print(f"  {t:13s} {dict(c)}")

print("terminal closures:")
for i in issues:
    if i.get("status") in ("resolved", "wontfix"):
        meta = i.get("metadata") or {}
        note = meta.get("executor_note") or meta.get("escalation_reason") or "-"
        path0 = (i.get("paths") or ["-"])[0]
        print(
            f"  [{i.get('status'):7s}] {i.get('id', '')[:8]} {i.get('type', ''):12s}"
            f" {path0:14s} | {note[:100]}"
        )
