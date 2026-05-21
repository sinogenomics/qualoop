import os
import json
from datetime import datetime
from automation.paths import get_abs_path, PROJECT_ROOT

class QualoopReporter:
    def __init__(self, issues, round_id):
        self.issues = issues
        self.round_id = round_id
        self.reports_dir = get_abs_path("automation/reports")
        os.makedirs(self.reports_dir, exist_ok=True)

    def write_value_scores_log(self, scored_issues):
        """Append scored issues to the value_scores.jsonl log."""
        log_path = os.path.join(self.reports_dir, "value_scores.jsonl")
        with open(log_path, "a", encoding="utf-8") as f:
            for issue in scored_issues:
                meta = issue.get("metadata", {})
                record = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "round_id": self.round_id,
                    "issue_id": issue["id"],
                    "fingerprint": issue["fingerprint"],
                    "description": issue["description"],
                    "value_score": meta.get("value_score"),
                    "value_qualified": meta.get("value_qualified"),
                    "rationale": meta.get("value_score_rationale")
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def write_low_value_log(self, qualified_count, min_required):
        """Append to low_value_rounds.jsonl if the count of qualified issues is insufficient."""
        log_path = os.path.join(self.reports_dir, "low_value_rounds.jsonl")
        with open(log_path, "a", encoding="utf-8") as f:
            record = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "round_id": self.round_id,
                "qualified_count": qualified_count,
                "min_required": min_required
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def format_issue_md(self, issue):
        """Format a single issue into markdown list bullet."""
        meta = issue.get("metadata", {})
        paths_str = ", ".join([f"`{p}`" for p in issue.get("paths", [])]) or "`root`"
        score = meta.get("value_score")
        qualified_str = " (Qualified)" if meta.get("value_qualified") else " (Low Value/Unqualified)"
        score_info = f" | Score: **{score}**{qualified_str}" if score is not None else ""
        
        md = f"- **[{issue['severity'].upper()}]** {issue['description']} (fingerprint: `{issue['fingerprint']}`)\n"
        md += f"  - Affected paths: {paths_str} | Status: `{issue['status']}`{score_info}\n"
        
        if meta.get("value_score_rationale"):
            md += f"  - Scorer Rationale: *{meta['value_score_rationale']}*\n"
        if meta.get("goal_alignment_note"):
            md += f"  - Goal Alignment: *{meta['goal_alignment_note']}*\n"
        return md

    def generate_report(self):
        """Assemble the markdown report using the templates/reports/latest_issues.template.md layout."""
        template_path = os.path.join(PROJECT_ROOT, "templates/reports/latest_issues.template.md")
        
        # Default fallback template if template doesn't exist
        template = """# Qualoop — Latest issues

Generated: `{{generated_at}}`  
Round: `{{round_id}}`  
Qualified this round: **{{qualified_count}}** (max score: {{max_score}})

---

## Needs human

Issues that require a person (`open` + `requires_human`, or `wontfix` + `terminal_reason: human_required`).

{{needs_human_section}}

---

## Open / assigned

{{open_section}}

---

## Resolved

{{resolved_section}}

---

## Closed / abandoned

`wontfix` / `duplicate` where **no** human action is expected (`terminal_reason` ≠ `human_required`).

{{abandoned_section}}

---

*Do not list all `wontfix` under "Needs human". See METHODOLOGY §3.1 and issue schema `metadata.terminal_reason`.*
"""
        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                template = f.read()

        # Categorize issues
        needs_human = []
        open_assigned = []
        resolved = []
        abandoned = []

        max_score = 0
        qualified_count = 0

        for issue in self.issues:
            status = issue["status"]
            meta = issue.get("metadata", {})
            requires_human = meta.get("requires_human", False)
            terminal_reason = meta.get("terminal_reason")

            # Track scores for qualified issues
            if meta.get("value_qualified"):
                qualified_count += 1
                score = meta.get("value_score", 0)
                if score > max_score:
                    max_score = score

            # Grouping logic matching Phase 1 spec
            if (status == "open" and requires_human) or (status == "wontfix" and terminal_reason == "human_required"):
                needs_human.append(issue)
            elif status in ["open", "assigned", "in_progress"]:
                open_assigned.append(issue)
            elif status == "resolved":
                resolved.append(issue)
            elif status in ["wontfix", "duplicate"] and terminal_reason != "human_required":
                abandoned.append(issue)

        # Build sections
        def build_sec_content(issue_list, empty_msg="No issues in this category."):
            if not issue_list:
                return f"\n{empty_msg}\n"
            return "\n" + "\n".join([self.format_issue_md(issue) for issue in issue_list]) + "\n"

        needs_human_sec = build_sec_content(needs_human, "No issues require human intervention at this moment.")
        open_sec = build_sec_content(open_assigned, "No open automated/assigned tasks.")
        resolved_sec = build_sec_content(resolved, "No resolved issues logged yet.")
        abandoned_sec = build_sec_content(abandoned, "No closed or abandoned issues.")

        generated_at = datetime.utcnow().isoformat() + "Z"

        # Substitute
        report_content = template
        report_content = report_content.replace("{{generated_at}}", generated_at)
        report_content = report_content.replace("{{round_id}}", self.round_id)
        report_content = report_content.replace("{{qualified_count}}", str(qualified_count))
        report_content = report_content.replace("{{max_score}}", str(max_score))
        report_content = report_content.replace("{{needs_human_section}}", needs_human_sec)
        report_content = report_content.replace("{{open_section}}", open_sec)
        report_content = report_content.replace("{{resolved_section}}", resolved_sec)
        report_content = report_content.replace("{{abandoned_section}}", abandoned_sec)

        # Save human-readable latest issues
        report_path = get_abs_path("automation/reports/latest_issues.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        return report_path
