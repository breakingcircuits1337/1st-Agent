"""
Self Modifier - Main interface for autonomous code improvement.
"""

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .code_analyzer import CodeAnalyzer, CodeLocation, ImprovementSuggestion
from .change_manager import ChangeManager, ChangeStatus, CodeChange, ModificationType, RiskLevel
from .code_generator import CodeGenerator
from .risk_assessor import RiskAssessor

logger = logging.getLogger(__name__)


@dataclass
class ImprovementResult:
    """Result of an improvement cycle."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    suggestions_generated: int = 0
    changes_proposed: int = 0
    changes_validated: int = 0
    changes_applied: int = 0
    changes: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class SelfModifier:
    """
    Main interface for autonomous code improvement.
    
    This class coordinates the entire self-modification process:
    1. Analyze code and performance
    2. Generate improvement suggestions
    3. Assess risks
    4. Apply changes (with validation)
    5. Monitor results
    
    Usage:
        modifier = SelfModifier(project_root=".")
        
        # Run a self-improvement cycle
        results = modifier.improve(
            focus_areas=["performance", "code_quality"],
            max_changes=5,
            auto_apply=False
        )
        
        # Or apply a specific suggestion
        change_id = modifier.apply_suggestion(suggestion, auto_validate=True)
    """
    
    def __init__(self, project_root: str = ".", llm_client: Any = None):
        self.project_root = Path(project_root)
        self.analyzer = CodeAnalyzer(project_root)
        self.generator = CodeGenerator(llm_client)
        self.change_manager = ChangeManager(project_root)
        self.risk_assessor = RiskAssessor()
        self._history: List[ImprovementResult] = []
        self._lock = threading.RLock()
    
    def improve(self, focus_areas: List[str] = None, 
                max_changes: int = 5, 
                auto_apply: bool = False,
                auto_validate: bool = True,
                min_confidence: float = 0.7,
                risk_threshold: RiskLevel = RiskLevel.HIGH) -> ImprovementResult:
        """
        Run a complete self-improvement cycle.
        
        Args:
            focus_areas: Areas to focus on (e.g., "performance", "code_quality")
            max_changes: Maximum number of changes to propose
            auto_apply: Whether to automatically apply validated changes
            auto_validate: Whether to automatically validate changes
            min_confidence: Minimum confidence score for suggestions
            risk_threshold: Maximum acceptable risk level
        
        Returns:
            ImprovementResult with results of the cycle
        """
        with self._lock:
            result = ImprovementResult()
            
            try:
                # Step 1: Analyze the project
                logger.info("Analyzing project...")
                analysis = self.analyzer.analyze_project()
                
                # Step 2: Filter and prioritize suggestions
                suggestions = []
                for suggestion_data in analysis.get("improvement_suggestions", []):
                    try:
                        if isinstance(suggestion_data, dict):
                            suggestion = ImprovementSuggestion(
                                suggestion_id=suggestion_data.get("suggestion_id", ""),
                                title=suggestion_data.get("title", ""),
                                description=suggestion_data.get("description", ""),
                                priority=suggestion_data.get("priority", 0),
                                category=suggestion_data.get("category", "general"),
                                current_code=suggestion_data.get("current_code", ""),
                                expected_impact=suggestion_data.get("expected_impact", ""),
                                confidence=suggestion_data.get("confidence", 0.8)
                            )
                            
                            # Set code_location if present
                            loc_data = suggestion_data.get("code_location", {})
                            if loc_data:
                                suggestion.code_location = CodeLocation(
                                    file_path=loc_data.get("file_path", ""),
                                    line_start=loc_data.get("line_start", 0),
                                    line_end=loc_data.get("line_end", 0),
                                    function_name=loc_data.get("function_name")
                                )
                        else:
                            suggestion = suggestion_data
                        
                        # Filter by focus areas
                        if focus_areas and suggestion.category not in focus_areas:
                            continue
                        
                        # Filter by confidence
                        if suggestion.confidence < min_confidence:
                            continue
                        
                        suggestions.append(suggestion)
                    except Exception as e:
                        logger.warning(f"Error processing suggestion: {e}")
                        continue
                
                # Sort by priority
                suggestions.sort(key=lambda x: x.priority, reverse=True)
                
                result.suggestions_generated = len(suggestions)
                
                # Step 3: Generate changes from suggestions
                for suggestion in suggestions[:max_changes]:
                    try:
                        # Generate change
                        change = self.generator.generate_from_suggestion(suggestion)
                        
                        if not change:
                            continue
                        
                        # Update change with suggestion details
                        if suggestion.code_location:
                            change.file_path = suggestion.code_location.file_path
                            change.line_start = suggestion.code_location.line_start
                            change.line_end = suggestion.code_location.line_end
                        
                        change_id = self.change_manager.propose_change(change)
                        result.changes.append(change.to_dict())
                        result.changes_proposed += 1
                        
                        # Step 4: Assess risk
                        risk_assessment = self.risk_assessor.assess_change(change)
                        change.risk_level = risk_assessment["risk_level"]
                        
                        # Update change in manager
                        self.change_manager._changes[change_id] = change
                        
                        # Check risk threshold
                        if risk_assessment["risk_level"].value > risk_threshold.value:
                            logger.warning(f"Change {change_id} exceeds risk threshold: {risk_assessment['risk_level']}")
                            continue
                        
                        # Step 5: Validate
                        if auto_validate:
                            if self.change_manager.validate_change(change_id):
                                result.changes_validated += 1
                                
                                # Step 6: Apply if auto_apply
                                if auto_apply:
                                    if self.change_manager.apply_change(change_id):
                                        result.changes_applied += 1
                        
                    except Exception as e:
                        result.errors.append(str(e))
                        logger.error(f"Error processing suggestion: {e}")
                
                # Record in history
                self._history.append(result)
                
                logger.info(f"Improvement cycle complete: {result.changes_proposed} changes proposed, "
                           f"{result.changes_validated} validated, {result.changes_applied} applied")
                
                return result
                
            except Exception as e:
                logger.error(f"Improvement cycle failed: {e}")
                result.errors.append(str(e))
                return result
    
    def apply_suggestion(self, suggestion: Dict[str, Any], 
                         auto_validate: bool = True,
                         auto_apply: bool = False) -> Optional[str]:
        """
        Apply a specific suggestion.
        
        Args:
            suggestion: The improvement suggestion to apply
            auto_validate: Whether to validate the change
            auto_apply: Whether to apply the change if validated
        
        Returns:
            The change ID if successful, None otherwise
        """
        try:
            # Generate change
            change = self.generator.generate_from_suggestion(suggestion)
            
            if not change:
                logger.error("Failed to generate change from suggestion")
                return None
            
            # Propose change
            change_id = self.change_manager.propose_change(change)
            
            if not change_id:
                logger.error("Failed to propose change")
                return None
            
            # Assess risk
            risk_assessment = self.risk_assessor.assess_change(change)
            change.risk_level = risk_assessment["risk_level"]
            
            logger.info(f"Risk assessment for {change_id}: {risk_assessment['risk_level']} "
                       f"(score: {risk_assessment['total_score']:.2f})")
            
            # Validate
            if auto_validate:
                if not self.change_manager.validate_change(change_id):
                    logger.error(f"Validation failed for {change_id}")
                    return None
            
            # Apply
            if auto_apply:
                if not self.change_manager.apply_change(change_id):
                    logger.error(f"Failed to apply {change_id}")
                    return None
            
            return change_id
            
        except Exception as e:
            logger.error(f"Failed to apply suggestion: {e}")
            return None
    
    def get_improvement_history(self, limit: int = 10) -> List[Dict]:
        """Get the history of improvement cycles."""
        with self._lock:
            return [r.to_dict() if hasattr(r, 'to_dict') else dict(r._asdict()) 
                   for r in self._history[-limit:]]
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get the current state of the self-modification system."""
        return {
            "pending_changes": len(self.change_manager.list_changes(ChangeStatus.PROPOSED)),
            "validated_changes": len(self.change_manager.list_changes(ChangeStatus.VALIDATED)),
            "applied_changes": len(self.change_manager.get_applied_changes()),
            "improvement_cycles": len(self._history),
            "last_cycle": self._history[-1].to_dict() if self._history else None
        }
    
    def rollback_all(self) -> int:
        """Rollback all applied changes."""
        applied = self.change_manager.get_applied_changes()
        rolled_back = 0
        
        for change in applied:
            if self.change_manager.rollback_change(change.change_id):
                rolled_back += 1
        
        logger.info(f"Rolled back {rolled_back} changes")
        return rolled_back
    
    def rollback_change(self, change_id: str) -> bool:
        """Rollback a specific change."""
        return self.change_manager.rollback_change(change_id)
    
    def list_changes(self, status: Optional[ChangeStatus] = None) -> List[CodeChange]:
        """List all changes, optionally filtered by status."""
        return self.change_manager.list_changes(status)
    
    def get_change(self, change_id: str) -> Optional[CodeChange]:
        """Get a specific change by ID."""
        return self.change_manager.get_change(change_id)
    
    def apply_change(self, change_id: str, backup: bool = True) -> bool:
        """Apply a validated change."""
        return self.change_manager.apply_change(change_id, backup)
    
    def validate_change(self, change_id: str, run_tests: bool = True) -> bool:
        """Validate a proposed change."""
        return self.change_manager.validate_change(change_id, run_tests)


# Helper function to convert ImprovementResult to dict
@dataclass
class ImprovementResultDict:
    timestamp: str
    suggestions_generated: int
    changes_proposed: int
    changes_validated: int
    changes_applied: int
    changes: List[Dict[str, Any]]
    errors: List[str]
    
    @classmethod
    def from_result(cls, result: ImprovementResult) -> "ImprovementResultDict":
        return cls(
            timestamp=result.timestamp,
            suggestions_generated=result.suggestions_generated,
            changes_proposed=result.changes_proposed,
            changes_validated=result.changes_validated,
            changes_applied=result.changes_applied,
            changes=result.changes,
            errors=result.errors
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "suggestions_generated": self.suggestions_generated,
            "changes_proposed": self.changes_proposed,
            "changes_validated": self.changes_validated,
            "changes_applied": self.changes_applied,
            "changes": self.changes,
            "errors": self.errors
        }
