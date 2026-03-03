"""Unittest discovery via AST (no code execution).

This module provides safe, deterministic test discovery by parsing Python
files with the ast module, without executing any code. It extracts unittest
test identifiers from TestCase subclasses and test_* methods.

Functions:
    discover_tests(file_path: str) -> list[dict]
        Find and return unittest test identifiers in a Python file.
"""

import ast
import os
from typing import Any


def discover_tests(file_path: str) -> list[dict]:
    """Discover unittest tests in a Python file using AST parsing.
    
    Scans a Python file for unittest.TestCase subclasses and returns
    a list of discovered test methods without executing any code.
    
    Args:
        file_path: Path to a .py file (absolute or relative).
    
    Returns:
        List of dicts, each with keys:
            - id: Fully qualified test ID (e.g., "module.ClassName.method_name")
            - module: Module name (derived from file basename without .py)
            - class: Class name (e.g., "TestExample")
            - method: Method name (e.g., "test_foo")
        
        Sorted by 'id' for determinism. Empty list if file has no tests,
        syntax error, or file not found.
    
    Examples:
        >>> discover_tests("test_sample.py")
        [
            {
                "id": "test_sample.TestExample.test_foo",
                "module": "test_sample",
                "class": "TestExample",
                "method": "test_foo"
            }
        ]
    """
    try:
        # Validate file exists
        if not os.path.isfile(file_path):
            return []
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Parse into AST
        try:
            tree = ast.parse(code)
        except SyntaxError:
            # Silently return empty list for malformed files
            return []
        
        # Derive module name from file path
        basename = os.path.basename(file_path)
        module_name = os.path.splitext(basename)[0]
        
        # Discover test classes and methods
        tests = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if class inherits from TestCase
                if _inherits_from_testcase(node):
                    # Collect test methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            if item.name.startswith('test_'):
                                test_dict = {
                                    'id': f"{module_name}.{node.name}.{item.name}",
                                    'module': module_name,
                                    'class': node.name,
                                    'method': item.name,
                                }
                                tests.append(test_dict)
        
        # Sort by id for determinism
        tests.sort(key=lambda t: t['id'])
        
        return tests
    
    except Exception:
        # Catch any unexpected errors and return empty list
        return []


def _inherits_from_testcase(class_node: ast.ClassDef) -> bool:
    """Check if a ClassDef node inherits from unittest.TestCase.
    
    Handles common patterns:
        - TestCase (direct reference)
        - unittest.TestCase (qualified reference)
    
    Args:
        class_node: ast.ClassDef node to check.
    
    Returns:
        True if any base is TestCase or unittest.TestCase, False otherwise.
    """
    for base in class_node.bases:
        # Direct name reference: TestCase
        if isinstance(base, ast.Name):
            if base.id == 'TestCase':
                return True
        # Attribute reference: unittest.TestCase
        elif isinstance(base, ast.Attribute):
            if base.attr == 'TestCase':
                return True
    
    return False
