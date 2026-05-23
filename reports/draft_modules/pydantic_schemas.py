# -*- coding: utf-8 -*-
"""
Qualoop Pydantic Schema Validation - Draft Implementation (Python 3)
Defines strong schemas for Issue Store entries and Scorer outputs.
Implements validation error catchers to provide structured feedback loops.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ValidationError

class IssueMetadataSchema(BaseModel):
    goal_alignment_note: str = Field(..., description="Explanation of how this issue aligns with the North Star")
    value_score: int = Field(..., ge=0, le=100, description="Qualoop value score (0-100)")
    value_qualified: bool = Field(..., description="True if value_score is above the threshold")
    override_reason: Optional[str] = Field(None, description="Reason for overriding Scorer decisions")

class IssueSchema(BaseModel):
    issue_id: str = Field(..., pattern=r"^QL-[A-Z0-9]+-[0-9]+$", description="Qualoop standardized Issue ID (e.g., QL-BUG-12)")
    issue_type: str = Field(..., description="Type of issue: 'bug', 'improvement', or 'architecture'")
    file_path: str = Field(..., description="Target file path relative to workspace root")
    description: str = Field(..., description="Detailed description of the issue or suggestion")
    metadata: IssueMetadataSchema = Field(..., description="Metadata block for alignment and scoring audit")

class ScorerSchema(BaseModel):
    value_score: int = Field(..., ge=0, le=100, description="Evaluated score of the suggestion")
    value_score_rationale: str = Field(..., min_length=15, description="Deep justification of the score")
    goal_aligned: bool = Field(..., description="True if it aligns with the project's ultimate goals")

class QualoopSchemaValidator:
    @staticmethod
    def validate_issue(issue_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Validates an issue and returns schema feedback on failure."""
        try:
            IssueSchema(**issue_dict)
            return {"valid": True, "errors": None}
        except ValidationError as ve:
            # Format validation errors for LLM consumption
            errors = []
            for err in ve.errors():
                loc = " -> ".join(str(l) for l in err["loc"])
                errors.append("[Field Validation Error] Path: '{}' | Msg: {} | Input: {}".format(
                    loc, err["msg"], err.get("input")
                ))
            return {"valid": False, "errors": errors}

    @staticmethod
    def validate_score(score_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Validates scorer output schema."""
        try:
            ScorerSchema(**score_dict)
            return {"valid": True, "errors": None}
        except ValidationError as ve:
            errors = []
            for err in ve.errors():
                loc = " -> ".join(str(l) for l in err["loc"])
                errors.append("[Scorer Schema Error] Path: '{}' | Msg: {} | Input: {}".format(
                    loc, err["msg"], err.get("input")
                ))
            return {"valid": False, "errors": errors}

if __name__ == "__main__":
    # Test execution
    validator = QualoopSchemaValidator()
    
    # 1. Test buggy issue payload (missing metadata fields and bad issue_id format)
    buggy_payload = {
        "issue_id": "QL-invalid-id",
        "issue_type": "bug",
        "file_path": "src/main.py",
        "description": "Fix bug",
        "metadata": {
            "value_score": 150,  # Invalid: must be <= 100
            "value_qualified": True
            # Missing goal_alignment_note
        }
    }
    print("Testing Pydantic validation on BUGGY payload:")
    res_buggy = validator.validate_issue(buggy_payload)
    print("Valid:", res_buggy["valid"])
    for err in res_buggy["errors"]:
        print(err)

    # 2. Test correct issue payload
    correct_payload = {
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
    print("\nTesting Pydantic validation on CORRECT payload:")
    res_correct = validator.validate_issue(correct_payload)
    print("Valid:", res_correct["valid"])
    print("Errors:", res_correct["errors"])
