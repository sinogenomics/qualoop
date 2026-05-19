# Case pattern: external APIs and browser E2E

Generic lessons from adopters that integrate **third-party SaaS** (OAuth, upload pipelines) plus **Playwright/Cypress** E2E.

## Symptoms

- Automation health checks call live auth (`--test`, token refresh) every 2–5 minutes → rate limits or account risk controls.
- Browser E2E runs whenever localhost is up → same external quota burn.
- E2E reports **pass** while users see error modals → defects never enter Issue Store.
- Revision UI maps all `wontfix` to "needs human" → alert fatigue.

## Qualoop responses (methodology)

| Problem | Mechanism |
|---------|-----------|
| External over-polling | §1.6 touch_class + `external_touch_guard` |
| Monolithic `/health` | Layered liveness (`?probe=light`) vs deep readiness |
| E2E false green | Business terminal assertions + `metadata.e2e_outcome` |
| wontfix overload | `metadata.terminal_reason` + split human report sections |
| L3 E2E backlog | ARCHITECTURE §5.1 Verifier policy A or B |

## Adopter checklist

1. Copy [templates/reference/external_touch_guard.py](../templates/reference/external_touch_guard.py) into `automation/`.
2. Set `external_touch_guard.channels.browser_e2e.min_interval_sec` (e.g. 21600).
3. Point Tester health probes at liveness URL only by default.
4. Assert business success in E2E; attach screenshots on `pipeline_fail`.
5. Generate `latest_issues.md` using [latest_issues.template.md](../templates/reports/latest_issues.template.md).

## Related GitHub issues

- External touch budget (methodology + config)
- E2E business-outcome assertions
- `terminal_reason` for wontfix reporting
