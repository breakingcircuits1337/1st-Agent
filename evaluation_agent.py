"""
Evaluation Agent - Closed-loop testing and reward signal generation.

This agent completes the RLHF-style loop:
1. Fine-tuning factory creates candidate models
2. Evaluation agent tests them against metrics
3. Reward signals drive further optimization

The evaluation system provides:
- Objective metrics (accuracy, precision, recall, F1)
- Tool-calling correctness
- Response quality scores
- Confidence calibration
- Reward signals for optimization
- Performance tracking over time

Architecture:
┌─────────────────────────────────────────────────────────────┐
│                    Closed-Loop System                          │
├───────────────────────────┬───────────────────────────────────┤
│ FineTuneFactory           │ EvaluationAgent                    │
│  - generate_data()        │  - test_model()                    │
│  - finetune()             │  - calculate_metrics()              │
│  - build_model()          │  - generate_reward()                │
│  - create_model()         │  - track_performance()             │
└───────────────────────────┴───────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ Reward Signal    │ ← Drives optimization
                    │ (Metrics + Scores)│
                    └─────────────────┘
"""

import json
import logging
import os
import random
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import needle
from pydantic import BaseModel

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# Metric Definitions
# =============================================================================

@dataclass
class Metric:
    """A single evaluation metric."""
    name: str
    value: float
    max_value: float = 1.0
    min_value: float = 0.0
    description: str = ""
    weight: float = 1.0  # Weight in overall score
    
    @property
    def normalized(self) -> float:
        """Normalize to 0-1 range."""
        if self.max_value == self.min_value:
            return 0.5
        return (self.value - self.min_value) / (self.max_value - self.min_value)
    
    def __repr__(self):
        return f"{self.name}={self.value:.4f}"


@dataclass
class MetricSuite:
    """Collection of metrics for evaluation."""
    metrics: List[Metric] = field(default_factory=list)
    
    @property
    def total_score(self) -> float:
        """Weighted sum of all normalized metrics."""
        if not self.metrics:
            return 0.0
        total_weight = sum(m.weight for m in self.metrics)
        if total_weight == 0:
            return 0.0
        return sum(m.normalized * m.weight for m in self.metrics) / total_weight
    
    def add_metric(self, metric: Metric) -> None:
        """Add a metric to the suite."""
        self.metrics.append(metric)
    
    def get_metric(self, name: str) -> Optional[Metric]:
        """Get a metric by name."""
        for m in self.metrics:
            if m.name == name:
                return m
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_score": self.total_score,
            "metrics": {m.name: m.value for m in self.metrics},
            "normalized": {m.name: m.normalized for m in self.metrics}
        }


# =============================================================================
# Evaluation Result Models
# =============================================================================

class TestCase(BaseModel):
    """A single test case for evaluation."""
    id: str
    query: str
    expected_tool: Optional[str] = None
    expected_args: Optional[Dict[str, Any]] = None
    expected_output: Optional[str] = None
    domain: str = "general"
    difficulty: str = "medium"  # easy, medium, hard
    weight: float = 1.0


class TestCaseResult(BaseModel):
    """Result of evaluating a single test case."""
    test_case_id: str
    passed: bool
    partial: bool = False
    score: float = 0.0  # 0-1
    actual_tool: Optional[str] = None
    actual_args: Optional[Dict[str, Any]] = None
    actual_output: Optional[str] = None
    error: Optional[str] = None
    latency: float = 0.0  # Seconds
    confidence: Optional[float] = None


class EvaluationResult(BaseModel):
    """Complete evaluation result for a model."""
    model_name: str
    model_path: str
    timestamp: str
    num_tests: int = 0
    num_passed: int = 0
    num_partial: int = 0
    num_failed: int = 0
    total_score: float = 0.0
    metrics: Dict[str, float] = field(default_factory=dict)
    test_case_results: List[TestCaseResult] = field(default_factory=list)
    reward_signal: float = 0.0
    feedback: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    baseline_comparison: Optional[Dict[str, float]] = None


@dataclass
class PerformanceHistory:
    """Historical performance tracking."""
    model_name: str
    evaluations: List[EvaluationResult] = field(default_factory=list)
    
    def add_evaluation(self, result: EvaluationResult) -> None:
        """Add an evaluation to history."""
        self.evaluations.append(result)
    
    def get_trend(self, metric: str = "total_score") -> float:
        """Get trend (positive = improving, negative = declining)."""
        if len(self.evaluations) < 2:
            return 0.0
        values = [e.metrics.get(metric, 0) for e in self.evaluations]
        if len(values) < 2:
            return 0.0
        # Linear trend: (last - first) / num_points
        return (values[-1] - values[0]) / len(values)
    
    def get_best_score(self, metric: str = "total_score") -> float:
        """Get best score achieved."""
        if not self.evaluations:
            return 0.0
        return max(e.metrics.get(metric, 0) for e in self.evaluations)
    
    def get_latest(self) -> Optional[EvaluationResult]:
        """Get latest evaluation."""
        return self.evaluations[-1] if self.evaluations else None


# =============================================================================
# Reward Signal Calculation
# =============================================================================

@dataclass
class RewardConfig:
    """Configuration for reward signal calculation."""
    # Metric weights (must sum to ~1.0)
    accuracy_weight: float = 0.4
    precision_weight: float = 0.2
    recall_weight: float = 0.2
    confidence_weight: float = 0.1
    latency_weight: float = -0.1  # Negative: faster is better
    
    # Thresholds
    pass_threshold: float = 0.8
    partial_threshold: float = 0.5
    
    # Bonuses
    perfect_bonus: float = 0.1  # Bonus for 100% pass rate
    improvement_bonus: float = 0.05  # Bonus for improvement over baseline
    
    def __post_init__(self):
        # Normalize weights
        total = (self.accuracy_weight + self.precision_weight + 
                self.recall_weight + abs(self.latency_weight) + self.confidence_weight)
        if total > 0:
            self.accuracy_weight /= total
            self.precision_weight /= total
            self.recall_weight /= total
            self.confidence_weight /= total
            self.latency_weight /= total


class RewardCalculator:
    """Calculates reward signals from evaluation results."""
    
    def __init__(self, config: Optional[RewardConfig] = None):
        self.config = config or RewardConfig()
    
    def calculate(self, result: EvaluationResult, baseline: Optional[float] = None) -> float:
        """
        Calculate reward signal from evaluation result.
        
        Args:
            result: EvaluationResult to calculate reward from
            baseline: Optional baseline score for comparison
        
        Returns:
            Reward signal (typically 0-1, can exceed 1 for bonuses)
        """
        metrics = result.metrics
        score = result.total_score
        
        # Start with normalized score
        reward = score
        
        # Add bonuses
        if baseline is not None:
            improvement = score - baseline
            if improvement > 0:
                reward += self.config.improvement_bonus * (improvement / (1.0 - baseline + 0.01))
        
        # Perfect bonus
        if result.num_passed == result.num_tests and result.num_tests > 0:
            reward += self.config.perfect_bonus
        
        # Clamp to reasonable range
        reward = max(0.0, min(reward, 2.0))
        
        return reward
    
    def calculate_from_metrics(self, metrics: Dict[str, float]) -> float:
        """Calculate reward directly from metrics dictionary."""
        accuracy = metrics.get("accuracy", 0.0)
        precision = metrics.get("precision", 0.0)
        recall = metrics.get("recall", 0.0)
        confidence = metrics.get("confidence_avg", 0.0)
        latency = metrics.get("latency_avg", 0.0)
        
        # Normalize latency (lower is better, assume 1s max acceptable)
        latency_norm = max(0, 1.0 - min(latency / 1.0, 1.0))
        
        reward = (
            self.config.accuracy_weight * accuracy +
            self.config.precision_weight * precision +
            self.config.recall_weight * recall +
            self.config.confidence_weight * confidence +
            self.config.latency_weight * latency_norm
        )
        
        return max(0.0, min(reward, 1.0))


# =============================================================================
# Evaluation Agent Tools
# =============================================================================

@needle.tool
def run_test_suite(
    model_path: str,
    test_data_path: str,
    num_samples: int = 50,
    domain: str = "general"
) -> EvaluationResult:
    """
    Run a complete test suite against a model.
    
    Args:
        model_path: Path to .cact model
        test_data_path: Path to JSONL test data
        num_samples: Number of test samples to use
        domain: Domain for context
    
    Returns:
        EvaluationResult with all metrics and results
    """
    evaluator = EvaluationAgent()
    return evaluator.evaluate_model(model_path, test_data_path, num_samples, domain)


@needle.tool
def calculate_reward(evaluation_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate reward signal from evaluation results.
    
    Args:
        evaluation_result: EvaluationResult as dictionary
    
    Returns:
        Dict with reward signal and breakdown
    """
    calculator = RewardCalculator()
    result = EvaluationResult(**evaluation_result)
    reward = calculator.calculate(result)
    
    return {
        "reward": reward,
        "model_name": result.model_name,
        "total_score": result.total_score,
        "breakdown": {
            "accuracy": result.metrics.get("accuracy", 0.0),
            "precision": result.metrics.get("precision", 0.0),
            "recall": result.metrics.get("recall", 0.0),
        }
    }


@needle.tool
def compare_models(
    model_a_path: str,
    model_b_path: str,
    test_data_path: str,
    num_samples: int = 50
) -> Dict[str, Any]:
    """
    Compare two models head-to-head.
    
    Args:
        model_a_path: Path to first model
        model_b_path: Path to second model
        test_data_path: Path to test data
        num_samples: Number of test samples
    
    Returns:
        Dict with comparison results
    """
    evaluator = EvaluationAgent()
    
    result_a = evaluator.evaluate_model(model_a_path, test_data_path, num_samples)
    result_b = evaluator.evaluate_model(model_b_path, test_data_path, num_samples)
    
    calculator = RewardCalculator()
    reward_a = calculator.calculate(result_a)
    reward_b = calculator.calculate(result_b)
    
    return {
        "model_a": {
            "name": result_a.model_name,
            "score": result_a.total_score,
            "reward": reward_a
        },
        "model_b": {
            "name": result_b.model_name,
            "score": result_b.total_score,
            "reward": reward_b
        },
        "winner": "model_a" if reward_a >= reward_b else "model_b",
        "difference": abs(reward_a - reward_b)
    }


@needle.tool
def generate_feedback(evaluation_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate actionable feedback from evaluation results.
    
    Args:
        evaluation_result: EvaluationResult as dictionary
    
    Returns:
        Dict with feedback and recommendations
    """
    result = EvaluationResult(**evaluation_result)
    feedback = []
    recommendations = []
    
    # Analyze results
    pass_rate = result.num_passed / result.num_tests if result.num_tests > 0 else 0
    
    if pass_rate >= 0.9:
        feedback.append("Model is performing excellently!")
        recommendations.append("Consider deploying to production")
    elif pass_rate >= 0.7:
        feedback.append("Model is performing well but has room for improvement")
        if result.num_failed > 0:
            recommendations.append(f"Analyze {result.num_failed} failed cases for patterns")
    else:
        feedback.append("Model needs significant improvement")
        recommendations.append("Increase training data or adjust hyperparameters")
    
    # Check for common issues
    if result.metrics.get("accuracy", 0) < 0.7:
        recommendations.append("Improve training data quality and diversity")
    
    if result.metrics.get("confidence_avg", 0) < 0.7:
        recommendations.append("Model confidence is low - may need more training")
    
    return {
        "feedback": feedback,
        "recommendations": recommendations,
        "priority": "high" if pass_rate < 0.7 else "medium"
    }


# =============================================================================
# Evaluation Agent Class
# =============================================================================

EVALUATION_TOOLS = [
    run_test_suite,
    calculate_reward,
    compare_models,
    generate_feedback
]


class EvaluationAgent:
    """
    Evaluation agent for closed-loop model testing.
    
    This agent:
    1. Tests fine-tuned models against test suites
    2. Calculates objective metrics (accuracy, precision, recall, F1)
    3. Generates reward signals for optimization
    4. Provides actionable feedback
    5. Tracks performance history
    
    It's the missing piece that closes the loop in the dual-model architecture.
    """
    
    def __init__(self, weights: Optional[str] = None):
        """
        Initialize the evaluation agent.
        
        Args:
            weights: Path to fine-tuned .cact file, or None for base model
        """
        self.weights = weights
        self.reward_calculator = RewardCalculator()
        self.performance_history: Dict[str, PerformanceHistory] = {}
        self.test_suites: Dict[str, List[TestCase]] = {}
        
        system_prompt = (
            "You are an evaluation specialist. Your job is to rigorously test "
            "machine learning models, calculate objective metrics, and provide "
            "reward signals for optimization. Be precise, data-driven, and "
            "unbiased in your assessments."
        )
        
        self.agent = needle.Needle(
            tools=EVALUATION_TOOLS,
            weights=weights,
            system=system_prompt
        )
    
    def run(self, query: str, max_steps: int = 8) -> dict:
        """Run the evaluation agent on a query."""
        return self.agent.run(query, max_steps=max_steps)
    
    # =========================================================================
    # Core Evaluation Methods
    # =========================================================================
    
    def evaluate_model(
        self,
        model_path: str,
        test_data_path: str,
        num_samples: int = 50,
        domain: str = "general"
    ) -> EvaluationResult:
        """
        Evaluate a model against test data.
        
        Args:
            model_path: Path to .cact model
            test_data_path: Path to JSONL test data
            num_samples: Number of test samples to use
            domain: Domain for context
        
        Returns:
            EvaluationResult with all metrics
        """
        import time
        
        model_name = Path(model_path).stem
        timestamp = datetime.now().isoformat()
        
        # Load test data
        test_cases = self._load_test_cases(test_data_path)
        
        # Sample if needed
        if num_samples and num_samples < len(test_cases):
            test_cases = random.sample(test_cases, num_samples)
        
        # Try to load the model
        try:
            agent = needle.Needle(weights=model_path, tools=[])
        except Exception as e:
            logger.error(f"Failed to load model {model_path}: {e}")
            return EvaluationResult(
                model_name=model_name,
                model_path=model_path,
                timestamp=timestamp,
                num_tests=0,
                feedback=[f"Failed to load model: {str(e)}"]
            )
        
        # Run tests
        results = []
        total_time = 0.0
        
        for test_case in test_cases:
            start_time = time.time()
            result = self._run_single_test(agent, test_case)
            elapsed = time.time() - start_time
            total_time += elapsed
            results.append(result)
        
        # Calculate metrics
        metrics, suite = self._calculate_metrics(results, test_cases)
        
        # Calculate reward
        reward = self.reward_calculator.calculate_from_metrics(metrics)
        
        # Generate feedback
        feedback, recommendations = self._generate_feedback(suite, results)
        
        # Create evaluation result
        evaluation = EvaluationResult(
            model_name=model_name,
            model_path=model_path,
            timestamp=timestamp,
            num_tests=len(test_cases),
            num_passed=sum(1 for r in results if r.passed),
            num_partial=sum(1 for r in results if r.partial),
            num_failed=sum(1 for r in results if not r.passed and not r.partial),
            total_score=suite.total_score,
            metrics=metrics,
            test_case_results=results,
            reward_signal=reward,
            feedback=feedback,
            recommendations=recommendations
        )
        
        # Track history
        if model_name not in self.performance_history:
            self.performance_history[model_name] = PerformanceHistory(model_name=model_name)
        self.performance_history[model_name].add_evaluation(evaluation)
        
        logger.info(f"Evaluated {model_name}: score={suite.total_score:.4f}, reward={reward:.4f}")
        
        return evaluation
    
    def _load_test_cases(self, path: str) -> List[TestCase]:
        """Load test cases from JSONL file."""
        test_cases = []
        
        try:
            with open(path, 'r') as f:
                for i, line in enumerate(f):
                    if line.strip():
                        data = json.loads(line)
                        test_case = TestCase(
                            id=str(i),
                            query=data.get("query", ""),
                            expected_tool=data.get("expected_tool"),
                            expected_args=data.get("expected_args"),
                            expected_output=data.get("expected_output"),
                            domain=data.get("domain", "general"),
                            difficulty=data.get("difficulty", "medium"),
                            weight=data.get("weight", 1.0)
                        )
                        test_cases.append(test_case)
        except FileNotFoundError:
            logger.error(f"Test data file not found: {path}")
        
        return test_cases
    
    def _run_single_test(self, agent: Any, test_case: TestCase) -> TestCaseResult:
        """Run a single test case."""
        import time
        
        start_time = time.time()
        
        try:
            result = agent.complete(test_case.query, max_new_tokens=256)
            function_calls = result.get("function_calls", [])
            
            # Check if expected tool was called
            if test_case.expected_tool:
                expected_tool = test_case.expected_tool
                actual_tools = [c.get("name") for c in function_calls]
                
                if expected_tool in actual_tools:
                    # Check arguments if specified
                    if test_case.expected_args:
                        call = next((c for c in function_calls if c.get("name") == expected_tool), None)
                        if call:
                            actual_args = call.get("arguments", {})
                            if actual_args == test_case.expected_args:
                                passed = True
                                score = 1.0
                            else:
                                # Partial match
                                passed = False
                                partial = True
                                score = self._compare_args(test_case.expected_args, actual_args)
                        else:
                            passed = False
                            partial = False
                            score = 0.0
                    else:
                        passed = True
                        score = 1.0
                else:
                    passed = False
                    partial = False
                    score = 0.0
            else:
                # No expected tool, just check for any valid response
                passed = len(function_calls) > 0
                score = 1.0 if passed else 0.0
            
            confidence = result.get("confidence")
            latency = time.time() - start_time
            
            return TestCaseResult(
                test_case_id=test_case.id,
                passed=passed,
                partial=partial if 'partial' in locals() else False,
                score=score,
                actual_tool=actual_tools[0] if actual_tools else None,
                actual_args=actual_args if 'actual_args' in locals() else None,
                latency=latency,
                confidence=confidence
            )
            
        except Exception as e:
            return TestCaseResult(
                test_case_id=test_case.id,
                passed=False,
                score=0.0,
                error=str(e),
                latency=time.time() - start_time
            )
    
    def _compare_args(self, expected: Dict, actual: Dict) -> float:
        """Compare expected and actual arguments, return similarity score."""
        if not expected or not actual:
            return 0.0
        
        # Count matching keys
        expected_keys = set(expected.keys())
        actual_keys = set(actual.keys())
        
        if not expected_keys:
            return 1.0 if not actual_keys else 0.5
        
        matching_keys = expected_keys & actual_keys
        match_ratio = len(matching_keys) / len(expected_keys)
        
        # Check value similarity
        value_score = 0.0
        for key in matching_keys:
            if expected[key] == actual[key]:
                value_score += 1.0
            elif isinstance(expected[key], (int, float)) and isinstance(actual[key], (int, float)):
                # Numeric similarity
                value_score += 1.0 - abs(expected[key] - actual[key]) / (abs(expected[key]) + 1)
        
        avg_value_score = value_score / len(matching_keys) if matching_keys else 0.0
        
        # Combine key match and value match
        return match_ratio * avg_value_score
    
    def _calculate_metrics(
        self,
        results: List[TestCaseResult],
        test_cases: List[TestCase]
    ) -> Tuple[Dict[str, float], MetricSuite]:
        """Calculate all metrics from test results."""
        suite = MetricSuite()
        metrics = {}
        
        # Basic counts
        num_tests = len(results)
        num_passed = sum(1 for r in results if r.passed)
        num_partial = sum(1 for r in results if r.partial)
        num_failed = num_tests - num_passed - num_partial
        
        # Accuracy
        accuracy = (num_passed + num_partial * 0.5) / num_tests if num_tests > 0 else 0.0
        suite.add_metric(Metric(name="accuracy", value=accuracy, weight=0.4, description="Overall accuracy"))
        metrics["accuracy"] = accuracy
        
        # Precision (passed / (passed + false positives))
        # For tool-calling, false positive = called wrong tool or wrong args
        true_positives = num_passed
        false_positives = num_partial + num_failed
        precision = true_positives / (true_positives + false_positives + 0.001) if (true_positives + false_positives) > 0 else 0.0
        suite.add_metric(Metric(name="precision", value=precision, weight=0.2, description="Precision of tool calls"))
        metrics["precision"] = precision
        
        # Recall (passed / (passed + false negatives))
        # For our case, all tests should have a correct answer, so recall = accuracy
        recall = accuracy
        suite.add_metric(Metric(name="recall", value=recall, weight=0.2, description="Recall of tool calls"))
        metrics["recall"] = recall
        
        # F1 Score
        f1 = 2 * precision * recall / (precision + recall + 0.001) if (precision + recall) > 0 else 0.0
        suite.add_metric(Metric(name="f1", value=f1, weight=0.2, description="F1 score"))
        metrics["f1"] = f1
        
        # Confidence metrics
        confidences = [r.confidence for r in results if r.confidence is not None]
        if confidences:
            confidence_avg = statistics.mean(confidences)
            confidence_std = statistics.stdev(confidences) if len(confidences) > 1 else 0.0
            suite.add_metric(Metric(name="confidence_avg", value=confidence_avg, weight=0.1, description="Average confidence"))
            suite.add_metric(Metric(name="confidence_std", value=confidence_std, max_value=0.5, weight=0.05, description="Confidence standard deviation"))
            metrics["confidence_avg"] = confidence_avg
            metrics["confidence_std"] = confidence_std
        
        # Latency metrics
        latencies = [r.latency for r in results]
        if latencies:
            latency_avg = statistics.mean(latencies)
            latency_std = statistics.stdev(latencies) if len(latencies) > 1 else 0.0
            # Normalize: lower is better, assume 1s max acceptable
            latency_score = max(0, 1.0 - min(latency_avg / 1.0, 1.0))
            suite.add_metric(Metric(name="latency_avg", value=latency_score, min_value=0, max_value=1, weight=-0.1, description="Average latency (normalized)"))
            metrics["latency_avg"] = latency_avg
            metrics["latency_std"] = latency_std
        
        # Pass rate
        pass_rate = num_passed / num_tests if num_tests > 0 else 0.0
        metrics["pass_rate"] = pass_rate
        
        # Partial rate
        partial_rate = num_partial / num_tests if num_tests > 0 else 0.0
        metrics["partial_rate"] = partial_rate
        
        # Fail rate
        fail_rate = num_failed / num_tests if num_tests > 0 else 0.0
        metrics["fail_rate"] = fail_rate
        
        return metrics, suite
    
    def _generate_feedback(
        self,
        suite: MetricSuite,
        results: List[TestCaseResult]
    ) -> Tuple[List[str], List[str]]:
        """Generate human-readable feedback from metrics."""
        feedback = []
        recommendations = []
        
        accuracy = suite.get_metric("accuracy")
        precision = suite.get_metric("precision")
        confidence = suite.get_metric("confidence_avg")
        
        if accuracy and accuracy.value >= 0.9:
            feedback.append(f"Excellent accuracy: {accuracy.value:.1%}")
            recommendations.append("Model is ready for production deployment")
        elif accuracy and accuracy.value >= 0.7:
            feedback.append(f"Good accuracy: {accuracy.value:.1%}")
            failed = sum(1 for r in results if not r.passed and not r.partial)
            if failed > 0:
                recommendations.append(f"Analyze {failed} failed test cases for improvement")
        else:
            feedback.append(f"Low accuracy: {accuracy.value:.1%} - needs improvement")
            recommendations.append("Increase training data or adjust hyperparameters")
        
        if precision and precision.value < 0.7:
            recommendations.append("Model has low precision - many incorrect tool calls")
        
        if confidence and confidence.value < 0.7:
            recommendations.append("Model confidence is low - may need more training")
        
        # Check for patterns in failures
        failed_tests = [r for r in results if not r.passed and not r.partial]
        if failed_tests:
            # Group by error type
            error_counts = {}
            for r in failed_tests:
                error = r.error or "unknown"
                error_counts[error] = error_counts.get(error, 0) + 1
            
            if error_counts:
                most_common = max(error_counts, key=error_counts.get)
                if error_counts[most_common] > len(failed_tests) * 0.5:
                    recommendations.append(f"Address common error: {most_common}")
        
        return feedback, recommendations
    
    # =========================================================================
    # Reward Signal Methods
    # =========================================================================
    
    def calculate_reward(
        self,
        evaluation: EvaluationResult,
        baseline: Optional[float] = None
    ) -> float:
        """
        Calculate reward signal from evaluation.
        
        Args:
            evaluation: EvaluationResult to calculate from
            baseline: Optional baseline score for comparison
        
        Returns:
            Reward signal (0-2 range, can exceed 1 for bonuses)
        """
        return self.reward_calculator.calculate(evaluation, baseline)
    
    def generate_optimization_signal(
        self,
        model_path: str,
        test_data_path: str,
        num_samples: int = 50
    ) -> Dict[str, Any]:
        """
        Generate a complete optimization signal for a model.
        
        This is the main method for closed-loop optimization.
        It evaluates the model and returns a reward signal with feedback
        that can be used to drive further fine-tuning.
        
        Args:
            model_path: Path to the model to evaluate
            test_data_path: Path to test data
            num_samples: Number of test samples
        
        Returns:
            Dict with evaluation results and optimization signal
        """
        # Evaluate the model
        evaluation = self.evaluate_model(model_path, test_data_path, num_samples)
        
        # Calculate reward
        reward = self.calculate_reward(evaluation)
        
        # Get baseline if available
        model_name = Path(model_path).stem
        baseline = None
        if model_name in self.performance_history:
            history = self.performance_history[model_name]
            previous = history.get_latest()
            if previous and previous.model_path != model_path:
                baseline = previous.total_score
        
        # Calculate improvement
        improvement = reward - baseline if baseline is not None else 0.0
        
        return {
            "model": model_name,
            "model_path": model_path,
            "evaluation": evaluation.dict(),
            "reward_signal": reward,
            "baseline": baseline,
            "improvement": improvement,
            "should_continue": improvement > 0.01 or reward < 0.8,
            "feedback": evaluation.feedback,
            "recommendations": evaluation.recommendations,
            "metrics": evaluation.metrics
        }
    
    # =========================================================================
    # Performance Tracking
    # =========================================================================
    
    def get_performance_history(self, model_name: str) -> Optional[PerformanceHistory]:
        """Get performance history for a model."""
        return self.performance_history.get(model_name)
    
    def get_trend(self, model_name: str, metric: str = "total_score") -> float:
        """Get performance trend for a model."""
        history = self.get_performance_history(model_name)
        if history:
            return history.get_trend(metric)
        return 0.0
    
    def get_best_score(self, model_name: str, metric: str = "total_score") -> float:
        """Get best score achieved for a model."""
        history = self.get_performance_history(model_name)
        if history:
            return history.get_best_score(metric)
        return 0.0
    
    # =========================================================================
    # Test Suite Management
    # =========================================================================
    
    def create_test_suite(
        self,
        name: str,
        test_cases: List[TestCase]
    ) -> None:
        """Create a named test suite."""
        self.test_suites[name] = test_cases
        logger.info(f"Created test suite: {name} ({len(test_cases)} cases)")
    
    def save_test_suite(self, name: str, path: str) -> None:
        """Save a test suite to file."""
        if name not in self.test_suites:
            raise ValueError(f"Test suite '{name}' not found")
        
        test_cases = self.test_suites[name]
        
        with open(path, 'w') as f:
            for tc in test_cases:
                f.write(json.dumps(tc.dict()) + "\n")
        
        logger.info(f"Saved test suite '{name}' to {path}")
    
    def load_test_suite(self, name: str, path: str) -> None:
        """Load a test suite from file."""
        test_cases = self._load_test_cases(path)
        self.test_suites[name] = test_cases
        logger.info(f"Loaded test suite '{name}' from {path} ({len(test_cases)} cases)")
    
    def get_test_suite(self, name: str) -> List[TestCase]:
        """Get a test suite by name."""
        return self.test_suites.get(name, [])
    
    def list_test_suites(self) -> List[str]:
        """List all test suite names."""
        return list(self.test_suites.keys())


# =============================================================================
# Convenience Functions
# =============================================================================

def create_evaluator(weights: Optional[str] = None) -> EvaluationAgent:
    """Factory function to create an evaluation agent."""
    return EvaluationAgent(weights=weights)


def run_evaluation(
    model_path: str,
    test_data_path: str,
    num_samples: int = 50
) -> EvaluationResult:
    """Quick evaluation of a model."""
    evaluator = EvaluationAgent()
    return evaluator.evaluate_model(model_path, test_data_path, num_samples)


def get_reward(
    model_path: str,
    test_data_path: str,
    num_samples: int = 50
) -> float:
    """Get reward signal for a model."""
    evaluator = EvaluationAgent()
    evaluation = evaluator.evaluate_model(model_path, test_data_path, num_samples)
    return evaluator.calculate_reward(evaluation)
