# -*- coding: utf-8 -*-
"""
Qualoop Peer Reviewer - Draft Implementation (Python 3)
Implements an automated peer-review gate before sandbox branches are merged.
Uses an LLM agent to audit diffs against the North Star and detect new regressions.
"""
import os
import sys
import difflib
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PeerReviewer")

class QualoopPeerReviewer(object):
    def __init__(self, llm_client=None, min_passing_score=80):
        self.llm_client = llm_client
        self.min_passing_score = min_passing_score

    def generate_diff(self, old_code, new_code, filepath="file.py"):
        """Generates unified diff representation."""
        old_lines = old_code.splitlines(True)
        new_lines = new_code.splitlines(True)
        diff = difflib.unified_diff(old_lines, new_lines, fromfile="a/" + filepath, tofile="b/" + filepath)
        return "".join(diff)

    def review_patch(self, filepath, old_code, new_code, north_star):
        """Audits the changes against the North Star and returns a structured approval verdict."""
        diff_str = self.generate_diff(old_code, new_code, filepath)
        if not diff_str.strip():
            logger.info("No diff detected for %s. Skipping review.", filepath)
            return {"review_approved": True, "score": 100, "rationale": "No changes made."}

        # Prompt definition
        prompt = """You are a senior software quality QA and architect playing the role of Peer Reviewer in Qualoop.
Audit the following code changes (Git Diff) against the project's North Star goal.

North Star Goal:
"{north_star}"

Modified File: {filepath}

Git Diff:
```diff
{diff}
```

Old Code Reference:
```python
{old_code}
```

New Code Reference:
```python
{new_code}
```

Respond with a strictly formatted JSON object containing:
{{
  "goal_aligned": true/false (must be false if changes weaken checks, bypass security, or violate North Star),
  "score": integer from 0 to 100 (rating the quality, security, and cleanliness of the diff),
  "rationale": "Clear, detailed justification of your scoring and review verdict",
  "suggestions": ["Optional list of improvements or issues found"]
}}
"""
        formatted_prompt = prompt.format(
            north_star=north_star,
            filepath=filepath,
            diff=diff_str,
            old_code=old_code,
            new_code=new_code
        )

        logger.info("Submitting diff of %s to Peer Reviewer LLM...", filepath)
        
        # Invoke LLM (simulated here for testing, using structured fallback)
        if self.llm_client:
            try:
                # Actual LLM call if client is provided
                response_str = self.llm_client.call(formatted_prompt)
                review_data = json.loads(response_str)
            except Exception as e:
                logger.error("LLM call failed in PeerReviewer: %s. Using default safety reject.", str(e))
                review_data = {
                    "goal_aligned": False,
                    "score": 0,
                    "rationale": "Review failed due to LLM error: {}".format(str(e)),
                    "suggestions": []
                }
        else:
            # Mock behavior for standalone test run
            logger.info("[Mock Mode] Simulated LLM review analysis...")
            if "raise ValueError" in new_code:
                review_data = {
                    "goal_aligned": False,
                    "score": 45,
                    "rationale": "The change introduces a hardcoded ValueError raise without handling, violating stability constraints.",
                    "suggestions": ["Remove the ValueError raise or catch it safely."]
                }
            else:
                review_data = {
                    "goal_aligned": True,
                    "score": 95,
                    "rationale": "The changes correctly implement safe handlers and align perfectly with project stability goals.",
                    "suggestions": []
                }

        # Calculate final verdict
        score = review_data.get("score", 0)
        goal_aligned = review_data.get("goal_aligned", False)
        
        review_approved = goal_aligned and (score >= self.min_passing_score)
        
        logger.info("Review Outcome - Approved: %s | Score: %d | Rationale: %s", 
                    review_approved, score, review_data.get("rationale"))
                    
        return {
            "review_approved": review_approved,
            "score": score,
            "goal_aligned": goal_aligned,
            "rationale": review_data.get("rationale"),
            "suggestions": review_data.get("suggestions", [])
        }

if __name__ == "__main__":
    # Test execution
    reviewer = QualoopPeerReviewer(min_passing_score=80)
    
    north_star = "Ensure the application handles input safely and remains highly available without hard crashes."
    
    old_code = """
def process_input(data):
    print("Processing:", data)
"""

    # 1. Test bad fix (introduces hard crash ValueError)
    bad_new_code = """
def process_input(data):
    if data is None:
        raise ValueError("Data cannot be None") # Bad: causes crash
    print("Processing:", data)
"""
    print("Reviewing BUGGY code patch:")
    res_bad = reviewer.review_patch("src/input.py", old_code, bad_new_code, north_star)
    print("Result Approved:", res_bad["review_approved"])
    print("Result Score:", res_bad["score"])

    # 2. Test good fix (returns error safely)
    good_new_code = """
def process_input(data):
    if data is None:
        return {"status": "error", "message": "Data cannot be None"}
    print("Processing:", data)
    return {"status": "success"}
"""
    print("\nReviewing CORRECT code patch:")
    res_good = reviewer.review_patch("src/input.py", old_code, good_new_code, north_star)
    print("Result Approved:", res_good["review_approved"])
    print("Result Score:", res_good["score"])
