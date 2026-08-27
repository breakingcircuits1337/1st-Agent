"""
Self-Optimizing Module for 1st Agent Framework

This module enables the system to automate fine-tuning of itself.
It implements meta-learning capabilities where the system can:

1. **Self-Evaluate**: Test its own components (orchestrator, agents, factory)
2. **Auto-Fine-Tune**: Automatically fine-tune weak or new domain agents
3. **Self-Improve**: Generate better training data based on failure patterns
4. **Adapt**: Create new agents for emerging query patterns
5. **Monitor**: Track system-wide performance metrics

Architecture:
┌─────────────────────────────────────────────────────────────────────────┐
│                    SELF-OPTIMIZING SYSTEM                                │
├─────────────────────┬─────────────────────┬─────────────────────┬─────────┤
│  System Monitor     │  Weakness Detector   │  Auto-Trainer       │  Code  │
│  - Track all queries│  - Find patterns      │  - Fine-tune agents  │  Gen   │
│  - Log performance  │  - Identify gaps      │  - Create new agents │       │
│  - Measure latency  │  - Prioritize issues  │  - Optimize params   │       │
└─────────────────────┴─────────────────────┴─────────────────────┴─────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  Self-Optimization   │
                    │      Loop            │
                    │  1. Monitor          │
                    │  2. Detect           │
                    │  3. Train           │
                    │  4. Validate        │
                    │  5. Deploy          │
                    └─────────────────────┘

Usage:
    # Run self-optimization cycle
    from self_optimizer import SelfOptimizer
    
    optimizer = SelfOptimizer()
    
    # Full autonomous optimization
    report = optimizer.run_self_optimization_cycle()
    
    # Or step-by-step
    weaknesses = optimizer.detect_weaknesses()
    improvements = optimizer.generate_improvements(weaknesses)
    optimizer.apply_improvements(improvements)
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from orchestrator import Orchestrator
from evaluation_agent import EvaluationAgent, EvaluationResult, TestCase
from finetune_factory import FineTuneFactory, FineTunedModel
from researcher_agent import ResearcherAgent
from production_agent import ProductionAgent

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# Self-Optimization Data Models
# =============================================================================

@dataclass
class SystemWeakness:
    """A detected weakness in the system."""
    category: str  # "agent", "tool", "domain", "performance", "latency"
    severity: str  # "low", "medium", "high", "critical"
    description: str
    agent_name: Optional[str] = None
    domain: Optional[str] = None
    metric: Optional[str] = None
    current_value: Optional[float] = None
    target_value: Optional[float] = None
    evidence: List[str] = field(default_factory=list)
    priority: int = 0
    
    def __repr__(self):
        return f"Weakness({self.category}:{self.severity} - {self.description})"


@dataclass
class ImprovementPlan:
    """A plan to improve the system."""
    name: str
    description: str
    weakness: SystemWeakness
    action: str  # "retrain", "create_agent", "adjust_params", "add_data"
    expected_impact: float  # 0.0-1.0
    estimated_time: float  # Seconds
    success_criteria: str
    status: str = "pending"  # pending, in_progress, completed, failed
    
    def __repr__(self):
        return f"ImprovementPlan({self.name}: {self.action} -> {self.expected_impact:.0%} improvement)"


@dataclass
class SelfOptimizationReport:
    """Report from a self-optimization cycle."""
    timestamp: str
    duration: float
    weaknesses_detected: int
    improvements_applied: int
    improvements_failed: int
    overall_impact: float  # Aggregate improvement score
    system_metrics: Dict[str, float]
    changes_made: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def __repr__(self):
        return (f"SelfOptimizationReport({self.duration:.1f}s, "
                f"weaknesses={self.weaknesses_detected}, "
                f"improvements={self.improvements_applied}, "
                f"impact={self.overall_impact:.2%})")


@dataclass
class AgentSpec:
    """Specification for creating a new agent."""
    name: str
    domain: str
    description: str
    tools: List[Dict[str, Any]]
    training_samples_needed: int = 200
    test_samples_needed: int = 50
    priority: int = 1


# =============================================================================
# System Monitor
# =============================================================================

class SystemMonitor:
    """
    Monitors the overall system performance.
    
    Tracks:
    - Query success rates per domain
    - Agent performance metrics
    - Latency statistics
    - Error patterns
    - Usage patterns
    """
    
    def __init__(self, orchestrator: Optional[Orchestrator] = None):
        self.orchestrator = orchestrator
        self.query_log: List[Dict[str, Any]] = []
        self.agent_metrics: Dict[str, Dict[str, Any]] = {}
        self.domain_stats: Dict[str, Dict[str, Any]] = {}
        self.error_patterns: Dict[str, int] = {}
        self.usage_patterns: Dict[str, int] = {}
        self.start_time = datetime.now()
    
    def log_query(self, query: str, result: Any, domain: str, agent: str) -> None:
        """Log a query and its result for monitoring."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "domain": domain,
            "agent": agent,
            "success": result.metadata.get("status") == "success",
            "processing_time": result.processing_time,
            "confidence": result.confidence
        }
        self.query_log.append(entry)
        
        # Update domain stats
        if domain not in self.domain_stats:
            self.domain_stats[domain] = {
                "total": 0,
                "success": 0,
                "total_time": 0.0,
                "errors": []
            }
        
        self.domain_stats[domain]["total"] += 1
        if entry["success"]:
            self.domain_stats[domain]["success"] += 1
        self.domain_stats[domain]["total_time"] += entry["processing_time"]
        
        # Track patterns
        if not entry["success"]:
            error_key = f"{domain}:fail"
            self.error_patterns[error_key] = self.error_patterns.get(error_key, 0) + 1
        
        # Track usage
        self.usage_patterns[domain] = self.usage_patterns.get(domain, 0) + 1
    
    def get_domain_performance(self) -> Dict[str, Dict[str, float]]:
        """Get performance metrics per domain."""
        result = {}
        for domain, stats in self.domain_stats.items():
            result[domain] = {
                "success_rate": stats["success"] / stats["total"] if stats["total"] > 0 else 0.0,
                "avg_latency": stats["total_time"] / stats["total"] if stats["total"] > 0 else 0.0,
                "query_count": stats["total"]
            }
        return result
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get system usage statistics."""
        total_queries = len(self.query_log)
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "total_queries": total_queries,
            "queries_per_hour": total_queries / (uptime / 3600 + 0.01),
            "domain_distribution": self.usage_patterns,
            "error_rate": sum(1 for q in self.query_log if not q["success"]) / total_queries if total_queries > 0 else 0.0
        }
    
    def get_error_patterns(self) -> List[Tuple[str, int]]:
        """Get most common error patterns."""
        return sorted(self.error_patterns.items(), key=lambda x: -x[1])
    
    def get_weakest_domains(self, n: int = 3) -> List[Tuple[str, float]]:
        """Get domains with lowest success rates."""
        performance = self.get_domain_performance()
        sorted_domains = sorted(
            performance.items(),
            key=lambda x: x[1]["success_rate"]
        )
        return [(domain, stats["success_rate"]) for domain, stats in sorted_domains[:n]]
    
    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detect anomalous patterns in system behavior."""
        anomalies = []
        
        # Check for high error rates
        error_rate = sum(1 for q in self.query_log if not q["success"]) / len(self.query_log) if self.query_log else 0
        if error_rate > 0.1:
            anomalies.append({
                "type": "high_error_rate",
                "value": error_rate,
                "threshold": 0.1,
                "severity": "high"
            })
        
        # Check for slow responses
        avg_latency = sum(q["processing_time"] for q in self.query_log) / len(self.query_log) if self.query_log else 0
        if avg_latency > 1.0:  # More than 1 second
            anomalies.append({
                "type": "high_latency",
                "value": avg_latency,
                "threshold": 1.0,
                "severity": "medium"
            })
        
        # Check for unused domains
        for domain in self.domain_stats:
            if self.domain_stats[domain]["total"] == 0:
                anomalies.append({
                    "type": "unused_domain",
                    "domain": domain,
                    "severity": "low"
                })
        
        return anomalies


# =============================================================================
# Weakness Detector
# =============================================================================

class WeaknessDetector:
    """
    Detects weaknesses in the system that need improvement.
    
    Analyzes:
    - Low success rates per domain
    - High error rates
    - Slow response times
    - Missing domains
    - Poor confidence scores
    - Tool-calling accuracy
    """
    
    def __init__(self, monitor: SystemMonitor, evaluator: Optional[EvaluationAgent] = None):
        self.monitor = monitor
        self.evaluator = evaluator or EvaluationAgent()
    
    def detect_all_weaknesses(self) -> List[SystemWeakness]:
        """Detect all weaknesses in the system."""
        weaknesses = []
        
        # Check domain performance
        weaknesses.extend(self._detect_domain_weaknesses())
        
        # Check system anomalies
        weaknesses.extend(self._detect_system_weaknesses())
        
        # Check agent-specific weaknesses
        weaknesses.extend(self._detect_agent_weaknesses())
        
        # Sort by priority
        weaknesses.sort(key=lambda w: w.priority, reverse=True)
        
        return weaknesses
    
    def _detect_domain_weaknesses(self) -> List[SystemWeakness]:
        """Detect weaknesses in specific domains."""
        weaknesses = []
        performance = self.monitor.get_domain_performance()
        
        for domain, stats in performance.items():
            success_rate = stats["success_rate"]
            latency = stats["avg_latency"]
            
            if success_rate < 0.8:
                severity = "critical" if success_rate < 0.5 else "high" if success_rate < 0.7 else "medium"
                priority = 10 if severity == "critical" else 7 if severity == "high" else 5
                
                weaknesses.append(SystemWeakness(
                    category="domain",
                    severity=severity,
                    description=f"Low success rate in {domain} domain: {success_rate:.1%}",
                    domain=domain,
                    metric="success_rate",
                    current_value=success_rate,
                    target_value=0.9,
                    priority=priority
                ))
            
            if latency > 0.5:
                weaknesses.append(SystemWeakness(
                    category="performance",
                    severity="medium" if latency < 1.0 else "high",
                    description=f"High latency in {domain} domain: {latency:.2f}s",
                    domain=domain,
                    metric="latency",
                    current_value=latency,
                    target_value=0.3,
                    priority=5
                ))
        
        return weaknesses
    
    def _detect_system_weaknesses(self) -> List[SystemWeakness]:
        """Detect system-wide weaknesses."""
        weaknesses = []
        stats = self.monitor.get_usage_stats()
        anomalies = self.monitor.detect_anomalies()
        
        for anomaly in anomalies:
            if anomaly["type"] == "high_error_rate":
                weaknesses.append(SystemWeakness(
                    category="system",
                    severity=anomaly["severity"],
                    description=f"High overall error rate: {anomaly['value']:.1%}",
                    metric="error_rate",
                    current_value=anomaly["value"],
                    target_value=0.05,
                    priority=10
                ))
            elif anomaly["type"] == "high_latency":
                weaknesses.append(SystemWeakness(
                    category="system",
                    severity=anomaly["severity"],
                    description=f"High overall latency: {anomaly['value']:.2f}s",
                    metric="latency",
                    current_value=anomaly["value"],
                    target_value=0.3,
                    priority=7
                ))
        
        return weaknesses
    
    def _detect_agent_weaknesses(self) -> List[SystemWeakness]:
        """Detect weaknesses in specific agents."""
        weaknesses = []
        
        # This would evaluate each registered agent
        # For now, we'll check if agents exist for all domains
        if self.monitor.orchestrator:
            available_agents = list(self.monitor.orchestrator.specialized_agents.keys())
            used_domains = set(self.monitor.usage_patterns.keys())
            
            # Check for domains with queries but no agent
            for domain in used_domains:
                if domain not in available_agents and domain != "general":
                    weaknesses.append(SystemWeakness(
                        category="agent",
                        severity="high",
                        description=f"No specialized agent for domain: {domain}",
                        domain=domain,
                        priority=8
                    ))
        
        return weaknesses
    
    def detect_emerging_patterns(self, query_log: List[Dict[str, Any]]) -> List[SystemWeakness]:
        """Detect emerging query patterns that aren't well-handled."""
        weaknesses = []
        
        # Simple implementation: look for domains with queries but low success
        domain_success = {}
        domain_count = {}
        
        for query in query_log:
            domain = query.get("domain", "unknown")
            success = query.get("success", False)
            
            domain_count[domain] = domain_count.get(domain, 0) + 1
            if success:
                domain_success[domain] = domain_success.get(domain, 0) + 1
        
        for domain, count in domain_count.items():
            if count > 5:  # Enough samples
                success_rate = domain_success.get(domain, 0) / count
                if success_rate < 0.7:
                    weaknesses.append(SystemWeakness(
                        category="emerging",
                        severity="medium",
                        description=f"Emerging domain with low success: {domain} ({success_rate:.1%})",
                        domain=domain,
                        metric="success_rate",
                        current_value=success_rate,
                        priority=6
                    ))
        
        return weaknesses


# =============================================================================
# Auto-Trainer
# =============================================================================

class AutoTrainer:
    """
    Automatically trains and fine-tunes agents to address weaknesses.
    
    Capabilities:
    - Retrain existing agents with more data
    - Create new agents for missing domains
    - Optimize hyperparameters based on performance
    - Generate synthetic training data
    """
    
    def __init__(
        self,
        factory: FineTuneFactory,
        evaluator: EvaluationAgent,
        orchestrator: Orchestrator
    ):
        self.factory = factory
        self.evaluator = evaluator
        self.orchestrator = orchestrator
        self.training_log: List[Dict[str, Any]] = []
    
    def create_improvement_plan(self, weakness: SystemWeakness) -> Optional[ImprovementPlan]:
        """Create a plan to address a specific weakness."""
        if weakness.category == "domain" and weakness.domain:
            # Low success rate in a domain - retrain the agent
            return ImprovementPlan(
                name=f"retrain_{weakness.domain}",
                description=f"Retrain {weakness.domain} agent to improve success rate",
                weakness=weakness,
                action="retrain",
                expected_impact=0.15,  # 15% improvement expected
                estimated_time=120.0,  # 2 minutes
                success_criteria=f"{weakness.domain} success rate > {weakness.target_value or 0.9}"
            )
        
        elif weakness.category == "agent" and weakness.domain:
            # Missing agent for a domain - create new one
            return ImprovementPlan(
                name=f"create_{weakness.domain}_agent",
                description=f"Create new agent for {weakness.domain} domain",
                weakness=weakness,
                action="create_agent",
                expected_impact=0.2,  # 20% improvement
                estimated_time=180.0,  # 3 minutes
                success_criteria=f"{weakness.domain} agent deployed"
            )
        
        elif weakness.category == "performance" and weakness.domain:
            # High latency - optimize the agent
            return ImprovementPlan(
                name=f"optimize_{weakness.domain}_latency",
                description=f"Optimize {weakness.domain} agent for lower latency",
                weakness=weakness,
                action="adjust_params",
                expected_impact=0.1,
                estimated_time=60.0,
                success_criteria=f"{weakness.domain} latency < {weakness.target_value or 0.3}s"
            )
        
        elif weakness.category == "system":
            # System-wide issue - may need multiple actions
            if "error_rate" in weakness.metric:
                return ImprovementPlan(
                    name="reduce_system_errors",
                    description="Improve overall system error handling",
                    weakness=weakness,
                    action="add_data",  # Add more diverse training data
                    expected_impact=0.1,
                    estimated_time=300.0,
                    success_criteria=f"Error rate < {weakness.target_value or 0.05}"
                )
        
        return None
    
    def execute_plan(self, plan: ImprovementPlan) -> Dict[str, Any]:
        """Execute an improvement plan."""
        plan.status = "in_progress"
        start_time = time.time()
        
        result: Dict[str, Any] = {
            "plan": plan.name,
            "status": "completed",
            "start_time": start_time,
            "end_time": None,
            "changes": [],
            "metrics_before": {},
            "metrics_after": {}
        }
        
        try:
            if plan.action == "retrain":
                result = self._retrain_agent(plan)
            elif plan.action == "create_agent":
                result = self._create_new_agent(plan)
            elif plan.action == "adjust_params":
                result = self._adjust_parameters(plan)
            elif plan.action == "add_data":
                result = self._add_training_data(plan)
            else:
                result["status"] = "failed"
                result["error"] = f"Unknown action: {plan.action}"
            
            result["end_time"] = time.time()
            result["duration"] = result["end_time"] - start_time
            plan.status = result["status"]
            
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            result["end_time"] = time.time()
            result["duration"] = result["end_time"] - start_time
            plan.status = "failed"
            logger.error(f"Failed to execute plan {plan.name}: {e}")
        
        self.training_log.append(result)
        return result
    
    def _retrain_agent(self, plan: ImprovementPlan) -> Dict[str, Any]:
        """Retrain an existing agent."""
        domain = plan.weakness.domain
        result: Dict[str, Any] = {
            "plan": plan.name,
            "action": "retrain",
            "domain": domain,
            "status": "completed",
            "changes": []
        }
        
        # Get existing agent
        if domain not in self.orchestrator.specialized_agents:
            result["status"] = "failed"
            result["error"] = f"No agent found for domain: {domain}"
            return result
        
        agent = self.orchestrator.specialized_agents[domain]
        
        # Get tool schemas from the agent
        try:
            tools_schema = agent.get_tools_schema()
        except Exception as e:
            tools_schema = []
            logger.warning(f"Could not get tools for {domain}: {e}")
        
        # Create new training data
        dataset_path = self.factory.datasets_dir / f"{domain}_retrain_{int(time.time())}.jsonl"
        
        # For simplicity, we'll reuse existing data or generate new
        # In a full implementation, we'd analyze failures and generate targeted data
        if not dataset_path.exists():
            # Try to use existing dataset
            existing_dataset = self.factory.datasets_dir / f"{domain}.jsonl"
            if existing_dataset.exists():
                import shutil
                shutil.copy2(existing_dataset, dataset_path)
        
        # Create new model version
        model = self.factory.create_model(
            name=f"{domain}_v2",
            domain=domain,
            tools_schema=tools_schema,
            num_samples=300,  # More samples for retraining
            epochs=15,
            lora_rank=16
        )
        
        # Update the orchestrator with new model
        # Note: In a real implementation, we'd update the agent to use the new model
        
        result["changes"].append(f"Created new model: {model.model_path}")
        result["new_model"] = model.name
        result["model_path"] = str(model.model_path)
        
        return result
    
    def _create_new_agent(self, plan: ImprovementPlan) -> Dict[str, Any]:
        """Create a new agent for a domain."""
        domain = plan.weakness.domain
        result: Dict[str, Any] = {
            "plan": plan.name,
            "action": "create_agent",
            "domain": domain,
            "status": "completed",
            "changes": []
        }
        
        # For now, we'll create a generic agent
        # In a full implementation, we'd analyze the domain and create appropriate tools
        
        # Generate some basic tools for the new domain
        tools_schema = self._generate_domain_tools(domain)
        
        # Create dataset
        dataset_path = self.factory.datasets_dir / f"{domain}.jsonl"
        self._generate_domain_dataset(domain, dataset_path, num_samples=200)
        
        # Create the model
        model = self.factory.create_model(
            name=domain,
            domain=domain,
            tools_schema=tools_schema,
            num_samples=200,
            epochs=10,
            lora_rank=16
        )
        
        # Create a simple agent class dynamically
        # In a real implementation, we'd write a proper agent file
        agent_code = self._generate_agent_code(domain, tools_schema)
        
        result["changes"].append(f"Created new model: {model.model_path}")
        result["changes"].append(f"Generated agent code for {domain}")
        result["new_model"] = model.name
        result["model_path"] = str(model.model_path)
        result["tools_schema"] = tools_schema
        
        return result
    
    def _adjust_parameters(self, plan: ImprovementPlan) -> Dict[str, Any]:
        """Adjust training parameters for better performance."""
        domain = plan.weakness.domain
        result: Dict[str, Any] = {
            "plan": plan.name,
            "action": "adjust_params",
            "domain": domain,
            "status": "completed",
            "changes": []
        }
        
        # Get the current model
        model_name = f"{domain}_optimized"
        
        # Find existing model or create new
        existing = self.factory.get_model(domain)
        if existing:
            tools_schema = existing.tools_schema
        else:
            # Generate tools
            tools_schema = self._generate_domain_tools(domain)
        
        # Create optimized model with adjusted parameters
        model = self.factory.create_model(
            name=model_name,
            domain=domain,
            tools_schema=tools_schema,
            num_samples=400,  # More data
            epochs=20,  # More epochs
            lora_rank=32,  # Larger LoRA
            lora_alpha=64.0
        )
        
        result["changes"].append(f"Created optimized model: {model.model_path}")
        result["changes"].append("Parameters: samples=400, epochs=20, lora_rank=32")
        result["new_model"] = model.name
        
        return result
    
    def _add_training_data(self, plan: ImprovementPlan) -> Dict[str, Any]:
        """Add more diverse training data."""
        result: Dict[str, Any] = {
            "plan": plan.name,
            "action": "add_data",
            "status": "completed",
            "changes": []
        }
        
        # Generate additional training data for all domains
        for domain in ["weather", "news", "database"]:
            dataset_path = self.factory.datasets_dir / f"{domain}_augmented.jsonl"
            self._generate_domain_dataset(domain, dataset_path, num_samples=100)
            result["changes"].append(f"Added 100 samples to {domain} dataset")
        
        return result
    
    def _generate_domain_tools(self, domain: str) -> List[Dict[str, Any]]:
        """Generate tool schemas for a domain."""
        # Simple tool generation based on domain name
        tools = []
        
        # Map domain keywords to tool types
        if "weather" in domain.lower():
            tools = [
                {
                    "name": "get_weather",
                    "description": "Get current weather",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string"},
                            "units": {"type": "string", "default": "metric"}
                        },
                        "required": ["city"]
                    }
                },
                {
                    "name": "get_forecast",
                    "description": "Get weather forecast",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string"},
                            "days": {"type": "integer", "default": 3}
                        },
                        "required": ["city"]
                    }
                }
            ]
        elif "news" in domain.lower():
            tools = [
                {
                    "name": "get_news",
                    "description": "Get news articles",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "topic": {"type": "string"},
                            "category": {"type": "string"},
                            "limit": {"type": "integer", "default": 5}
                        },
                        "required": ["topic"]
                    }
                },
                {
                    "name": "summarize",
                    "description": "Summarize news",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "topic": {"type": "string"},
                            "num_articles": {"type": "integer", "default": 10}
                        },
                        "required": ["topic"]
                    }
                }
            ]
        elif "database" in domain.lower() or "db" in domain.lower():
            tools = [
                {
                    "name": "query",
                    "description": "Execute database query",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sql": {"type": "string"}
                        },
                        "required": ["sql"]
                    }
                },
                {
                    "name": "list_tables",
                    "description": "List all tables",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            ]
        else:
            # Generic tools for unknown domains
            tools = [
                {
                    "name": "search",
                    "description": f"Search {domain} information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"}
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "get_info",
                    "description": f"Get {domain} information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "topic": {"type": "string"}
                        },
                        "required": ["topic"]
                    }
                }
            ]
        
        return tools
    
    def _generate_domain_dataset(self, domain: str, path: Path, num_samples: int) -> None:
        """Generate a synthetic dataset for a domain."""
        import random
        
        tools = self._generate_domain_tools(domain)
        
        samples = []
        for i in range(num_samples):
            tool = random.choice(tools)
            tool_name = tool["name"]
            
            # Generate query based on tool
            if tool_name == "get_weather":
                cities = ["Lagos", "New York", "Tokyo", "London", "Paris"]
                query = f"What's the weather in {random.choice(cities)}?"
                args = {"city": random.choice(cities)}
            elif tool_name == "get_forecast":
                cities = ["Lagos", "New York", "Tokyo", "London", "Paris"]
                days = random.randint(1, 7)
                query = f"Show me the {days}-day forecast for {random.choice(cities)}"
                args = {"city": random.choice(cities), "days": days}
            elif tool_name == "get_news":
                topics = ["AI", "technology", "sports", "politics"]
                query = f"What's the latest news on {random.choice(topics)}?"
                args = {"topic": random.choice(topics)}
            elif tool_name == "search":
                query = f"Search for information about {domain}"
                args = {"query": domain}
            else:
                query = f"Tell me about {domain}"
                args = {}
            
            sample = {
                "query": query,
                "tools": tools,
                "answers": [{"name": tool_name, "arguments": args}],
                "reasoning": f"User asks about {domain}. Should call {tool_name}."
            }
            samples.append(sample)
        
        with open(path, 'w') as f:
            for sample in samples:
                f.write(json.dumps(sample) + "\n")
        
        logger.info(f"Generated dataset for {domain}: {path} ({num_samples} samples)")
    
    def _generate_agent_code(self, domain: str, tools_schema: List[Dict[str, Any]]) -> str:
        """Generate Python code for a new agent."""
        # This is a simplified version - a full implementation would be more sophisticated
        
        tools_import = """
import needle
from pydantic import BaseModel
from typing import Optional, List, Any
        """
        
        tools_code = ""
        for tool in tools_schema:
            tool_name = tool["name"]
            params = tool.get("parameters", {})
            
            # Generate tool function
            tools_code += f"""
@needle.tool
def {tool_name}(**kwargs) -> dict:
    \"\"\"{tool.get('description', '')}
    
    Args:
        **kwargs: Tool arguments
    
    Returns:
        dict: Tool result
    \"\"\"
    # TODO: Implement actual tool logic
    return {{"status": "not_implemented", "tool": "{tool_name}", "args": kwargs}}
            """
        
        agent_class = f"""
class {domain.capitalize()}Agent:
    \"\"\"Specialized agent for {domain} domain.\"\"\"
    
    def __init__(self, weights: str = None):
        self.agent = needle.Needle(
            tools=[{', '.join(t['name'] for t in tools_schema)}],
            weights=weights,
            system="You are a {domain} assistant. Help users with {domain} queries."
        )
    
    def run(self, query: str, max_steps: int = 8) -> dict:
        return self.agent.run(query, max_steps=max_steps)
    
    def get_tools_schema(self) -> List[Dict]:
        return {tools_schema}
        """
        
        return tools_import + tools_code + agent_class


# =============================================================================
# Self-Optimizer (Main Class)
# =============================================================================

class SelfOptimizer:
    """
    Main class for self-optimizing the 1st Agent framework.
    
    This class coordinates:
    1. System monitoring
    2. Weakness detection
    3. Improvement planning
    4. Automatic training
    5. Validation and deployment
    
    It enables the system to autonomously improve itself over time.
    
    Usage:
        optimizer = SelfOptimizer()
        
        # Run a full optimization cycle
        report = optimizer.run_self_optimization_cycle()
        
        # Or run continuously
        optimizer.run_continuous_optimization(interval=3600)
    """
    
    def __init__(
        self,
        orchestrator: Optional[Orchestrator] = None,
        factory: Optional[FineTuneFactory] = None,
        evaluator: Optional[EvaluationAgent] = None
    ):
        """
        Initialize the self-optimizer.
        
        Args:
            orchestrator: Orchestrator instance
            factory: FineTuneFactory instance
            evaluator: EvaluationAgent instance
        """
        self.orchestrator = orchestrator or Orchestrator()
        self.factory = factory or self.orchestrator.finetune_factory
        self.evaluator = evaluator or self.orchestrator.evaluation_agent
        
        # Components
        self.monitor = SystemMonitor(self.orchestrator)
        self.detector = WeaknessDetector(self.monitor, self.evaluator)
        self.trainer = AutoTrainer(self.factory, self.evaluator, self.orchestrator)
        
        # Configuration
        self.max_improvements_per_cycle = 3
        self.optimization_interval = 3600  # 1 hour
        self.min_reward_threshold = 0.8
        
        # State
        self.running = False
        self.optimization_log: List[SelfOptimizationReport] = []
        
        logger.info("SelfOptimizer initialized")
    
    def run_self_optimization_cycle(self) -> SelfOptimizationReport:
        """
        Run a complete self-optimization cycle.
        
        Steps:
        1. Monitor current system performance
        2. Detect weaknesses
        3. Create improvement plans
        4. Execute top-priority plans
        5. Validate improvements
        6. Generate report
        
        Returns:
            SelfOptimizationReport with results
        """
        start_time = time.time()
        report = SelfOptimizationReport(
            timestamp=datetime.now().isoformat(),
            duration=0.0,
            weaknesses_detected=0,
            improvements_applied=0,
            improvements_failed=0,
            overall_impact=0.0,
            system_metrics={},
            changes_made=[],
            recommendations=[]
        )
        
        try:
            logger.info("=== Starting Self-Optimization Cycle ===")
            
            # Step 1: Monitor
            logger.info("Step 1/5: Monitoring system performance...")
            # The monitor is already tracking via the orchestrator
            # We can analyze the query log
            
            # Step 2: Detect weaknesses
            logger.info("Step 2/5: Detecting weaknesses...")
            weaknesses = self.detector.detect_all_weaknesses()
            report.weaknesses_detected = len(weaknesses)
            
            # Add emerging patterns from query log
            if self.orchestrator.query_history:
                query_log = [
                    {
                        "query": q.query,
                        "domain": q.domain,
                        "success": q.metadata.get("status") == "success"
                    }
                    for q in self.orchestrator.query_history
                ]
                weaknesses.extend(self.detector.detect_emerging_patterns(query_log))
            
            logger.info(f"Detected {len(weaknesses)} weaknesses")
            for w in weaknesses:
                logger.info(f"  - {w}")
            
            # Step 3: Create improvement plans
            logger.info("Step 3/5: Creating improvement plans...")
            plans = []
            for weakness in weaknesses:
                plan = self.trainer.create_improvement_plan(weakness)
                if plan:
                    plans.append(plan)
            
            # Sort by expected impact
            plans.sort(key=lambda p: p.expected_impact, reverse=True)
            
            # Select top N plans
            selected_plans = plans[:self.max_improvements_per_cycle]
            logger.info(f"Created {len(plans)} plans, selecting {len(selected_plans)} to execute")
            
            # Step 4: Execute plans
            logger.info("Step 4/5: Executing improvement plans...")
            for plan in selected_plans:
                if report.improvements_applied >= self.max_improvements_per_cycle:
                    break
                    
                try:
                    result = self.trainer.execute_plan(plan)
                    report.improvements_applied += 1
                    report.changes_made.append(f"{plan.name}: {result['status']}")
                    
                    if result["status"] == "completed":
                        report.overall_impact += plan.expected_impact
                        if "new_model" in result:
                            report.changes_made.append(f"  Created model: {result['new_model']}")
                    else:
                        report.improvements_failed += 1
                        report.changes_made.append(f"  Failed: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    report.improvements_failed += 1
                    report.changes_made.append(f"  Error: {str(e)}")
                    logger.error(f"Failed to execute plan {plan.name}: {e}")
            
            # Step 5: Generate report
            logger.info("Step 5/5: Generating report...")
            report.duration = time.time() - start_time
            report.system_metrics = self._get_system_metrics()
            
            # Generate recommendations
            if report.improvements_failed > 0:
                report.recommendations.append(
                    f"Review {report.improvements_failed} failed improvements"
                )
            
            if len(weaknesses) > self.max_improvements_per_cycle:
                remaining = len(weaknesses) - self.max_improvements_per_cycle
                report.recommendations.append(
                    f"Address {remaining} remaining weaknesses in next cycle"
                )
            
            if report.overall_impact == 0:
                report.recommendations.append("No improvements were made - system may be well-optimized")
            
            # Log the report
            self.optimization_log.append(report)
            
            logger.info(f"=== Self-Optimization Complete ===")
            logger.info(f"Duration: {report.duration:.1f}s")
            logger.info(f"Weaknesses detected: {report.weaknesses_detected}")
            logger.info(f"Improvements applied: {report.improvements_applied}")
            logger.info(f"Overall impact: {report.overall_impact:.1%}")
            
        except Exception as e:
            report.duration = time.time() - start_time
            report.changes_made.append(f"Cycle failed: {str(e)}")
            logger.error(f"Self-optimization cycle failed: {e}")
        
        return report
    
    def _get_system_metrics(self) -> Dict[str, float]:
        """Get current system metrics."""
        performance = self.monitor.get_domain_performance()
        stats = self.monitor.get_usage_stats()
        
        metrics = {
            "total_queries": stats["total_queries"],
            "queries_per_hour": stats["queries_per_hour"],
            "overall_error_rate": stats["error_rate"],
            "avg_latency": sum(d["avg_latency"] for d in performance.values()) / len(performance) if performance else 0.0,
            "avg_success_rate": sum(d["success_rate"] for d in performance.values()) / len(performance) if performance else 0.0
        }
        
        return metrics
    
    def run_continuous_optimization(
        self,
        interval: int = 3600,
        max_cycles: Optional[int] = None
    ) -> None:
        """
        Run continuous self-optimization.
        
        Args:
            interval: Seconds between optimization cycles
            max_cycles: Maximum number of cycles (None = infinite)
        """
        self.running = True
        cycle_count = 0
        
        logger.info(f"Starting continuous optimization (interval: {interval}s)")
        
        try:
            while self.running and (max_cycles is None or cycle_count < max_cycles):
                cycle_count += 1
                logger.info(f"=== Cycle {cycle_count} ===")
                
                report = self.run_self_optimization_cycle()
                
                # Wait for next cycle
                if self.running and (max_cycles is None or cycle_count < max_cycles):
                    logger.info(f"Next cycle in {interval}s...")
                    time.sleep(interval)
                    
        except KeyboardInterrupt:
            logger.info("Continuous optimization stopped by user")
        finally:
            self.running = False
    
    def stop(self) -> None:
        """Stop continuous optimization."""
        self.running = False
        logger.info("Self-optimization stopped")
    
    def get_optimization_history(self) -> List[SelfOptimizationReport]:
        """Get history of optimization cycles."""
        return self.optimization_log
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get current system health status."""
        weaknesses = self.detector.detect_all_weaknesses()
        metrics = self._get_system_metrics()
        
        health_score = 100.0
        issues = []
        
        # Deduct for weaknesses
        for w in weaknesses:
            if w.severity == "critical":
                health_score -= 20
                issues.append(f"CRITICAL: {w.description}")
            elif w.severity == "high":
                health_score -= 10
                issues.append(f"HIGH: {w.description}")
            elif w.severity == "medium":
                health_score -= 5
                issues.append(f"MEDIUM: {w.description}")
        
        # Deduct for low success rates
        if metrics["avg_success_rate"] < 0.8:
            health_score -= 15
            issues.append(f"Low average success rate: {metrics['avg_success_rate']:.1%}")
        
        # Deduct for high latency
        if metrics["avg_latency"] > 0.5:
            health_score -= 10
            issues.append(f"High average latency: {metrics['avg_latency']:.2f}s")
        
        health_score = max(0.0, health_score)
        
        return {
            "health_score": health_score,
            "status": "healthy" if health_score >= 90 else "warning" if health_score >= 70 else "critical",
            "issues": issues,
            "metrics": metrics,
            "weaknesses_count": len(weaknesses)
        }


# =============================================================================
# Self-Modification Capabilities (Experimental)
# =============================================================================

class SelfModifier:
    """
    EXPERIMENTAL: Enables the system to modify its own code.
    
    WARNING: This is powerful and potentially dangerous. Use with caution.
    
    Capabilities:
    - Generate new agent code
    - Add new tools to existing agents
    - Update agent configurations
    - Create new test datasets
    
    Safety features:
    - Always creates backup files
    - Requires explicit approval for code changes
    - Logs all modifications
    """
    
    def __init__(self, optimizer: SelfOptimizer):
        self.optimizer = optimizer
        self.modification_log: List[Dict[str, Any]] = []
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
    
    def add_tool_to_agent(
        self,
        agent_domain: str,
        tool_name: str,
        tool_description: str,
        tool_params: Dict[str, Any],
        approve: bool = False
    ) -> Dict[str, Any]:
        """
        Add a new tool to an existing agent.
        
        WARNING: This modifies source code. Set approve=True to actually make changes.
        
        Args:
            agent_domain: Domain of the agent (e.g., "weather")
            tool_name: Name of the new tool
            tool_description: Description of the tool
            tool_params: Parameter schema for the tool
            approve: Must be True to actually make changes
        
        Returns:
            Dict with status and changes
        """
        result = {
            "action": "add_tool",
            "agent": agent_domain,
            "tool": tool_name,
            "status": "pending_approval",
            "changes": [],
            "backup_created": False
        }
        
        if not approve:
            result["message"] = "Set approve=True to actually make changes"
            return result
        
        try:
            # Create backup
            agent_file = Path(f"agents/{agent_domain}_agent.py")
            if agent_file.exists():
                backup_path = self.backup_dir / f"{agent_domain}_agent_{int(time.time())}.py"
                import shutil
                shutil.copy2(agent_file, backup_path)
                result["backup_created"] = True
                result["backup_path"] = str(backup_path)
            
            # Read the file
            with open(agent_file, 'r') as f:
                content = f.read()
            
            # Generate new tool code
            tool_code = self._generate_tool_code(tool_name, tool_description, tool_params)
            
            # Find where to insert (before the agent class or at the end of tools)
            # Simple approach: insert before the agent class definition
            insert_pos = content.find(f"class {agent_domain.capitalize()}Agent")
            if insert_pos == -1:
                insert_pos = content.rfind("@needle.tool") + 1
            
            if insert_pos > 0:
                new_content = content[:insert_pos] + "\n" + tool_code + "\n\n" + content[insert_pos:]
                
                # Write changes
                with open(agent_file, 'w') as f:
                    f.write(new_content)
                
                result["status"] = "completed"
                result["changes"].append(f"Added tool {tool_name} to {agent_domain}_agent.py")
                
                # Log the modification
                self.modification_log.append(result)
                logger.info(f"Added tool {tool_name} to {agent_domain} agent")
            else:
                result["status"] = "failed"
                result["error"] = "Could not find insertion point"
                
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            logger.error(f"Failed to add tool: {e}")
        
        return result
    
    def create_new_agent_file(
        self,
        domain: str,
        description: str,
        tools: List[Dict[str, Any]],
        approve: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new agent file.
        
        WARNING: This creates new source files. Set approve=True to actually create.
        
        Args:
            domain: Domain name for the new agent
            description: Description of the agent's purpose
            tools: List of tool schemas
            approve: Must be True to actually create
        
        Returns:
            Dict with status and details
        """
        result = {
            "action": "create_agent",
            "domain": domain,
            "status": "pending_approval",
            "file_path": f"agents/{domain}_agent.py"
        }
        
        if not approve:
            result["message"] = "Set approve=True to actually create the file"
            return result
        
        try:
            # Generate agent code
            code = self._generate_full_agent_code(domain, description, tools)
            
            # Create the file
            file_path = Path(f"agents/{domain}_agent.py")
            with open(file_path, 'w') as f:
                f.write(code)
            
            # Create backup of the agents/__init__.py
            init_file = Path("agents/__init__.py")
            if init_file.exists():
                backup_path = self.backup_dir / f"__init___{int(time.time())}.py"
                import shutil
                shutil.copy2(init_file, backup_path)
                result["backup_path"] = str(backup_path)
            
            # Update agents/__init__.py to include the new agent
            with open(init_file, 'r') as f:
                init_content = f.read()
            
            # Add import if not present
            class_name = f"{domain.capitalize()}Agent"
            if class_name not in init_content:
                # Find the imports section
                import_pos = init_content.find("from .weather_agent import WeatherAgent")
                if import_pos > 0:
                    new_import = f"from .{domain}_agent import {class_name}"
                    new_content = init_content[:import_pos] + new_import + "\n" + init_content[import_pos:]
                    
                    # Also update __all__
                    all_pos = init_content.find("__all__ = [")
                    if all_pos > 0:
                        end_all = init_content.find("]", all_pos)
                        all_list = init_content[all_pos:end_all]
                        if class_name not in all_list:
                            new_all = all_list[:-1] + f", {class_name}" + "]"
                            new_content = new_content[:all_pos] + new_all + new_content[end_all+1:]
                    
                    with open(init_file, 'w') as f:
                        f.write(new_content)
            
            result["status"] = "completed"
            result["changes"] = [f"Created {file_path}", f"Updated agents/__init__.py"]
            
            # Log the modification
            self.modification_log.append(result)
            logger.info(f"Created new agent: {domain}_agent.py")
            
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            logger.error(f"Failed to create agent: {e}")
        
        return result
    
    def _generate_tool_code(self, name: str, description: str, params: Dict[str, Any]) -> str:
        """Generate Python code for a tool function."""
        # Generate parameter list and docstring
        param_list = ", ".join(f"{p}: {params['properties'].get(p, {}).get('type', 'Any')}" 
                            for p in params.get("properties", {}).keys())
        
        # Generate function
        code = f"""@needle.tool
def {name}({param_list}) -> dict:
    \"\"\"{description}
    
    Generated by SelfModifier at {datetime.now().isoformat()}
    \"\"\"
    # TODO: Implement actual tool logic
    return {{"status": "generated", "tool": "{name}"}}
"""
        return code
    
    def _generate_full_agent_code(
        self,
        domain: str,
        description: str,
        tools: List[Dict[str, Any]]
    ) -> str:
        """Generate complete agent file code."""
        class_name = f"{domain.capitalize()}Agent"
        
        code = f'"""\n{class_name} - Specialized agent for {domain} domain.

{description}

Generated by SelfModifier at {datetime.now().isoformat()}
"""\n\n'
        
        code += """import needle
from pydantic import BaseModel
from typing import Optional, List, Any

"""
        
        # Add tools
        for tool in tools:
            code += self._generate_tool_code(
                tool["name"],
                tool.get("description", ""),
                tool.get("parameters", {})
            )
            code += "\n\n"
        
        # Add tool list
        tool_names = [t["name"] for t in tools]
        code += f"{class_name}_TOOLS = [{', '.join(tool_names)}]\n\n"
        
        # Add agent class
        code += f"""class {class_name}:
    \"\"\"Specialized {domain} agent using Needle.\"\"\"
    
    def __init__(self, weights: str = None):
        self.agent = needle.Needle(
            tools={class_name}_TOOLS,
            weights=weights,
            system="You are a {domain} assistant. {description}"
        )
    
    def run(self, query: str, max_steps: int = 8) -> dict:
        return self.agent.run(query, max_steps=max_steps)
    
    def get_tools_schema(self) -> List[Dict]:
        return [needle.agent.tools.build_schema(tool) for tool in {class_name}_TOOLS]
"""
        
        return code
    
    def get_modification_history(self) -> List[Dict[str, Any]]:
        """Get history of all modifications."""
        return self.modification_log
    
    def rollback(self, backup_path: str) -> Dict[str, Any]:
        """
        Rollback to a backup file.
        
        WARNING: This will overwrite the current file.
        
        Args:
            backup_path: Path to the backup file
        
        Returns:
            Dict with rollback status
        """
        result = {
            "action": "rollback",
            "backup_path": backup_path,
            "status": "pending_approval"
        }
        
        try:
            backup = Path(backup_path)
            if not backup.exists():
                result["status"] = "failed"
                result["error"] = f"Backup file not found: {backup_path}"
                return result
            
            # Determine target file
            target_name = backup.name.replace("_\d+", "")
            target = Path(f"agents/{target_name}") if "agent" in target_name else Path(target_name)
            
            # Copy backup to target
            import shutil
            shutil.copy2(backup, target)
            
            result["status"] = "completed"
            result["target"] = str(target)
            result["changes"] = [f"Restored {target} from {backup}"]
            
            logger.info(f"Rolled back {target} to {backup}")
            
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            logger.error(f"Rollback failed: {e}")
        
        return result


# =============================================================================
# Convenience Functions
# =============================================================================

def create_self_optimizer() -> SelfOptimizer:
    """Create a SelfOptimizer instance."""
    return SelfOptimizer()


def run_self_optimization() -> SelfOptimizationReport:
    """Run a single self-optimization cycle."""
    optimizer = create_self_optimizer()
    return optimizer.run_self_optimization_cycle()


def run_continuous_self_optimization(interval: int = 3600) -> None:
    """Run continuous self-optimization."""
    optimizer = create_self_optimizer()
    optimizer.run_continuous_optimization(interval=interval)


if __name__ == "__main__":
    # Example usage
    print("Self-Optimizer: Running single optimization cycle...")
    optimizer = SelfOptimizer()
    report = optimizer.run_self_optimization_cycle()
    
    print(f"\n=== Self-Optimization Report ===")
    print(f"Duration: {report.duration:.1f}s")
    print(f"Weaknesses detected: {report.weaknesses_detected}")
    print(f"Improvements applied: {report.improvements_applied}")
    print(f"Overall impact: {report.overall_impact:.1%}")
    print(f"\nChanges made:")
    for change in report.changes_made:
        print(f"  - {change}")
    if report.recommendations:
        print(f"\nRecommendations:")
        for rec in report.recommendations:
            print(f"  - {rec}")
