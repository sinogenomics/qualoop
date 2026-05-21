import os
import re
import json
import subprocess
from automation.paths import PROJECT_ROOT, get_abs_path, get_rel_path

class QualoopTester:
    def __init__(self, deep=False):
        self.deep = deep
        self.candidates = []
        self.active_fingerprints = set()

    def run_all_checks(self):
        """Run all active discovery channels and return candidate issues."""
        self.candidates = []
        
        # 1. JSON syntax check
        self.check_json_syntax()

        # 2. Markdown local link and anchor check
        self.check_markdown_links()

        # 3. Shell script checks
        self.check_shell_scripts()

        # 4. Drift and placeholder check
        self.check_drift_and_placeholders()

        # 5. Deep inspection checks
        if self.deep:
            self.run_deep_checks()

        # Prerequisite Two: Ensure there is at least one output!
        # If no issues are detected, generate a high-quality improvement proposal.
        if not self.candidates:
            self.generate_improvement_proposal()

        return self.candidates

    def add_issue(self, severity, issue_type, description, paths, metadata=None):
        metadata = metadata or {}
        # Tag with output_kind
        if "output_kind" not in metadata:
            metadata["output_kind"] = "defect" if severity in ["critical", "high"] else "optimization"
            if issue_type == "improvement":
                metadata["output_kind"] = "improvement"

        self.candidates.append({
            "severity": severity,
            "type": issue_type,
            "description": description,
            "paths": [get_rel_path(p) for p in paths],
            "metadata": metadata
        })

    def check_json_syntax(self):
        """Check that all JSON files in the repo are valid JSON."""
        for root, _, files in os.walk(PROJECT_ROOT):
            if "node_modules" in root or ".git" in root or "automation" in root:
                continue
            for file in files:
                if file.endswith(".json"):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            json.load(f)
                    except Exception as e:
                        self.add_issue(
                            severity="high",
                            issue_type="static",
                            description=f"JSON parsing failed in {file}: {str(e)}",
                            paths=[filepath],
                            metadata={"requires_human": True}
                        )

    def check_markdown_links(self):
        """Scan all markdown files for broken relative links and anchors."""
        md_files = []
        for root, _, files in os.walk(PROJECT_ROOT):
            if "node_modules" in root or ".git" in root or "automation" in root:
                continue
            for file in files:
                if file.endswith(".md"):
                    md_files.append(os.path.join(root, file))

        link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

        for md_file in md_files:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()

            links = link_pattern.findall(content)
            for text, target in links:
                # Filter out remote URLs or mailto links
                if target.startswith(("http://", "https://", "mailto:", "ftp:", "git:")):
                    continue
                
                # Handle anchor-only link
                if target.startswith("#"):
                    anchor = target[1:]
                    # Check if anchor exists as a header or is defined in the same file
                    if not self._anchor_exists(md_file, anchor):
                        self.add_issue(
                            severity="medium",
                            issue_type="static",
                            description=f"Broken local anchor link '{target}' in {os.path.basename(md_file)}",
                            paths=[md_file],
                            metadata={"broken_target": target}
                        )
                    continue

                # Handle relative path with optional anchor
                parts = target.split("#")
                rel_path = parts[0]
                anchor = parts[1] if len(parts) > 1 else None

                # Resolve the absolute path of the target file
                target_abs = os.path.abspath(os.path.join(os.path.dirname(md_file), rel_path))
                
                if not os.path.exists(target_abs):
                    self.add_issue(
                        severity="high",
                        issue_type="static",
                        description=f"Broken relative markdown link '{rel_path}' inside {os.path.basename(md_file)}",
                        paths=[md_file],
                        metadata={"broken_target": rel_path}
                    )
                elif anchor:
                    # If file exists, check if the anchor exists inside it
                    if not target_abs.endswith(".md"):
                        continue  # Anchor check only applies to markdown files
                    if not self._anchor_exists(target_abs, anchor):
                        self.add_issue(
                            severity="medium",
                            issue_type="static",
                            description=f"Broken anchor '#{anchor}' in reference '{rel_path}' inside {os.path.basename(md_file)}",
                            paths=[md_file, target_abs],
                            metadata={"broken_target": target}
                        )

    def _anchor_exists(self, filepath, anchor):
        """Check if an anchor slug or text exists as a heading in the file."""
        if not os.path.exists(filepath):
            return False
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Clean the anchor for matching
        clean_anchor = anchor.lower().replace("-", "").strip()
        
        for line in lines:
            if line.startswith("#"):
                # Extract header text
                header_text = line.lstrip("#").strip()
                # Simple loose matching: check if the anchor string appears in the header text
                # or if the slugified header matches the anchor.
                clean_header = header_text.lower().replace("-", "").replace(" ", "").strip()
                if clean_anchor in clean_header or clean_header in clean_anchor:
                    return True
                # Check section markers like §1.3
                if "§" in header_text and "§" in anchor:
                    sec_h = header_text.split("§")[-1].split()[0]
                    sec_a = anchor.split("§")[-1].split()[0]
                    if sec_h == sec_a:
                        return True
        return False

    def check_shell_scripts(self):
        """Check shell scripts for standard shebangs and syntax correctness."""
        scripts_dir = os.path.join(PROJECT_ROOT, "scripts")
        if not os.path.exists(scripts_dir):
            return

        for file in os.listdir(scripts_dir):
            if file.endswith(".sh"):
                filepath = os.path.join(scripts_dir, file)
                
                # Check shebang
                with open(filepath, "r", encoding="utf-8") as f:
                    first_line = f.readline()
                if not first_line.startswith("#!"):
                    self.add_issue(
                        severity="medium",
                        issue_type="static",
                        description=f"Missing shebang in shell script: {file}",
                        paths=[filepath]
                    )

                # Bash syntax check (dry run parser)
                try:
                    result = subprocess.run(
                        ["bash", "-n", filepath],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    if result.returncode != 0:
                        self.add_issue(
                            severity="high",
                            issue_type="static",
                            description=f"Shell script syntax validation failed in {file}: {result.stderr.strip()}",
                            paths=[filepath]
                        )
                except FileNotFoundError:
                    # bash command not available, skip syntax parser check
                    pass

    def check_drift_and_placeholders(self):
        """Check for git conflict markers and standard template placeholders."""
        conflict_marker = re.compile(r'^(<<<<<<<|=======|>>>>>>>)(?:\s|$)')
        
        for root, _, files in os.walk(PROJECT_ROOT):
            if "node_modules" in root or ".git" in root or "automation" in root:
                continue
            for file in files:
                if file.endswith((".md", ".json", ".sh", ".py")):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                        
                        for i, line in enumerate(lines, 1):
                            if conflict_marker.match(line):
                                self.add_issue(
                                    severity="critical",
                                    issue_type="static",
                                    description=f"Git conflict markers detected in {file} at line {i}",
                                    paths=[filepath],
                                    metadata={"requires_human": True}
                                )
                                break
                    except Exception:
                        pass

        # Check for unconfigured North Star placeholders in AGENTS.md
        agents_md = os.path.join(PROJECT_ROOT, "AGENTS.md")
        if os.path.exists(agents_md):
            with open(agents_md, "r", encoding="utf-8") as f:
                content = f.read()
            if "_（请替换为本项目实际目标；未填写时拒绝执行任何 L2+ 操作）_" in content:
                self.add_issue(
                    severity="high",
                    issue_type="static",
                    description="North Star placeholder remains unconfigured in AGENTS.md",
                    paths=[agents_md],
                    metadata={"requires_human": True}
                )

    def run_deep_checks(self):
        """Run additional stylistic and thorough quality checks when depth is escalated."""
        for root, _, files in os.walk(PROJECT_ROOT):
            if "node_modules" in root or ".git" in root or "automation" in root:
                continue
            for file in files:
                if file.endswith(".md"):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                        
                        # 1. Check for trailing whitespaces in markdown
                        lines = content.splitlines()
                        for idx, line in enumerate(lines, 1):
                            if line.endswith(" ") and not line.endswith("  "):
                                self.add_issue(
                                    severity="low",
                                    issue_type="static",
                                    description=f"Trailing whitespace in {file} at line {idx}",
                                    paths=[filepath]
                                )
                                break  # Report once per file

                        # 2. Check for missing EOF newlines
                        if content and not content.endswith("\n"):
                            self.add_issue(
                                severity="low",
                                issue_type="static",
                                description=f"Missing end-of-file newline in {file}",
                                paths=[filepath]
                                )
                    except Exception:
                        pass

    def generate_improvement_proposal(self):
        """Create a default high-value improvement proposal when all discovery channels are green."""
        # Check if we have glossary terms that can be added, or suggest a doc format improvement
        self.add_issue(
            severity="low",
            issue_type="improvement",
            description="Documentation enhancement: Standardize relative path anchors and cross-references across all core methodology files.",
            paths=[os.path.join(PROJECT_ROOT, "METHODOLOGY.md")],
            metadata={
                "goal_alignment_note": "Ensures the methodology files are extremely readable and easily navigable ('可理解' success criterion in DEVELOPMENT_GOALS.md).",
                "output_kind": "improvement"
            }
        )
