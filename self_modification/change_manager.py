"""
Change Manager - Manages the lifecycle of code changes.
"""

import difflib
import logging
import os
import shutil
import tempfile
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ModificationType(Enum):
    BUG_FIX = "bug_fix"
    PERFORMANCE = "performance"
    FEATURE = "feature"
    REFACTOR = "refactor"
    DOCUMENTATION = "documentation"
    CONFIGURATION = "configuration"
    TEST = "test"
    OPTIMIZATION = "optimization"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ChangeStatus(Enum):
    PROPOSED = "proposed"
    GENERATED = "generated"
    VALIDATED = "validated"
    TESTED = "tested"
    APPLIED = "applied"
    ROLLED_BACK = "rolled_back"
    REJECTED = "rejected"


@dataclass
class CodeChange:
    """Represents a proposed code change."""
    change_id: str = field(default_factory=lambda: f"change_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")
    description: str = ""
    modification_type: ModificationType = ModificationType.OPTIMIZATION
    risk_level: RiskLevel = RiskLevel.LOW
    status: ChangeStatus = ChangeStatus.PROPOSED
    file_path: str = ""
    line_start: int = 0
    line_end: int = 0
    old_code: str = ""
    new_code: str = ""
    reasoning: str = ""
    impact_analysis: str = ""
    dependencies: List[str] = field(default_factory=list)
    tests_affected: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    applied_at: Optional[str] = None
    validated_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "change_id": self.change_id,
            "description": self.description,
            "modification_type": self.modification_type.value,
            "risk_level": self.risk_level.value,
            "status": self.status.value,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "old_code": self.old_code,
            "new_code": self.new_code,
            "reasoning": self.reasoning,
            "impact_analysis": self.impact_analysis,
            "dependencies": self.dependencies,
            "tests_affected": self.tests_affected,
            "created_at": self.created_at,
            "applied_at": self.applied_at,
            "validated_at": self.validated_at,
            "metadata": self.metadata
        }
    
    def to_patch(self) -> str:
        """Generate a unified diff patch."""
        old_lines = self.old_code.splitlines(keepends=True)
        new_lines = self.new_code.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f"a/{self.file_path}",
            tofile=f"b/{self.file_path}",
            lineterm=""
        )
        return "".join(diff)


class ChangeManager:
    """Manages the lifecycle of code changes."""
    
    def __init__(self, project_root: str = ".", backup_dir: str = "backups"):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / backup_dir
        self._changes: Dict[str, CodeChange] = {}
        self._applied_changes: List[str] = []
        self._lock = threading.RLock()
        
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def propose_change(self, change: CodeChange) -> str:
        """Propose a new code change."""
        with self._lock:
            change.change_id = change.change_id or f"change_{len(self._changes) + 1}"
            change.status = ChangeStatus.PROPOSED
            self._changes[change.change_id] = change
            logger.info(f"Proposed change: {change.change_id} - {change.description}")
            return change.change_id
    
    def validate_change(self, change_id: str, run_tests: bool = True) -> bool:
        """Validate a proposed change."""
        with self._lock:
            if change_id not in self._changes:
                logger.error(f"Change {change_id} not found")
                return False
            
            change = self._changes[change_id]
            
            # Syntax validation
            if not self._validate_syntax(change):
                change.status = ChangeStatus.REJECTED
                return False
            
            # Import validation
            if not self._validate_imports(change):
                change.status = ChangeStatus.REJECTED
                return False
            
            # Run tests if requested
            if run_tests:
                if not self._run_tests(change):
                    change.status = ChangeStatus.REJECTED
                    return False
            
            change.status = ChangeStatus.VALIDATED
            change.validated_at = datetime.now().isoformat()
            logger.info(f"Validated change: {change_id}")
            return True
    
    def apply_change(self, change_id: str, backup: bool = True) -> bool:
        """Apply a validated change to the codebase."""
        with self._lock:
            if change_id not in self._changes:
                return False
            
            change = self._changes[change_id]
            
            if change.status != ChangeStatus.VALIDATED:
                logger.error(f"Change {change_id} is not validated")
                return False
            
            # Create backup
            if backup:
                backup_path = self._create_backup(change)
                change.metadata["backup_path"] = str(backup_path)
            
            # Apply the change
            try:
                file_path = self.project_root / change.file_path
                content = file_path.read_text(encoding="utf-8")
                
                # Replace old code with new code
                new_content = content.replace(change.old_code, change.new_code)
                
                if new_content == content:
                    # Try line-based replacement
                    lines = content.splitlines(keepends=True)
                    old_lines = change.old_code.splitlines(keepends=True)
                    new_lines = change.new_code.splitlines(keepends=True)
                    
                    start_line = change.line_start - 1
                    end_line = change.line_end
                    
                    new_content = (
                        "".join(lines[:start_line]) +
                        "".join(new_lines) +
                        "".join(lines[end_line:])
                    )
                
                file_path.write_text(new_content, encoding="utf-8")
                
                change.status = ChangeStatus.APPLIED
                change.applied_at = datetime.now().isoformat()
                self._applied_changes.append(change_id)
                
                logger.info(f"Applied change: {change_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to apply change {change_id}: {e}")
                change.status = ChangeStatus.REJECTED
                return False
    
    def rollback_change(self, change_id: str) -> bool:
        """Rollback a previously applied change."""
        with self._lock:
            if change_id not in self._changes:
                return False
            
            change = self._changes[change_id]
            
            if change.status != ChangeStatus.APPLIED:
                return False
            
            backup_path = change.metadata.get("backup_path")
            if not backup_path or not Path(backup_path).exists():
                return False
            
            try:
                file_path = self.project_root / change.file_path
                backup_content = Path(backup_path).read_text(encoding="utf-8")
                file_path.write_text(backup_content, encoding="utf-8")
                
                change.status = ChangeStatus.ROLLED_BACK
                self._applied_changes.remove(change_id)
                
                logger.info(f"Rolled back change: {change_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to rollback change {change_id}: {e}")
                return False
    
    def get_change(self, change_id: str) -> Optional[CodeChange]:
        with self._lock:
            return self._changes.get(change_id)
    
    def list_changes(self, status: Optional[ChangeStatus] = None) -> List[CodeChange]:
        with self._lock:
            changes = list(self._changes.values())
            if status:
                changes = [c for c in changes if c.status == status]
            return sorted(changes, key=lambda x: x.created_at, reverse=True)
    
    def get_applied_changes(self) -> List[CodeChange]:
        with self._lock:
            return [self._changes[cid] for cid in self._applied_changes if cid in self._changes]
    
    def clear_change(self, change_id: str) -> bool:
        with self._lock:
            if change_id in self._changes:
                if change_id in self._applied_changes:
                    self._applied_changes.remove(change_id)
                del self._changes[change_id]
                return True
            return False
    
    def _create_backup(self, change: CodeChange) -> Path:
        """Create a backup of the file before modification."""
        file_path = self.project_root / change.file_path
        backup_file = self.backup_dir / f"{file_path.name}.{change.change_id}.backup"
        shutil.copy2(file_path, backup_file)
        return backup_file
    
    def _validate_syntax(self, change: CodeChange) -> bool:
        """Validate that the new code has correct syntax."""
        try:
            file_path = self.project_root / change.file_path
            if not file_path.exists():
                return False
            
            content = file_path.read_text(encoding="utf-8")
            new_content = content.replace(change.old_code, change.new_code)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(new_content)
                temp_path = f.name
            
            try:
                with open(temp_path, 'r', encoding='utf-8') as f:
                    compile(f.read(), temp_path, 'exec')
                return True
            except SyntaxError as e:
                logger.warning(f"Syntax error in change {change.change_id}: {e}")
                return False
            finally:
                os.unlink(temp_path)
        except Exception as e:
            logger.warning(f"Syntax validation failed: {e}")
            return False
    
    def _validate_imports(self, change: CodeChange) -> bool:
        """Validate that all imports in the new code are available."""
        try:
            import ast
            file_path = self.project_root / change.file_path
            content = file_path.read_text(encoding="utf-8")
            new_content = content.replace(change.old_code, change.new_code)
            
            tree = ast.parse(new_content)
            imports = set()
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
            
            for imp in imports:
                if imp.startswith("__") or imp.startswith("."):
                    continue
                try:
                    __import__(imp)
                except ImportError:
                    logger.warning(f"Import error for {imp}")
                    return False
            
            return True
        except Exception as e:
            logger.warning(f"Import validation failed: {e}")
            return False
    
    def _run_tests(self, change: CodeChange) -> bool:
        """Run tests related to the change."""
        test_files = self._find_related_tests(change)
        
        if not test_files:
            logger.info("No related tests found")
            return True
        
        try:
            for test_file in test_files:
                result = subprocess.run(
                    ["python", "-m", "pytest", str(test_file), "-v"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode != 0:
                    logger.warning(f"Tests failed for {test_file}")
                    return False
            
            return True
        except Exception as e:
            logger.warning(f"Failed to run tests: {e}")
            return False
    
    def _find_related_tests(self, change: CodeChange) -> List[Path]:
        """Find test files related to the change."""
        test_files = []
        module_path = change.file_path.replace(".py", "").replace("/", ".")
        
        test_patterns = [
            f"test_{module_path}.py",
            f"{module_path}_test.py",
            f"tests/test_{module_path}.py",
            f"tests/{module_path}_test.py"
        ]
        
        for pattern in test_patterns:
            test_path = self.project_root / pattern
            if test_path.exists():
                test_files.append(test_path)
        
        return test_files
