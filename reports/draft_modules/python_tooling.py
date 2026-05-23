# -*- coding: utf-8 -*-
"""
Qualoop Safe Python Tooling - Draft Implementation (Suggestion 9)
Provides a restricted Python execution sandbox using AST-based validation.
Allows executing small code snippets (e.g. data processing, AST queries) safely.
"""
import ast
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PythonTooling")

class SecurityError(Exception):
    pass

class SafeASTValidator(ast.NodeVisitor):
    def __init__(self, allowed_imports=None):
        self.allowed_imports = allowed_imports or ["math", "json", "datetime", "re"]
        self.dangerous_calls = ["eval", "exec", "open", "compile", "globals", "locals", "getattr", "setattr", "delattr"]

    def visit_Import(self, node):
        for name in node.names:
            if name.name not in self.allowed_imports:
                raise SecurityError("Import of module '{}' is blocked in sandbox mode.".format(name.name))
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module not in self.allowed_imports:
            raise SecurityError("Import from module '{}' is blocked in sandbox mode.".format(node.module))
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in self.dangerous_calls:
                raise SecurityError("Invocation of unsafe built-in function '{}' is blocked.".format(func_name))
        self.generic_visit(node)

class SafePythonExecutor(object):
    def __init__(self, allowed_imports=None):
        self.validator = SafeASTValidator(allowed_imports)
        
    def execute(self, code_str, context=None):
        """Compiles and executes the python snippet in a restricted namespace."""
        logger.info("Parsing and validating Python snippet (Length: %d chars)...", len(code_str))
        try:
            tree = ast.parse(code_str)
            # Perform security analysis via AST visitation
            self.validator.visit(tree)
            
            # Prepare restricted environment
            globals_dict = {
                "__builtins__": {
                    "abs": abs,
                    "all": all,
                    "any": any,
                    "bin": bin,
                    "bool": bool,
                    "chr": chr,
                    "dict": dict,
                    "divmod": divmod,
                    "enumerate": enumerate,
                    "filter": filter,
                    "float": float,
                    "format": format,
                    "hash": hash,
                    "hex": hex,
                    "id": id,
                    "int": int,
                    "isinstance": isinstance,
                    "issubclass": issubclass,
                    "iter": iter,
                    "len": len,
                    "list": list,
                    "map": map,
                    "max": max,
                    "min": min,
                    "next": next,
                    "oct": oct,
                    "ord": ord,
                    "pow": pow,
                    "range": range,
                    "repr": repr,
                    "reversed": reversed,
                    "round": round,
                    "set": set,
                    "slice": slice,
                    "sorted": sorted,
                    "str": str,
                    "sum": sum,
                    "tuple": tuple,
                    "type": type,
                    "zip": zip,
                }
            }
            
            if context:
                globals_dict.update(context)
                
            # Compile AST
            compiled = compile(tree, "<sandbox>", "exec")
            
            # Execute
            exec(compiled, globals_dict)
            return {
                "success": True,
                "globals": {k: v for k, v in globals_dict.items() if k != "__builtins__" and not hasattr(v, "__call__")},
                "error": None
            }
        except Exception as e:
            logger.error("Sandbox execution failed: %s", str(e))
            return {
                "success": False,
                "globals": {},
                "error": str(e)
            }

if __name__ == "__main__":
    executor = SafePythonExecutor()
    
    # Safe code
    safe_code = """
import math
result = math.sqrt(64) + 10
"""
    res = executor.execute(safe_code)
    print("Safe Execution Result:", res)
    
    # Dangerous code (should be blocked)
    dangerous_code = """
import os
os.system("echo HACKED")
"""
    res_dangerous = executor.execute(dangerous_code)
    print("Dangerous Execution Result:", res_dangerous)
