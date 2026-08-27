"""
Self-Modification Module - Autonomous code improvement system.

This module enables the 1st Agent framework to:
1. Analyze its own performance and code
2. Identify areas for improvement
3. Generate and apply code changes
4. Test changes before deployment
5. Rollback if issues are detected

Usage:
    from self_modification import SelfModifier
    
    modifier = SelfModifier(project_root=".")
    results = modifier.improve(focus_areas=["performance", "code_quality"])
"""

from .code_analyzer import CodeAnalyzer, CodeLocation, ImprovementSuggestion
from .change_manager import ChangeManager, ChangeStatus, ModificationType, RiskLevel, CodeChange
from .code_generator import CodeGenerator
from .risk_assessor import RiskAssessor
from .self_modifier import SelfModifier, ImprovementResult

__all__ = [
    "CodeAnalyzer",
    "CodeLocation",
    "ImprovementSuggestion",
    "ChangeManager",
    "ChangeStatus",
    "ModificationType",
    "RiskLevel",
    "CodeChange",
    "CodeGenerator",
    "RiskAssessor",
    "SelfModifier",
    "ImprovementResult"
]
