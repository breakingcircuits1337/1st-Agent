"""
Risk Assessor - Assesses the risk of code changes.
"""

import logging
from typing import Any, Dict

from .change_manager import CodeChange, ModificationType, RiskLevel

logger = logging.getLogger(__name__)


class RiskAssessor:
    """Assesses the risk of code changes."""
    
    def __init__(self):
        self._risk_factors = {
            "type": {
                ModificationType.BUG_FIX: 0.4,
                ModificationType.PERFORMANCE: 0.3,
                ModificationType.FEATURE: 0.7,
                ModificationType.REFACTOR: 0.5,
                ModificationType.DOCUMENTATION: 0.1,
                ModificationType.CONFIGURATION: 0.2,
                ModificationType.TEST: 0.2,
                ModificationType.OPTIMIZATION: 0.3
            },
            "complexity": 0.3,
            "dependencies": 0.4,
            "test_coverage": -0.5
        }
    
    def assess_change(self, change: CodeChange, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Assess the risk of a code change."""
        context = context or {}
        
        scores = {}
        total_score = 0.0
        weight_sum = 0.0
        
        # Assess based on change type
        type_risk = self._assess_by_type(change)
        scores["type_risk"] = type_risk
        total_score += type_risk * 0.3
        weight_sum += 0.3
        
        # Assess based on code complexity
        complexity_risk = self._assess_complexity(change)
        scores["complexity_risk"] = complexity_risk
        total_score += complexity_risk * 0.3
        weight_sum += 0.3
        
        # Assess based on dependencies
        dep_risk = self._assess_dependencies(change)
        scores["dependency_risk"] = dep_risk
        total_score += dep_risk * 0.2
        weight_sum += 0.2
        
        # Assess based on test impact
        test_risk = self._assess_test_impact(change, context)
        scores["test_risk"] = test_risk
        total_score += test_risk * 0.2
        weight_sum += 0.2
        
        # Normalize score
        if weight_sum > 0:
            total_score /= weight_sum
        
        # Determine risk level
        risk_level = self._score_to_level(total_score)
        
        return {
            "scores": scores,
            "total_score": total_score,
            "risk_level": risk_level,
            "recommendation": self._get_recommendation(total_score, risk_level)
        }
    
    def _assess_by_type(self, change: CodeChange) -> float:
        """Assess risk based on change type."""
        return self._risk_factors["type"].get(change.modification_type, 0.5)
    
    def _assess_complexity(self, change: CodeChange) -> float:
        """Assess risk based on code complexity."""
        try:
            old_lines = change.old_code.count("\n") + 1
            new_lines = change.new_code.count("\n") + 1
            lines_changed = abs(old_lines - new_lines)
            
            complexity_score = min(1.0, lines_changed / 50)
            
            if "def " in change.old_code and "def " in change.new_code:
                complexity_score = min(1.0, complexity_score + 0.3)
            if "class " in change.old_code and "class " in change.new_code:
                complexity_score = min(1.0, complexity_score + 0.4)
            
            return complexity_score
        except Exception:
            return 0.5
    
    def _assess_dependencies(self, change: CodeChange) -> float:
        """Assess risk based on dependencies."""
        dep_count = len(change.dependencies)
        
        if dep_count == 0:
            return 0.2
        elif dep_count <= 3:
            return 0.4
        elif dep_count <= 10:
            return 0.7
        else:
            return 1.0
    
    def _assess_test_impact(self, change: CodeChange, context: Dict[str, Any]) -> float:
        """Assess risk based on test impact."""
        test_count = len(change.tests_affected)
        
        if test_count == 0:
            return 0.5
        elif test_count <= 3:
            return 0.3
        elif test_count <= 10:
            return 0.6
        else:
            return 0.9
    
    def _score_to_level(self, score: float) -> RiskLevel:
        """Convert numeric score to risk level."""
        if score < 0.3:
            return RiskLevel.LOW
        elif score < 0.6:
            return RiskLevel.MEDIUM
        elif score < 0.8:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
    
    def _get_recommendation(self, score: float, level: RiskLevel) -> str:
        """Get a human-readable recommendation."""
        if level == RiskLevel.LOW:
            return "Low risk. Can be applied automatically with monitoring."
        elif level == RiskLevel.MEDIUM:
            return "Medium risk. Review recommended before applying."
        elif level == RiskLevel.HIGH:
            return "High risk. Manual review required. Consider running in staging first."
        else:
            return "Critical risk. Manual approval required. Rollback plan must be in place."
