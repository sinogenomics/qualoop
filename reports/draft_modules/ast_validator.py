# -*- coding: utf-8 -*-
"""
Qualoop AST Validator - Draft Implementation
Parses Python code using Python's AST library to check for syntax and structure errors.
Acts as a gatekeeper to prevent malformed code from being written to disk.
"""
import ast
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ASTValidator")

class ASTValidationError(Exception):
    pass

class QualoopASTValidator(object):
    @staticmethod
    def validate_syntax(code_string):
        """Runs ast.parse to check for Python syntax errors."""
        try:
            ast.parse(code_string)
            logger.info("AST Syntax Validation: PASSED")
            return {"valid": True, "error": None}
        except SyntaxError as se:
            err_msg = "SyntaxError on line {}:{}: {}".format(se.lineno, se.offset, se.msg)
            logger.warning("AST Syntax Validation: FAILED - %s", err_msg)
            return {"valid": False, "error": err_msg}
        except Exception as e:
            err_msg = "AST parsing error: {}".format(str(e))
            logger.warning("AST Syntax Validation: FAILED - %s", err_msg)
            return {"valid": False, "error": err_msg}

    @staticmethod
    def extract_defined_symbols(code_string):
        """Extracts top-level class and function names defined in the module."""
        try:
            tree = ast.parse(code_string)
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            return {
                "classes": classes,
                "functions": functions
            }
        except Exception as e:
            logger.error("Failed to extract symbols: %s", str(e))
            return {"classes": [], "functions": []}

    def verify_integrity(self, old_code, new_code):
        """
        Compares old and new AST symbols to check if crucial components were deleted.
        Helps prevent hallucination where LLM deletes class or function definitions entirely.
        """
        # Validate new syntax first
        validation = self.validate_syntax(new_code)
        if not validation["valid"]:
            return validation

        old_symbols = self.extract_defined_symbols(old_code)
        new_symbols = self.extract_defined_symbols(new_code)
        
        # Check if functions present in the old file are missing in the new file
        missing_functions = set(old_symbols["functions"]) - set(new_symbols["functions"])
        missing_classes = set(old_symbols["classes"]) - set(new_symbols["classes"])
        
        warnings = []
        if missing_functions:
            warnings.append("Warning: Missing functions after edit: {}".format(", ".join(missing_functions)))
        if missing_classes:
            warnings.append("Warning: Missing classes after edit: {}".format(", ".join(missing_classes)))
            
        return {
            "valid": True,
            "warnings": warnings,
            "error": None
        }

if __name__ == "__main__":
    # Test execution
    validator = QualoopASTValidator()
    
    # 1. Test syntax validation
    buggy_code = """
def test_func():
    if True
        print("Missing colon")
"""
    print("Testing syntax validation on BUGGY code:")
    print(validator.validate_syntax(buggy_code))
    
    correct_code = """
def test_func():
    if True:
        print("Correct syntax")
"""
    print("\nTesting syntax validation on CORRECT code:")
    print(validator.validate_syntax(correct_code))

    # 2. Test integrity verification
    old_code = """
class MyClass:
    pass

def save():
    pass

def load():
    pass
"""
    # LLM accidentally deleted the load() function during refactoring
    new_code = """
class MyClass:
    pass

def save():
    print("Saving data...")
"""
    print("\nTesting AST Integrity Check (detecting missing functions):")
    res = validator.verify_integrity(old_code, new_code)
    print("Valid:", res["valid"])
    print("Warnings:", res["warnings"])
