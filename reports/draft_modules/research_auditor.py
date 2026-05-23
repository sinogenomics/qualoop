# -*- coding: utf-8 -*-
"""
Qualoop Research Auditor - Automated Quality Gate (Upgraded)
Parses open_source_research_report.html, extracts all 15 recommendations,
verifies that their Python draft modules compile, and runs the unittest suite
to verify runtime behavior.
"""
import os
import sys
import re
import ast
import logging
import subprocess

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ResearchAuditor")

class ResearchAuditor(object):
    def __init__(self, workspace_root):
        self.workspace_root = os.path.abspath(workspace_root)
        self.report_path = os.path.join(self.workspace_root, "reports", "open_source_research_report.html")
        self.drafts_dir = os.path.join(self.workspace_root, "reports", "draft_modules")

        self.required_mappings = {
            "建议一": "qualoop_aci.py",
            "建议二": "sandbox_manager.py",
            "建议三": "replan_executor.py",
            "建议四": "rule_injector.py",
            "建议五": "event_bus.py",
            "建议六": "peer_reviewer.py",
            "建议七": "ast_validator.py",
            "建议八": "repo_sym_map.py",
            "建议九": "python_tooling.py",
            "建议十": "swarm_router.py",
            "建议十一": "pydantic_schemas.py",
            "建议十二": "agent_tracer.py",
            "建议十三": "gui_tester.py",
            "建议十四": "docker_sandbox.py",
            "建议十五": "loop_blocker.py"
        }

    def run_audit(self):
        logger.info("Starting automated Qualoop Research Audit...")
        
        if not os.path.exists(self.report_path):
            return {"status": "FAILED", "reason": "Research report HTML file not found."}

        with open(self.report_path, "r", encoding="utf-8") if sys.version_info.major >= 3 else open(self.report_path, "r") as f:
            report_content = f.read()

        # Extract all recommendations mentioned in the HTML file (e.g., "建议一", "建议二")
        found_suggestions = re.findall(r"建议[一二三四五六七八九十百千万]+", report_content)
        unique_suggestions = sorted(list(set(found_suggestions)))
        
        logger.info("Found suggestions in HTML report: %s", ", ".join(unique_suggestions))
        
        audit_records = []
        all_passed = True
        
        # Check existence and compilation of each suggestion
        for sug in unique_suggestions:
            if sug not in self.required_mappings:
                logger.info("Suggestion '%s' is not mapped to a code file. Skipping validation.", sug)
                continue
                
            required_file = self.required_mappings[sug]
            file_path = os.path.join(self.drafts_dir, required_file)
            
            record = {
                "suggestion": sug,
                "required_file": required_file,
                "file_exists": False,
                "syntax_valid": False,
                "error": None
            }
            
            # Check 1: File Existence
            if os.path.exists(file_path):
                record["file_exists"] = True
                
                # Check 2: AST Syntax Compilation Check
                try:
                    with open(file_path, "r", encoding="utf-8") if sys.version_info.major >= 3 else open(file_path, "r") as pf:
                        code = pf.read()
                    ast.parse(code)
                    record["syntax_valid"] = True
                except Exception as e:
                    record["error"] = "AST syntax check failed: {}".format(str(e))
                    all_passed = False
            else:
                record["error"] = "Missing draft Python implementation file."
                all_passed = False
                
            audit_records.append(record)

        # Check 3: Run Dynamic Unit Tests
        logger.info("Executing dynamic unit tests suite for all draft modules...")
        test_script = os.path.join(self.drafts_dir, "run_all_draft_tests.py")
        tests_passed = False
        test_details = ""
        
        if os.path.exists(test_script):
            try:
                # Use current python executable to run tests
                res = subprocess.Popen(
                    [sys.executable, test_script],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=self.drafts_dir,
                    shell=False
                )
                stdout, stderr = res.communicate()
                out = stdout.decode("utf-8", errors="ignore") + stderr.decode("utf-8", errors="ignore")
                if res.returncode == 0:
                    tests_passed = True
                    test_details = "All unittest suites passed successfully."
                else:
                    all_passed = False
                    test_details = "Unit tests failed:\n{}".format(out)
            except Exception as e:
                all_passed = False
                test_details = "Failed to run unit tests: {}".format(str(e))
        else:
            all_passed = False
            test_details = "Unified test suite script (run_all_draft_tests.py) not found."

        # Print audit summary
        print("\n================ QUALOOP RESEARCH AUDIT SUMMARY ================")
        for r in audit_records:
            status = "PASSED" if r["syntax_valid"] else "FAILED"
            print(" - [{}] {} -> File: {} | Details: {}".format(
                status, r["suggestion"], r["required_file"], r["error"] or "OK"
            ))
        print("----------------------------------------------------------------")
        print("Dynamic Tests Status: {}".format("PASSED" if tests_passed else "FAILED"))
        print("Details: {}".format(test_details))
        print("================================================================\n")

        final_status = "PASSED" if (all_passed and tests_passed) else "FAILED"
        logger.info("Research Audit Final Status: %s", final_status)
        return {
            "status": final_status,
            "records": audit_records,
            "tests_passed": tests_passed,
            "test_details": test_details
        }

if __name__ == "__main__":
    # Run auditor on the current repository workspace
    auditor = ResearchAuditor(r"e:\20260502_MZH\Qualoop")
    auditor.run_audit()
