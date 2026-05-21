import os
import json
import uuid
import hashlib
from datetime import datetime
from automation.paths import get_abs_path

class IssueStore:
    def __init__(self, filename="automation/issues.json"):
        self.filepath = get_abs_path(filename)
        self.data = {"issues": [], "meta": {"version": 1}}
        self.load()

    def load(self):
        """Load issues from the store file, or initialize it if it doesn't exist."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                    if "issues" not in self.data:
                        self.data["issues"] = []
                    if "meta" not in self.data:
                        self.data["meta"] = {"version": 1}
            except Exception as e:
                print(f"Warning: failed to load issue store: {e}. Reinitializing.")
                self.data = {"issues": [], "meta": {"version": 1}}
        else:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            self.save()

    def save(self):
        """Save the issues back to the store file."""
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def calculate_fingerprint(issue_type, description, paths):
        """Generate a stable 16-character hexadecimal fingerprint."""
        sorted_paths = ",".join(sorted(paths))
        raw_str = f"{issue_type}:{description}:{sorted_paths}"
        sha = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()
        return sha[:16]

    def add_candidate(self, severity, issue_type, description, paths, metadata=None):
        """
        Add a newly discovered candidate issue.
        Deduplicates against existing issues using the fingerprint.
        Returns the issue object.
        """
        fingerprint = self.calculate_fingerprint(issue_type, description, paths)
        now = datetime.utcnow().isoformat() + "Z"
        
        # Check for existing issue with the same fingerprint
        existing = None
        for issue in self.data["issues"]:
            if issue.get("fingerprint") == fingerprint:
                existing = issue
                break

        if existing:
            # If the issue was resolved/closed but is found again, reopen it
            if existing["status"] in ["resolved", "wontfix", "duplicate"]:
                existing["status"] = "open"
                existing["updated_at"] = now
                # Clear previous terminal reasons if reopening
                if "metadata" in existing:
                    existing["metadata"].pop("terminal_reason", None)
                    existing["metadata"].pop("value_insufficient", None)
                    existing["metadata"].pop("executor_note", None)
            else:
                # Just update it
                existing["updated_at"] = now
            
            # Merge metadata if provided
            if metadata:
                if "metadata" not in existing:
                    existing["metadata"] = {}
                existing["metadata"].update(metadata)
            
            return existing
        else:
            # Create a brand new issue
            new_issue = {
                "id": str(uuid.uuid4()),
                "severity": severity,
                "type": issue_type,
                "description": description,
                "status": "open",
                "assigned_executor": None,
                "paths": paths,
                "fingerprint": fingerprint,
                "metadata": metadata or {},
                "created_at": now,
                "updated_at": now
            }
            self.data["issues"].append(new_issue)
            return new_issue

    def resolve_missing(self, active_fingerprints):
        """
        Mark open/assigned issues as resolved if they are no longer reported by the tester.
        This provides automatic verification and lifecycle transitions.
        """
        now = datetime.utcnow().isoformat() + "Z"
        resolved_count = 0
        for issue in self.data["issues"]:
            if issue["status"] in ["open", "assigned", "in_progress"]:
                # Architecture planning milestones are not discovered by periodic scanning, so prevent them from auto-resolving
                if issue.get("type") == "architecture":
                    continue
                if issue["fingerprint"] not in active_fingerprints:
                    issue["status"] = "resolved"
                    issue["updated_at"] = now
                    if "metadata" not in issue:
                        issue["metadata"] = {}
                    issue["metadata"]["executor_note"] = "Automatically resolved because the issue is no longer detected by the tester."
                    resolved_count += 1
        return resolved_count

    def get_issues(self):
        return self.data["issues"]
