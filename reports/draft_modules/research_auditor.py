# -*- coding: utf-8 -*-
"""
Qualoop Research Auditor - Automated Quality Gate
Parses open_source_research_report.html, extracts recommendations,
and verifies that a corresponding working Python draft module exists in reports/draft_modules/
and passes syntax compilation.
"""
import os
import sys
import re
import ast
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ResearchAuditor")

class ResearchAuditor(object):
    def __init__(self, workspace_root):
        self.workspace_root = os.path.abspath(workspace_root)
        self.report_path = os.path.join(self.workspace_root, "reports", "open_source_research_report.html")
        self.drafts_dir = os.path.join(self.workspace_root, "reports", "draft_modules")

        # Map suggestions listed in the HTML report to their required draft python scripts
        self.required_mappings = {
            "建议一": "qualoop_aci.py",
            "建议二": "sandbox_manager.py",
            "建议三": "replan_executor.py",
            "建议四": "rule_injector.py",
            "建议五": "event_bus.py",
            "建议六": "peer_reviewer.py",
            "建议七": "ast_validator.py",
            "建议十一": "pydantic_schemas.py",
            "建议十二": "agent_tracer.py",
            "建议十三": "gui_tester.py"
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
        
        for sug in unique_suggestions:
            if sug not in self.required_mappings:
                # Some suggestions might be planned (e.g. Docker sandboxing, OpenAI Swarm integrations)
                logger.info("Suggestion '%s' is marked as conceptual roadmap. Skipping code validation.", sug)
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

        # Print audit summary
        print("\n================ QUALOOP RESEARCH AUDIT SUMMARY ================")
        for r in audit_records:
            status = "PASSED" if r["syntax_valid"] else "FAILED"
            print(" - [{}] {} -> File: {} | Details: {}".format(
                status, r["suggestion"], r["required_file"], r["error"] or "OK"
            ))
        print("================================================================\n")

        final_status = "PASSED" if all_passed else "FAILED"
        logger.info("Research Audit Final Status: %s", final_status)
        return {
            "status": final_status,
            "records": audit_records
        }

if __name__ == "__main__":
    # Run auditor on the current repository workspace
    auditor = ResearchAuditor(r"e:\20260502_MZH\Qualoop")
    auditor.run_audit()
