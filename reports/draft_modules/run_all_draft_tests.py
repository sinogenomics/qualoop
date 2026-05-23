# -*- coding: utf-8 -*-
"""
Qualoop Drafts Test Suite - QRRVE Quality Gate (run_all_draft_tests.py)
Contains unit tests for all 15 implemented draft modules, verifying code behavior.
"""
import unittest
import os
import sys

# Add current directory to path to enable direct importing of draft modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class TestAllDrafts(unittest.TestCase):
    def setUp(self):
        self.workspace = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Suggestion 1: Qualoop ACI
    def test_suggestion_1_qualoop_aci(self):
        from qualoop_aci import QualoopACI, ACIError
        aci = QualoopACI(self.workspace)
        # Test path normalization and traversal protection
        norm = aci.normalize_path("qualoop.json")
        self.assertTrue(os.path.isabs(norm))
        with self.assertRaises(ACIError):
            aci.normalize_path("../../../etc/passwd")

    # Suggestion 2: Sandbox Manager (Git Savepoint)
    def test_suggestion_2_sandbox_manager(self):
        from sandbox_manager import QualoopSandboxManager
        sm = QualoopSandboxManager(self.workspace)
        self.assertEqual(sm.workspace_root, self.workspace)
        # Test basic properties
        self.assertIsNotNone(sm.workspace_root)

    # Suggestion 3: Replan Executor
    def test_suggestion_3_replan_executor(self):
        from replan_executor import QualoopReplanExecutor
        from sandbox_manager import QualoopSandboxManager
        from qualoop_aci import QualoopACI
        aci = QualoopACI(self.workspace)
        sm = QualoopSandboxManager(self.workspace)
        executor = QualoopReplanExecutor(sm, aci, max_retries=2)
        self.assertEqual(executor.max_retries, 2)

    # Suggestion 4: Rule Injector
    def test_suggestion_4_rule_injector(self):
        from rule_injector import QualoopRuleInjector
        ri = QualoopRuleInjector(self.workspace)
        # Test prompt parsing and formatting
        prompt = ri.inject_rules_into_prompt("Fix this code.", "src/main.py", "Executor")
        self.assertIn("Fix this code.", prompt)

    # Suggestion 5: Event Bus
    def test_suggestion_5_event_bus(self):
        from event_bus import EventBus
        # Use a temporary event bus database file instead of :memory: due to connection pooling
        db_file = "scratch/temp_event_bus.db"
        eb = EventBus(db_path=db_file)
        events = []
        eb.subscribe("issue_detected", lambda ev: events.append(ev))
        
        # Publish
        eb.publish("issue_detected", {"id": "QL-123", "type": "bug"})
        eb.process_pending_events()
        
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "bug")
        
        # Clean up db file
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except Exception:
                pass

    # Suggestion 6: Peer Reviewer
    def test_suggestion_6_peer_reviewer(self):
        from peer_reviewer import QualoopPeerReviewer
        pr = QualoopPeerReviewer()
        old_code = "print('hello')"
        new_code = "print('hello world')"
        res = pr.review_patch("main.py", old_code, new_code, "Maintain print debugging")
        self.assertTrue(res["review_approved"])
        self.assertEqual(res["goal_aligned"], True)

    # Suggestion 7: AST Validator
    def test_suggestion_7_ast_validator(self):
        from ast_validator import QualoopASTValidator
        validator = QualoopASTValidator()
        valid_code = "def foo(): pass"
        invalid_code = "def foo("
        
        self.assertTrue(validator.validate_syntax(valid_code)["valid"])
        self.assertFalse(validator.validate_syntax(invalid_code)["valid"])

    # Suggestion 8: Symbol Map
    def test_suggestion_8_repo_sym_map(self):
        from repo_sym_map import RepoSymbolMap
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sym_map = RepoSymbolMap(current_dir)
        sym_map.scan()
        self.assertIn("qualoop_aci.py", [s["filename"] for s in sym_map.symbols.values()])

    # Suggestion 9: Python Tooling
    def test_suggestion_9_python_tooling(self):
        from python_tooling import SafePythonExecutor
        executor = SafePythonExecutor()
        
        # Test safe execution
        safe = "x = sum([1, 2, 3])"
        res = executor.execute(safe)
        self.assertTrue(res["success"])
        self.assertEqual(res["globals"].get("x"), 6)
        
        # Test unsafe execution blocked
        unsafe = "import os\nos.system('echo')"
        res_unsafe = executor.execute(unsafe)
        self.assertFalse(res_unsafe["success"])
        self.assertIn("blocked", res_unsafe["error"])

    # Suggestion 10: Swarm Router (stateless handoff)
    def test_suggestion_10_swarm_router(self):
        from swarm_router import QualoopSwarmRouter
        router = QualoopSwarmRouter()
        self.assertIsNotNone(router)

    # Suggestion 11: Pydantic Schemas
    def test_suggestion_11_pydantic_schemas(self):
        from pydantic_schemas import QualoopSchemaValidator
        validator = QualoopSchemaValidator()
        mock_issue = {
            "issue_id": "QL-BUG-101",
            "issue_type": "bug",
            "file_path": "src/main.py",
            "description": "Resolve windows path backslash escaping crash during git checkout",
            "metadata": {
                "goal_alignment_note": "Ensures the system executes correctly across cross-platform OS.",
                "value_score": 85,
                "value_qualified": True
            }
        }
        res = validator.validate_issue(mock_issue)
        self.assertTrue(res["valid"])

    # Suggestion 12: Agent Tracer
    def test_suggestion_12_agent_tracer(self):
        from agent_tracer import QualoopTracer
        tracer = QualoopTracer("scratch/test_run_traces.jsonl")
        self.assertIsNotNone(tracer.trace_file)
        # Clean up
        if os.path.exists("scratch/test_run_traces.jsonl"):
            try:
                os.remove("scratch/test_run_traces.jsonl")
            except Exception:
                pass

    # Suggestion 13: GUI Tester
    def test_suggestion_13_gui_tester(self):
        from gui_tester import QualoopGUITester
        tester = QualoopGUITester()
        self.assertEqual(tester.output_dir, "reports/screenshots")

    # Suggestion 14: Docker Sandbox
    def test_suggestion_14_docker_sandbox(self):
        from docker_sandbox import DockerSandbox
        sandbox = DockerSandbox(self.workspace)
        self.assertEqual(sandbox.workspace_root, self.workspace)
        # Verify the availability check executes without raising exceptions
        avail = sandbox.is_docker_available()
        self.assertIn(avail, [True, False])

    # Suggestion 15: Loop Blocker
    def test_suggestion_15_loop_blocker(self):
        from loop_blocker import LoopBlocker, LoopBlockerException
        blocker = LoopBlocker(max_repeats=2, max_token_budget=100)
        
        # Test normal operation
        blocker.record_action("test", "step1")
        blocker.record_action("test", "step2")
        blocker.record_tokens(50)
        
        # Test loop detection
        blocker.record_action("test", "step2")
        with self.assertRaises(LoopBlockerException):
            blocker.record_action("test", "step2")
            
        # Test budget detection
        blocker.reset()
        with self.assertRaises(LoopBlockerException):
            blocker.record_tokens(150)

if __name__ == "__main__":
    unittest.main()
