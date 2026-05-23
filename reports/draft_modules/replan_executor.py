# -*- coding: utf-8 -*-
"""
Qualoop Re-planning Executor - Draft Implementation
Implements a state machine for self-correction loops.
Captures test errors, feeds tracebacks back to the agent, and blocks infinite loops.
"""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ReplanExecutor")

class LoopBlockerError(Exception):
    """Raised when the agent exceeds maximum tool invocation or retries to prevent API cost storm."""
    pass

class QualoopReplanExecutor(object):
    def __init__(self, sandbox_manager, aci, max_retries=3):
        self.sandbox = sandbox_manager
        self.aci = aci
        self.max_retries = max_retries
        self.call_counter = 0
        self.call_limit = 15  # Suggestion 15: prevent infinite loops in 30 seconds

    def record_api_call(self):
        self.call_counter += 1
        logger.info("API/Tool Call Counter: %d/%d", self.call_counter, self.call_limit)
        if self.call_counter > self.call_limit:
            raise LoopBlockerError("Infinite Loop Detection! Exceeded tool call limit of {}".format(self.call_limit))

    def run_replan_loop(self, issue_id, fix_agent_fn, verify_cmd):
        """
        Executes a self-correction repair transaction.
        Tries to fix, runs verifier, and replans on traceback output.
        """
        logger.info("Starting Re-planning Loop for Issue ID: %s", issue_id)
        
        # 1. Create Git sandbox savepoint
        self.sandbox.create_savepoint()
        
        try:
            retry_count = 0
            error_context = ""
            
            while retry_count < self.max_retries:
                self.record_api_call()
                
                logger.info("Attempt %d/%d to fix Issue: %s", retry_count + 1, self.max_retries, issue_id)
                
                # 2. Invoke the mock fix agent function (passing the error traceback context if any)
                logger.info("Calling Fix Agent...")
                fix_proposal = fix_agent_fn(issue_id, error_context)
                
                # 3. Apply the proposed fixes using ACI
                for filepath, content in fix_proposal.items():
                    logger.info("ACI writing proposed changes to: %s", filepath)
                    self.aci.safe_write_file(filepath, content, overwrite=True)
                
                # 4. Run verification command via ACI
                logger.info("Running Verifier: %s", " ".join(verify_cmd))
                res = self.aci.safe_execute_command(verify_cmd)
                
                if res["exit_code"] == 0:
                    logger.info("Verification succeeded! Issue %s resolved.", issue_id)
                    # 5. Commit and merge sandbox changes
                    self.sandbox.commit_and_merge("Qualoop Auto-Fix: successfully resolved {}".format(issue_id))
                    return True
                else:
                    logger.warning("Verification failed (Exit Code %d). Traceback captured.", res["exit_code"])
                    # Capture traceback/stdout/stderr to feed back to next iteration
                    error_context = "Stdout:\n{}\nStderr:\n{}".format(res["stdout"], res["stderr"])
                    retry_count += 1
            
            # If all retries exhausted, raise error to trigger rollback
            raise LoopBlockerError("Failed to resolve Issue {} after {} retries.".format(issue_id, self.max_retries))
            
        except Exception as e:
            logger.error("Error occurred during repair loop: %s. Initiating Git rollback...", str(e))
            self.sandbox.rollback()
            # Mark issue as requiring human intervention
            logger.warning("Marking Issue %s as requires_human = True", issue_id)
            return {
                "success": False,
                "requires_human": True,
                "error_reason": str(e)
            }

if __name__ == "__main__":
    # Test execution
    from qualoop_aci import QualoopACI
    from sandbox_manager import QualoopSandboxManager
    
    workspace = r"e:\20260502_MZH\Qualoop"
    aci = QualoopACI(workspace)
    sandbox = QualoopSandboxManager(workspace)
    
    executor = QualoopReplanExecutor(sandbox, aci, max_retries=2)
    
    # Mock fix agent function that fails on the first run and succeeds on the second
    run_states = {"runs": 0}
    def mock_fix_agent(issue_id, error_context):
        run_states["runs"] += 1
        if run_states["runs"] == 1:
            logger.info("[Mock LLM] Generating buggy fix code...")
            return {"scratch/test_bug.py": "def test():\n    raise ValueError('Simulated error')\n"}
        else:
            logger.info("[Mock LLM] Analyzing traceback and generating CORRECT fix...")
            return {"scratch/test_bug.py": "def test():\n    return 'Fixed'\n"}

    # Mock verifier command that checks if scratch/test_bug.py exists and returns success if it has no ValueError
    # We will simulate verification by calling a custom python script or system command
    verify_cmd = ["python", "-c", "import sys; content=open('scratch/test_bug.py').read(); sys.exit(1 if 'ValueError' in content else 0)"]
    
    # Run loop
    print("\nRunning simulated Self-Correction loop...")
    result = executor.run_replan_loop("QL-TEST-01", mock_fix_agent, verify_cmd)
    print("Execution Loop Final Result:", result)
