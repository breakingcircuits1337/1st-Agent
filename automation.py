"""
Automation Module - Master automation for the 1st Agent framework.

This module provides high-level automation capabilities:

1. **One-Command Setup**: Initialize and configure the entire system
2. **Batch Processing**: Process multiple queries efficiently
3. **Autonomous Optimization**: Run self-optimization cycles automatically
4. **Scheduled Tasks**: Run operations on a schedule
5. **Pipeline Automation**: Chain multiple operations together

Architecture:
┌─────────────────────────────────────────────────────────────────────────┐
│                          AUTOMATION LAYER                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │   Pipeline       │  │   Scheduler      │  │   Batch          │         │
│  │   - Chain ops    │  │   - Cron jobs    │  │   - Multi-query  │         │
│  │   - Workflows    │  │   - Intervals    │  │   - Parallel     │         │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘         │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Master Controller                        │   │
│  │  - manage_pipeline()                                       │   │
│  │  - run_scheduled()                                         │   │
│  │  - process_batch()                                         │   │
│  │  - auto_optimize()                                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         EXISTING SYSTEM                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ Orchestrator│  │Self-Optimizer│  │FineTuneFactory│  │ Evaluation  │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  │  Agent      │    │
│                                                        └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘

Usage:
    # Run the master automation
    python automation.py
    
    # Or use as a library
    from automation import AutomationController
    
    controller = AutomationController()
    
    # Run a pipeline
    controller.run_pipeline([
        {"action": "query", "query": "What's the weather?"},
        {"action": "evaluate", "model": "weather.cact"},
        {"action": "optimize", "domain": "weather"}
    ])
    
    # Run scheduled tasks
    controller.start_scheduler()
"""

import json
import logging
import os
import signal
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from orchestrator import Orchestrator
from self_optimizer import SelfOptimizer, SelfModifier
from evaluation_agent import EvaluationAgent
from finetune_factory import FineTuneFactory

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class PipelineStep:
    """A single step in an automation pipeline."""
    action: str  # query, evaluate, finetune, optimize, etc.
    parameters: Dict[str, Any] = field(default_factory=dict)
    name: Optional[str] = None
    depends_on: Optional[List[str]] = None
    timeout: int = 300  # Seconds
    
    def __repr__(self):
        return f"PipelineStep({self.action}, params={list(self.parameters.keys())})"


@dataclass
class PipelineResult:
    """Result of running a pipeline."""
    success: bool
    steps_completed: int
    steps_failed: int
    total_duration: float
    step_results: List[Dict[str, Any]] = field(default_factory=list)
    output: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class ScheduledTask:
    """A task to be run on a schedule."""
    name: str
    action: str
    parameters: Dict[str, Any]
    schedule: str  # "hourly", "daily", "interval:N" (seconds), or cron-like
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    
    def __repr__(self):
        return f"ScheduledTask({self.name}, {self.schedule})"


@dataclass
class BatchJob:
    """A batch processing job."""
    name: str
    queries: List[str]
    parallel: bool = False
    max_workers: int = 4
    results: List[Any] = field(default_factory=list)
    status: str = "pending"
    progress: int = 0
    
    def __repr__(self):
        return f"BatchJob({self.name}, {len(self.queries)} queries, {self.progress}/{len(self.queries)})"


# =============================================================================
# Automation Controller
# =============================================================================

class AutomationController:
    """
    Master controller for automating the 1st Agent framework.
    
    This class provides:
    - Pipeline execution
    - Batch processing
    - Scheduled task management
    - Autonomous optimization
    - System health monitoring
    
    Usage:
        controller = AutomationController()
        
        # Run a simple query
        result = controller.query("What's the weather in Lagos?")
        
        # Run a pipeline
        pipeline = [
            {"action": "query", "parameters": {"query": "Weather in Tokyo?"}},
            {"action": "evaluate", "parameters": {"model": "models/weather.cact"}},
            {"action": "optimize", "parameters": {"domain": "weather"}}
        ]
        result = controller.run_pipeline(pipeline)
        
        # Run batch queries
        job = controller.create_batch_job("test_run", ["query1", "query2"])
        controller.run_batch_job(job)
        
        # Start scheduler
        controller.start_scheduler()
    """
    
    def __init__(self):
        """Initialize the automation controller."""
        self.orchestrator = Orchestrator()
        self.optimizer = SelfOptimizer()
        self.modifier = SelfModifier(self.optimizer)
        
        # Pipeline state
        self.pipeline_registry: Dict[str, List[PipelineStep]] = {}
        self.pipeline_results: Dict[str, PipelineResult] = {}
        
        # Batch state
        self.batch_jobs: Dict[str, BatchJob] = {}
        
        # Scheduled tasks
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.scheduler_thread: Optional[threading.Thread] = None
        self.scheduler_running = False
        
        # State
        self.running = True
        self.start_time = datetime.now()
        
        logger.info("AutomationController initialized")
    
    # =========================================================================
    # Query Methods
    # =========================================================================
    
    def query(self, query: str, **kwargs) -> Any:
        """Run a single query through the orchestrator."""
        return self.orchestrator.query(query, **kwargs)
    
    def batch_query(self, queries: List[str], **kwargs) -> List[Any]:
        """Run multiple queries."""
        return self.orchestrator.batch_query(queries, **kwargs)
    
    # =========================================================================
    # Pipeline Methods
    # =========================================================================
    
    def register_pipeline(self, name: str, steps: List[Dict[str, Any]]) -> None:
        """
        Register a named pipeline.
        
        Args:
            name: Pipeline name
            steps: List of step definitions (dicts or PipelineStep objects)
        """
        pipeline_steps = []
        for step in steps:
            if isinstance(step, dict):
                pipeline_steps.append(PipelineStep(**step))
            else:
                pipeline_steps.append(step)
        
        self.pipeline_registry[name] = pipeline_steps
        logger.info(f"Registered pipeline: {name} ({len(pipeline_steps)} steps)")
    
    def run_pipeline(
        self,
        pipeline: Union[str, List[Dict[str, Any]]],
        timeout: Optional[int] = None
    ) -> PipelineResult:
        """
        Run a pipeline of operations.
        
        Args:
            pipeline: Pipeline name or list of steps
            timeout: Optional timeout in seconds
        
        Returns:
            PipelineResult with status and results
        """
        start_time = time.time()
        
        # Get pipeline steps
        if isinstance(pipeline, str):
            if pipeline not in self.pipeline_registry:
                raise ValueError(f"Pipeline '{pipeline}' not registered")
            steps = self.pipeline_registry[pipeline]
        else:
            steps = [PipelineStep(**s) if isinstance(s, dict) else s for s in pipeline]
        
        result = PipelineResult(
            success=True,
            steps_completed=0,
            steps_failed=0,
            total_duration=0.0,
            step_results=[],
            output=None
        )
        
        step_outputs: Dict[str, Any] = {}
        
        try:
            for i, step in enumerate(steps):
                # Check timeout
                if timeout and (time.time() - start_time) > timeout:
                    result.success = False
                    result.error = "Pipeline timeout"
                    break
                
                logger.info(f"Pipeline step {i+1}/{len(steps)}: {step.action}")
                
                try:
                    # Execute the step
                    output = self._execute_step(step, step_outputs)
                    step_outputs[step.name or f"step_{i}"] = output
                    
                    step_result = {
                        "step": i,
                        "action": step.action,
                        "name": step.name,
                        "status": "completed",
                        "duration": time.time() - start_time,
                        "output": output
                    }
                    result.step_results.append(step_result)
                    result.steps_completed += 1
                    
                    # Store final output
                    result.output = output
                    
                except Exception as e:
                    result.success = False
                    result.steps_failed += 1
                    step_result = {
                        "step": i,
                        "action": step.action,
                        "name": step.name,
                        "status": "failed",
                        "error": str(e),
                        "duration": time.time() - start_time
                    }
                    result.step_results.append(step_result)
                    logger.error(f"Pipeline step {i+1} failed: {e}")
                    
                    # Stop on failure by default
                    if step.parameters.get("continue_on_error", False) != True:
                        result.error = f"Step {i+1} ({step.action}) failed: {e}"
                        break
            
            result.total_duration = time.time() - start_time
            
        except Exception as e:
            result.success = False
            result.error = str(e)
            result.total_duration = time.time() - start_time
        
        # Store result
        if isinstance(pipeline, str):
            self.pipeline_results[pipeline] = result
        
        logger.info(f"Pipeline completed: {result.steps_completed}/{len(steps)} steps, duration={result.total_duration:.1f}s")
        return result
    
    def _execute_step(self, step: PipelineStep, step_outputs: Dict[str, Any]) -> Any:
        """Execute a single pipeline step."""
        action = step.action.lower()
        params = step.parameters.copy()
        
        # Resolve dependencies
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("$"):
                # Reference to previous step output
                ref = value[1:]
                if ref in step_outputs:
                    params[key] = step_outputs[ref]
        
        # Execute based on action
        if action == "query":
            return self.orchestrator.query(**params)
        
        elif action == "evaluate":
            return self.orchestrator.evaluate_model(
                model_path=params.get("model"),
                test_data_path=params.get("test_data"),
                num_samples=params.get("num_samples", 50)
            )
        
        elif action == "finetune" or action == "create_model":
            return self.orchestrator.create_finetuned_model(
                name=params.get("name"),
                domain=params.get("domain"),
                tools_schema=params.get("tools_schema", []),
                num_samples=params.get("num_samples", 200),
                epochs=params.get("epochs", 10)
            )
        
        elif action == "optimize" or action == "closed_loop":
            return self.orchestrator.closed_loop_optimize(
                target_domain=params.get("domain"),
                target_tools=params.get("tools", []),
                test_data_path=params.get("test_data"),
                max_iterations=params.get("max_iterations", 5)
            )
        
        elif action == "self_optimize":
            return self.optimizer.run_self_optimization_cycle()
        
        elif action == "status":
            return {
                "orchestrator": self.orchestrator.get_status(),
                "system_health": self.optimizer.get_system_health()
            }
        
        elif action == "sleep":
            time.sleep(params.get("seconds", 1))
            return {"status": "slept", "seconds": params.get("seconds", 1)}
        
        elif action == "log":
            message = params.get("message", "")
            logger.info(f"[Pipeline] {message}")
            return {"status": "logged", "message": message}
        
        else:
            # Try to call a method on the orchestrator
            if hasattr(self.orchestrator, action):
                method = getattr(self.orchestrator, action)
                return method(**params)
            else:
                raise ValueError(f"Unknown action: {action}")
    
    def list_pipelines(self) -> List[str]:
        """List all registered pipelines."""
        return list(self.pipeline_registry.keys())
    
    def get_pipeline_result(self, name: str) -> Optional[PipelineResult]:
        """Get the result of a pipeline run."""
        return self.pipeline_results.get(name)
    
    # =========================================================================
    # Batch Processing Methods
    # =========================================================================
    
    def create_batch_job(self, name: str, queries: List[str], parallel: bool = False) -> BatchJob:
        """
        Create a new batch processing job.
        
        Args:
            name: Job name
            queries: List of queries to process
            parallel: Run queries in parallel
        
        Returns:
            BatchJob object
        """
        job = BatchJob(
            name=name,
            queries=queries,
            parallel=parallel,
            max_workers=min(4, len(queries)) if parallel else 1
        )
        self.batch_jobs[name] = job
        logger.info(f"Created batch job: {name} ({len(queries)} queries)")
        return job
    
    def run_batch_job(self, name: str, **kwargs) -> BatchJob:
        """
        Run a batch job.
        
        Args:
            name: Job name
            **kwargs: Additional arguments for query processing
        
        Returns:
            Updated BatchJob with results
        """
        if name not in self.batch_jobs:
            raise ValueError(f"Batch job '{name}' not found")
        
        job = self.batch_jobs[name]
        job.status = "running"
        job.progress = 0
        job.results = []
        
        start_time = time.time()
        
        try:
            if job.parallel and job.max_workers > 1:
                # Run in parallel
                from concurrent.futures import ThreadPoolExecutor, as_completed
                
                with ThreadPoolExecutor(max_workers=job.max_workers) as executor:
                    futures = {
                        executor.submit(self.orchestrator.query, query, **kwargs): i 
                        for i, query in enumerate(job.queries)
                    }
                    
                    for future in as_completed(futures):
                        i = futures[future]
                        try:
                            result = future.result()
                            job.results.append(result)
                            job.progress += 1
                        except Exception as e:
                            job.results.append({"error": str(e), "query": job.queries[i]})
                            job.progress += 1
            else:
                # Run sequentially
                for query in job.queries:
                    try:
                        result = self.orchestrator.query(query, **kwargs)
                        job.results.append(result)
                        job.progress += 1
                    except Exception as e:
                        job.results.append({"error": str(e), "query": query})
                        job.progress += 1
            
            job.status = "completed"
            logger.info(f"Batch job '{name}' completed: {job.progress}/{len(job.queries)} queries, {time.time() - start_time:.1f}s")
            
        except Exception as e:
            job.status = "failed"
            job.results.append({"error": str(e)})
            logger.error(f"Batch job '{name}' failed: {e}")
        
        return job
    
    def get_batch_job(self, name: str) -> Optional[BatchJob]:
        """Get a batch job by name."""
        return self.batch_jobs.get(name)
    
    def list_batch_jobs(self) -> List[str]:
        """List all batch jobs."""
        return list(self.batch_jobs.keys())
    
    # =========================================================================
    # Scheduled Task Methods
    # =========================================================================
    
    def add_scheduled_task(
        self,
        name: str,
        action: str,
        parameters: Dict[str, Any],
        schedule: str = "daily"
    ) -> ScheduledTask:
        """
        Add a new scheduled task.
        
        Args:
            name: Task name
            action: Action to perform (pipeline, self_optimize, etc.)
            parameters: Parameters for the action
            schedule: Schedule string ("hourly", "daily", "interval:N", or cron-like)
        
        Returns:
            ScheduledTask object
        """
        task = ScheduledTask(
            name=name,
            action=action,
            parameters=parameters,
            schedule=schedule,
            enabled=True
        )
        
        # Calculate next run time
        task.next_run = self._calculate_next_run(schedule)
        
        self.scheduled_tasks[name] = task
        logger.info(f"Added scheduled task: {name} (next run: {task.next_run})")
        return task
    
    def _calculate_next_run(self, schedule: str) -> datetime:
        """Calculate the next run time based on schedule."""
        now = datetime.now()
        
        if schedule == "hourly":
            # Next hour
            return now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        elif schedule == "daily":
            # Tomorrow at midnight
            return now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        elif schedule.startswith("interval:"):
            try:
                seconds = int(schedule[9:])
                return now + timedelta(seconds=seconds)
            except ValueError:
                return now + timedelta(hours=1)
        else:
            # Try to parse as cron-like (simplified)
            # For now, default to hourly
            return now + timedelta(hours=1)
        
        return now
    
    def run_scheduled_task(self, task: ScheduledTask) -> Dict[str, Any]:
        """
        Run a scheduled task.
        
        Args:
            task: ScheduledTask to run
        
        Returns:
            Dict with run results
        """
        task.last_run = datetime.now()
        task.run_count += 1
        
        result = {
            "task": task.name,
            "action": task.action,
            "start_time": task.last_run.isoformat(),
            "end_time": None,
            "status": "completed",
            "output": None,
            "error": None
        }
        
        try:
            start_time = time.time()
            
            if task.action == "self_optimize":
                output = self.optimizer.run_self_optimization_cycle()
            elif task.action == "pipeline":
                pipeline_name = task.parameters.get("pipeline")
                if pipeline_name:
                    output = self.run_pipeline(pipeline_name)
                else:
                    output = self.run_pipeline(task.parameters.get("steps", []))
            elif task.action == "batch":
                job = self.create_batch_job(
                    name=f"scheduled_{task.name}_{task.run_count}",
                    queries=task.parameters.get("queries", []),
                    parallel=task.parameters.get("parallel", False)
                )
                output = self.run_batch_job(job.name)
            else:
                # Try to run as a generic action
                if hasattr(self, task.action):
                    method = getattr(self, task.action)
                    output = method(**task.parameters)
                else:
                    raise ValueError(f"Unknown scheduled action: {task.action}")
            
            result["output"] = output
            result["end_time"] = datetime.now().isoformat()
            result["duration"] = time.time() - start_time
            
            logger.info(f"Scheduled task '{task.name}' completed in {result['duration']:.1f}s")
            
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            result["end_time"] = datetime.now().isoformat()
            logger.error(f"Scheduled task '{task.name}' failed: {e}")
        
        # Calculate next run
        task.next_run = self._calculate_next_run(task.schedule)
        
        return result
    
    def _scheduler_loop(self) -> None:
        """Main loop for the scheduler thread."""
        logger.info("Scheduler started")
        
        while self.scheduler_running:
            try:
                now = datetime.now()
                
                # Check all tasks
                for name, task in self.scheduled_tasks.items():
                    if not task.enabled:
                        continue
                    
                    if task.next_run and task.next_run <= now:
                        logger.info(f"Running scheduled task: {name}")
                        self.run_scheduled_task(task)
                
                # Sleep for a minute
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)
        
        logger.info("Scheduler stopped")
    
    def start_scheduler(self) -> None:
        """Start the scheduler thread."""
        if self.scheduler_running:
            logger.warning("Scheduler is already running")
            return
        
        self.scheduler_running = True
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            name="AutomationScheduler",
            daemon=True
        )
        self.scheduler_thread.start()
        logger.info("Scheduler started in background thread")
    
    def stop_scheduler(self) -> None:
        """Stop the scheduler thread."""
        self.scheduler_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
            self.scheduler_thread = None
        logger.info("Scheduler stopped")
    
    def list_scheduled_tasks(self) -> List[str]:
        """List all scheduled tasks."""
        return list(self.scheduled_tasks.keys())
    
    def get_scheduled_task(self, name: str) -> Optional[ScheduledTask]:
        """Get a scheduled task by name."""
        return self.scheduled_tasks.get(name)
    
    # =========================================================================
    # Autonomous Optimization Methods
    # =========================================================================
    
    def run_self_optimization(self, **kwargs) -> Any:
        """Run a self-optimization cycle."""
        return self.optimizer.run_self_optimization_cycle()
    
    def start_continuous_optimization(self, interval: int = 3600) -> None:
        """Start continuous self-optimization."""
        def optimization_loop():
            while self.running:
                try:
                    logger.info("Running self-optimization cycle...")
                    self.optimizer.run_self_optimization_cycle()
                    logger.info(f"Next optimization in {interval}s...")
                    time.sleep(interval)
                except Exception as e:
                    logger.error(f"Optimization error: {e}")
                    time.sleep(60)
        
        self.optimization_thread = threading.Thread(
            target=optimization_loop,
            name="ContinuousOptimization",
            daemon=True
        )
        self.optimization_thread.start()
        logger.info(f"Continuous optimization started (interval: {interval}s)")
    
    def stop_continuous_optimization(self) -> None:
        """Stop continuous optimization."""
        self.running = False
        logger.info("Continuous optimization stopped")
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health."""
        return {
            "orchestrator": self.orchestrator.get_status(),
            "optimizer": self.optimizer.get_system_health(),
            "uptime": (datetime.now() - self.start_time).total_seconds()
        }
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def shutdown(self) -> None:
        """Gracefully shutdown all components."""
        logger.info("Shutting down AutomationController...")
        
        self.running = False
        self.stop_scheduler()
        self.stop_continuous_optimization()
        self.optimizer.stop()
        
        logger.info("AutomationController shutdown complete")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get automation statistics."""
        return {
            "pipelines_registered": len(self.pipeline_registry),
            "pipelines_run": len(self.pipeline_results),
            "batch_jobs": len(self.batch_jobs),
            "scheduled_tasks": len(self.scheduled_tasks),
            "optimization_cycles": len(self.optimizer.optimization_log),
            "uptime": (datetime.now() - self.start_time).total_seconds()
        }


# =============================================================================
# Pre-built Pipelines
# =============================================================================

class PrebuiltPipelines:
    """Collection of pre-built automation pipelines."""
    
    @staticmethod
    def get_pipeline(name: str) -> List[Dict[str, Any]]:
        """Get a pre-built pipeline by name."""
        pipelines = {
            "full_optimization": [
                {"action": "status", "name": "initial_status"},
                {"action": "self_optimize", "name": "self_optimize"},
                {"action": "status", "name": "final_status"},
            ],
            "domain_training": [
                {"action": "log", "parameters": {"message": "Starting domain training"}},
                {"action": "finetune", "parameters": {"name": "custom", "domain": "custom"}},
                {"action": "evaluate", "parameters": {"model": "models/custom.cact"}},
                {"action": "log", "parameters": {"message": "Domain training complete"}},
            ],
            "batch_evaluation": [
                {"action": "log", "parameters": {"message": "Starting batch evaluation"}},
                {"action": "batch", "parameters": {"queries": ["test query 1", "test query 2"]}},
                {"action": "log", "parameters": {"message": "Batch evaluation complete"}},
            ],
            "health_check": [
                {"action": "status"},
                {"action": "log", "parameters": {"message": "System status checked"}},
            ],
            "closed_loop": [
                {"action": "log", "parameters": {"message": "Starting closed-loop optimization"}},
                {"action": "closed_loop", "parameters": {
                    "domain": "weather",
                    "tools": [],  # Would be filled with actual tools
                    "test_data": "datasets/weather_test.jsonl",
                    "max_iterations": 5
                }},
                {"action": "log", "parameters": {"message": "Closed-loop optimization complete"}},
            ]
        }
        
        if name not in pipelines:
            raise ValueError(f"Unknown pipeline: {name}. Available: {list(pipelines.keys())}")
        
        return pipelines[name]


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """CLI entry point for automation."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="1st Agent Automation Controller - Automate fine-tuning and optimization"
    )
    
    # General options
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Start interactive mode"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show system status"
    )
    
    # Query options
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="Run a single query"
    )
    
    # Pipeline options
    parser.add_argument(
        "--pipeline", "-p",
        type=str,
        help="Run a registered pipeline"
    )
    parser.add_argument(
        "--list-pipelines",
        action="store_true",
        help="List all registered pipelines"
    )
    
    # Batch options
    parser.add_argument(
        "--batch", "-b",
        type=str,
        help="Run a batch job"
    )
    parser.add_argument(
        "--create-batch",
        type=str,
        nargs=2,
        metavar=("NAME", "QUERY_FILE"),
        help="Create a batch job from a file containing queries (one per line)"
    )
    
    # Optimization options
    parser.add_argument(
        "--optimize",
        action="store_true",
        help="Run a self-optimization cycle"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuous optimization"
    )
    
    # Scheduler options
    parser.add_argument(
        "--start-scheduler",
        action="store_true",
        help="Start the scheduler"
    )
    parser.add_argument(
        "--stop-scheduler",
        action="store_true",
        help="Stop the scheduler"
    )
    parser.add_argument(
        "--list-tasks",
        action="store_true",
        help="List scheduled tasks"
    )
    
    args = parser.parse_args()
    
    controller = AutomationController()
    
    if args.interactive:
        print("\n=== 1st Agent Automation (Interactive Mode) ===")
        print("Commands:")
        print("  query <text>          - Run a query")
        print("  pipeline <name>      - Run a pipeline")
        print("  batch <name>         - Run a batch job")
        print("  optimize            - Run self-optimization")
        print("  status              - Show system status")
        print("  pipelines           - List pipelines")
        print("  batches             - List batch jobs")
        print("  tasks               - List scheduled tasks")
        print("  start-scheduler     - Start scheduler")
        print("  stop-scheduler      - Stop scheduler")
        print("  quit                - Exit")
        
        while True:
            try:
                command = input("\n> ").strip()
                
                if not command:
                    continue
                
                parts = command.split()
                cmd = parts[0].lower()
                args_list = parts[1:]
                
                if cmd in ['quit', 'exit', 'q']:
                    print("Goodbye!")
                    controller.shutdown()
                    break
                
                elif cmd == 'query':
                    query = ' '.join(args_list)
                    result = controller.query(query)
                    print(f"\n[{result.domain}] {result.answer}")
                
                elif cmd == 'pipeline':
                    pipeline_name = args_list[0] if args_list else None
                    if not pipeline_name:
                        print("Usage: pipeline <name>")
                        continue
                    result = controller.run_pipeline(pipeline_name)
                    print(f"Pipeline {pipeline_name}: {result.steps_completed}/{result.steps_completed + result.steps_failed} steps")
                
                elif cmd == 'batch':
                    job_name = args_list[0] if args_list else None
                    if not job_name:
                        print("Usage: batch <name>")
                        continue
                    job = controller.get_batch_job(job_name)
                    if job:
                        result = controller.run_batch_job(job_name)
                        print(f"Batch job {job_name}: {result.progress}/{len(result.queries)} queries")
                    else:
                        print(f"Batch job '{job_name}' not found")
                
                elif cmd == 'optimize':
                    report = controller.run_self_optimization()
                    print(f"\nOptimization: {report.weaknesses_detected} weaknesses, {report.improvements_applied} improvements")
                
                elif cmd == 'status':
                    health = controller.get_system_health()
                    stats = controller.get_stats()
                    print(f"\n=== System Status ===")
                    print(f"Pipelines: {stats['pipelines_registered']}")
                    print(f"Batch jobs: {stats['batch_jobs']}")
                    print(f"Scheduled tasks: {stats['scheduled_tasks']}")
                    print(f"Optimization cycles: {stats['optimization_cycles']}")
                    print(f"Uptime: {stats['uptime']:.1f}s")
                    
                    print(f"\n=== Health ===")
                    print(f"Status: {health['optimizer']['status']}")
                    print(f"Health score: {health['optimizer']['health_score']:.1f}")
                
                elif cmd == 'pipelines':
                    pipelines = controller.list_pipelines()
                    print(f"\nRegistered pipelines: {pipelines}")
                
                elif cmd == 'batches':
                    batches = controller.list_batch_jobs()
                    print(f"\nBatch jobs: {batches}")
                
                elif cmd == 'tasks':
                    tasks = controller.list_scheduled_tasks()
                    print(f"\nScheduled tasks: {tasks}")
                
                elif cmd == 'start-scheduler':
                    controller.start_scheduler()
                    print("Scheduler started")
                
                elif cmd == 'stop-scheduler':
                    controller.stop_scheduler()
                    print("Scheduler stopped")
                
                else:
                    print(f"Unknown command: {cmd}")
                    
            except KeyboardInterrupt:
                print("\nGoodbye!")
                controller.shutdown()
                break
            except Exception as e:
                print(f"Error: {e}")
    
    elif args.status:
        controller = AutomationController()
        health = controller.get_system_health()
        stats = controller.get_stats()
        
        print("\n=== System Status ===")
        print(f"Pipelines registered: {stats['pipelines_registered']}")
        print(f"Batch jobs: {stats['batch_jobs']}")
        print(f"Scheduled tasks: {stats['scheduled_tasks']}")
        print(f"Optimization cycles: {stats['optimization_cycles']}")
        print(f"Uptime: {stats['uptime']:.1f}s")
        
        print(f"\n=== Health ===")
        print(f"Status: {health['optimizer']['status']}")
        print(f"Health score: {health['optimizer']['health_score']:.1f}")
        print(f"Issues: {len(health['optimizer']['issues'])}")
        
        for issue in health['optimizer']['issues']:
            print(f"  - {issue}")
    
    elif args.query:
        controller = AutomationController()
        result = controller.query(args.query)
        print(f"\nQuery: {result.query}")
        print(f"Domain: {result.domain}")
        print(f"Answer:\n{result.answer}")
    
    elif args.pipeline:
        controller = AutomationController()
        # Register pre-built pipelines
        for name in PrebuiltPipelines.get_pipeline.keys():
            try:
                steps = PrebuiltPipelines.get_pipeline(name)
                controller.register_pipeline(name, steps)
            except:
                pass
        
        result = controller.run_pipeline(args.pipeline)
        print(f"Pipeline {args.pipeline}:")
        print(f"  Success: {result.success}")
        print(f"  Steps completed: {result.steps_completed}")
        print(f"  Steps failed: {result.steps_failed}")
        print(f"  Duration: {result.total_duration:.1f}s")
    
    elif args.list_pipelines:
        controller = AutomationController()
        pipelines = controller.list_pipelines()
        print("\nRegistered pipelines:")
        for p in pipelines:
            print(f"  - {p}")
    
    elif args.batch:
        controller = AutomationController()
        job = controller.get_batch_job(args.batch)
        if job:
            result = controller.run_batch_job(args.batch)
            print(f"Batch job {args.batch}:")
            print(f"  Status: {result.status}")
            print(f"  Progress: {result.progress}/{len(result.queries)}")
        else:
            print(f"Batch job '{args.batch}' not found")
    
    elif args.create_batch:
        name, query_file = args.create_batch
        with open(query_file, 'r') as f:
            queries = [line.strip() for line in f if line.strip()]
        
        controller = AutomationController()
        job = controller.create_batch_job(name, queries)
        print(f"Created batch job '{name}' with {len(queries)} queries")
    
    elif args.optimize:
        controller = AutomationController()
        report = controller.run_self_optimization()
        print(f"\nSelf-Optimization Report:")
        print(f"  Duration: {report.duration:.1f}s")
        print(f"  Weaknesses detected: {report.weaknesses_detected}")
        print(f"  Improvements applied: {report.improvements_applied}")
        print(f"  Overall impact: {report.overall_impact:.1%}")
        
        if report.changes_made:
            print(f"\n  Changes made:")
            for change in report.changes_made:
                print(f"    - {change}")
    
    elif args.continuous:
        controller = AutomationController()
        print("Starting continuous optimization (Ctrl+C to stop)...")
        controller.start_continuous_optimization()
        
        # Keep running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            controller.stop_continuous_optimization()
            print("\nContinuous optimization stopped")
    
    elif args.start_scheduler:
        controller = AutomationController()
        controller.start_scheduler()
        print("Scheduler started in background")
    
    elif args.stop_scheduler:
        controller = AutomationController()
        controller.stop_scheduler()
        print("Scheduler stopped")
    
    elif args.list_tasks:
        controller = AutomationController()
        tasks = controller.list_scheduled_tasks()
        print("\nScheduled tasks:")
        for t in tasks:
            task = controller.get_scheduled_task(t)
            print(f"  - {t}: {task.schedule} (next: {task.next_run})")
    
    else:
        parser.print_help()


# =============================================================================
# Signal Handling
# =============================================================================

def handle_signals(controller: AutomationController):
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        controller.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


if __name__ == "__main__":
    main()
