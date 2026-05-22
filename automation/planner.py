import os
import re
from automation.paths import PROJECT_ROOT, get_abs_path, load_config
from automation.issue_store import IssueStore

class QualoopPlanner:
    def __init__(self, goals_path=None, scheme_path=None):
        self.config = load_config()
        
        # Determine goals file path
        if goals_path:
            self.goals_path = get_abs_path(goals_path)
        else:
            # Try common goals filenames in project root
            candidates = ["DEVELOPMENT_GOALS.md", "GOALS.md", "goals.md", "requirements.txt"]
            self.goals_path = None
            for c in candidates:
                abs_c = os.path.join(PROJECT_ROOT, c)
                if os.path.exists(abs_c):
                    self.goals_path = abs_c
                    break
            if not self.goals_path:
                self.goals_path = os.path.join(PROJECT_ROOT, "DEVELOPMENT_GOALS.md")

        # Determine scheme output path
        planner_cfg = self.config.get("planner", {})
        config_scheme_path = planner_cfg.get("scheme_output_path", "docs/ARCHITECTURE_SCHEME.md")
        self.scheme_path = get_abs_path(scheme_path or config_scheme_path)
        
        # Load North Star from AGENTS.md if possible
        self.north_star = self._extract_north_star()

    def _extract_north_star(self):
        """Extract project North Star from AGENTS.md or return a default placeholder."""
        agents_path = os.path.join(PROJECT_ROOT, "AGENTS.md")
        if os.path.exists(agents_path):
            try:
                with open(agents_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # Find between <!-- NORTH_STAR_BEGIN --> and <!-- NORTH_STAR_END -->
                match = re.search(r"<!-- NORTH_STAR_BEGIN -->(.*?)<!-- NORTH_STAR_END -->", content, re.DOTALL)
                if match:
                    ns = match.group(1).strip()
                    # Clean up markdown bullet points/placeholders
                    lines = [l.strip().lstrip("-* ").strip() for l in ns.split("\n") if l.strip()]
                    lines = [l for l in lines if "请替换为本项目实际目标" not in l and l]
                    if lines:
                        return " & ".join(lines)
            except Exception:
                pass
        return "Implement Qualoop methodology to achieve continuous self-improvement."

    def parse_goals(self):
        """Parse goals from the goal document or generate defaults."""
        milestones = []
        
        if os.path.exists(self.goals_path):
            try:
                with open(self.goals_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Scan for sections under Core Development Goals (## 二、核心开发目标)
                # We search for ### headers or list items
                core_goals_match = re.search(r"##\s+二、核心开发目标(.*?)(?=##\s+三|$)", content, re.DOTALL)
                if core_goals_match:
                    section_content = core_goals_match.group(1)
                    subheaders = re.findall(r"###\s+\d+\.\d+\s+(.*?)(?=\n)", section_content)
                    if not subheaders:
                        subheaders = re.findall(r"###\s+(.*?)(?=\n)", section_content)
                    
                    for sub in subheaders:
                        name = sub.strip()
                        milestones.append({
                            "name": name,
                            "description": f"Milestone: Implement goals and mechanisms aligned with '{name}'.",
                            "paths": ["automation/", "docs/"]
                        })
            except Exception as e:
                print(f"Warning: Failed to parse goals file: {e}. Using default milestones.")

        if not milestones:
            # Default milestones fallback
            milestones = [
                {
                    "name": "Milestone 1: Project Setup & Baseline Config",
                    "description": "Establish the basic workspace structure including AGENTS.md, qualoop.json, config.json, and paths.",
                    "paths": ["automation/config.json", "qualoop.json"]
                },
                {
                    "name": "Milestone 2: Implement Baseline Verification Loop",
                    "description": "Implement core issue tracking, tester discovery checks, and scorer evaluation logic.",
                    "paths": ["automation/tester.py", "automation/scorer.py"]
                },
                {
                    "name": "Milestone 3: Enable Scheduler & Conflict Avoidance",
                    "description": "Establish the single-writer Scheduler with path locks and execution lease mechanisms.",
                    "paths": ["automation/scheduler.py"]
                },
                {
                    "name": "Milestone 4: CI/CD Integration & Production Readiness",
                    "description": "Integrate Qualoop check triggers into PR gate and setup Guardian for long-running loop monitoring.",
                    "paths": ["automation/qualoop.py", "automation/reports/"]
                }
            ]
            
        return milestones

    def generate_scheme(self, milestones):
        """Generate docs/ARCHITECTURE_SCHEME.md scheme document."""
        os.makedirs(os.path.dirname(self.scheme_path), exist_ok=True)
        
        lines = [
            "# Architecture Planning Scheme",
            "",
            "This document is automatically generated by the Architect / Planner role based on the project's North Star goals.",
            "",
            "## 1. Project North Star",
            "",
            f"> {self.north_star}",
            "",
            "## 2. Milestone Planning",
            "",
            "The following high-level milestones have been planned to guide the project execution and prevent unstructured, scattered code modifications:",
            ""
        ]
        
        for i, m in enumerate(milestones, 1):
            lines.extend([
                f"### Milestone {i}: {m['name']}",
                "",
                f"- **Description**: {m['description']}",
                f"- **Affected Paths**: `{', '.join(m['paths'])}`",
                ""
            ])
            
        lines.extend([
            "## 3. Execution Strategy",
            "",
            "- The milestone issues listed below have been appended to the Issue Store.",
            "- The Scheduler will distribute these tasks sequentially based on path conflicts and severity.",
            "- The Scorer will review the implementation and verify goals alignment before closing."
        ])
        
        with open(self.scheme_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
            
        print(f"Generated overall architecture planning scheme at: {self.scheme_path}")

    def create_milestone_issues(self, milestones):
        """Add planning milestones as issues of type 'architecture' in Issue Store."""
        store = IssueStore()
        added_count = 0
        
        from datetime import datetime
        from automation.scorer import QualoopScorer
        scorer = QualoopScorer()
        round_id = f"plan_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        for m in milestones:
            desc = f"[{m['name']}] {m['description']}"
            align_note = f"Directly implements core goal: {m['name']}"
            metadata = {
                "goal_alignment_note": align_note,
                "output_kind": "improvement"
            }
            issue = store.add_candidate(
                severity="high",
                issue_type="architecture",
                description=desc,
                paths=m["paths"],
                metadata=metadata
            )
            if issue:
                scorer.evaluate_and_score(issue, round_id)
                store.update(issue["id"], metadata=issue.get("metadata"))
                added_count += 1
                
        store.save()
        print(f"Added and scored {added_count} milestone issue(s) of type 'architecture' to Issue Store.")
        return added_count

    def run_planning(self):
        """Execute the full planning workflow: parse goals, generate scheme doc, and add issues."""
        print(f"Reading goals document from: {self.goals_path}")
        milestones = self.parse_goals()
        self.generate_scheme(milestones)
        self.create_milestone_issues(milestones)
        print("Architect/Planner run completed successfully.")
