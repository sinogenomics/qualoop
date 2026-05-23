# -*- coding: utf-8 -*-
"""
Qualoop Symbol Dependency Map - Draft Implementation (Suggestion 8)
Scans Python source files, extracts classes, functions, and call relationships,
and builds an in-memory dependency call graph for automated tracing.
"""
import os
import sys
import ast
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SymbolMap")

class SymbolVisitor(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.current_class = None
        self.current_function = None
        self.symbols = {}  # symbol_name -> symbol_info
        self.calls = []  # List of tuples: (caller_symbol, callee_name)

    def visit_ClassDef(self, node):
        prev_class = self.current_class
        self.current_class = node.name
        class_symbol = node.name
        self.symbols[class_symbol] = {
            "type": "class",
            "name": class_symbol,
            "filename": self.filename,
            "lineno": node.lineno,
            "methods": []
        }
        self.generic_visit(node)
        self.current_class = prev_class

    def visit_FunctionDef(self, node):
        prev_func = self.current_function
        func_name = node.name
        if self.current_class:
            func_symbol = "{}.{}".format(self.current_class, func_name)
            self.symbols[self.current_class]["methods"].append(func_name)
        else:
            func_symbol = func_name

        self.symbols[func_symbol] = {
            "type": "function",
            "name": func_symbol,
            "filename": self.filename,
            "lineno": node.lineno,
            "args": [arg.arg for arg in node.args.args] if hasattr(node.args, "args") else []
        }
        
        self.current_function = func_symbol
        self.generic_visit(node)
        self.current_function = prev_func

    def visit_Call(self, node):
        # We try to resolve the callee name
        callee = None
        if isinstance(node.func, ast.Name):
            callee = node.func.id
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                callee = "{}.{}".format(node.func.value.id, node.func.attr)
            else:
                callee = node.func.attr

        if callee and (self.current_function or self.current_class):
            caller = self.current_function or self.current_class
            self.calls.append((caller, callee))
        
        self.generic_visit(node)

class RepoSymbolMap(object):
    def __init__(self, target_dir):
        self.target_dir = os.path.abspath(target_dir)
        self.symbols = {}
        self.call_graph = {}  # caller -> set(callees)
        self.reverse_call_graph = {}  # callee -> set(callers)

    def scan(self):
        logger.info("Scanning directory: %s for Python symbols", self.target_dir)
        for root, _, files in os.walk(self.target_dir):
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.target_dir)
                    try:
                        with open(full_path, "r", encoding="utf-8") if sys.version_info.major >= 3 else open(full_path, "r") as f:
                            code = f.read()
                        
                        tree = ast.parse(code)
                        visitor = SymbolVisitor(rel_path)
                        visitor.visit(tree)
                        
                        # Merge results
                        self.symbols.update(visitor.symbols)
                        
                        # Record call relationships
                        for caller, callee in visitor.calls:
                            if caller not in self.call_graph:
                                self.call_graph[caller] = set()
                            self.call_graph[caller].add(callee)
                            
                            if callee not in self.reverse_call_graph:
                                self.reverse_call_graph[callee] = set()
                            self.reverse_call_graph[callee].add(caller)
                            
                    except Exception as e:
                        logger.warning("Failed to parse %s: %s", rel_path, str(e))

    def get_dependents(self, symbol_name):
        """Returns symbols that call/depend on the given symbol."""
        visited = set()
        queue = [symbol_name]
        dependents = set()
        
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            
            # Find callers
            callers = self.reverse_call_graph.get(current, set())
            for caller in callers:
                if caller not in dependents:
                    dependents.add(caller)
                    queue.append(caller)
                    
        return list(dependents)

    def to_json(self):
        # Convert sets to lists for JSON serialization
        graph_serializable = {caller: list(callees) for caller, callees in self.call_graph.items()}
        rev_graph_serializable = {callee: list(callers) for callee, callers in self.reverse_call_graph.items()}
        return json.dumps({
            "symbols": self.symbols,
            "call_graph": graph_serializable,
            "reverse_call_graph": rev_graph_serializable
        }, indent=2)

if __name__ == "__main__":
    # Self-test on current draft modules directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sym_map = RepoSymbolMap(current_dir)
    sym_map.scan()
    print("Found symbols:", len(sym_map.symbols))
    print("Exporting symbol call graph...")
    print(list(sym_map.call_graph.keys())[:5])
