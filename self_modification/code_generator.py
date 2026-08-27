"""
Code Generator - Generates improved code from suggestions.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .code_analyzer import CodeLocation, ImprovementSuggestion
from .change_manager import CodeChange, ChangeStatus, ModificationType, RiskLevel

logger = logging.getLogger(__name__)


class CodeGenerator:
    """Generates improved code from suggestions."""
    
    def __init__(self, llm_client: Any = None):
        self.llm_client = llm_client
        self._templates = self._load_templates()
    
    def generate_from_suggestion(self, suggestion: Dict[str, Any]) -> Optional[CodeChange]:
        """Generate a code change from a suggestion dictionary."""
        # Convert to ImprovementSuggestion if needed
        if isinstance(suggestion, dict):
            sugg = ImprovementSuggestion(
                title=suggestion.get("title", ""),
                description=suggestion.get("description", ""),
                priority=suggestion.get("priority", 0),
                category=suggestion.get("category", "general"),
                current_code=suggestion.get("current_code", ""),
                expected_impact=suggestion.get("expected_impact", ""),
                confidence=suggestion.get("confidence", 0.8)
            )
            
            location_data = suggestion.get("code_location", {})
            if location_data:
                sugg.code_location = CodeLocation(
                    file_path=location_data.get("file_path", ""),
                    line_start=location_data.get("line_start", 0),
                    line_end=location_data.get("line_end", 0),
                    function_name=location_data.get("function_name")
                )
        else:
            sugg = suggestion
        
        # Generate improved code
        improved_code = self._generate_improved_code(sugg)
        
        if not improved_code or improved_code == sugg.current_code:
            return None
        
        # Create CodeChange
        location = sugg.code_location or CodeLocation(file_path="")
        
        return CodeChange(
            description=sugg.description or sugg.title,
            modification_type=self._category_to_type(sugg.category),
            risk_level=RiskLevel.LOW,
            status=ChangeStatus.GENERATED,
            file_path=location.file_path,
            line_start=location.line_start,
            line_end=location.line_end,
            old_code=sugg.current_code,
            new_code=improved_code,
            reasoning=f"Generated from suggestion: {sugg.title}",
            impact_analysis=sugg.expected_impact
        )
    
    def _generate_improved_code(self, suggestion: ImprovementSuggestion) -> str:
        """Generate improved code for a suggestion."""
        # Try LLM first if available
        if self.llm_client:
            code = self._generate_with_llm(suggestion)
            if code and code != suggestion.current_code:
                return code
        
        # Try templates
        code = self._generate_from_template(suggestion)
        if code and code != suggestion.current_code:
            return code
        
        # Simple optimizations
        return self._apply_simple_optimizations(suggestion.current_code)
    
    def _generate_with_llm(self, suggestion: ImprovementSuggestion) -> Optional[str]:
        """Generate code using LLM."""
        try:
            prompt = self._build_llm_prompt(suggestion)
            response = self.llm_client.generate(prompt, temperature=0.3, max_tokens=1000)
            return self._parse_llm_response(response, suggestion)
        except Exception as e:
            logger.warning(f"LLM generation failed: {e}")
            return None
    
    def _generate_from_template(self, suggestion: ImprovementSuggestion) -> Optional[str]:
        """Generate code from templates."""
        category = suggestion.category.lower()
        
        for template_name, template in self._templates.items():
            if category in template_name.lower():
                try:
                    new_code = template["code"].format(
                        function_name=suggestion.code_location.function_name or "",
                        current_code=suggestion.current_code,
                        description=suggestion.description
                    )
                    return new_code
                except Exception as e:
                    logger.warning(f"Template application failed: {e}")
                    continue
        
        return None
    
    def _apply_simple_optimizations(self, code: str) -> str:
        """Apply simple code optimizations."""
        # Replace string concatenation with f-strings or join
        optimized = code
        
        # Simple pattern: "a" + "b" -> "ab"
        optimized = re.sub(r'"([^"]+)"\s*\+\s*"([^"]+)"', r'"\1\2"', optimized)
        
        return optimized
    
    def _build_llm_prompt(self, suggestion: ImprovementSuggestion) -> str:
        """Build a prompt for LLM code generation."""
        return f"""You are a senior Python developer. Improve the following code.

Current code:
```python
{suggestion.current_code}
```

Issue: {suggestion.description}
Category: {suggestion.category}
Expected impact: {suggestion.expected_impact}

Provide ONLY the improved Python code, without any explanation or markdown.
Keep the same interface (function signature, class names).
Only change what's necessary.
Ensure the code is syntactically correct.
"""
    
    def _parse_llm_response(self, response: str, suggestion: ImprovementSuggestion) -> Optional[str]:
        """Parse LLM response to extract code."""
        try:
            # Try to extract code from response
            code_match = re.search(r'```python\s*([\s\S]*?)```', response)
            if code_match:
                return code_match.group(1).strip()
            
            # Try to get the first non-empty line
            lines = [l.strip() for l in response.split('\n') if l.strip()]
            if lines:
                return '\n'.join(lines)
            
            return response
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return None
    
    def _load_templates(self) -> Dict[str, Dict[str, str]]:
        """Load code improvement templates."""
        return {
            "caching_template": {
                "category": "performance",
                "code": """from functools import lru_cache

@lru_cache(maxsize=128)
def {function_name}(*args, **kwargs):
    {current_code}
"""
            },
            "type_hints_template": {
                "category": "code_quality",
                "code": """def {function_name}(*args, **kwargs):
    {current_code}
"""
            },
            "docstring_template": {
                "category": "documentation",
                "code": '''"""
{description}

Args:
    *args: Function arguments
    **kwargs: Additional arguments

Returns:
    Result of the function
"""
def {function_name}(*args, **kwargs):
    {current_code}
'''
            }
        }
    
    def _category_to_type(self, category: str) -> ModificationType:
        """Convert category string to ModificationType."""
        category_map = {
            "performance": ModificationType.PERFORMANCE,
            "bug": ModificationType.BUG_FIX,
            "bug_fix": ModificationType.BUG_FIX,
            "feature": ModificationType.FEATURE,
            "refactor": ModificationType.REFACTOR,
            "documentation": ModificationType.DOCUMENTATION,
            "configuration": ModificationType.CONFIGURATION,
            "test": ModificationType.TEST,
            "code_quality": ModificationType.REFACTOR,
            "general": ModificationType.OPTIMIZATION
        }
        return category_map.get(category.lower(), ModificationType.OPTIMIZATION)
