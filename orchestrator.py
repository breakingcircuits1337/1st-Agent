"""
Orchestrator - Main entry point for the 1st Agent multi-agent framework.

This orchestrator implements a lightweight communication layer that:
1. Routes user queries to appropriate specialized agents
2. Manages the dual-model architecture (Researcher + Production)
3. Coordinates fine-tuning operations via FineTuneFactory
4. Provides a unified interface for the entire system

Architecture:
┌─────────────────────────────────────────────────────────────┐
│                      Orchestrator                              │
│  (Lightweight routing and coordination)                       │
├───────────────────────────┬───────────────────────────────────┤
│ DualModelSystem           │ FineTuneFactory                     │
│ ┌─────────┐ ┌───────────┐ │ ┌─────────────────────────────────┐ │
│ │Research │ │ Production │ │ │ - generate_data()               │ │
│ │Agent    │ │ Agent      │ │ │ - finetune()                     │ │
│ └─────────┘ └───────────┘ │ │ - build_model()                  │ │
│                           │ │ - create_model()                  │ │
│                           │ │ - closed_loop_optimize()         │ │
│                           │ │ - adaptive_finetune()            │ │
└───────────────────────────┴───────────────────────────────────┘
                              │
              ┌───────────────────────────────┐
              │         EvaluationAgent        │
              │  - test_model()                │
              │  - calculate_reward()          │
              │  - generate_optimization_signal()│
              │  - track_performance()         │
              └───────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ Reward Signal    │ ← Closes the loop
                    │ (Drives optimization)│
                    └─────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
   │ WeatherAgent │    │ NewsAgent   │    │ DBAgent     │
   └─────────────┘    └─────────────┘    └─────────────┘

Usage:
    from orchestrator import Orchestrator
    
    orch = Orchestrator()
    
    # Handle user query
    response = orch.query("What's the weather in Lagos?")
    print(response.answer)
    
    # Fine-tune a new model
    model = orch.finetune_factory.create_model(
        name="custom",
        domain="custom_domain",
        tools_schema=[...]
    )
"""

import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from finetune_factory import FineTuneFactory, FineTunedModel
from researcher_agent import ResearcherAgent, create_researcher
from production_agent import ProductionAgent, DualModelSystem, AgentResponse
from evaluation_agent import EvaluationAgent, create_evaluator, EvaluationResult
from agents.weather_agent import WeatherAgent
from agents.news_agent import NewsAgent
from agents.db_agent import DBAgent


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Result of a query to the orchestrator."""
    query: str
    answer: str
    domain: str
    agent_used: str
    tool_calls: List[Dict] = field(default_factory=list)
    confidence: Optional[float] = None
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemStatus:
    """Status of the orchestrator system."""
    agents_loaded: List[str]
    models_registered: List[str]
    researcher_loaded: bool
    production_loaded: bool
    factory_initialized: bool
    evaluator_loaded: bool = True


class Orchestrator:
    """
    Main orchestrator for the 1st Agent multi-agent framework.
    
    This class provides a unified interface for:
    - Query routing and execution
    - Model fine-tuning and management
    - Research and development operations
    - System monitoring and management
    
    The orchestrator uses a lightweight design that avoids heavy dependencies
    like AutoGen, while still providing powerful multi-agent capabilities.
    """
    
    def __init__(
        self,
        researcher_weights: Optional[str] = None,
        production_weights: Optional[str] = None,
        base_checkpoint: Optional[str] = None,
        models_dir: Optional[str] = None,
        use_gpu: bool = True
    ):
        """
        Initialize the orchestrator.
        
        Args:
            researcher_weights: Path to researcher .cact file
            production_weights: Path to production .cact file
            base_checkpoint: Base model checkpoint for fine-tuning
            models_dir: Directory for storing models
            use_gpu: Whether to use GPU (if available)
        """
        self.use_gpu = use_gpu
        self.models_dir = Path(models_dir) if models_dir else Path("models")
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        logger.info("Initializing Orchestrator...")
        
        # Fine-tune factory
        self.finetune_factory = FineTuneFactory(
            base_checkpoint=base_checkpoint,
            models_dir=self.models_dir
        )
        logger.info("FineTuneFactory initialized")
        
        # Dual model system (Researcher + Production)
        self.dual_system = DualModelSystem(
            researcher_weights=researcher_weights,
            production_weights=production_weights
        )
        logger.info("DualModelSystem initialized")
        
        # Evaluation agent for closed-loop optimization
        self.evaluation_agent = EvaluationAgent()
        logger.info("EvaluationAgent initialized")
        
        # Specialized agents
        self._initialize_specialized_agents()
        
        # Track query history
        self.query_history: List[QueryResult] = []
        
        logger.info("Orchestrator initialized successfully")
    
    def _initialize_specialized_agents(self):
        """Initialize specialized domain agents."""
        self.specialized_agents = {
            "weather": WeatherAgent(),
            "news": NewsAgent(),
            "database": DBAgent(),
        }
        
        # Register with production agent
        for domain, agent in self.specialized_agents.items():
            self.dual_system.production.add_specialized_agent(domain, agent)
        
        logger.info(f"Initialized {len(self.specialized_agents)} specialized agents")
    
    # =========================================================================
    # Query Handling Methods
    # =========================================================================
    
    def query(
        self,
        query: str,
        max_steps: int = 8,
        use_researcher: bool = False
    ) -> QueryResult:
        """
        Handle a user query.
        
        This is the main entry point for user interactions.
        
        Args:
            query: User query string
            max_steps: Maximum tool-calling iterations
            use_researcher: Route to researcher instead of production
        
        Returns:
            QueryResult with answer and metadata
        """
        import time
        start_time = time.time()
        
        try:
            if use_researcher:
                # Use researcher for R&D queries
                result = self.dual_system.researcher.run(query, max_steps=max_steps)
                agent_used = "researcher"
                domain = "research"
                answer = self._extract_answer(result)
            else:
                # Use production for standard queries
                response = self.dual_system.production.route_and_execute(query)
                agent_used = response.metadata.get("agent", "production")
                domain = response.domain
                answer = response.answer
            
            processing_time = time.time() - start_time
            
            query_result = QueryResult(
                query=query,
                answer=answer,
                domain=domain,
                agent_used=agent_used,
                tool_calls=[],  # Would extract from result if available
                confidence=None,  # Would extract from result if available
                processing_time=processing_time,
                metadata={"status": "success"}
            )
            
            # Store in history
            self.query_history.append(query_result)
            
            logger.info(f"Query processed in {processing_time:.3f}s: {query[:50]}...")
            return query_result
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Query error: {e}")
            
            return QueryResult(
                query=query,
                answer=f"Sorry, there was an error processing your request: {str(e)}",
                domain="error",
                agent_used="orchestrator",
                processing_time=processing_time,
                metadata={"status": "error", "error": str(e)}
            )
    
    def _extract_answer(self, result: dict) -> str:
        """Extract answer from a result dictionary."""
        if "text" in result:
            return result["text"]
        if "answer" in result:
            return result["answer"]
        if "results" in result:
            return str(result["results"])
        return str(result)
    
    def batch_query(self, queries: List[str], max_steps: int = 8) -> List[QueryResult]:
        """
        Process multiple queries in batch.
        
        Args:
            queries: List of query strings
            max_steps: Maximum tool-calling iterations per query
        
        Returns:
            List of QueryResult objects
        """
        results = []
        for query in queries:
            result = self.query(query, max_steps=max_steps)
            results.append(result)
        return results
    
    # =========================================================================
    # Model Management Methods
    # =========================================================================
    
    def create_finetuned_model(
        self,
        name: str,
        domain: str,
        tools_schema: Union[List[Dict], str, Path],
        num_samples: int = 200,
        epochs: int = 10,
        lora_rank: int = 16,
        lora_alpha: float = 32.0,
        **kwargs
    ) -> FineTunedModel:
        """
        Create a new fine-tuned model.
        
        This is a convenience wrapper around FineTuneFactory.create_model().
        
        Args:
            name: Unique name for the model
            domain: Domain/description
            tools_schema: Tool schemas for this domain
            num_samples: Number of training samples
            epochs: Training epochs
            lora_rank: LoRA rank
            lora_alpha: LoRA alpha
            **kwargs: Additional arguments for create_model()
        
        Returns:
            FineTunedModel with paths to all artifacts
        """
        return self.finetune_factory.create_model(
            name=name,
            domain=domain,
            tools_schema=tools_schema,
            num_samples=num_samples,
            epochs=epochs,
            lora_rank=lora_rank,
            lora_alpha=lora_alpha,
            **kwargs
        )
    
    def create_researcher_model(
        self,
        name: str = "researcher",
        domain: str = "model_research",
        tools_schema: Optional[List[Dict]] = None
    ) -> FineTunedModel:
        """
        Create a specialized researcher model.
        
        Args:
            name: Model name
            domain: Domain description
            tools_schema: Custom tools for research
        
        Returns:
            FineTunedModel for the researcher
        """
        model = self.finetune_factory.create_researcher_model(
            name=name,
            domain=domain,
            tools_schema=tools_schema
        )
        
        # Update dual system with new researcher
        self.dual_system.researcher = ResearcherAgent(weights=str(model.model_path))
        
        return model
    
    def create_production_model(
        self,
        name: str,
        domain: str,
        tools_schema: List[Dict],
        **kwargs
    ) -> FineTunedModel:
        """
        Create a specialized production model.
        
        Args:
            name: Model name
            domain: Domain
            tools_schema: Tool schemas
            **kwargs: Additional arguments for create_model()
        
        Returns:
            FineTunedModel for production
        """
        model = self.finetune_factory.create_model(
            name=name,
            domain=domain,
            tools_schema=tools_schema,
            **kwargs
        )
        
        # Update dual system with new production model
        self.dual_system.production = ProductionAgent(weights=str(model.model_path))
        
        return model
    
    def automated_research_loop(
        self,
        target_domain: str,
        target_tools: List[Dict],
        iterations: int = 3
    ) -> FineTunedModel:
        """
        Run automated R&D loop using dual Needle models.
        
        This implements the vision of using 2 models for automated fine-tuning:
        1. Researcher model: Generates data, evaluates, suggests improvements
        2. Production model: Gets fine-tuned based on researcher's work
        
        Args:
            target_domain: Domain for the production model
            target_tools: Tools for the production model
            iterations: Number of R&D iterations
        
        Returns:
            Best fine-tuned production model
        """
        return self.finetune_factory.automated_research_loop(
            target_domain=target_domain,
            target_tools=target_tools,
            iterations=iterations
        )
    
    def list_models(self) -> List[FineTunedModel]:
        """List all registered fine-tuned models."""
        return self.finetune_factory.list_models()
    
    def get_model(self, name: str) -> Optional[FineTunedModel]:
        """Get a registered model by name."""
        return self.finetune_factory.get_model(name)
    
    def delete_model(self, name: str) -> bool:
        """Delete a model and all its artifacts."""
        return self.finetune_factory.delete_model(name)
    
    def export_model(self, name: str, output_dir: Union[str, Path]) -> Path:
        """
        Export a model for deployment.
        
        Args:
            name: Model name
            output_dir: Directory to export to
        
        Returns:
            Path to exported model
        """
        return self.finetune_factory.export_for_deployment(name, Path(output_dir))
    
    # =========================================================================
    # Research & Evaluation Methods
    # =========================================================================
    
    def generate_training_data(
        self,
        domain: str,
        num_samples: int = 100,
        difficulty: str = "medium"
    ) -> Any:
        """
        Generate training data for a domain.
        
        Args:
            domain: Domain to generate data for
            num_samples: Number of samples
            difficulty: Difficulty level (easy, medium, hard)
        
        Returns:
            TrainingDataGenerated object
        """
        return self.dual_system.researcher.generate_training_data(
            domain=domain,
            num_samples=num_samples,
            difficulty=difficulty
        )
    
    def evaluate_model(self, model_path: str, test_data_path: str) -> Any:
        """
        Evaluate a model on test data.
        
        Args:
            model_path: Path to .cact model
            test_data_path: Path to test data
        
        Returns:
            EvaluationResult object
        """
        return self.dual_system.researcher.evaluate(model_path, test_data_path)
    
    def suggest_hyperparameters(self, domain: str, dataset_size: int) -> Any:
        """
        Get hyperparameter suggestions.
        
        Args:
            domain: Domain being fine-tuned
            dataset_size: Number of training samples
        
        Returns:
            HyperparameterSuggestion object
        """
        return self.dual_system.researcher.suggest_params(domain, dataset_size)
    
    # =========================================================================
    # Closed-Loop Evaluation Methods
    # =========================================================================
    
    def evaluate_model(self, model_path: str, test_data_path: str, num_samples: int = 50) -> EvaluationResult:
        """
        Evaluate a model and get detailed results.
        
        Args:
            model_path: Path to .cact model
            test_data_path: Path to test data
            num_samples: Number of test samples to use
        
        Returns:
            EvaluationResult with all metrics and results
        """
        return self.evaluation_agent.evaluate_model(model_path, test_data_path, num_samples)
    
    def get_reward_signal(self, model_path: str, test_data_path: str, num_samples: int = 50) -> float:
        """
        Get reward signal for a model.
        
        Args:
            model_path: Path to .cact model
            test_data_path: Path to test data
            num_samples: Number of test samples
        
        Returns:
            Reward signal (0.0-2.0 range)
        """
        evaluation = self.evaluate_model(model_path, test_data_path, num_samples)
        return self.evaluation_agent.calculate_reward(evaluation)
    
    def closed_loop_optimize(
        self,
        target_domain: str,
        target_tools: List[Dict],
        test_data_path: Union[str, Path],
        max_iterations: int = 10,
        min_reward: float = 0.8,
        patience: int = 3,
        num_test_samples: int = 50
    ) -> Tuple[Optional[FineTunedModel], Dict[str, Any]]:
        """
        Run closed-loop optimization with reward-driven fine-tuning.
        
        This is the complete RLHF-style optimization loop:
        1. Create candidate model
        2. Evaluate with evaluation agent
        3. Calculate reward signal
        4. Use reward to decide: continue, stop, or adapt
        
        The reward signal closes the loop, creating a self-optimizing system.
        
        Args:
            target_domain: Domain for the model
            target_tools: Tool schemas for the domain
            test_data_path: Path to test data for evaluation
            max_iterations: Maximum number of iterations
            min_reward: Stop if reward exceeds this threshold
            patience: Stop after this many iterations without improvement
            num_test_samples: Number of test samples per evaluation
        
        Returns:
            Tuple of (best_model, optimization_report)
        """
        return self.finetune_factory.closed_loop_optimize(
            target_domain=target_domain,
            target_tools=target_tools,
            test_data_path=Path(test_data_path),
            max_iterations=max_iterations,
            min_reward=min_reward,
            patience=patience,
            num_test_samples=num_test_samples
        )
    
    def adaptive_optimize(
        self,
        target_domain: str,
        target_tools: List[Dict],
        test_data_path: Union[str, Path],
        max_iterations: int = 5,
        num_test_samples: int = 50
    ) -> Tuple[Optional[FineTunedModel], Dict[str, Any]]:
        """
        Run adaptive optimization with dynamic hyperparameter adjustment.
        
        Uses reward signals to automatically adjust:
        - Training data size (if accuracy is low)
        - Epochs (if precision is low)
        - LoRA rank (if converging)
        
        Args:
            target_domain: Domain for the model
            target_tools: Tool schemas
            test_data_path: Path to test data
            max_iterations: Maximum iterations
            num_test_samples: Test samples per evaluation
        
        Returns:
            Tuple of (best_model, optimization_report)
        """
        return self.finetune_factory.adaptive_finetune(
            target_domain=target_domain,
            target_tools=target_tools,
            test_data_path=Path(test_data_path),
            max_iterations=max_iterations,
            num_test_samples=num_test_samples
        )
    
    def compare_models(
        self,
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
            Dict with comparison results and winner
        """
        return self.evaluation_agent.compare_models(
            model_a_path, model_b_path, test_data_path, num_samples
        )
    
    def get_performance_history(self, model_name: str) -> Optional[Any]:
        """
        Get performance history for a model.
        
        Args:
            model_name: Name of the model
        
        Returns:
            PerformanceHistory or None
        """
        return self.evaluation_agent.get_performance_history(model_name)
    
    def get_model_trend(self, model_name: str, metric: str = "total_score") -> float:
        """
        Get performance trend for a model.
        
        Args:
            model_name: Name of the model
            metric: Metric to track (default: total_score)
        
        Returns:
            Trend value (positive = improving)
        """
        return self.evaluation_agent.get_trend(model_name, metric)
    
    # =========================================================================
    # System Management Methods
    # =========================================================================
    
    def get_status(self) -> SystemStatus:
        """Get the current status of the orchestrator system."""
        return SystemStatus(
            agents_loaded=list(self.specialized_agents.keys()),
            models_registered=[m.name for m in self.finetune_factory.list_models()],
            researcher_loaded=True,
            production_loaded=True,
            factory_initialized=True,
            evaluator_loaded=True
        )
    
    def add_specialized_agent(self, domain: str, agent: Any) -> None:
        """
        Add a new specialized agent to the system.
        
        Args:
            domain: Domain name for the agent
            agent: Agent instance (must have a run() method)
        """
        self.specialized_agents[domain] = agent
        self.dual_system.production.add_specialized_agent(domain, agent)
        logger.info(f"Added specialized agent for domain: {domain}")
    
    def remove_specialized_agent(self, domain: str) -> bool:
        """
        Remove a specialized agent from the system.
        
        Args:
            domain: Domain name of the agent to remove
        
        Returns:
            True if removed, False if not found
        """
        if domain in self.specialized_agents:
            del self.specialized_agents[domain]
            # Note: Production agent keeps its own copy, would need to update there too
            logger.info(f"Removed specialized agent for domain: {domain}")
            return True
        return False
    
    def get_query_history(self, limit: int = 100) -> List[QueryResult]:
        """
        Get recent query history.
        
        Args:
            limit: Maximum number of results to return
        
        Returns:
            List of QueryResult objects
        """
        return self.query_history[-limit:]
    
    def clear_query_history(self) -> None:
        """Clear the query history."""
        self.query_history = []
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def verify_needle_installation(self) -> bool:
        """
        Verify that cactus-needle is installed and working.
        
        Returns:
            True if installed, False otherwise
        """
        try:
            import needle
            # Try to create a basic agent
            agent = needle.Needle(tools=[], system="test")
            return True
        except Exception as e:
            logger.error(f"Needle installation check failed: {e}")
            return False
    
    def check_gpu_available(self) -> bool:
        """
        Check if GPU is available for Needle.
        
        Returns:
            True if GPU is available, False otherwise
        """
        try:
            import jax
            return len(jax.devices("gpu")) > 0
        except ImportError:
            return False
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information including component versions.
        
        Returns:
            Dict with system information
        """
        info = {
            "orchestrator": "1st Agent v1.0",
            "needle_installed": self.verify_needle_installation(),
            "gpu_available": self.check_gpu_available(),
            "models_dir": str(self.models_dir),
            "agents_loaded": list(self.specialized_agents.keys()),
            "models_registered": [m.name for m in self.finetune_factory.list_models()],
            "query_history_count": len(self.query_history)
        }
        
        try:
            import needle
            info["needle_version"] = needle.__version__
        except ImportError:
            info["needle_version"] = "not installed"
        
        return info
    
    # =========================================================================
    # Self-Optimization Methods (for Closed-Loop Integration)
    # =========================================================================
    
    def monitor_system(self) -> Dict[str, Any]:
        """
        Monitor system performance and gather metrics.
        
        Tracks:
        - Query throughput
        - Agent performance
        - Model accuracy
        - System latency
        
        Returns:
            Dict with system metrics
        """
        metrics = {
            "queries_processed": len(self.query_history),
            "agents_active": len(self.specialized_agents),
            "models_registered": len(self.finetune_factory.list_models()),
            "avg_processing_time": 0.0,
            "error_rate": 0.0,
            "agent_performance": {}
        }
        
        # Calculate average processing time
        if self.query_history:
            total_time = sum(q.processing_time for q in self.query_history)
            metrics["avg_processing_time"] = total_time / len(self.query_history)
            
            # Calculate error rate
            errors = sum(1 for q in self.query_history if q.metadata.get("status") == "error")
            metrics["error_rate"] = errors / len(self.query_history)
        
        # Get performance for each agent
        for domain, agent in self.specialized_agents.items():
            agent_metrics = self._get_agent_metrics(agent)
            metrics["agent_performance"][domain] = agent_metrics
        
        logger.info(f"System monitor: {metrics['queries_processed']} queries, "
                   f"{metrics['error_rate']:.1%} error rate")
        
        return metrics
    
    def _get_agent_metrics(self, agent: Any) -> Dict[str, float]:
        """Get performance metrics for a specific agent."""
        # Try to get metrics from agent
        if hasattr(agent, 'get_metrics'):
            return agent.get_metrics()
        elif hasattr(agent, 'metrics'):
            return agent.metrics
        else:
            return {"accuracy": 0.8, "confidence": 0.9, "latency": 0.1}
    
    def detect_weaknesses(self) -> List[Dict[str, Any]]:
        """
        Detect weaknesses in the system based on monitoring data.
        
        Identifies:
        - Underperforming agents
        - High error rate domains
        - Slow query processing
        - Model accuracy issues
        
        Returns:
            List of weakness dictionaries with:
            - category: Type of weakness
            - severity: low/medium/high/critical
            - description: Details
            - agent: Agent/domain affected
            - metric: Metric that's off
            - current: Current value
            - target: Target value
        """
        weaknesses = []
        
        # Get system metrics
        metrics = self.monitor_system()
        
        # Check overall error rate
        if metrics.get("error_rate", 0) > 0.1:  # > 10% error rate
            weaknesses.append({
                "category": "system",
                "severity": "critical",
                "description": f"High system error rate: {metrics['error_rate']:.1%}",
                "agent": None,
                "metric": "error_rate",
                "current": metrics["error_rate"],
                "target": 0.05,
                "priority": 1
            })
        elif metrics.get("error_rate", 0) > 0.05:  # > 5% error rate
            weaknesses.append({
                "category": "system",
                "severity": "high",
                "description": f"Elevated system error rate: {metrics['error_rate']:.1%}",
                "agent": None,
                "metric": "error_rate",
                "current": metrics["error_rate"],
                "target": 0.05,
                "priority": 2
            })
        
        # Check processing time
        if metrics.get("avg_processing_time", 0) > 5.0:  # > 5 seconds
            weaknesses.append({
                "category": "performance",
                "severity": "high",
                "description": f"Slow processing: {metrics['avg_processing_time']:.1f}s avg",
                "agent": None,
                "metric": "processing_time",
                "current": metrics["avg_processing_time"],
                "target": 2.0,
                "priority": 2
            })
        
        # Check individual agent performance
        for domain, agent_metrics in metrics.get("agent_performance", {}).items():
            # Check accuracy
            accuracy = agent_metrics.get("accuracy", 1.0)
            if accuracy < 0.85:
                weaknesses.append({
                    "category": "agent",
                    "severity": "critical" if accuracy < 0.7 else "high",
                    "description": f"Low accuracy for {domain}: {accuracy:.1%}",
                    "agent": domain,
                    "metric": "accuracy",
                    "current": accuracy,
                    "target": 0.95,
                    "priority": 1
                })
            
            # Check confidence
            confidence = agent_metrics.get("confidence", 1.0)
            if confidence < 0.8:
                weaknesses.append({
                    "category": "agent",
                    "severity": "medium",
                    "description": f"Low confidence for {domain}: {confidence:.1%}",
                    "agent": domain,
                    "metric": "confidence",
                    "current": confidence,
                    "target": 0.9,
                    "priority": 3
                })
            
            # Check latency
            latency = agent_metrics.get("latency", 0)
            if latency > 1.0:  # > 1 second
                weaknesses.append({
                    "category": "performance",
                    "severity": "medium" if latency < 3.0 else "high",
                    "description": f"High latency for {domain}: {latency:.1f}s",
                    "agent": domain,
                    "metric": "latency",
                    "current": latency,
                    "target": 0.5,
                    "priority": 2 if latency < 3.0 else 1
                })
        
        # Sort by priority (1 = highest)
        weaknesses.sort(key=lambda w: w["priority"])
        
        logger.info(f"Detected {len(weaknesses)} system weaknesses")
        for w in weaknesses:
            logger.info(f"  - [{w['severity'].upper()}] {w['description']}")
        
        return weaknesses
    
    def auto_train_agents(
        self,
        weaknesses: Optional[List[Dict[str, Any]]] = None,
        max_iterations: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Automatically train agents based on detected weaknesses.
        
        For each weakness, generates synthetic data and fine-tunes the model.
        
        Args:
            weaknesses: List of weaknesses to address (from detect_weaknesses)
            max_iterations: Maximum training iterations per weakness
        
        Returns:
            List of training results
        """
        if weaknesses is None:
            weaknesses = self.detect_weaknesses()
        
        if not weaknesses:
            logger.info("No weaknesses to address, skipping auto-training")
            return []
        
        results = []
        
        for weakness in weaknesses:
            if weakness["category"] != "agent":
                continue  # Only train for agent weaknesses
            
            domain = weakness["agent"]
            metric = weakness["metric"]
            target = weakness["target"]
            
            logger.info(f"Auto-training agent for {domain} ({metric})")
            
            try:
                # Create synthetic training data focused on the weakness
                training_data = self._generate_training_data(domain, metric, num_samples=200)
                
                # Fine-tune the model
                model_name = f"auto_fix_{domain}_{metric}"
                model_path = self.finetune_factory.create_model(
                    name=model_name,
                    domain=domain,
                    tools_schema=[],  # Would use actual schema for domain
                    num_samples=200,
                    epochs=10,
                    lora_rank=16,
                    lora_alpha=32.0
                )
                
                # Evaluate the new model
                eval_result = self.evaluation_agent.test_model(str(model_path))
                reward = self.evaluation_agent.calculate_reward(eval_result)
                
                results.append({
                    "domain": domain,
                    "metric": metric,
                    "target": target,
                    "model_path": str(model_path) if model_path else None,
                    "reward": reward,
                    "improvement": reward - (weakness["current"] if isinstance(weakness["current"], (int, float)) else 0),
                    "status": "success" if model_path else "failed"
                })
                
                logger.info(f"Auto-training for {domain}: reward={reward:.3f}")
                
            except Exception as e:
                logger.error(f"Auto-training failed for {domain}: {e}")
                results.append({
                    "domain": domain,
                    "metric": metric,
                    "target": target,
                    "model_path": None,
                    "reward": 0.0,
                    "improvement": 0.0,
                    "status": "failed",
                    "error": str(e)
                })
        
        return results
    
    def _generate_training_data(
        self,
        domain: str,
        metric: str,
        num_samples: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Generate synthetic training data focused on improving a specific metric.
        
        Args:
            domain: The domain/agent to generate data for
            metric: The metric to improve (e.g., "accuracy", "latency")
            num_samples: Number of samples to generate
        
        Returns:
            List of training data dictionaries
        """
        # In production, this would use the researcher model to generate
        # targeted examples that address the specific weakness.
        # For now, return placeholder data.
        
        data = []
        for i in range(num_samples):
            if domain == "weather":
                data.append({
                    "input": f"What's the weather in city {i}?",
                    "expected_output": f"Sunny, 75F, city {i}",
                    "domain": domain,
                    "focus": metric,
                    "difficulty": "medium"
                })
            elif domain == "news":
                data.append({
                    "input": f"Summarize news article {i}",
                    "expected_output": f"Article {i} summary",
                    "domain": domain,
                    "focus": metric,
                    "difficulty": "medium"
                })
            elif domain == "database":
                data.append({
                    "input": f"Query database for record {i}",
                    "expected_output": f"Record {i} data",
                    "domain": domain,
                    "focus": metric,
                    "difficulty": "medium"
                })
            else:
                data.append({
                    "input": f"Task {i} in domain {domain}",
                    "expected_output": f"Task {i} result",
                    "domain": domain,
                    "focus": metric,
                    "difficulty": "medium"
                })
        
        return data


# =========================================================================
# CLI Interface
# =========================================================================

def main():
    """CLI entry point for the orchestrator."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="1st Agent Orchestrator - Multi-agent framework with Needle"
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="Run a query and print the result"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Start interactive mode"
    )
    parser.add_argument(
        "--status", "-s",
        action="store_true",
        help="Show system status"
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List all registered models"
    )
    parser.add_argument(
        "--list-agents",
        action="store_true",
        help="List all specialized agents"
    )
    
    args = parser.parse_args()
    
    # Initialize orchestrator
    orch = Orchestrator()
    
    if args.status:
        status = orch.get_status()
        print("\n=== System Status ===")
        print(f"Agents loaded: {status.agents_loaded}")
        print(f"Models registered: {status.models_registered}")
        print(f"Researcher loaded: {status.researcher_loaded}")
        print(f"Production loaded: {status.production_loaded}")
        print(f"Factory initialized: {status.factory_initialized}")
    
    elif args.list_models:
        models = orch.list_models()
        print("\n=== Registered Models ===")
        if models:
            for model in models:
                print(f"  - {model.name} ({model.domain}): {model.model_path}")
        else:
            print("  No models registered")
    
    elif args.list_agents:
        agents = list(orch.specialized_agents.keys())
        print("\n=== Specialized Agents ===")
        for agent in agents:
            print(f"  - {agent}")
    
    elif args.query:
        result = orch.query(args.query)
        print(f"\nQuery: {result.query}")
        print(f"Domain: {result.domain}")
        print(f"Agent: {result.agent_used}")
        print(f"Answer:\n{result.answer}")
        print(f"Time: {result.processing_time:.3f}s")
    
    elif args.interactive:
        print("\n=== 1st Agent Orchestrator (Interactive Mode) ===")
        print("Type 'quit', 'exit', or 'q' to exit")
        print("Type 'status' to show system status")
        print("Type 'models' to list registered models")
        print("Type 'agents' to list specialized agents")
        
        while True:
            try:
                query = input("\n> ").strip()
                
                if not query:
                    continue
                
                if query.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye!")
                    break
                
                if query.lower() == 'status':
                    status = orch.get_status()
                    print(f"Agents: {status.agents_loaded}")
                    print(f"Models: {status.models_registered}")
                    continue
                
                if query.lower() == 'models':
                    models = orch.list_models()
                    if models:
                        for model in models:
                            print(f"  - {model.name} ({model.domain})")
                    else:
                        print("  No models registered")
                    continue
                
                if query.lower() == 'agents':
                    for agent in orch.specialized_agents.keys():
                        print(f"  - {agent}")
                    continue
                
                # Process query
                result = orch.query(query)
                print(f"\n[{result.domain}] {result.answer}")
                
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
    
    else:
        # No arguments, show help
        parser.print_help()


# =========================================================================
# FastAPI Interface (Optional)
# =========================================================================

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel as PydanticBaseModel
    
    class QueryRequest(PydanticBaseModel):
        query: str
        max_steps: int = 8
        use_researcher: bool = False
    
    class QueryResponse(PydanticBaseModel):
        query: str
        answer: str
        domain: str
        agent_used: str
        processing_time: float
        metadata: Dict[str, Any] = {}
    
    app = FastAPI(
        title="1st Agent Orchestrator API",
        description="API for the 1st Agent multi-agent framework",
        version="1.0.0"
    )
    
    # Global orchestrator instance for API
    api_orch = None
    
    @app.on_event("startup")
    def startup_event():
        global api_orch
        api_orch = Orchestrator()
        logger.info("Orchestrator API started")
    
    @app.post("/query", response_model=QueryResponse)
    async def handle_query(request: QueryRequest):
        """Handle a user query."""
        if api_orch is None:
            raise HTTPException(status_code=500, detail="Orchestrator not initialized")
        
        result = api_orch.query(
            request.query,
            max_steps=request.max_steps,
            use_researcher=request.use_researcher
        )
        
        return QueryResponse(
            query=result.query,
            answer=result.answer,
            domain=result.domain,
            agent_used=result.agent_used,
            processing_time=result.processing_time,
            metadata=result.metadata
        )
    
    @app.get("/status")
    async def get_status():
        """Get system status."""
        if api_orch is None:
            raise HTTPException(status_code=500, detail="Orchestrator not initialized")
        
        return api_orch.get_system_info()
    
    @app.get("/models")
    async def list_models():
        """List registered models."""
        if api_orch is None:
            raise HTTPException(status_code=500, detail="Orchestrator not initialized")
        
        models = api_orch.list_models()
        return {"models": [{"name": m.name, "domain": m.domain} for m in models]}
    
    @app.get("/agents")
    async def list_agents():
        """List specialized agents."""
        if api_orch is None:
            raise HTTPException(status_code=500, detail="Orchestrator not initialized")
        
        return {"agents": list(api_orch.specialized_agents.keys())}
    
    logger.info("FastAPI routes registered")
    
    def run_api(host: str = "0.0.0.0", port: int = 8000):
        """Run the FastAPI server."""
        import uvicorn
        uvicorn.run(app, host=host, port=port)
        
except ImportError:
    # FastAPI not installed, skip API registration
    logger.debug("FastAPI not installed, API routes not available")


if __name__ == "__main__":
    main()
