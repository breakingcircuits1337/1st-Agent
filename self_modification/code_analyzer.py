"""
Code Analyzer - Analyzes code to find improvement opportunities.
"""

import ast
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CodeLocation:
    """Location of code to modify."""
    file_path: str
    line_start: int = 0
    line_end: int = 0
    function_name: Optional[str] = None
    class_name: Optional[str] = None


@dataclass
class ImprovementSuggestion:
    """Suggestion for code improvement."""
    suggestion_id: str = ""
    title: str = ""
    description: str = ""
    priority: int = 0
    category: str = "general"
    code_location: Optional[CodeLocation] = None
    current_code: str = ""
    suggested_code: str = ""
    expected_impact: str = ""
    confidence: float = 0.0
    
    def __post_init__(self):
        if not self.suggestion_id:
            self.suggestion_id = f"suggestion_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


class CodeAnalyzer:
    """Analyzes code to find improvement opportunities."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
    
    def analyze_project(self) -> Dict[str, Any]:
        """Analyze the entire project."""
        analysis = {
            "files": {},
            "improvement_suggestions": []
        }
        
        for py_file in self._find_python_files():
            file_analysis = self.analyze_file(str(py_file))
            analysis["files"][str(py_file.relative_to(self.project_root))] = file_analysis
            analysis["improvement_suggestions"].extend(file_analysis.get("suggestions", []))
        
        analysis["improvement_suggestions"].sort(key=lambda x: x.get("priority", 0), reverse=True)
        return analysis
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a single Python file."""
        file_path = Path(file_path)
        if not file_path.exists():
            return {"error": f"File not found: {file_path}"}
        
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))
            
            analysis = {
                "path": str(file_path),
                "size_bytes": len(content),
                "lines": len(content.splitlines()),
                "functions": [],
                "classes": [],
                "imports": [],
                "complexity": 0,
                "suggestions": []
            }
            
            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        analysis["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        full_name = f"{node.module}.{alias.name}" if node.module else alias.name
                        analysis["imports"].append(full_name)
            
            # Extract functions and classes
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "parameters": [arg.arg for arg in node.args.args],
                        "complexity": self._calculate_function_complexity(node),
                        "lines": node.end_lineno - node.lineno + 1
                    }
                    analysis["functions"].append(func_info)
                    
                    if func_info["lines"] > 100:
                        analysis["suggestions"].append(self._create_suggestion(
                            f"Long function: {node.name}",
                            f"Function {node.name} is {func_info['lines']} lines long",
                            5, "code_quality",
                            CodeLocation(str(file_path), node.lineno, node.end_lineno, node.name),
                            ast.get_source_segment(content, node) or "",
                            "Consider breaking this function into smaller functions"
                        ))
                    
                    if func_info["complexity"] > 10:
                        analysis["suggestions"].append(self._create_suggestion(
                            f"Complex function: {node.name}",
                            f"Function {node.name} has complexity {func_info['complexity']}",
                            7, "code_quality",
                            CodeLocation(str(file_path), node.lineno, node.end_lineno, node.name),
                            ast.get_source_segment(content, node) or "",
                            "Consider simplifying this function"
                        ))
                
                elif isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "methods": [item.name for item in node.body if isinstance(item, ast.FunctionDef)],
                        "lines": node.end_lineno - node.lineno + 1
                    }
                    analysis["classes"].append(class_info)
            
            analysis["complexity"] = self._calculate_complexity(tree)
            
            # Check for string concatenation
            for node in ast.walk(tree):
                if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                    if isinstance(node.left, ast.Str) and isinstance(node.right, ast.Str):
                        analysis["suggestions"].append(self._create_suggestion(
                            "Use f-strings or .join()",
                            "String concatenation with + is inefficient",
                            3, "performance",
                            CodeLocation(str(file_path), node.lineno),
                            ast.get_source_segment(content, node) or "",
                            "Use f-strings or str.join() for better performance"
                        ))
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return {"error": str(e)}
    
    def _find_python_files(self) -> List[Path]:
        """Find all Python files."""
        python_files = []
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["__pycache__", ".venv", "node_modules"]]
            for file in files:
                if file.endswith(".py"):
                    python_files.append(Path(root) / file)
        return python_files
    
    def _calculate_complexity(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity of AST."""
        complexity = 1
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
        return complexity
    
    def _calculate_function_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate complexity of a function."""
        complexity = 1
        for n in ast.walk(node):
            if isinstance(n, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(n, ast.BoolOp):
                complexity += len(n.values)
            elif isinstance(n, ast.Compare):
                complexity += len(n.ops)
            elif isinstance(n, (ast.And, ast.Or)):
                complexity += 1
        return complexity
    
    def _create_suggestion(self, title: str, description: str, priority: int, 
                          category: str, location: CodeLocation, 
                          current_code: str, expected_impact: str) -> Dict[str, Any]:
        """Create a suggestion dictionary."""
        return {
            "title": title,
            "description": description,
            "priority": priority,
            "category": category,
            "code_location": {
                "file_path": location.file_path,
                "line_start": location.line_start,
                "line_end": location.line_end,
                "function_name": location.function_name
            },
            "current_code": current_code,
            "expected_impact": expected_impact,
            "confidence": 0.8,
            "suggestion_id": f"suggestion_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
