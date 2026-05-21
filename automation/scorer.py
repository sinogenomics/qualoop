import os
from datetime import datetime
from automation.paths import load_config

class QualoopScorer:
    def __init__(self):
        self.config = load_config()
        scorer_conf = self.config.get("scorer", {})
        self.min_score = scorer_conf.get("min_value_score", 60)
        self.min_qualified = scorer_conf.get("min_qualified_per_round", 1)

    def evaluate_and_score(self, issue, round_id):
        """
        Evaluate and score a single candidate issue according to the rubric.
        Modifies the issue object in-place with Scorer metadata fields.
        """
        now = datetime.utcnow().isoformat() + "Z"
        metadata = issue.setdefault("metadata", {})

        # Prerequisite One: Check for explicit goal misalignment
        if metadata.get("goal_misaligned", False):
            metadata["value_score"] = 0
            metadata["value_score_rationale"] = "Rejected: This issue or action works against the project North Star."
            metadata["value_qualified"] = False
            metadata["value_insufficient"] = True
            metadata["scored_at"] = now
            metadata["scorer_round_id"] = round_id
            return

        # Prerequisite One: Improvements and Architecture milestones must have a non-empty goal_alignment_note
        is_alignment_required = (issue.get("type") in ["improvement", "architecture"] or metadata.get("output_kind") == "improvement")
        alignment_note = metadata.get("goal_alignment_note", "").strip()
        if is_alignment_required and not alignment_note:
            metadata["value_score"] = 20
            metadata["value_score_rationale"] = f"Rejected: {issue.get('type').capitalize()} suggestions must include a non-empty 'goal_alignment_note'."
            metadata["value_qualified"] = False
            metadata["value_insufficient"] = True
            metadata["scored_at"] = now
            metadata["scorer_round_id"] = round_id
            return

        # Rubric scoring dimensions (from 0 to 10)
        # Dimensions: Observability (25%), Coordination (20%), Verification (25%), Safeness (15%), Durability (15%)
        dims = {
            "observability": 5,
            "coordination": 10,  # All static checks are high coordination (no parallel write risks)
            "verification": 10,  # Static checks are 100% deterministic and verifiable
            "safeness": 10,      # Doc/script checks are low risk
            "durability": 5
        }

        rationale_parts = []
        issue_type = issue.get("type")
        description = issue.get("description")
        severity = issue.get("severity")

        if issue_type == "static":
            if "JSON parsing failed" in description or "conflict markers" in description:
                # Critical/high severity defects
                dims["observability"] = 9
                dims["durability"] = 9
                rationale_parts.append("Remedies a critical syntax/corruption error blocking observation and compilation.")
            elif "Broken relative markdown link" in description or "Broken local anchor link" in description:
                dims["observability"] = 9
                dims["durability"] = 8
                rationale_parts.append("Fixes structural documentation broken links, direct support for readability.")
            elif "Trailing whitespace" in description or "newline" in description:
                dims["observability"] = 4
                dims["durability"] = 6
                rationale_parts.append("Resolves minor styling/lint issues.")
            else:
                dims["observability"] = 8
                dims["durability"] = 8
                rationale_parts.append("Resolves standard static validation rules.")
        elif issue_type == "improvement":
            dims["observability"] = 8
            dims["durability"] = 8
            rationale_parts.append(f"Provides valuable enhancement: {alignment_note}")
        elif issue_type == "architecture":
            dims["observability"] = 9
            dims["coordination"] = 9
            dims["verification"] = 8
            dims["safeness"] = 9
            dims["durability"] = 9
            rationale_parts.append(f"Milestone architecture planning issue: {description}")

        # Compute weighted sum
        score = (
            dims["observability"] * 0.25 +
            dims["coordination"] * 0.20 +
            dims["verification"] * 0.25 +
            dims["safeness"] * 0.15 +
            dims["durability"] * 0.15
        ) * 10  # Scale 0-10 to 0-100

        score = int(round(score))
        
        # Verify min_value_score
        qualified = score >= self.min_score

        # Set Scorer-only fields
        metadata["value_score"] = score
        metadata["value_score_rationale"] = " | ".join(rationale_parts) or "Qualified contribution toward North Star stability."
        metadata["value_qualified"] = qualified
        metadata["scored_at"] = now
        metadata["scorer_round_id"] = round_id
        
        if not qualified:
            metadata["value_insufficient"] = True
        else:
            metadata.pop("value_insufficient", None)
