# -*- coding: utf-8 -*-
"""
Qualoop Loop Blocker - Draft Implementation (Suggestion 15)
Tracks agent execution hashes, action logs, and token/API budgets to detect
runaway loops, repetitive states, and trigger circuit breakers.
"""
import hashlib
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("LoopBlocker")

class LoopBlockerException(Exception):
    """Raised when an infinite loop, excessive repetition, or budget overflow is blocked."""
    pass

class LoopBlocker(object):
    def __init__(self, max_repeats=3, max_token_budget=100000, max_seconds=300):
        self.max_repeats = max_repeats
        self.max_token_budget = max_token_budget
        self.max_seconds = max_seconds
        
        self.start_time = time.time()
        self.action_history = []
        self.state_hashes = {}  # state_hash -> count
        self.tokens_used = 0

    def record_action(self, action_type, detail):
        """Records an agent action (e.g. 'write_file', 'run_command')."""
        elapsed = time.time() - self.start_time
        if elapsed > self.max_seconds:
            raise LoopBlockerException("Execution Timeout: Loop blocker triggered after {:.2f}s".format(elapsed))
            
        action_str = "{}:{}".format(action_type, detail)
        # Compute SHA-256 state hash for exact duplicates
        state_hash = hashlib.sha256(action_str.encode("utf-8") if hasattr(action_str, "encode") else action_str).hexdigest()
        
        self.action_history.append({
            "timestamp": time.time(),
            "action": action_type,
            "detail": detail,
            "hash": state_hash
        })
        
        # Track repetition
        self.state_hashes[state_hash] = self.state_hashes.get(state_hash, 0) + 1
        if self.state_hashes[state_hash] > self.max_repeats:
            raise LoopBlockerException(
                "Infinite Loop Blocked: Action '{}:{}' was repeated {} times consecutively/repetitively.".format(
                    action_type, detail, self.state_hashes[state_hash]
                )
            )

    def record_tokens(self, count):
        """Updates cumulative token consumption and triggers budget circuit breaker."""
        self.tokens_used += count
        logger.debug("Tokens used: %d / %d", self.tokens_used, self.max_token_budget)
        if self.tokens_used > self.max_token_budget:
            raise LoopBlockerException(
                "Budget Exceeded: Token consumption of {} exceeded maximum budget of {}.".format(
                    self.tokens_used, self.max_token_budget
                )
            )

    def reset(self):
        """Resets the loop blocker state."""
        self.start_time = time.time()
        self.action_history = []
        self.state_hashes = {}
        self.tokens_used = 0
        logger.info("Loop blocker successfully reset.")

if __name__ == "__main__":
    blocker = LoopBlocker(max_repeats=2, max_token_budget=1000)
    
    try:
        print("Recording normal token usage...")
        blocker.record_tokens(500)
        
        print("Recording repetitive write file actions...")
        blocker.record_action("write_file", "qualoop.json")
        blocker.record_action("write_file", "qualoop.json")
        
        print("Triggering repetition block...")
        blocker.record_action("write_file", "qualoop.json")  # 3rd time -> exceeds max_repeats=2
    except LoopBlockerException as e:
        print("Blocked successfully:", str(e))
        
    try:
        blocker.reset()
        print("Triggering budget block...")
        blocker.record_tokens(1200)  # Exceeds max_token_budget=1000
    except LoopBlockerException as e:
        print("Blocked successfully:", str(e))
