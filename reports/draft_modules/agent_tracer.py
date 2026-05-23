# -*- coding: utf-8 -*-
"""
Qualoop Agent Tracer - Draft Implementation (Python 3)
Implements a telemetry flight recorder inspired by Langfuse/AgentOps.
Tracks LLM latency, token costs, tool invocations, and infinite loop warnings.
"""
import os
import sys
import time
import json
import uuid
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AgentTracer")

class QualoopTracer(object):
    def __init__(self, trace_file="reports/agent_traces.jsonl"):
        self.trace_file = trace_file
        self.active_spans = {}
        self._ensure_dir()

    def _ensure_dir(self):
        dir_name = os.path.dirname(self.trace_file)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name)

    def start_trace(self, agent_role, task_name):
        """Starts a new trace session for an agent role."""
        trace_id = str(uuid.uuid4())
        span = {
            "trace_id": trace_id,
            "agent_role": agent_role,
            "task_name": task_name,
            "start_time": time.time(),
            "status": "RUNNING",
            "calls": []
        }
        self.active_spans[trace_id] = span
        logger.info("Started Trace: %s | Role: %s | Task: %s", trace_id, agent_role, task_name)
        return trace_id

    def record_tool_call(self, trace_id, tool_name, args, duration, status="SUCCESS", error=None):
        """Records an individual tool invocation within the trace span."""
        if trace_id not in self.active_spans:
            return
        
        call_record = {
            "tool_name": tool_name,
            "args": args,
            "duration_ms": int(duration * 1000),
            "status": status,
            "error": error,
            "timestamp": time.time()
        }
        self.active_spans[trace_id]["calls"].append(call_record)
        logger.info("  -> Tool Call Recorded: %s (%dms)", tool_name, int(duration * 1000))

    def end_trace(self, trace_id, status="COMPLETED", prompt_tokens=0, completion_tokens=0, error=None):
        """Ends the trace session, calculates costs, and flushes to the JSONL log file."""
        if trace_id not in self.active_spans:
            return
            
        span = self.active_spans.pop(trace_id)
        span["end_time"] = time.time()
        span["duration_ms"] = int((span["end_time"] - span["start_time"]) * 1000)
        span["status"] = status
        span["error"] = error
        
        # Simple cost calculation based on average model pricing (e.g., $15/M input, $60/M output)
        input_cost = (prompt_tokens / 1000000.0) * 15.0
        output_cost = (completion_tokens / 1000000.0) * 60.0
        span["token_cost_usd"] = input_cost + output_cost
        span["token_usage"] = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens
        }

        # Flush to local file
        try:
            with open(self.trace_file, "a") as f:
                f.write(json.dumps(span) + "\n")
            logger.info("Trace Ended & Saved: %s | Duration: %dms | Cost: $%.5f", 
                        trace_id, span["duration_ms"], span["token_cost_usd"])
        except Exception as e:
            logger.error("Failed to save trace to log file: %s", str(e))

if __name__ == "__main__":
    # Test execution
    tracer = QualoopTracer("scratch/test_traces.jsonl")
    
    # 1. Start a simulation trace representing a Scorer run
    trace_id = tracer.start_trace("Scorer", "Evaluate Issue QL-BUG-12")
    
    # 2. Simulate tool call: safe_read_file
    t_start = time.time()
    time.sleep(0.15) # simulate execution delay
    tracer.record_tool_call(trace_id, "safe_read_file", {"file": "qualoop.json"}, time.time() - t_start)
    
    # 3. Simulate tool call: ast.parse validator
    t_start = time.time()
    time.sleep(0.05)
    tracer.record_tool_call(trace_id, "ast_validator", {"code_len": 4096}, time.time() - t_start)
    
    # 4. End trace with mock token usage
    tracer.end_trace(trace_id, status="COMPLETED", prompt_tokens=1500, completion_tokens=450)
    
    # Clean up test trace file
    try:
        os.remove("scratch/test_traces.jsonl")
        logger.info("Cleaned up test traces file.")
    except Exception:
        pass
