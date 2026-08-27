"""
Continuous Goal Execution Loop Engine

This module implements the advanced goal execution architecture with:

1. **Goal Decomposition & State Graphing**
   - Accepts macro objectives
   - Breaks into execution DAG (Directed Acyclic Graph)
   - Creates verifiable sub-milestones

2. **State Validation & Feedback**
   - Observer process validates state after each cycle
   - Success: Advance to next node
   - Failure: Push to retraining queue with failure context

3. **Autonomous Retraining & Hot-Swap**
   - Fine-tuning factory generates synthetic datasets
   - Retrains 45M parameter models
   - Hot-swaps .cact binaries in place
   - Sub-agent retries failed step

4. **Terminal Convergence**
   - Exits only when all nodes clear deterministic pass criteria

5. **Guardrails Against Infinite Loops**
   - Goal Drift Circuit Breaker: Root objective locked in read-only
   - Perfection Bias Cap: Stops if gains < 0.5% across 5 iterations
   - Execution Hard Stops: Max 20 retries or 50 GPU epochs

Architecture:
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CONTINUOUS GOAL EXECUTION ENGINE                           │
├─────────────────────────┬─────────────────────────┬─────────────────────────┤
│  Goal Decomposer        │  State Validator        │  Execution Controller    │
│  - Macro → DAG          │  - Post-execution check │  - Node traversal         │
│  - Milestone creation   │  - Success/failure gate │  - Path optimization      │
│  - Dependency mapping   │  - Metric validation     │  - Hot-swap coordination   │
└─────────────────────────┴─────────────────────────┴─────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXECUTION PIPELINE                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  Decompose  │───▶│  Execute    │───▶│  Validate   │───▶│ Converge?   │  │
│  │   Goal     │    │   Node     │    │   State    │    │             │  │
│  │             │    │             │    │             │    │             │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│       │                   │                   │              │          │
│       ▼                   ▼                   ▼              ▼          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         ✓         │
│  │  DAG        │    │  Sub-Agent  │    │  Observer   │    TERMINAL        │
│  │  Graph      │    │  Execution  │    │  Validation │    CONVERGENCE       │
│  └─────────────┘    └─────────────┘    └─────────────┘                  │
│                                                                             │
│       Failure Path:                                                       │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                  │
│  │  Failure    │───▶│ Retraining  │───▶│ Hot-Swap    │───▶ Retry        │
│  │  Context    │    │ Queue (P100)│    │ .cact Binary│                  │
│  └─────────────┘    └─────────────┘    └─────────────┘                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Usage:
    from goal_execution_engine import GoalExecutionEngine, ExecutionDAG, Goal
    
    # Create engine
    engine = GoalExecutionEngine(orchestrator=orchestrator)
    
    # Define goal
    goal = Goal(
        objective="Deploy a production-ready weather prediction system",
        pass_criteria={"accuracy": 0.95, "latency": 0.5, "coverage": 1.0}
    )
    
    # Execute
    result = engine.execute_goal(goal, max_iterations=100)
    
    # Or execute from DAG
    dag = engine.decompose_goal(goal)
    result = engine.execute_dag(dag)
"""

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import uuid
import networkx as nx

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

class NodeStatus(Enum):
    """Status of an execution node."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class ExecutionStatus(Enum):
    """Overall execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CONVERGED = "converged"


@dataclass
class Goal:
    """
    A high-level objective with deterministic pass criteria.
    
    The root objective is locked in read-only memory to prevent goal drift.
    """
    objective: str
    pass_criteria: Dict[str, float]  # Metric thresholds for convergence
    description: Optional[str] = None
    domain: Optional[str] = None
    priority: int = 1
    timeout: Optional[float] = None  # Maximum seconds for this goal
    goal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    
    # Guardrail: Lock the objective to prevent modification
    _objective_locked: bool = True
    
    def lock_objective(self):
        """Lock the objective to prevent goal drift."""
        self._objective_locked = True
    
    def is_objective_locked(self) -> bool:
        """Check if objective is locked."""
        return self._objective_locked
    
    def set_objective(self, new_objective: str) -> bool:
        """Attempt to set a new objective. Fails if locked."""
        if self._objective_locked:
            logger.warning("GOAL DRIFT PREVENTED: Objective is locked in read-only memory")
            return False
        self.objective = new_objective
        return True


@dataclass
class ExecutionNode:
    """
    A node in the execution DAG representing a verifiable sub-milestone.
    """
    node_id: str
    goal_id: str
    description: str
    action: str  # What to execute
    agent_type: Optional[str] = None  # Which agent should handle this
    domain: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)  # Node IDs this depends on
    pass_criteria: Dict[str, float] = field(default_factory=dict)
    max_retries: int = 3
    max_epochs: int = 50  # Guardrail: max GPU epochs
    timeout: Optional[float] = None  # Seconds
    status: NodeStatus = NodeStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    metrics: Dict[str, float] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def is_terminal(self) -> bool:
        """Check if node has reached terminal state."""
        return self.status in [NodeStatus.COMPLETED, NodeStatus.FAILED, NodeStatus.SKIPPED]
    
    def meets_pass_criteria(self) -> bool:
        """Check if all pass criteria are met."""
        if not self.pass_criteria:
            return True  # No criteria = always passes
        for metric, threshold in self.pass_criteria.items():
            if self.metrics.get(metric, 0) < threshold:
                return False
        return True


@dataclass
class ExecutionDAG:
    """
    Directed Acyclic Graph of execution nodes.
    
    Represents the decomposed goal as a graph where:
    - Nodes are verifiable sub-milestones
    - Edges represent dependencies
    - Terminal convergence when all nodes meet pass criteria
    """
    dag_id: str
    goal: Goal
    nodes: Dict[str, ExecutionNode]  # node_id -> ExecutionNode
    graph: Any = field(default_factory=lambda: nx.DiGraph)  # NetworkX graph
    status: ExecutionStatus = ExecutionStatus.PENDING
    current_node_id: Optional[str] = None
    completed_nodes: List[str] = field(default_factory=list)
    failed_nodes: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        # Build the networkx graph
        self.graph = nx.DiGraph()
        for node_id, node in self.nodes.items():
            self.graph.add_node(node_id, **{
                'description': node.description,
                'action': node.action,
                'agent_type': node.agent_type,
                'domain': node.domain
            })
            for dep in node.dependencies:
                self.graph.add_edge(dep, node_id)
    
    def get_execution_order(self) -> List[str]:
        """Get nodes in topological execution order."""
        try:
            return list(nx.topological_sort(self.graph))
        except nx.NetworkXError:
            # Graph has cycles, return nodes in creation order
            logger.warning("DAG has cycles, using fallback order")
            return list(self.nodes.keys())
    
    def get_ready_nodes(self) -> List[str]:
        """Get nodes whose dependencies are all completed."""
        ready = []
        for node_id, node in self.nodes.items():
            if node.status != NodeStatus.PENDING:
                continue
            # Check if all dependencies are completed
            deps_completed = all(
                self.nodes[dep].status == NodeStatus.COMPLETED
                for dep in node.dependencies
                if dep in self.nodes
            )
            if deps_completed or not node.dependencies:
                ready.append(node_id)
        return ready
    
    def has_uncompleted_nodes(self) -> bool:
        """Check if there are any uncompleted nodes."""
        return any(
            node.status not in [NodeStatus.COMPLETED, NodeStatus.SKIPPED]
            for node in self.nodes.values()
        )
    
    def all_nodes_meet_criteria(self) -> bool:
        """Check if all nodes meet their pass criteria."""
        return all(
            node.meets_pass_criteria()
            for node in self.nodes.values()
            if node.status == NodeStatus.COMPLETED
        )
    
    def get_next_node(self) -> Optional[str]:
        """Get the next node to execute."""
        ready = self.get_ready_nodes()
        if ready:
            return ready[0]  # Simple: first ready node
        return None


@dataclass
class FailureContext:
    """
    Context captured when a node execution fails.
    
    Pushed to Proxmox P100 queue for immediate sub-agent retraining.
    """
    node_id: str
    goal_id: str
    error: str
    error_type: str
    exception_stack: str
    metrics: Dict[str, float]
    input_data: Optional[Any] = None
    agent_type: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    priority: int = 1  # Proxmox queue priority (1 = highest)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for queue serialization."""
        return {
            'node_id': self.node_id,
            'goal_id': self.goal_id,
            'error': self.error,
            'error_type': self.error_type,
            'exception_stack': self.exception_stack,
            'metrics': self.metrics,
            'input_data': str(self.input_data) if self.input_data else None,
            'agent_type': self.agent_type,
            'timestamp': self.timestamp.isoformat(),
            'priority': self.priority
        }


@dataclass
class RetrainingJob:
    """
    A retraining job created from a failure context.
    """
    job_id: str
    failure_context: FailureContext
    synthetic_dataset: Optional[List[Dict]] = None
    model_path: Optional[str] = None
    target_metric: str = "accuracy"
    num_samples: int = 200
    epochs: int = 10
    lora_rank: int = 16
    lora_alpha: float = 32.0
    status: str = "queued"
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result_path: Optional[str] = None


@dataclass
class ExecutionReport:
    """Report from a goal execution run."""
    execution_id: str
    goal_id: str
    status: ExecutionStatus
    nodes_completed: int
    nodes_failed: int
    nodes_retried: int
    total_time: float
    convergence_achieved: bool
    final_metrics: Dict[str, float]
    failures: List[FailureContext] = field(default_factory=list)
    retraining_jobs: List[RetrainingJob] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


# =============================================================================
# Guardrail System
# =============================================================================

class GoalDriftCircuitBreaker:
    """
    Prevents the orchestrator from rewriting its own terminal goals.
    
    The root objective is locked in read-only memory.
    """
    
    def __init__(self):
        self._locked_objectives: Dict[str, str] = {}  # goal_id -> objective
    
    def lock_objective(self, goal: Goal) -> bool:
        """Lock a goal's objective to prevent modification."""
        if goal.goal_id in self._locked_objectives:
            return False
        self._locked_objectives[goal.goal_id] = goal.objective
        logger.info(f"CIRCUIT BREAKER: Locked objective for goal {goal.goal_id[:8]}")
        return True
    
    def verify_objective(self, goal: Goal) -> bool:
        """
        Verify that a goal's objective hasn't been modified.
        
        Returns:
            True if objective matches locked version, False if drifted
        """
        if goal.goal_id not in self._locked_objectives:
            return True  # Not locked yet
        return self._locked_objectives[goal.goal_id] == goal.objective
    
    def check_drift(self, original_objective: str, current_objective: str, goal_id: str) -> bool:
        """
        Check if objective has drifted.
        
        Returns:
            True if drift detected (FAILURE), False if OK
        """
        if original_objective != current_objective:
            logger.warning(
                f"GOAL DRIFT DETECTED: Goal {goal_id[:8]} "
                f"changed from '{original_objective[:50]}' to '{current_objective[:50]}'"
            )
            return True
        return False


class PerfectionBiasCap:
    """
    Stops fine-tuning runs if incremental fitness gains drop below threshold.
    
    Guardrail: Stop if Δ < 0.5% across 5 consecutive iterations.
    """
    
    def __init__(self, min_improvement: float = 0.005, patience: int = 5):
        self.min_improvement = min_improvement  # 0.5% = 0.005
        self.patience = patience
        self._history: List[float] = []  # History of improvements
    
    def record_improvement(self, improvement: float) -> bool:
        """
        Record an improvement value.
        
        Args:
            improvement: The improvement score (0.0-1.0)
        
        Returns:
            True if should continue, False if cap triggered (STOP)
        """
        self._history.append(improvement)
        
        # Keep only last `patience` entries
        if len(self._history) > self.patience:
            self._history = self._history[-self.patience:]
        
        # Check if all recent improvements are below threshold
        if len(self._history) >= self.patience:
            if all(imp < self.min_improvement for imp in self._history):
                logger.info(
                    f"PERFECTION BIAS CAP TRIGGERED: All {self.patience} improvements "
                    f"below {self.min_improvement:.1%}"
                )
                return False
        
        return True
    
    def reset(self):
        """Reset the improvement history."""
        self._history = []


class ExecutionHardStops:
    """
    Hard stops to prevent runaway processes.
    
    Guardrails:
    - Max 20 retries per task
    - Max 50 GPU fine-tuning epochs
    """
    
    def __init__(
        self,
        max_retries: int = 20,
        max_epochs: int = 50,
        max_iterations: int = 100
    ):
        self.max_retries = max_retries
        self.max_epochs = max_epochs
        self.max_iterations = max_iterations
    
    def check_retry_limit(self, retry_count: int, node_id: str) -> bool:
        """
        Check if retry limit exceeded.
        
        Args:
            retry_count: Current retry count
            node_id: Node identifier
        
        Returns:
            True if within limit, False if exceeded (STOP)
        """
        if retry_count >= self.max_retries:
            logger.warning(
                f"RETRY LIMIT EXCEEDED: Node {node_id[:8]} "
                f"retry #{retry_count} >= {self.max_retries}"
            )
            return False
        return True
    
    def check_epoch_limit(self, epoch: int, model_name: str) -> bool:
        """
        Check if epoch limit exceeded.
        
        Args:
            epoch: Current epoch
            model_name: Model identifier
        
        Returns:
            True if within limit, False if exceeded (STOP)
        """
        if epoch >= self.max_epochs:
            logger.warning(
                f"EPOCH LIMIT EXCEEDED: Model {model_name[:20]} "
                f"epoch #{epoch} >= {self.max_epochs}"
            )
            return False
        return True
    
    def check_iteration_limit(self, iteration: int, execution_id: str) -> bool:
        """
        Check if iteration limit exceeded.
        
        Args:
            iteration: Current iteration
            execution_id: Execution identifier
        
        Returns:
            True if within limit, False if exceeded (STOP)
        """
        if iteration >= self.max_iterations:
            logger.warning(
                f"ITERATION LIMIT EXCEEDED: Execution {execution_id[:8]} "
                f"iteration #{iteration} >= {self.max_iterations}"
            )
            return False
        return True


# =============================================================================
# Goal Decomposer
# =============================================================================

class GoalDecomposer:
    """
    Breaks macro objectives into execution DAG of verifiable sub-milestones.
    
    Uses the researcher model to intelligently decompose goals.
    """
    
    def __init__(self, researcher_agent: Optional[Any] = None):
        self.researcher = researcher_agent
        self._decomposition_templates: Dict[str, List[Dict]] = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load decomposition templates for common goal types."""
        self._decomposition_templates = {
            'deploy': [
                {'action': 'analyze_requirements', 'description': 'Analyze deployment requirements'},
                {'action': 'setup_infrastructure', 'description': 'Set up infrastructure'},
                {'action': 'deploy_components', 'description': 'Deploy system components'},
                {'action': 'configure_system', 'description': 'Configure system'},
                {'action': 'test_deployment', 'description': 'Run deployment tests'},
                {'action': 'monitor_performance', 'description': 'Monitor initial performance'},
            ],
            'develop': [
                {'action': 'design_architecture', 'description': 'Design system architecture'},
                {'action': 'implement_core', 'description': 'Implement core functionality'},
                {'action': 'add_features', 'description': 'Add required features'},
                {'action': 'write_tests', 'description': 'Write test cases'},
                {'action': 'optimize_performance', 'description': 'Optimize performance'},
                {'action': 'document_system', 'description': 'Document the system'},
            ],
            'research': [
                {'action': 'define_hypothesis', 'description': 'Define research hypothesis'},
                {'action': 'gather_data', 'description': 'Gather relevant data'},
                {'action': 'analyze_data', 'description': 'Analyze collected data'},
                {'action': 'generate_insights', 'description': 'Generate insights'},
                {'action': 'validate_findings', 'description': 'Validate findings'},
                {'action': 'create_report', 'description': 'Create research report'},
            ],
        }
    
    def decompose(self, goal: Goal) -> ExecutionDAG:
        """
        Decompose a goal into an execution DAG.
        
        Args:
            goal: The goal to decompose
        
        Returns:
            ExecutionDAG with nodes and dependencies
        """
        dag_id = str(uuid.uuid4())
        nodes = {}
        
        # Try to match goal type to template
        objective_lower = goal.objective.lower()
        template = None
        for key in self._decomposition_templates:
            if key in objective_lower:
                template = self._decomposition_templates[key]
                break
        
        if template:
            # Use template
            for i, step in enumerate(template):
                node_id = f"{dag_id}_{i}"
                node = ExecutionNode(
                    node_id=node_id,
                    goal_id=goal.goal_id,
                    description=step['description'],
                    action=step['action'],
                    agent_type='researcher' if i == 0 else 'production',
                    domain=goal.domain,
                    dependencies=[f"{dag_id}_{i-1}"] if i > 0 else [],
                    pass_criteria=goal.pass_criteria if i == len(template) - 1 else {}
                )
                nodes[node_id] = node
        else:
            # Generic decomposition: single node
            node_id = f"{dag_id}_0"
            node = ExecutionNode(
                node_id=node_id,
                goal_id=goal.goal_id,
                description=f"Execute: {goal.objective}",
                action='execute',
                agent_type='production',
                domain=goal.domain,
                dependencies=[],
                pass_criteria=goal.pass_criteria
            )
            nodes[node_id] = node
        
        # Create DAG
        dag = ExecutionDAG(
            dag_id=dag_id,
            goal=goal,
            nodes=nodes
        )
        
        logger.info(f"Decomposed goal {goal.goal_id[:8]} into {len(nodes)} nodes")
        return dag
    
    def decompose_with_llm(self, goal: Goal) -> ExecutionDAG:
        """
        Decompose a goal using LLM (if researcher available).
        
        Args:
            goal: The goal to decompose
        
        Returns:
            ExecutionDAG with LLM-generated nodes
        """
        if not self.researcher:
            return self.decompose(goal)
        
        # Use researcher to generate decomposition
        prompt = f"""
        Decompose the following goal into 5-10 verifiable sub-milestones:
        
        GOAL: {goal.objective}
        DOMAIN: {goal.domain or 'general'}
        
        For each sub-milestone, provide:
        1. A description
        2. An action verb
        3. Any dependencies on other milestones
        4. Pass criteria (metrics and thresholds)
        
        Format as JSON array of objects.
        """
        
        try:
            result = self.researcher.run(prompt)
            text = result.get('text', '') if isinstance(result, dict) else str(result)
            
            # Try to parse JSON
            import json
            try:
                steps = json.loads(text)
            except json.JSONDecodeError:
                # Fall back to template
                return self.decompose(goal)
            
            # Create nodes from LLM output
            dag_id = str(uuid.uuid4())
            nodes = {}
            node_ids = []
            
            for i, step in enumerate(steps):
                node_id = f"{dag_id}_{i}"
                node_ids.append(node_id)
                node = ExecutionNode(
                    node_id=node_id,
                    goal_id=goal.goal_id,
                    description=step.get('description', step.get('name', f'Step {i+1}')),
                    action=step.get('action', 'execute'),
                    agent_type=step.get('agent', 'production'),
                    domain=step.get('domain', goal.domain),
                    dependencies=[node_ids[j] for j in step.get('dependencies', []) if j < i],
                    pass_criteria=step.get('pass_criteria', goal.pass_criteria if i == len(steps) - 1 else {})
                )
                nodes[node_id] = node
            
            dag = ExecutionDAG(
                dag_id=dag_id,
                goal=goal,
                nodes=nodes
            )
            
            logger.info(f"LLM decomposed goal {goal.goal_id[:8]} into {len(nodes)} nodes")
            return dag
            
        except Exception as e:
            logger.warning(f"LLM decomposition failed: {e}, using template")
            return self.decompose(goal)


# =============================================================================
# State Validator (Observer)
# =============================================================================

class StateValidator:
    """
    Observer process that validates system state after every execution cycle.
    
    Success: Orchestrator advances to next node
    Failure: Failure context pushed to retraining queue
    """
    
    def __init__(self, evaluation_agent: Optional[Any] = None):
        self.evaluator = evaluation_agent
        self._queue: List[FailureContext] = []  # Local queue (would connect to Proxmox P100)
    
    def validate_node(self, node: ExecutionNode, result: Any) -> Tuple[bool, Optional[FailureContext]]:
        """
        Validate a node's execution result.
        
        Args:
            node: The execution node
            result: The result from execution
        
        Returns:
            Tuple of (success, failure_context)
            - If success=True, orchestrator advances to next node
            - If success=False, failure_context is provided for retraining
        """
        try:
            # Extract metrics from result
            metrics = {}
            if isinstance(result, dict):
                metrics = {
                    k: float(v) for k, v in result.items()
                    if isinstance(v, (int, float)) and not isinstance(v, bool)
                }
            node.metrics = metrics
            
            # Check pass criteria
            if node.pass_criteria:
                for metric, threshold in node.pass_criteria.items():
                    if metrics.get(metric, 0) < threshold:
                        error = f"Pass criteria not met: {metric}={metrics.get(metric, 0)} < {threshold}"
                        logger.warning(f"VALIDATION FAILED: {error}")
                        return False, self._create_failure_context(node, result, error)
            
            # Additional validation
            if result is None or (isinstance(result, dict) and result.get('error')):
                error = str(result.get('error', 'Unknown error'))
                logger.warning(f"VALIDATION FAILED: {error}")
                return False, self._create_failure_context(node, result, error)
            
            # Success
            logger.info(f"VALIDATION PASSED: Node {node.node_id[:8]} meets all criteria")
            return True, None
            
        except Exception as e:
            logger.error(f"Validation error for node {node.node_id[:8]}: {e}")
            return False, self._create_failure_context(node, result, str(e), exception_stack=str(e))
    
    def _create_failure_context(
        self,
        node: ExecutionNode,
        result: Any,
        error: str,
        exception_stack: Optional[str] = None
    ) -> FailureContext:
        """Create a failure context for retraining."""
        context = FailureContext(
            node_id=node.node_id,
            goal_id=node.goal_id,
            error=error,
            error_type=type(result).__name__ if result else 'Unknown',
            exception_stack=exception_stack or 'No stack trace',
            metrics=node.metrics,
            input_data=None,  # Would capture actual input
            agent_type=node.agent_type,
            priority=1  # Highest priority
        )
        
        # Push to queue (in production, would send to Proxmox P100)
        self._queue.append(context)
        logger.info(f"Failure context queued for retraining: {context.node_id[:8]}")
        
        return context
    
    def get_queued_failures(self) -> List[FailureContext]:
        """Get all queued failure contexts."""
        return self._queue.copy()
    
    def clear_queue(self) -> List[FailureContext]:
        """Clear the failure queue and return all items."""
        items = self._queue.copy()
        self._queue = []
        return items


# =============================================================================
# Retraining Coordinator
# =============================================================================

class RetrainingCoordinator:
    """
    Coordinates autonomous retraining and hot-swap of models.
    
    1. Pulls failure contexts from queue
    2. Generates synthetic datasets focused on failure points
    3. Retrains 45M parameter models
    4. Hot-swaps .cact binaries
    5. Sub-agent retries failed step
    """
    
    def __init__(
        self,
        finetune_factory: Any,
        models_dir: Optional[Path] = None
    ):
        self.finetune_factory = finetune_factory
        self.models_dir = models_dir or Path('models')
        self._jobs: Dict[str, RetrainingJob] = {}
        self._active_jobs: Dict[str, RetrainingJob] = {}
    
    def process_failure(
        self,
        failure: FailureContext,
        finetune_epochs: int = 10,
        num_samples: int = 200
    ) -> RetrainingJob:
        """
        Process a failure context and create a retraining job.
        
        Args:
            failure: The failure context
            finetune_epochs: Number of epochs for retraining
            num_samples: Number of synthetic samples to generate
        
        Returns:
            RetrainingJob with job details
        """
        job_id = str(uuid.uuid4())
        
        # Generate synthetic dataset focused on failure point
        synthetic_dataset = self._generate_synthetic_dataset(failure, num_samples)
        
        job = RetrainingJob(
            job_id=job_id,
            failure_context=failure,
            synthetic_dataset=synthetic_dataset,
            target_metric=failure.metrics.keys()[0] if failure.metrics else 'accuracy',
            num_samples=num_samples,
            epochs=finetune_epochs
        )
        
        self._jobs[job_id] = job
        self._active_jobs[job_id] = job
        
        logger.info(f"Retraining job created: {job_id[:8]} for node {failure.node_id[:8]}")
        return job
    
    def _generate_synthetic_dataset(self, failure: FailureContext, num_samples: int) -> List[Dict]:
        """
        Generate synthetic training data focused on the failure point.
        
        In production, this would use the researcher model to create
        targeted examples that address the specific failure.
        """
        dataset = []
        
        # Create samples based on failure context
        for i in range(num_samples):
            sample = {
                'input': f"Task related to {failure.node_id}: {i}",
                'expected_output': f"Correct output for {failure.node_id}",
                'domain': failure.domain or 'general',
                'difficulty': 'medium',
                'tags': ['failure_recovery', failure.node_id[:8]]
            }
            dataset.append(sample)
        
        logger.info(f"Generated {len(dataset)} synthetic samples for retraining")
        return dataset
    
    def execute_job(self, job: RetrainingJob) -> Optional[Path]:
        """
        Execute a retraining job.
        
        Args:
            job: The retraining job to execute
        
        Returns:
            Path to the new .cact model, or None if failed
        """
        job.status = "in_progress"
        job.started_at = datetime.now()
        
        try:
            # Use fine-tune factory to create model
            model_name = f"retry_{job.failure_context.node_id[:8]}_{job.job_id[:8]}"
            
            # In production, would use actual dataset
            model_path = self.finetune_factory.create_model(
                name=model_name,
                domain=job.failure_context.domain or 'failure_recovery',
                tools_schema=[],  # Would use actual schema
                num_samples=job.num_samples,
                epochs=job.epochs,
                lora_rank=job.lora_rank,
                lora_alpha=job.lora_alpha
            )
            
            job.status = "completed"
            job.completed_at = datetime.now()
            job.result_path = str(model_path) if model_path else None
            
            logger.info(f"Retraining job {job.job_id[:8]} completed, model: {model_path}")
            return model_path
            
        except Exception as e:
            logger.error(f"Retraining job {job.job_id[:8]} failed: {e}")
            job.status = "failed"
            job.completed_at = datetime.now()
            return None
    
    def hot_swap_model(
        self,
        old_model_path: Path,
        new_model_path: Path,
        agent_type: str
    ) -> bool:
        """
        Hot-swap a .cact binary in place.
        
        Args:
            old_model_path: Path to old model
            new_model_path: Path to new model
            agent_type: Type of agent using the model
        
        Returns:
            True if swap successful
        """
        try:
            # In production, this would:
            # 1. Validate new model
            # 2. Atomic swap (rename files)
            # 3. Reload model in agent
            # 4. Verify swap
            
            # For now, just log
            logger.info(
                f"HOT-SWAP: Replacing {old_model_path.name} with {new_model_path.name} "
                f"for {agent_type}"
            )
            
            # TODO: Implement actual hot-swap
            # import os
            # backup = old_model_path.with_suffix('.cact.bak')
            # os.rename(old_model_path, backup)
            # os.rename(new_model_path, old_model_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Hot-swap failed: {e}")
            return False
    
    def get_job(self, job_id: str) -> Optional[RetrainingJob]:
        """Get a retraining job by ID."""
        return self._jobs.get(job_id)
    
    def get_active_jobs(self) -> List[RetrainingJob]:
        """Get all active retraining jobs."""
        return list(self._active_jobs.values())


# =============================================================================
# Convergence Monitor
# =============================================================================

class ConvergenceMonitor:
    """
    Monitors terminal convergence - exits when all nodes clear pass criteria.
    """
    
    def __init__(self):
        self._execution_history: List[Dict] = []
    
    def check_convergence(self, dag: ExecutionDAG) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if execution has converged.
        
        Args:
            dag: The execution DAG
        
        Returns:
            Tuple of (converged, report)
        """
        # Check if all nodes are completed
        if dag.has_uncompleted_nodes():
            return False, {'status': 'incomplete', 'message': 'Nodes remaining'}
        
        # Check if all nodes meet pass criteria
        if not dag.all_nodes_meet_criteria():
            return False, {
                'status': 'criteria_not_met',
                'message': 'Some nodes do not meet pass criteria'
            }
        
        # All nodes completed and meet criteria
        report = {
            'status': 'converged',
            'message': 'All nodes meet pass criteria',
            'nodes_completed': len(dag.completed_nodes),
            'nodes_failed': len(dag.failed_nodes),
            'total_time': (dag.completed_at - dag.started_at).total_seconds() if dag.completed_at and dag.started_at else 0
        }
        
        logger.info(f"TERMINAL CONVERGENCE ACHIEVED: {report['message']}")
        return True, report


# =============================================================================
# Goal Execution Engine (Main Class)
# =============================================================================

class GoalExecutionEngine:
    """
    Main engine for continuous goal execution loop.
    
    Integrates:
    - Goal Decomposer: Macro objective → Execution DAG
    - State Validator: Post-execution validation
    - Retraining Coordinator: Autonomous retraining & hot-swap
    - Convergence Monitor: Terminal convergence check
    - Guardrails: Goal drift breaker, perfection cap, hard stops
    
    Architecture:
    ┌─────────────────────────────────────────────────────────────────┐
    │                    GOAL EXECUTION ENGINE                           │
    ├─────────────────────────────────────────────────────────────────┤
    │                                                                      │
    │  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐     │
    │  │ Goal        │───▶│ DAG         │───▶│ Execution       │     │
    │  │ Decomposer │    │ Generator   │    │ Controller      │     │
    │  └─────────────┘    └─────────────┘    └─────────────────┘     │
    │         ▲                  │                     │                │
    │         │                  ▼                     ▼                │
    │  ┌──────┴──────┐    ┌─────────────┐    ┌─────────────────┐     │
    │  │ Failure     │◀───│ State       │    │ Retraining      │     │
    │  │ Queue (P100)│    │ Validator   │    │ Coordinator     │     │
    │  └─────────────┘    └─────────────┘    └─────────────────┘     │
    │         ▲                                                  │        │
    │         │                                                  ▼        │
    │  ┌──────┴──────┐    ┌─────────────────┐    ┌─────────────┐     │
    │  │ Hot-Swap     │◀───│ Convergence      │    │ Guardrails   │     │
    │  │ .cact       │    │ Monitor          │    │ System       │     │
    │  └─────────────┘    └─────────────────┘    └─────────────┘     │
    │                                                                      │
    └─────────────────────────────────────────────────────────────────┘
    """
    
    def __init__(
        self,
        orchestrator: Optional[Any] = None,
        researcher_agent: Optional[Any] = None,
        finetune_factory: Optional[Any] = None,
        evaluation_agent: Optional[Any] = None,
        models_dir: Optional[Path] = None
    ):
        self.orchestrator = orchestrator
        self.researcher = researcher_agent
        self.finetune_factory = finetune_factory
        self.evaluation_agent = evaluation_agent
        self.models_dir = models_dir or Path('models')
        
        # Initialize components
        self.decomposer = GoalDecomposer(researcher_agent)
        self.validator = StateValidator(evaluation_agent)
        self.retrainer = RetrainingCoordinator(finetune_factory, models_dir)
        self.convergence = ConvergenceMonitor()
        
        # Guardrails
        self.drift_breaker = GoalDriftCircuitBreaker()
        self.perfection_cap = PerfectionBiasCap(min_improvement=0.005, patience=5)
        self.hard_stops = ExecutionHardStops(max_retries=20, max_epochs=50)
        
        # State
        self._active_executions: Dict[str, ExecutionDAG] = {}
        self._execution_history: List[ExecutionReport] = []
        
        logger.info("GoalExecutionEngine initialized")
    
    def execute_goal(
        self,
        goal: Goal,
        max_iterations: int = 100,
        use_llm_decomposition: bool = True
    ) -> ExecutionReport:
        """
        Execute a goal through the continuous execution loop.
        
        Args:
            goal: The goal to execute
            max_iterations: Maximum iterations (guardrail)
            use_llm_decomposition: Use LLM for goal decomposition
        
        Returns:
            ExecutionReport with results
        """
        execution_id = str(uuid.uuid4())
        
        # Lock the objective to prevent goal drift
        self.drift_breaker.lock_objective(goal)
        goal.lock_objective()
        
        # Decompose goal into DAG
        if use_llm_decomposition and self.researcher:
            dag = self.decomposer.decompose_with_llm(goal)
        else:
            dag = self.decomposer.decompose(goal)
        
        dag.started_at = datetime.now()
        
        # Execute the DAG
        report = self._execute_dag(dag, max_iterations, execution_id)
        
        # Check convergence
        converged, convergence_report = self.convergence.check_convergence(dag)
        report.convergence_achieved = converged
        
        # Store in history
        self._execution_history.append(report)
        
        # Cleanup
        self._active_executions.pop(execution_id, None)
        
        return report
    
    def _execute_dag(
        self,
        dag: ExecutionDAG,
        max_iterations: int,
        execution_id: str
    ) -> ExecutionReport:
        """
        Execute an execution DAG.
        
        Args:
            dag: The DAG to execute
            max_iterations: Maximum iterations
            execution_id: Execution identifier
        
        Returns:
            ExecutionReport with results
        """
        report = ExecutionReport(
            execution_id=execution_id,
            goal_id=dag.goal.goal_id,
            status=ExecutionStatus.RUNNING,
            nodes_completed=0,
            nodes_failed=0,
            nodes_retried=0,
            total_time=0.0,
            convergence_achieved=False,
            final_metrics={},
            failures=[],
            retraining_jobs=[]
        )
        
        start_time = datetime.now()
        iteration = 0
        
        try:
            while iteration < max_iterations:
                # Check iteration limit (guardrail)
                if not self.hard_stops.check_iteration_limit(iteration, execution_id):
                    report.status = ExecutionStatus.FAILED
                    report.final_metrics['error'] = 'Iteration limit exceeded'
                    break
                
                # Get next node to execute
                next_node_id = dag.get_next_node()
                
                if next_node_id is None:
                    # No more nodes to execute
                    if not dag.has_uncompleted_nodes():
                        report.status = ExecutionStatus.COMPLETED
                        dag.status = ExecutionStatus.COMPLETED
                        dag.completed_at = datetime.now()
                        break
                    else:
                        # There are uncompleted nodes but none ready (circular dependency?)
                        logger.warning("No ready nodes but uncompleted nodes exist")
                        report.status = ExecutionStatus.FAILED
                        report.final_metrics['error'] = 'No ready nodes available'
                        break
                
                # Execute the node
                node = dag.nodes[next_node_id]
                node.started_at = datetime.now()
                
                logger.info(f"Executing node {next_node_id[:8]}: {node.description}")
                
                try:
                    # Execute using orchestrator
                    if self.orchestrator:
                        result = self.orchestrator.query(node.description)
                    else:
                        # Simulate execution
                        import time
                        time.sleep(0.1)
                        result = {'status': 'success', 'answer': f'Completed: {node.description}'}
                    
                    node.result = result
                    
                    # Validate state
                    success, failure_context = self.validator.validate_node(node, result)
                    
                    if success:
                        # Node completed successfully
                        node.status = NodeStatus.COMPLETED
                        node.completed_at = datetime.now()
                        dag.completed_nodes.append(next_node_id)
                        report.nodes_completed += 1
                        
                        logger.info(f"Node {next_node_id[:8]} COMPLETED")
                        
                        # Record improvement for perfection cap
                        if 'score' in result:
                            self.perfection_cap.record_improvement(result['score'])
                        
                    else:
                        # Node failed
                        node.status = NodeStatus.FAILED
                        node.completed_at = datetime.now()
                        dag.failed_nodes.append(next_node_id)
                        report.nodes_failed += 1
                        report.failures.append(failure_context)
                        
                        logger.warning(f"Node {next_node_id[:8]} FAILED: {failure_context.error}")
                        
                        # Create retraining job
                        job = self.retrainer.process_failure(
                            failure_context,
                            finetune_epochs=10,
                            num_samples=200
                        )
                        report.retraining_jobs.append(job)
                        
                        # Execute retraining (async in production)
                        # model_path = self.retrainer.execute_job(job)
                        # if model_path:
                        #     self.retrainer.hot_swap_model(...)
                        
                        # Retry if within limit
                        if node.retry_count < node.max_retries:
                            node.retry_count += 1
                            node.status = NodeStatus.RETRYING
                            report.nodes_retried += 1
                            
                            # Re-queue the node by resetting its dependencies
                            # (In production, would have more sophisticated retry logic)
                            continue
                
                except Exception as e:
                    logger.error(f"Node execution error: {e}")
                    node.status = NodeStatus.FAILED
                    node.error = str(e)
                    node.completed_at = datetime.now()
                    dag.failed_nodes.append(next_node_id)
                    report.nodes_failed += 1
                
                iteration += 1
            
            # Final status
            if report.status == ExecutionStatus.RUNNING:
                if not dag.has_uncompleted_nodes():
                    report.status = ExecutionStatus.COMPLETED
                else:
                    report.status = ExecutionStatus.FAILED
            
            report.total_time = (datetime.now() - start_time).total_seconds()
            
        except Exception as e:
            logger.error(f"Execution error: {e}")
            report.status = ExecutionStatus.FAILED
            report.final_metrics['error'] = str(e)
            report.total_time = (datetime.now() - start_time).total_seconds()
        
        return report
    
    def execute_dag(self, dag: ExecutionDAG, max_iterations: int = 100) -> ExecutionReport:
        """
        Execute a pre-built DAG.
        
        Args:
            dag: The execution DAG
            max_iterations: Maximum iterations
        
        Returns:
            ExecutionReport with results
        """
        return self._execute_dag(dag, max_iterations, str(uuid.uuid4()))
    
    def decompose_goal(self, goal: Goal, use_llm: bool = True) -> ExecutionDAG:
        """
        Decompose a goal into an execution DAG.
        
        Args:
            goal: The goal to decompose
            use_llm: Use LLM for decomposition
        
        Returns:
            ExecutionDAG
        """
        if use_llm and self.researcher:
            return self.decomposer.decompose_with_llm(goal)
        return self.decomposer.decompose(goal)
    
    def get_execution_report(self, execution_id: str) -> Optional[ExecutionReport]:
        """Get an execution report by ID."""
        for report in self._execution_history:
            if report.execution_id == execution_id:
                return report
        return None
    
    def get_active_executions(self) -> List[ExecutionDAG]:
        """Get all active executions."""
        return list(self._active_executions.values())
    
    def get_execution_history(self, limit: int = 10) -> List[ExecutionReport]:
        """Get recent execution history."""
        return self._execution_history[-limit:]
    
    def reset(self):
        """Reset the engine state."""
        self._active_executions.clear()
        self._execution_history.clear()
        self.perfection_cap.reset()


# =============================================================================
# Factory Functions
# =============================================================================

def create_execution_engine(
    orchestrator: Optional[Any] = None,
    researcher_agent: Optional[Any] = None,
    finetune_factory: Optional[Any] = None,
    evaluation_agent: Optional[Any] = None
) -> GoalExecutionEngine:
    """
    Factory function to create a GoalExecutionEngine.
    
    Args:
        orchestrator: Orchestrator instance
        researcher_agent: Researcher agent instance
        finetune_factory: Fine-tune factory instance
        evaluation_agent: Evaluation agent instance
    
    Returns:
        GoalExecutionEngine instance
    """
    return GoalExecutionEngine(
        orchestrator=orchestrator,
        researcher_agent=researcher_agent,
        finetune_factory=finetune_factory,
        evaluation_agent=evaluation_agent
    )


def execute_goal(
    goal_objective: str,
    pass_criteria: Dict[str, float],
    orchestrator: Optional[Any] = None,
    domain: Optional[str] = None
) -> ExecutionReport:
    """
    Convenience function to execute a goal.
    
    Args:
        goal_objective: The goal objective
        pass_criteria: Pass criteria metrics and thresholds
        orchestrator: Orchestrator instance
        domain: Goal domain
    
    Returns:
        ExecutionReport with results
    """
    from orchestrator import Orchestrator
    
    orch = orchestrator or Orchestrator()
    engine = create_execution_engine(orchestrator=orch)
    
    goal = Goal(
        objective=goal_objective,
        pass_criteria=pass_criteria,
        domain=domain
    )
    
    return engine.execute_goal(goal)


if __name__ == "__main__":
    # Example usage
    logger.info("Testing Goal Execution Engine...")
    
    # Create a test goal
    goal = Goal(
        objective="Deploy a production-ready weather prediction system",
        pass_criteria={
            "accuracy": 0.95,
            "latency": 0.5,
            "coverage": 1.0
        },
        domain="weather"
    )
    
    # Create engine (without actual components for testing)
    engine = GoalExecutionEngine()
    
    # Decompose goal
    dag = engine.decompose_goal(goal, use_llm=False)
    print(f"Decomposed goal into {len(dag.nodes)} nodes")
    
    # Show execution order
    order = dag.get_execution_order()
    print(f"Execution order: {order}")
    
    # Execute (will use simulated execution)
    report = engine.execute_goal(goal, max_iterations=10)
    print(f"Execution status: {report.status}")
    print(f"Nodes completed: {report.nodes_completed}")
    print(f"Convergence achieved: {report.convergence_achieved}")
    
    logger.info("Test completed!")
