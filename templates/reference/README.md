# Reference modules (copy into `automation/`)

These files are **not** imported by the methodology repo itself. Adopters copy and wire them in their Tester / Guardian project.

| File | Purpose |
|------|---------|
| [external_touch_guard.py](./external_touch_guard.py) | Enforce `min_interval_sec` per external channel; write `throttled_channels.jsonl` |

Configure via `automation/config.json` → `external_touch_guard` (see [config.example.json](../config.example.json)).

Case study: [references/EXTERNAL_API_AND_E2E.md](../../references/EXTERNAL_API_AND_E2E.md).
