# Qualoop — Latest issues

Generated: `2026-05-23T10:38:17.599870Z`  
Round: `pass_20260523_103816`  
Qualified this round: **2** (max score: 80)

---

## Needs human

Issues that require a person (`open` + `requires_human`, or `wontfix` + `terminal_reason: human_required`).


No issues require human intervention at this moment.


---

## Open / assigned


No open automated/assigned tasks.


---

## Resolved


- **[MEDIUM]** Qualoop self-upgrade content check failed: Modified files (automation/tester.py) are not referenced in the added description of `reports/development-report.html`. Please ensure the report update description explicitly mentions: tester. (fingerprint: `cd202a6ee11068fc`)
  - Affected paths: `automation/tester.py`, `reports/development-report.html` | Status: `resolved` | Score: **80** (Qualified)
  - Scorer Rationale: *Alignment verified deterministically. | Medium observability. | Standard coordination. | Standard verifiable channel. | Standard safety profile. | Standard durability.*

- **[MEDIUM]** Qualoop self-upgrade rule violation: Qualoop framework code has been modified (automation/__init__.py, automation/executors/base.py, automation/paths.py, automation/qualoop.py, automation/scheduler.py, automation/tester.py, automation/_qsum.py, automation/guardian.py), but no corresponding update was recorded in `reports/development-report.html`. Every Qualoop upgrade must be documented. (fingerprint: `2e552cc2fe548130`)
  - Affected paths: `reports/development-report.html`, `automation/__init__.py`, `automation/executors/base.py`, `automation/paths.py`, `automation/qualoop.py`, `automation/scheduler.py`, `automation/tester.py`, `automation/_qsum.py`, `automation/guardian.py` | Status: `resolved` | Score: **80** (Qualified)
  - Scorer Rationale: *Alignment verified deterministically. | Medium observability. | Standard coordination. | Standard verifiable channel. | Standard safety profile. | Standard durability.*



---

## Closed / abandoned

`wontfix` / `duplicate` where **no** human action is expected (`terminal_reason` ≠ `human_required`).


No closed or abandoned issues.


---

*Do not list all `wontfix` under "Needs human". See METHODOLOGY §3.1 and issue schema `metadata.terminal_reason`.*
