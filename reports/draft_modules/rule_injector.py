# -*- coding: utf-8 -*-
"""
Qualoop Rule Injector - Draft Implementation
Parses markdown rules under .qualoop/rules/ and dynamically injects them into agent prompts.
Ensures that the LLM agent complies with project-specific coding guidelines and architectural rules.
"""
import os
import sys
import re
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("RuleInjector")

class QualoopRuleInjector(object):
    def __init__(self, workspace_root):
        self.workspace_root = os.path.abspath(workspace_root)
        self.rules_dir = os.path.join(self.workspace_root, ".qualoop", "rules")
        
    def _create_mock_rules(self):
        """Creates dummy rules files in .qualoop/rules for testing purposes."""
        if not os.path.exists(self.rules_dir):
            os.makedirs(self.rules_dir)
            
        # Rule 1: Python naming conventions
        rule1_content = """# Rule: Python Naming Conventions
---
Target-Paths: *.py
Roles: Executor, Tester
---
- Ensure all function names use snake_case (e.g., `calculate_metrics`).
- Avoid using global variables.
- Keep function lengths under 50 lines.
"""
        # Rule 2: SQL security rules
        rule2_content = """# Rule: SQL Query Security
---
Target-Paths: src/db/*.py, src/auth/*.py
Roles: Executor
---
- Never use string interpolation (f-strings) to format SQL queries.
- Always use parametrized queries or parameterized placeholders to prevent SQL injection.
"""
        with open(os.path.join(self.rules_dir, "naming_rules.md"), "w") as f:
            f.write(rule1_content)
        with open(os.path.join(self.rules_dir, "sql_rules.md"), "w") as f:
            f.write(rule2_content)
        logger.info("Mock rules files generated for test run.")

    def parse_rule_file(self, file_path):
        """Parses front-matter metadata and body from a markdown rule file."""
        try:
            with open(file_path, "r") as f:
                content = f.read()
            
            # Simple markdown front-matter parser using ---
            parts = content.split("---")
            if len(parts) >= 3:
                front_matter = parts[1]
                body = "---".join(parts[2:])
            else:
                front_matter = ""
                body = content
                
            # Parse front-matter metadata
            metadata = {}
            for line in front_matter.strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    metadata[k.strip().lower()] = [x.strip() for x in v.split(",")]
            
            return {
                "metadata": metadata,
                "body": body.strip()
            }
        except Exception as e:
            logger.error("Failed to parse rule file %s: %s", file_path, str(e))
            return None

    def get_applicable_rules(self, target_filepath, role_name):
        """Matches applicable rules based on target file path globs and the agent's role name."""
        if not os.path.exists(self.rules_dir):
            return []
            
        applicable_rules = []
        for filename in os.listdir(self.rules_dir):
            if not filename.endswith(".md"):
                continue
                
            rule_path = os.path.join(self.rules_dir, filename)
            rule = self.parse_rule_file(rule_path)
            if not rule:
                continue
                
            metadata = rule["metadata"]
            
            # 1. Match Roles
            applicable_roles = metadata.get("roles", ["all"])
            role_match = (role_name in applicable_roles) or ("all" in applicable_roles)
            
            # 2. Match Paths (using simple regex/glob match)
            paths = metadata.get("target-paths", ["*"])
            path_match = False
            for p_pattern in paths:
                # Convert glob pattern to simple regex
                regex_pattern = p_pattern.replace(".", "\\.").replace("*", ".*")
                if re.search(regex_pattern, target_filepath):
                    path_match = True
                    break
                    
            if role_match and path_match:
                applicable_rules.append(rule["body"])
                
        return applicable_rules

    def inject_rules_into_prompt(self, base_system_prompt, target_filepath, role_name):
        """Appends applicable rules to the base system prompt as a structured block."""
        rules = self.get_applicable_rules(target_filepath, role_name)
        if not rules:
            return base_system_prompt
            
        rules_block = "\n\n=== PROJECT-SPECIFIC ARCHITECTURAL RULES (CRITICAL) ===\n"
        rules_block += "You MUST strictly comply with the following localized team rules when executing tasks:\n"
        for idx, rule_body in enumerate(rules, start=1):
            rules_block += "\n[Rule #{}]\n{}\n".format(idx, rule_body)
        rules_block += "========================================================\n"
        
        return base_system_prompt + rules_block

if __name__ == "__main__":
    # Test execution
    workspace = r"e:\20260502_MZH\Qualoop"
    injector = QualoopRuleInjector(workspace)
    
    # 1. Setup mock rules
    injector._create_mock_rules()
    
    # 2. Match rules for Python file edited by an Executor
    print("Rules for src/db/connection.py and Role: Executor:")
    rules = injector.get_applicable_rules("src/db/connection.py", "Executor")
    for r in rules:
        print(r)
        print("-" * 40)
        
    # 3. Match rules for YAML config edited by a Tester (should only match naming rules glob *.py)
    print("\nRules for config.yaml and Role: Tester (should be empty):")
    rules_yaml = injector.get_applicable_rules("config.yaml", "Tester")
    print("Found rules count:", len(rules_yaml))
    
    # 4. Inject prompt test
    base_prompt = "You are a coding assistant. Rewrite the function."
    injected_prompt = injector.inject_rules_into_prompt(base_prompt, "src/auth/login.py", "Executor")
    print("\nInjected System Prompt:")
    print(injected_prompt)
    
    # Clean up test directories
    try:
        os.remove(os.path.join(injector.rules_dir, "naming_rules.md"))
        os.remove(os.path.join(injector.rules_dir, "sql_rules.md"))
        os.rmdir(injector.rules_dir)
        os.rmdir(os.path.join(workspace, ".qualoop"))
        logger.info("Cleaned up test rules directory.")
    except Exception:
        pass
