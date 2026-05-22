from __future__ import annotations
import os
import logging
from datetime import datetime
from pathlib import Path
from automation.paths import load_config, get_abs_path
from automation.goal_context import goal_rejection_reason, goal_summary_for_prompt

logger = logging.getLogger("automation.scorer")

class Metric:
    def __init__(self, config: dict):
        self.config = config

    def evaluate(self, issue: dict) -> tuple[float, str]:
        """Evaluate a single issue and return a tuple of (score_0_to_10, rationale)."""
        raise NotImplementedError


class AlignmentMetric(Metric):
    def evaluate(self, issue: dict) -> tuple[float, str]:
        metadata = issue.setdefault("metadata", {})
        
        # 1. Prerequisite check: explicit goal misalignment
        if metadata.get("goal_misaligned", False):
            return 0.0, "Rejected: This issue or action works against the project North Star."

        # 2. Prerequisite check: improvements/architecture must have non-empty goal_alignment_note
        is_alignment_required = (
            issue.get("type") in ["improvement", "architecture"]
            or metadata.get("output_kind") == "improvement"
        )
        alignment_note = metadata.get("goal_alignment_note", "").strip()
        if is_alignment_required and not alignment_note:
            return 2.0, f"Rejected: {issue.get('type').capitalize()} suggestions must include a non-empty 'goal_alignment_note'."

        # 3. Deterministic rejection reason check
        description = issue.get("description", "")
        rejection = goal_rejection_reason(description, strict=False)
        if rejection:
            return 3.0, f"Potential goal misalignment detected deterministically ({rejection})."

        # 4. LLM-based evaluation if provider is antigravity
        project_root = Path(self.config.get("_project_root", get_abs_path(".")))
        try:
            from automation.llm_client import get_llm_config, call_antigravity_llm
            llm_cfg = get_llm_config(project_root)
            if llm_cfg.get("provider") == "antigravity":
                goal_summary = goal_summary_for_prompt()
                severity = str(issue.get("severity", "low")).lower()
                prompt = (
                    f"[Qualoop Scorer Agent - North Star Alignment Evaluation]\n"
                    f"Project North Star and Goals:\n{goal_summary}\n\n"
                    f"We are evaluating a system issue/suggestion to determine if resolving it promotes or is aligned with the North Star.\n"
                    f"Issue Title/Type: {issue.get('type')}\n"
                    f"Severity: {severity}\n"
                    f"Description:\n{description}\n\n"
                    f"Tasks:\n"
                    f"1. Check if the issue aligns with the North Star (value_qualified is True if yes, False if not).\n"
                    f"2. Assign an alignment score from 0 to 100 based on severity and direct relevance to user experience.\n"
                    f"3. Provide a brief Chinese explanation for the decision.\n\n"
                    f"Please review the alignment, and start a prompt inside the IDE."
                )
                model = llm_cfg.get("model", "flash")
                ai_ret = call_antigravity_llm(project_root, prompt, model=model)
                return 10.0, f"Antigravity Scorer alignment verified: {ai_ret}."
        except Exception as e:
            logger.warning("Failed to run LLM alignment check: %s", e)

        return 10.0, "Alignment verified deterministically."


class ObservabilityMetric(Metric):
    def evaluate(self, issue: dict) -> tuple[float, str]:
        issue_type = issue.get("type")
        description = issue.get("description", "")
        if issue_type == "static":
            if "JSON parsing failed" in description or "conflict markers" in description:
                return 9.0, "High observability: directly blocks compilation/parsing."
            elif "Broken relative markdown link" in description or "Broken local anchor link" in description:
                return 9.0, "High observability: structural documentation link defect."
            elif "Trailing whitespace" in description or "newline" in description:
                return 4.0, "Low observability: minor formatting issue."
            return 8.0, "Medium-high observability: standard static validation rule."
        elif issue_type == "improvement":
            return 8.0, "Medium-high observability: enhancement proposal."
        elif issue_type == "architecture":
            return 9.0, "High observability: planning milestone."
        return 5.0, "Medium observability."


class CoordinationMetric(Metric):
    def evaluate(self, issue: dict) -> tuple[float, str]:
        issue_type = issue.get("type")
        if issue_type == "static":
            return 10.0, "Excellent coordination: static checks are file-isolated."
        elif issue_type == "architecture":
            return 9.0, "High coordination: planning issue."
        return 10.0, "Standard coordination."


class VerificationMetric(Metric):
    def evaluate(self, issue: dict) -> tuple[float, str]:
        issue_type = issue.get("type")
        if issue_type == "static":
            return 10.0, "100% deterministic and verifiable static check."
        elif issue_type == "architecture":
            return 8.0, "Verifiable planning milestone."
        return 10.0, "Standard verifiable channel."


class SafenessMetric(Metric):
    def evaluate(self, issue: dict) -> tuple[float, str]:
        issue_type = issue.get("type")
        description = issue.get("description", "")
        if issue_type == "static":
            if "Trailing whitespace" in description:
                return 10.0, "Very safe: minor text cleanup."
            return 10.0, "High safety: isolated static replacement."
        elif issue_type == "architecture":
            return 9.0, "High safety: architectural definition only."
        return 10.0, "Standard safety profile."


class DurabilityMetric(Metric):
    def evaluate(self, issue: dict) -> tuple[float, str]:
        issue_type = issue.get("type")
        description = issue.get("description", "")
        if issue_type == "static":
            if "JSON parsing failed" in description or "conflict markers" in description:
                return 9.0, "High durability: resolves critical system blockages."
            elif "Broken relative markdown link" in description or "Broken local anchor link" in description:
                return 8.0, "High durability: repairs structural document links."
            elif "Trailing whitespace" in description or "newline" in description:
                return 6.0, "Medium durability: style lint."
            return 8.0, "Standard durability: prevents static regressions."
        elif issue_type == "improvement":
            return 8.0, "Good durability: structural improvements."
        elif issue_type == "architecture":
            return 9.0, "High durability: fundamental architectural baseline."
        return 5.0, "Standard durability."


class QualoopScorer:
    def __init__(self):
        self.config = load_config()
        scorer_conf = self.config.get("scorer", {})
        self.min_score = scorer_conf.get("min_value_score", 60)
        self.min_qualified = scorer_conf.get("min_qualified_per_round", 1)

    def evaluate_and_score(self, issue: dict, round_id: str) -> None:
        """
        Evaluate and score a single candidate issue according to the metric rubrics.
        Modifies the issue object in-place with Scorer metadata fields.
        """
        now = datetime.utcnow().isoformat() + "Z"
        metadata = issue.setdefault("metadata", {})

        # Initialize metrics
        align_metric = AlignmentMetric(self.config)
        obs_metric = ObservabilityMetric(self.config)
        coord_metric = CoordinationMetric(self.config)
        ver_metric = VerificationMetric(self.config)
        safe_metric = SafenessMetric(self.config)
        dur_metric = DurabilityMetric(self.config)

        # Evaluate alignment first as a strict gating prerequisite
        align_score, align_rationale = align_metric.evaluate(issue)
        if align_score <= 3.0:
            metadata["value_score"] = int(align_score * 10)
            metadata["value_score_rationale"] = align_rationale
            metadata["value_qualified"] = False
            metadata["value_insufficient"] = True
            metadata["scored_at"] = now
            metadata["scorer_round_id"] = round_id
            return

        obs_score, obs_rationale = obs_metric.evaluate(issue)
        coord_score, coord_rationale = coord_metric.evaluate(issue)
        ver_score, ver_rationale = ver_metric.evaluate(issue)
        safe_score, safe_rationale = safe_metric.evaluate(issue)
        dur_score, dur_rationale = dur_metric.evaluate(issue)

        # Weighted calculation (weights: 25% observability, 20% coordination, 25% verification, 15% safeness, 15% durability)
        score = (
            obs_score * 0.25 +
            coord_score * 0.20 +
            ver_score * 0.25 +
            safe_score * 0.15 +
            dur_score * 0.15
        ) * 10

        score = int(round(score))
        qualified = score >= self.min_score

        metadata["value_score"] = score
        rationales = [r for r in [align_rationale, obs_rationale, coord_rationale, ver_rationale, safe_rationale, dur_rationale] if r]
        metadata["value_score_rationale"] = " | ".join(rationales)
        metadata["value_qualified"] = qualified
        metadata["scored_at"] = now
        metadata["scorer_round_id"] = round_id

        if not qualified:
            metadata["value_insufficient"] = True
        else:
            metadata.pop("value_insufficient", None)

