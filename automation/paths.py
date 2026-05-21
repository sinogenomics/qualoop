import os
import json

# The project root is the parent directory of this automation package.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def get_abs_path(rel_path):
    """Convert a repository-relative path to an absolute path."""
    if os.path.isabs(rel_path):
        return rel_path
    # Strip leading slash or dot-slash if present
    if rel_path.startswith("./"):
        rel_path = rel_path[2:]
    elif rel_path.startswith("/"):
        rel_path = rel_path[1:]
    return os.path.abspath(os.path.join(PROJECT_ROOT, rel_path))

def get_rel_path(abs_path):
    """Convert an absolute path to a repository-relative path."""
    return os.path.relpath(abs_path, PROJECT_ROOT)

def load_config():
    """Load configuration from automation/config.json."""
    config_path = os.path.join(PROJECT_ROOT, "automation", "config.json")
    if not os.path.exists(config_path):
        return {
            "project_root": ".",
            "tester": {
                "markdown_link_check": True,
                "json_schema_check": True,
                "script_syntax_check": True,
                "drift_check": True
            },
            "planner": {
                "enabled": True,
                "scheme_output_path": "docs/ARCHITECTURE_SCHEME.md"
            },
            "scorer": {
                "enabled": True,
                "min_value_score": 60,
                "scale_max": 100,
                "min_qualified_per_round": 1,
                "rubric_path": "templates/scorer_rubric.md"
            },
            "app": {
                "name": "Qualoop",
                "description": "Continuous, bounded self-improvement through quality loops methodology."
            }
        }
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)
