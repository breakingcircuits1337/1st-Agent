"""
Closed-Loop System Integration

This module integrates all components of the 1st Agent framework into a unified
closed-loop system:

1. Communication Layer - Message passing between agents
2. Dual-Model Architecture - Researcher + Production models
3. Fine-Tune Factory - Automated model creation and optimization
4. Evaluation Agent - Testing and reward signal generation
5. Self-Optimizer - Autonomous system improvement
6. Self-Modification - Code-level autonomous improvements
7. Automation Controller - Pipeline orchestration

Architecture:
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CLOSED-LOOP SYSTEM                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────┐  │
│  │   Communication      │    │     Dual-Model       │    │   Fine-Tune      │  │
│  │      Layer          │    │     Architecture     │    │     Factory      │  │
│  │ - Message passing    │    │ - Researcher Model   │    │ - Model creation │  │
│  │ - Pub/Sub           │    │ - Production Model   │    │ - LoRA fine-tune │  │
│  │ - Request/Response   │    │ - Query routing      │    │ - .cact building │  │
│  └─────────────────────┘    └─────────────────────┘    └─────────────────┘  │
│                           │              │                     │              │
│                           ▼              ▼                     ▼              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         EVALUATION LAYER                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │ Metrics     │  │ Reward      │  │ Performance  │  │ Model       │    │   │
│  │  │ Calculation │  │ Generation  │  │ Tracking    │  │ Comparison  │    │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                           │                                              │
│                           ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      SELF-OPTIMIZATION LAYER                           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │ Self-       │  │ Self-        │  │ Automation   │  │ Closed-Loop  │    │   │
│  │  │ Modifier    │  │ Optimizer    │  │ Controller   │  │ Integration │    │   │
│  │  │ - Code      │  │ - System     │  │ - Pipelines  │  │ - Orchestrate│    │   │
│  │  │   changes   │  │   monitoring │  │ - Scheduling │  │   all        │    │   │
│  │  │ - Risk      │  │ - Weakness   │  │ - Batch jobs │  │   components │    │   │
│  │  │   assess.   │  │   detection  │  │             │  │             │    │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
      ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
      │ Specialized │       │ Needle      │       │ Closed-Loop │
      │ Agents      │       │ Models      │       │ Feedback    │
      └─────────────┘       └─────────────┘       └─────────────┘
"""

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# Import all components
from communication_layer import (
    CommunicationLayer,
    AgentInfo,
    Message,
    MessageType,
    AgentCommunicator,
    create_agent_info
)
from self_modification import SelfModifier, CodeChange, RiskLevel, ChangeStatus
from evaluation_agent import EvaluationAgent
from finetune_factory import FineTuneFactory
from automation import AutomationController
from orchestrator import Orchestrator

logger = logging.getLogger(__name__)


class ClosedLoopStatus(Enum):
    """Status of the closed-loop system."""
    IDLE = "idle"
    ANALYZING = "analyzing"
    OPTIMIZING = "optimizing"
    EVALUATING = "evaluating"
    APPLYING = "applying"
    MONITORING = "monitoring"
    ERROR = "error"
    AUTO_MODE = "auto_mode"  # 24/7 continuous self-improvement mode
    AUTO_MODE_PAUSED = "auto_mode_paused"  # AUTO mode temporarily paused


@dataclass
class ClosedLoopConfig:
    """Configuration for the closed-loop system."""
    # AUTO MODE - 24/7 continuous self-improvement
    auto_mode: bool = False  # Master switch for 24/7 autonomous operation
    auto_mode_interval: float = 300.0  # 5 minutes between cycles in auto mode
    
    # Self-optimization settings
    auto_optimize: bool = True
    optimization_interval: float = 3600.0  # 1 hour
    max_optimizations_per_cycle: int = 5
    
    # Self-modification settings
    auto_modify: bool = False  # Safety: disabled by default
    modification_risk_threshold: RiskLevel = RiskLevel.HIGH
    max_modifications_per_cycle: int = 3
    auto_modify_in_auto_mode: bool = True  # Enable auto-apply in AUTO mode
    
    # Evaluation settings
    evaluation_interval: float = 600.0  # 10 minutes
    metrics_threshold: float = 0.8  # Minimum acceptable metric score
    
    # Fine-tuning settings
    auto_finetune: bool = True
    finetune_iterations: int = 3
    
    # Communication settings
    enable_communication: bool = True
    agent_heartbeat_interval: float = 60.0
    
    # Safety settings
    require_human_approval: bool = True  # Require approval for high-risk changes
    backup_before_modification: bool = True
    max_rollback_attempts: int = 3
    
    # AUTO mode safety overrides
    auto_mode_allow_high_risk: bool = False  # Allow HIGH risk changes in AUTO mode
    auto_mode_max_changes_per_hour: int = 20  # Rate limit for auto mode


@dataclass
class ClosedLoopMetrics:
    """Metrics for the closed-loop system."""
    cycle_count: int = 0
    optimizations_applied: int = 0
    modifications_applied: int = 0
    models_created: int = 0
    evaluations_run: int = 0
    avg_accuracy: float = 0.0
    avg_precision: float = 0.0
    avg_recall: float = 0.0
    avg_f1: float = 0.0
    reward_signal: float = 0.0
    last_cycle_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    
    # AUTO mode specific metrics
    auto_mode_cycles: int = 0
    auto_mode_start_time: Optional[datetime] = None
    auto_mode_changes_applied: int = 0
    auto_mode_improvements: int = 0
    auto_mode_models_created: int = 0
    uptime_seconds: float = 0.0
    consecutive_success_cycles: int = 0
    consecutive_failure_cycles: int = 0


class ClosedLoopSystem:
    """
    Unified closed-loop system that integrates all components.
    
    This system implements a complete feedback loop:
    1. Agents perform tasks
    2. Evaluation Agent measures performance
    3. Reward signals drive optimization
    4. Self-Optimizer detects weaknesses
    5. Self-Modifier generates code improvements
    6. Fine-Tune Factory creates better models
    7. Loop continues autonomously
    
    Usage:
        # Create the closed-loop system
        system = ClosedLoopSystem()
        
        # Start the system
        system.start()
        
        # Run a task
        result = system.run_task("What's the weather in Lagos?")
        
        # Or let it run autonomously
        system.run_autonomous()
        
        # Stop the system
        system.stop()
    """
    
    def __init__(self, config: Optional[ClosedLoopConfig] = None):
        self.config = config or ClosedLoopConfig()
        self._status = ClosedLoopStatus.IDLE
        self._metrics = ClosedLoopMetrics()
        self._lock = threading.RLock()
        
        # AUTO mode tracking
        self._auto_mode_active = False
        self._auto_mode_paused = False
        self._auto_mode_thread: Optional[threading.Thread] = None
        self._auto_mode_start_time: Optional[datetime] = None
        self._changes_this_hour: int = 0
        self._last_hour_reset: datetime = datetime.now()
        
        # Initialize all components
        self._initialize_components()
        
        # Thread control
        self._running = False
        self._threads: List[threading.Thread] = []
        
        logger.info("ClosedLoopSystem initialized")
    
    def _initialize_components(self):
        """Initialize all system components."""
        # Communication layer
        self.comm_layer = CommunicationLayer()
        
        # Orchestrator
        self.orchestrator = Orchestrator(comm_layer=self.comm_layer)
        
        # Fine-tune factory
        self.finetune_factory = FineTuneFactory()
        
        # Evaluation agent
        self.evaluation_agent = EvaluationAgent()
        
        # Self-modifier
        self.self_modifier = SelfModifier(project_root=".")
        
        # Automation controller
        self.automation = AutomationController()
        
        # Register all agents with communication layer
        self._register_agents()
        
        # Set up event handlers
        self._setup_event_handlers()
    
    def _register_agents(self):
        """Register all agents with the communication layer."""
        # Register orchestrator
        orch_info = create_agent_info(
            agent_id="orchestrator",
            name="Orchestrator",
            agent_type="orchestrator",
            domain="coordination",
            capabilities=["query_routing", "agent_management", "system_coordination"]
        )
        self.comm_layer.register_agent(orch_info)
        
        # Register evaluation agent
        eval_info = create_agent_info(
            agent_id="evaluation_agent",
            name="Evaluation Agent",
            agent_type="evaluation",
            domain="metrics",
            capabilities=["testing", "metrics", "reward_signals", "performance_tracking"]
        )
        self.comm_layer.register_agent(eval_info)
        
        # Register self-modifier
        mod_info = create_agent_info(
            agent_id="self_modifier",
            name="Self-Modifier",
            agent_type="self_modification",
            domain="code_improvement",
            capabilities=["code_analysis", "change_generation", "risk_assessment", "code_application"]
        )
        self.comm_layer.register_agent(mod_info)
        
        # Register fine-tune factory
        ft_info = create_agent_info(
            agent_id="finetune_factory",
            name="Fine-Tune Factory",
            agent_type="model_training",
            domain="model_creation",
            capabilities=["data_generation", "finetuning", "model_building", "model_optimization"]
        )
        self.comm_layer.register_agent(ft_info)
        
        logger.info("All agents registered with communication layer")
    
    def _setup_event_handlers(self):
        """Set up event handlers between components."""
        # Connect evaluation results to optimization
        self.evaluation_agent.on_evaluation_complete = self._handle_evaluation_results
        
        # Connect self-modifier to system
        self.self_modifier.change_manager = self._create_enhanced_change_manager()
    
    def start(self):
        """Start the closed-loop system."""
        with self._lock:
            if self._running:
                return
            
            self._running = True
            self._status = ClosedLoopStatus.IDLE
            
            # Start communication layer
            self.comm_layer.start()
            
            # Start autonomous loop if configured
            if self.config.auto_optimize or self.config.auto_modify:
                self._start_autonomous_loop()
            
            logger.info("ClosedLoopSystem started")
    
    def stop(self):
        """Stop the closed-loop system."""
        with self._lock:
            # Disable AUTO mode first
            if self._auto_mode_active:
                self.disable_auto_mode()
            
            self._running = False
            self._status = ClosedLoopStatus.IDLE
            
            # Stop all threads
            for thread in self._threads:
                thread.join(timeout=5)
            self._threads = []
            
            # Stop communication layer
            self.comm_layer.stop()
            
            logger.info("ClosedLoopSystem stopped")
    
    # ==================== AUTO MODE METHODS ====================
    
    def enable_auto_mode(self, allow_high_risk: bool = False) -> bool:
        """
        Enable 24/7 AUTO mode for continuous self-improvement.
        
        In AUTO mode, the system runs continuous cycles of:
        1. Task execution and evaluation
        2. Self-optimization
        3. Self-modification (with auto-apply)
        4. Fine-tuning
        5. Model creation and testing
        
        Args:
            allow_high_risk: If True, allows HIGH and CRITICAL risk changes to be auto-applied
                           WARNING: This can modify critical system code automatically
        
        Returns:
            bool: True if AUTO mode was successfully enabled
        """
        with self._lock:
            if self._auto_mode_active:
                logger.warning("AUTO mode is already active")
                return False
            
            if not self._running:
                self.start()
            
            # Update config for AUTO mode
            self.config.auto_mode = True
            self.config.auto_optimize = True
            self.config.auto_finetune = True
            self.config.auto_modify = self.config.auto_modify_in_auto_mode
            self.config.auto_mode_allow_high_risk = allow_high_risk
            
            # Reset rate limiting
            self._changes_this_hour = 0
            self._last_hour_reset = datetime.now()
            
            # Start AUTO mode loop
            self._start_auto_mode_loop()
            
            self._auto_mode_active = True
            self._auto_mode_paused = False
            self._auto_mode_start_time = datetime.now()
            self._metrics.auto_mode_start_time = datetime.now()
            self._status = ClosedLoopStatus.AUTO_MODE
            
            logger.info("✅ AUTO MODE ENABLED - 24/7 continuous self-improvement active")
            logger.warning(f"High risk changes auto-apply: {'ENABLED' if allow_high_risk else 'DISABLED'}")
            
            # Publish AUTO mode status
            self.comm_layer.publish("system.auto_mode", {
                "status": "enabled",
                "timestamp": datetime.now().isoformat(),
                "high_risk_allowed": allow_high_risk
            })
            
            return True
    
    def disable_auto_mode(self) -> bool:
        """
        Disable 24/7 AUTO mode.
        
        Returns:
            bool: True if AUTO mode was successfully disabled
        """
        with self._lock:
            if not self._auto_mode_active:
                logger.warning("AUTO mode is not active")
                return False
            
            # Stop AUTO mode loop
            self._auto_mode_active = False
            self._status = ClosedLoopStatus.IDLE
            self.config.auto_mode = False
            
            # Restore safety defaults
            self.config.auto_modify = False
            self.config.require_human_approval = True
            
            # Wait for AUTO mode thread to finish current cycle
            if self._auto_mode_thread:
                self._auto_mode_thread.join(timeout=10)
                self._auto_mode_thread = None
            
            # Calculate uptime
            if self._auto_mode_start_time:
                uptime = (datetime.now() - self._auto_mode_start_time).total_seconds()
                self._metrics.uptime_seconds += uptime
            
            logger.info(f"❌ AUTO MODE DISABLED - Ran for {self._metrics.uptime_seconds:.0f} seconds")
            logger.info(f"AUTO mode stats: {self._metrics.auto_mode_cycles} cycles, "
                       f"{self._metrics.auto_mode_changes_applied} changes, "
                       f"{self._metrics.auto_mode_models_created} models")
            
            # Publish AUTO mode status
            self.comm_layer.publish("system.auto_mode", {
                "status": "disabled",
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": self._metrics.uptime_seconds,
                "cycles_completed": self._metrics.auto_mode_cycles,
                "changes_applied": self._metrics.auto_mode_changes_applied
            })
            
            return True
    
    def toggle_auto_mode(self, allow_high_risk: bool = False) -> bool:
        """
        Toggle AUTO mode on/off.
        
        Args:
            allow_high_risk: Only applies when enabling - allows high risk changes
        
        Returns:
            bool: New state (True = enabled, False = disabled)
        """
        if self._auto_mode_active:
            return self.disable_auto_mode()
        else:
            return self.enable_auto_mode(allow_high_risk)
    
    def pause_auto_mode(self) -> bool:
        """Pause AUTO mode temporarily without disabling it."""
        with self._lock:
            if not self._auto_mode_active:
                logger.warning("AUTO mode is not active")
                return False
            
            self._auto_mode_paused = True
            self._status = ClosedLoopStatus.AUTO_MODE_PAUSED
            logger.info("⏸️  AUTO MODE PAUSED")
            
            self.comm_layer.publish("system.auto_mode", {
                "status": "paused",
                "timestamp": datetime.now().isoformat()
            })
            
            return True
    
    def resume_auto_mode(self) -> bool:
        """Resume AUTO mode after pause."""
        with self._lock:
            if not self._auto_mode_active:
                logger.warning("AUTO mode is not active")
                return False
            
            self._auto_mode_paused = False
            self._status = ClosedLoopStatus.AUTO_MODE
            logger.info("▶️  AUTO MODE RESUMED")
            
            self.comm_layer.publish("system.auto_mode", {
                "status": "resumed",
                "timestamp": datetime.now().isoformat()
            })
            
            return True
    
    def is_auto_mode_active(self) -> bool:
        """Check if AUTO mode is currently active."""
        return self._auto_mode_active and not self._auto_mode_paused
    
    def is_auto_mode_paused(self) -> bool:
        """Check if AUTO mode is paused."""
        return self._auto_mode_active and self._auto_mode_paused
    
    def _start_autonomous_loop(self):
        """Start the autonomous optimization loop."""
        loop_thread = threading.Thread(
            target=self._autonomous_loop,
            daemon=True
        )
        loop_thread.start()
        self._threads.append(loop_thread)
    
    def _start_auto_mode_loop(self):
        """Start the 24/7 AUTO mode loop."""
        auto_thread = threading.Thread(
            target=self._auto_mode_loop,
            daemon=True
        )
        auto_thread.start()
        self._auto_mode_thread = auto_thread
        self._threads.append(auto_thread)
    
    def _autonomous_loop(self):
        """Main autonomous loop for continuous improvement."""
        logger.info("Autonomous loop started")
        
        while self._running:
            try:
                # Run evaluation cycle
                if self.config.auto_optimize:
                    self._run_optimization_cycle()
                
                # Run self-modification cycle
                if self.config.auto_modify:
                    self._run_modification_cycle()
                
                # Sleep for a while
                import time
                sleep_time = min(
                    self.config.optimization_interval,
                    self.config.evaluation_interval
                )
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in autonomous loop: {e}")
                import time
                time.sleep(60)  # Wait before retrying
        
        logger.info("Autonomous loop stopped")
    
    def _auto_mode_loop(self):
        """
        24/7 AUTO mode loop for continuous self-improvement.
        
        This is the heart of AUTO mode - runs continuous cycles of:
        1. Evaluation and metrics collection
        2. Self-optimization
        3. Self-modification with auto-apply
        4. Fine-tuning
        5. Model improvement
        
        Each cycle runs every auto_mode_interval seconds.
        """
        logger.info("🔥 AUTO MODE LOOP STARTED - 24/7 continuous self-improvement")
        
        while self._auto_mode_active and self._running:
            cycle_start = datetime.now()
            self._metrics.auto_mode_cycles += 1
            
            try:
                # Check if paused
                if self._auto_mode_paused:
                    import time
                    time.sleep(5)
                    continue
                
                # Reset hourly rate limit if new hour
                self._check_hourly_rate_limit()
                
                logger.info(f"=== AUTO MODE CYCLE #{self._metrics.auto_mode_cycles} ===")
                
                # Step 1: Run evaluation cycle
                logger.info("AUTO: Running evaluation...")
                self._run_evaluation_cycle()
                
                # Step 2: Check reward signal and trigger optimization if needed
                if self._metrics.reward_signal < self.config.metrics_threshold:
                    logger.info("AUTO: Reward below threshold, triggering optimization...")
                    self._run_optimization_cycle()
                else:
                    # Still run periodic optimization
                    if self._metrics.auto_mode_cycles % 3 == 0:
                        logger.info("AUTO: Periodic optimization...")
                        self._run_optimization_cycle()
                
                # Step 3: Run self-modification cycle (the key feature of AUTO mode)
                logger.info("AUTO: Running self-modification...")
                self._run_auto_modification_cycle()
                
                # Step 4: Run fine-tuning cycle
                logger.info("AUTO: Running fine-tuning...")
                self._run_auto_finetune_cycle()
                
                # Update consecutive cycle counters
                self._metrics.consecutive_success_cycles += 1
                self._metrics.consecutive_failure_cycles = 0
                
                # Log cycle completion
                cycle_time = (datetime.now() - cycle_start).total_seconds()
                logger.info(f"AUTO: Cycle #{self._metrics.auto_mode_cycles} completed in {cycle_time:.1f}s")
                logger.info(f"AUTO: Metrics - Reward: {self._metrics.reward_signal:.3f}, "
                           f"Accuracy: {self._metrics.avg_accuracy:.3f}")
                
                # Publish cycle completion
                self.comm_layer.publish("auto_mode.cycle_complete", {
                    "cycle": self._metrics.auto_mode_cycles,
                    "timestamp": datetime.now().isoformat(),
                    "duration_seconds": cycle_time,
                    "reward": self._metrics.reward_signal,
                    "changes_applied": self._metrics.auto_mode_changes_applied,
                    "models_created": self._metrics.auto_mode_models_created
                })
                
            except Exception as e:
                logger.error(f"AUTO MODE ERROR in cycle #{self._metrics.auto_mode_cycles}: {e}")
                self._metrics.errors.append(f"AUTO cycle {self._metrics.auto_mode_cycles}: {e}")
                self._metrics.consecutive_success_cycles = 0
                self._metrics.consecutive_failure_cycles += 1
                
                # Publish error
                self.comm_layer.publish("auto_mode.error", {
                    "cycle": self._metrics.auto_mode_cycles,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                
                # Wait before retrying
                import time
                time.sleep(30)
            
            # Sleep until next cycle
            import time
            cycle_end = datetime.now()
            elapsed = (cycle_end - cycle_start).total_seconds()
            sleep_time = max(0, self.config.auto_mode_interval - elapsed)
            
            if sleep_time > 0:
                logger.info(f"AUTO: Sleeping for {sleep_time:.1f}s until next cycle...")
                time.sleep(sleep_time)
        
        logger.info("🔥 AUTO MODE LOOP STOPPED")
    
    def _run_auto_modification_cycle(self):
        """
        Run self-modification cycle in AUTO mode with auto-apply.
        
        This is the key difference from regular mode - changes are auto-applied
        after validation, within rate limits.
        """
        self._status = ClosedLoopStatus.APPLYING
        
        try:
            # Run code analysis and improvement
            results = self.self_modifier.improve(
                focus_areas=["performance", "code_quality", "bug_fixes"],
                max_changes=self.config.max_modifications_per_cycle,
                auto_validate=True,
                auto_apply=False  # We'll handle application manually with rate limiting
            )
            
            if not results or not results.changes:
                logger.info("AUTO: No modifications proposed")
                return
            
            # Apply changes with rate limiting and risk checking
            applied_count = 0
            for change_dict in results.changes:
                change_id = change_dict.get("change_id")
                if not change_id:
                    continue
                
                change = self.self_modifier.get_change(change_id)
                if not change:
                    continue
                
                # Check if we've hit hourly rate limit
                if self._changes_this_hour >= self.config.auto_mode_max_changes_per_hour:
                    logger.info(f"AUTO: Hit hourly rate limit ({self.config.auto_mode_max_changes_per_hour} changes/hour)")
                    break
                
                # Validate change
                if change.status != ChangeStatus.VALIDATED:
                    logger.info(f"AUTO: Change {change_id} not validated, skipping")
                    continue
                
                # Check risk level
                risk_allowed = (self.config.auto_mode_allow_high_risk or 
                              change.risk_level.value <= RiskLevel.MEDIUM.value)
                
                if not risk_allowed:
                    logger.info(f"AUTO: Change {change_id} risk level {change.risk_level} too high for auto-apply")
                    self._notify_human_review(change)
                    continue
                
                # Apply the change
                logger.info(f"AUTO: Applying change {change_id} - {change.description}")
                success = self.self_modifier.apply_change(change_id)
                
                if success:
                    self._metrics.auto_mode_changes_applied += 1
                    self._metrics.modifications_applied += 1
                    self._changes_this_hour += 1
                    applied_count += 1
                    
                    logger.info(f"✅ AUTO: Change applied successfully")
                    
                    # Publish change applied event
                    self.comm_layer.publish("auto_mode.change_applied", {
                        "change_id": change_id,
                        "description": change.description,
                        "risk_level": change.risk_level.value,
                        "file": change.file_path,
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    logger.warning(f"⚠️  AUTO: Change {change_id} failed to apply")
            
            if applied_count > 0:
                self._metrics.auto_mode_improvements += applied_count
                logger.info(f"AUTO: Applied {applied_count} improvements this cycle")
            
            self._metrics.cycle_count += 1
            
        except Exception as e:
            logger.error(f"AUTO modification cycle failed: {e}")
            self._metrics.errors.append(str(e))
        finally:
            self._status = ClosedLoopStatus.AUTO_MODE
    
    def _run_auto_finetune_cycle(self):
        """
        Run fine-tuning cycle in AUTO mode.
        
        Automatically creates and evaluates new models based on performance.
        """
        try:
            # Check if we should create a new model
            # Create a model every 5 cycles or if reward is low
            should_create = (self._metrics.auto_mode_cycles % 5 == 0 or 
                           self._metrics.reward_signal < self.config.metrics_threshold * 0.9)
            
            if should_create:
                # Generate a name based on cycle and timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                model_name = f"auto_model_cycle{self._metrics.auto_mode_cycles}_{timestamp}"
                
                # Determine domain based on recent queries
                domain = self._determine_domain_for_finetuning()
                
                logger.info(f"AUTO: Creating fine-tuned model '{model_name}' for domain '{domain}'")
                
                # Create the model
                try:
                    model_path = self.finetune_factory.create_model(
                        name=model_name,
                        domain=domain,
                        num_samples=100  # Smaller for AUTO mode
                    )
                    
                    if model_path:
                        self._metrics.auto_mode_models_created += 1
                        self._metrics.models_created += 1
                        
                        # Evaluate the new model
                        eval_results = self.evaluate_model(model_path)
                        reward = eval_results.get("reward", 0.0)
                        
                        logger.info(f"AUTO: New model '{model_name}' created with reward: {reward:.3f}")
                        
                        # Publish model created event
                        self.comm_layer.publish("auto_mode.model_created", {
                            "model_name": model_name,
                            "model_path": model_path,
                            "domain": domain,
                            "reward": reward,
                            "timestamp": datetime.now().isoformat()
                        })
                        
                        # If model is good, promote it
                        if reward > self._metrics.reward_signal:
                            logger.info(f"AUTO: New model performs better! Promoting...")
                            # TODO: Implement model promotion logic
                except Exception as e:
                    logger.error(f"AUTO: Model creation failed: {e}")
            
        except Exception as e:
            logger.error(f"AUTO finetune cycle failed: {e}")
    
    def _determine_domain_for_finetuning(self) -> str:
        """Determine the best domain for fine-tuning based on recent activity."""
        # TODO: Implement intelligent domain selection based on query patterns
        # For now, use a simple rotation
        domains = ["general", "weather", "news", "database", "coding"]
        return domains[self._metrics.auto_mode_cycles % len(domains)]
    
    def _check_hourly_rate_limit(self):
        """Reset hourly change counter if a new hour has started."""
        now = datetime.now()
        if now.hour != self._last_hour_reset.hour:
            self._changes_this_hour = 0
            self._last_hour_reset = now
    
    def _run_optimization_cycle(self):
        """Run a self-optimization cycle."""
        self._status = ClosedLoopStatus.OPTIMIZING
        
        try:
            # Run system monitoring
            self.orchestrator.monitor_system()
            
            # Check for weaknesses
            weaknesses = self.orchestrator.detect_weaknesses()
            
            if weaknesses:
                logger.info(f"Detected {len(weaknesses)} weaknesses, starting optimization...")
                
                # Auto-train agents
                self.orchestrator.auto_train_agents(
                    weaknesses=weaknesses,
                    max_iterations=self.config.finetune_iterations
                )
            
            self._metrics.optimizations_applied += 1
            self._metrics.cycle_count += 1
            
        except Exception as e:
            logger.error(f"Optimization cycle failed: {e}")
            self._metrics.errors.append(str(e))
        finally:
            self._status = ClosedLoopStatus.IDLE
    
    def _run_modification_cycle(self):
        """Run a self-modification cycle."""
        self._status = ClosedLoopStatus.APPLYING
        
        try:
            # Run code analysis and improvement
            results = self.self_modifier.improve(
                focus_areas=["performance", "code_quality"],
                max_changes=self.config.max_modifications_per_cycle,
                auto_validate=True,
                auto_apply=False  # Never auto-apply without review
            )
            
            # Apply validated changes
            for change_dict in results.changes:
                change_id = change_dict.get("change_id")
                if change_id:
                    change = self.self_modifier.get_change(change_id)
                    if change and change.status == ChangeStatus.VALIDATED:
                        # Check risk threshold
                        if change.risk_level.value <= self.config.modification_risk_threshold.value:
                            if self.config.require_human_approval:
                                logger.info(f"Change {change_id} ready for review (risk: {change.risk_level})")
                                self._notify_human_review(change)
                            else:
                                self.self_modifier.apply_change(change_id)
                                self._metrics.modifications_applied += 1
            
            self._metrics.cycle_count += 1
            
        except Exception as e:
            logger.error(f"Modification cycle failed: {e}")
            self._metrics.errors.append(str(e))
        finally:
            self._status = ClosedLoopStatus.IDLE
    
    def _run_evaluation_cycle(self):
        """Run an evaluation cycle."""
        self._status = ClosedLoopStatus.EVALUATING
        
        try:
            # Run comprehensive evaluation
            results = self.evaluation_agent.run_comprehensive_evaluation()
            
            # Update metrics
            if results:
                self._metrics.avg_accuracy = results.get("accuracy", 0.0)
                self._metrics.avg_precision = results.get("precision", 0.0)
                self._metrics.avg_recall = results.get("recall", 0.0)
                self._metrics.avg_f1 = results.get("f1", 0.0)
                self._metrics.reward_signal = results.get("reward", 0.0)
                self._metrics.evaluations_run += 1
            
        except Exception as e:
            logger.error(f"Evaluation cycle failed: {e}")
            self._metrics.errors.append(str(e))
        finally:
            self._status = ClosedLoopStatus.IDLE
    
    def _handle_evaluation_results(self, results: Dict[str, Any]):
        """Handle results from evaluation."""
        logger.info(f"Evaluation results received: {results}")
        
        # Update metrics
        self._metrics.avg_accuracy = results.get("accuracy", self._metrics.avg_accuracy)
        self._metrics.reward_signal = results.get("reward", self._metrics.reward_signal)
        
        # Check if we meet thresholds
        reward = results.get("reward", 0.0)
        if reward < self.config.metrics_threshold:
            logger.warning(f"Reward signal below threshold: {reward} < {self.config.metrics_threshold}")
            # Trigger optimization
            self._run_optimization_cycle()
    
    def _notify_human_review(self, change: CodeChange):
        """Notify that a change requires human review."""
        # Publish to review topic
        self.comm_layer.publish(
            "human_review.required",
            {
                "change_id": change.change_id,
                "description": change.description,
                "risk_level": change.risk_level.value,
                "file": change.file_path,
                "lines": f"{change.line_start}-{change.line_end}",
                "timestamp": change.created_at
            }
        )
        
        logger.info(f"Human review requested for change {change.change_id}")
    
    def _create_enhanced_change_manager(self):
        """Create a change manager with enhanced capabilities."""
        from self_modification.change_manager import ChangeManager
        
        class EnhancedChangeManager(ChangeManager):
            """Change manager with closed-loop integration."""
            
            def validate_change(self, change_id: str, run_tests: bool = True) -> bool:
                """Enhanced validation with evaluation agent."""
                # First do normal validation
                if not super().validate_change(change_id, run_tests):
                    return False
                
                # Then run performance evaluation
                change = self.get_change(change_id)
                if change:
                    # Evaluate the change
                    eval_results = self._evaluate_change(change)
                    if not eval_results.get("passed", True):
                        logger.warning(f"Change {change_id} failed performance evaluation")
                        return False
                
                return True
            
            def _evaluate_change(self, change: CodeChange) -> Dict[str, Any]:
                """Evaluate a change using the evaluation agent."""
                # This would be implemented to run specific tests
                # for the changed functionality
                return {"passed": True, "score": 1.0}
        
        return EnhancedChangeManager(project_root=".")
    
    def run_task(self, query: str, agent_id: Optional[str] = None) -> Any:
        """Run a task through the system."""
        # Use orchestrator to handle the query
        return self.orchestrator.query(query)
    
    def run_autonomous(self):
        """Run the system in fully autonomous mode."""
        self.start()
        
        # Keep running until stopped
        try:
            import time
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the system."""
        uptime = 0.0
        if self._auto_mode_start_time:
            uptime = (datetime.now() - self._auto_mode_start_time).total_seconds()
        
        return {
            "status": self._status.value,
            "running": self._running,
            "auto_mode": {
                "active": self._auto_mode_active,
                "paused": self._auto_mode_paused,
                "uptime_seconds": uptime + self._metrics.uptime_seconds,
                "cycles": self._metrics.auto_mode_cycles,
                "changes_applied": self._metrics.auto_mode_changes_applied,
                "improvements": self._metrics.auto_mode_improvements,
                "models_created": self._metrics.auto_mode_models_created,
                "consecutive_success": self._metrics.consecutive_success_cycles,
                "consecutive_failures": self._metrics.consecutive_failure_cycles
            },
            "metrics": {
                "cycle_count": self._metrics.cycle_count,
                "optimizations_applied": self._metrics.optimizations_applied,
                "modifications_applied": self._metrics.modifications_applied,
                "avg_reward": self._metrics.reward_signal,
                "avg_accuracy": self._metrics.avg_accuracy,
                "errors": len(self._metrics.errors)
            },
            "components": {
                "orchestrator": "active" if self.orchestrator else "inactive",
                "finetune_factory": "active" if self.finetune_factory else "inactive",
                "evaluation_agent": "active" if self.evaluation_agent else "inactive",
                "self_modifier": "active" if self.self_modifier else "inactive",
                "communication_layer": "active" if self.comm_layer else "inactive"
            }
        }
    
    def get_metrics(self) -> ClosedLoopMetrics:
        """Get the current metrics."""
        return self._metrics
    
    def optimize_now(self):
        """Trigger an immediate optimization cycle."""
        self._run_optimization_cycle()
        self._run_evaluation_cycle()
        if self.config.auto_modify:
            self._run_modification_cycle()
    
    def create_finetuned_model(self, name: str, domain: str, 
                              num_samples: int = 200) -> Optional[str]:
        """Create a fine-tuned model."""
        return self.finetune_factory.create_model(
            name=name,
            domain=domain,
            num_samples=num_samples
        )
    
    def evaluate_model(self, model_path: str) -> Dict[str, Any]:
        """Evaluate a model."""
        return self.evaluation_agent.test_model(model_path)
    
    def propose_improvement(self, focus_areas: List[str] = None) -> Dict[str, Any]:
        """Propose code improvements."""
        return self.self_modifier.improve(
            focus_areas=focus_areas,
            max_changes=self.config.max_modifications_per_cycle,
            auto_validate=False,
            auto_apply=False
        )
    
    def apply_improvement(self, change_id: str) -> bool:
        """Apply a proposed improvement."""
        return self.self_modifier.apply_change(change_id)
    
    def rollback_improvement(self, change_id: str) -> bool:
        """Rollback an applied improvement."""
        return self.self_modifier.rollback_change(change_id)
    
    def run_auto_mode(self, allow_high_risk: bool = False):
        """
        Run the system in AUTO mode (24/7 continuous self-improvement).
        
        This is the main entry point for AUTO mode operation.
        
        Args:
            allow_high_risk: Allow automatic application of HIGH/CRITICAL risk changes
        """
        self.enable_auto_mode(allow_high_risk=allow_high_risk)
        
        # Keep running until stopped
        try:
            import time
            while self._running and self._auto_mode_active:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()


class ClosedLoopAgent(AgentCommunicator):
    """
    Agent that participates in the closed-loop system.
    
    This agent can:
    - Receive tasks from the orchestrator
    - Send results back
    - Participate in optimization
    - Report metrics
    """
    
    def __init__(self, agent_id: str, domain: str, 
                 capabilities: List[str],
                 comm_layer: Optional[CommunicationLayer] = None):
        super().__init__(agent_id, comm_layer or comm_layer)
        
        # Register with communication layer
        self.register(create_agent_info(
            agent_id=agent_id,
            name=agent_id.replace("_", " ").title(),
            agent_type="specialized",
            domain=domain,
            capabilities=capabilities
        ))
        
        # Subscribe to relevant topics
        self.subscribe("tasks", self._handle_task)
        self.subscribe("optimization", self._handle_optimization)
        self.subscribe("evaluation", self._handle_evaluation)
    
    def _handle_task(self, message: Message):
        """Handle a task message."""
        task = message.content.get("task")
        task_id = message.content.get("task_id")
        
        if task:
            result = self._process_task(task)
            
            # Send result back
            self.send(
                message.sender_id,
                {
                    "task_id": task_id,
                    "result": result,
                    "status": "completed"
                }
            )
    
    def _handle_optimization(self, message: Message):
        """Handle an optimization message."""
        optimization_type = message.content.get("type")
        
        if optimization_type == "retrain":
            self._retrain(message.content)
        elif optimization_type == "evaluate":
            self._evaluate(message.content)
    
    def _handle_evaluation(self, message: Message):
        """Handle an evaluation message."""
        # Run self-evaluation
        results = self._self_evaluate()
        
        # Send results back
        self.send(
            message.sender_id,
            {
                "agent_id": self.agent_id,
                "metrics": results
            }
        )
    
    def _process_task(self, task: str) -> Any:
        """Process a task. Override in subclasses."""
        return {"result": f"Processed: {task}", "agent": self.agent_id}
    
    def _retrain(self, config: Dict[str, Any]):
        """Retrain the agent. Override in subclasses."""
        logger.info(f"Agent {self.agent_id} retraining...")
    
    def _evaluate(self, config: Dict[str, Any]):
        """Evaluate the agent. Override in subclasses."""
        logger.info(f"Agent {self.agent_id} evaluating...")
    
    def _self_evaluate(self) -> Dict[str, float]:
        """Self-evaluate performance. Override in subclasses."""
        return {"accuracy": 0.8, "confidence": 0.9}


# Global instance
closed_loop_system = None


def get_closed_loop_system(config: Optional[ClosedLoopConfig] = None) -> ClosedLoopSystem:
    """Get or create the global closed-loop system instance."""
    global closed_loop_system
    if closed_loop_system is None:
        closed_loop_system = ClosedLoopSystem(config)
    return closed_loop_system


def run_closed_loop_autonomous(config: Optional[ClosedLoopConfig] = None):
    """Run the closed-loop system in autonomous mode."""
    system = get_closed_loop_system(config)
    system.run_autonomous()


def run_auto_mode(allow_high_risk: bool = False, config: Optional[ClosedLoopConfig] = None):
    """
    Run the system in AUTO mode for 24/7 continuous self-improvement.
    
    This enables all autonomous features:
    - Continuous evaluation
    - Self-optimization
    - Self-modification with auto-apply
    - Fine-tuning
    - Model creation
    
    Args:
        allow_high_risk: Allow automatic application of HIGH/CRITICAL risk changes
        config: Optional configuration overrides
    """
    system = get_closed_loop_system(config)
    system.run_auto_mode(allow_high_risk=allow_high_risk)


if __name__ == "__main__":
    import sys
    
    # Check for AUTO mode flag
    auto_mode = "--auto" in sys.argv or "-a" in sys.argv
    allow_high_risk = "--high-risk" in sys.argv or "-hr" in sys.argv
    
    if auto_mode:
        # Run in AUTO mode
        logger.info("🔥 Starting in AUTO MODE - 24/7 continuous self-improvement")
        if allow_high_risk:
            logger.warning("⚠️  HIGH RISK MODE ENABLED - Changes will auto-apply without review!")
        
        config = ClosedLoopConfig(
            auto_mode=True,
            auto_optimize=True,
            auto_modify_in_auto_mode=True,
            auto_finetune=True,
            auto_mode_interval=300.0,  # 5 minutes between cycles
            auto_mode_allow_high_risk=allow_high_risk,
            auto_mode_max_changes_per_hour=20
        )
        
        run_auto_mode(allow_high_risk=allow_high_risk, config=config)
    else:
        # Create and run the closed-loop system
        logger.info("Starting Closed-Loop System...")
        
        # Create config
        config = ClosedLoopConfig(
            auto_optimize=True,
            auto_modify=False,  # Keep disabled for safety
            auto_finetune=True,
            optimization_interval=300.0,  # 5 minutes
            evaluation_interval=120.0  # 2 minutes
        )
        
        # Create and start system
        system = get_closed_loop_system(config)
        system.start()
        
        # Run a test task
        result = system.run_task("What's the weather in Lagos?")
        logger.info(f"Task result: {result}")
        
        # Get status
        status = system.get_status()
        logger.info(f"System status: {status}")
        
        # Keep running for a while
        try:
            import time
            time.sleep(10)
        except KeyboardInterrupt:
            system.stop()
        
        system.stop()
        logger.info("Closed-Loop System stopped")
