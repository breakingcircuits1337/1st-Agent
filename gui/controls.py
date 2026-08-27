"""
Control Panel - Provides controls for managing the system.

This module provides:
- System start/stop/restart controls
- Agent management controls
- Optimization controls
- Emergency controls
- Configuration management
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ControlCommand(Enum):
    """System control commands."""
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    PAUSE = "pause"
    RESUME = "resume"


class AgentCommand(Enum):
    """Agent control commands."""
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    PAUSE = "pause"
    RESUME = "resume"
    CREATE = "create"
    DELETE = "delete"


class OptimizationCommand(Enum):
    """Optimization control commands."""
    START = "start"
    STOP = "stop"
    PAUSE = "pause"
    RESUME = "resume"
    RUN_NOW = "run_now"


class AutoModeCommand(Enum):
    """AUTO mode control commands."""
    ENABLE = "enable_auto"
    DISABLE = "disable_auto"
    TOGGLE = "toggle_auto"
    PAUSE = "pause_auto"
    RESUME = "resume_auto"
    STATUS = "auto_status"


@dataclass
class ControlResult:
    """Result of a control operation."""
    success: bool
    command: str
    message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "command": self.command,
            "message": self.message,
            "timestamp": self.timestamp,
            "error": self.error,
            "details": self.details
        }


class ControlPanel:
    """
    Central control panel for managing the 1st Agent system.
    
    This class provides:
    - System-level controls (start, stop, restart)
    - Agent management
    - Optimization controls
    - Emergency stop
    - Configuration management
    - Command history
    """
    
    def __init__(self, system=None):
        self.system = system
        self._command_history: List[ControlResult] = []
        self._lock = threading.RLock()
        self._listeners: List[Callable] = []
        
        logger.info("Control panel initialized")
    
    def execute_command(self, command: str, *args, **kwargs) -> ControlResult:
        """
        Execute a control command.
        
        Args:
            command: The command to execute
            *args: Additional arguments
            **kwargs: Additional keyword arguments
        
        Returns:
            ControlResult with operation result
        """
        command_lower = command.lower()
        
        # Try to match enum commands
        try:
            if command_lower == "start":
                return self.start_system()
            elif command_lower == "stop":
                return self.stop_system()
            elif command_lower == "restart":
                return self.restart_system()
            elif command_lower == "pause":
                return self.pause_system()
            elif command_lower == "resume":
                return self.resume_system()
            
            # AUTO mode commands
            elif command_lower in ["enable_auto", "auto_on", "auto_mode_on"]:
                allow_high_risk = kwargs.get("allow_high_risk", False)
                return self.enable_auto_mode(allow_high_risk=allow_high_risk)
            elif command_lower in ["disable_auto", "auto_off", "auto_mode_off"]:
                return self.disable_auto_mode()
            elif command_lower in ["toggle_auto", "auto_toggle"]:
                allow_high_risk = kwargs.get("allow_high_risk", False)
                return self.toggle_auto_mode(allow_high_risk=allow_high_risk)
            elif command_lower in ["pause_auto", "auto_pause"]:
                return self.pause_auto_mode()
            elif command_lower in ["resume_auto", "auto_resume"]:
                return self.resume_auto_mode()
            elif command_lower == "auto_status":
                return self.get_auto_mode_status()
        except Exception as e:
            return ControlResult(
                success=False,
                command=command,
                message=f"Failed to execute command: {e}",
                error=str(e)
            )
        
        return ControlResult(
            success=False,
            command=command,
            message=f"Unknown command: {command}"
        )
    
    def start_system(self) -> ControlResult:
        """Start the system."""
        with self._lock:
            try:
                if self.system:
                    self.system.start()
                    result = ControlResult(
                        success=True,
                        command="start",
                        message="System started successfully",
                        details={"status": "running"}
                    )
                else:
                    result = ControlResult(
                        success=True,
                        command="start",
                        message="System start command sent (no system attached)"
                    )
                
                self._command_history.append(result)
                self._notify_listeners(result)
                logger.info("System start command executed")
                return result
                
            except Exception as e:
                result = ControlResult(
                    success=False,
                    command="start",
                    message="Failed to start system",
                    error=str(e)
                )
                self._command_history.append(result)
                return result
    
    def stop_system(self) -> ControlResult:
        """Stop the system."""
        with self._lock:
            try:
                if self.system:
                    self.system.stop()
                    result = ControlResult(
                        success=True,
                        command="stop",
                        message="System stopped successfully",
                        details={"status": "stopped"}
                    )
                else:
                    result = ControlResult(
                        success=True,
                        command="stop",
                        message="System stop command sent (no system attached)"
                    )
                
                self._command_history.append(result)
                self._notify_listeners(result)
                logger.info("System stop command executed")
                return result
                
            except Exception as e:
                result = ControlResult(
                    success=False,
                    command="stop",
                    message="Failed to stop system",
                    error=str(e)
                )
                self._command_history.append(result)
                return result
    
    def restart_system(self) -> ControlResult:
        """Restart the system."""
        with self._lock:
            try:
                if self.system:
                    self.system.stop()
                    time.sleep(2)
                    self.system.start()
                    result = ControlResult(
                        success=True,
                        command="restart",
                        message="System restarted successfully",
                        details={"status": "running"}
                    )
                else:
                    result = ControlResult(
                        success=True,
                        command="restart",
                        message="System restart command sent (no system attached)"
                    )
                
                self._command_history.append(result)
                self._notify_listeners(result)
                logger.info("System restart command executed")
                return result
                
            except Exception as e:
                result = ControlResult(
                    success=False,
                    command="restart",
                    message="Failed to restart system",
                    error=str(e)
                )
                self._command_history.append(result)
                return result
    
    def pause_system(self) -> ControlResult:
        """Pause the system."""
        # Pause would suspend non-critical operations
        return ControlResult(
            success=True,
            command="pause",
            message="System pause command sent (not implemented)"
        )
    
    def resume_system(self) -> ControlResult:
        """Resume the system."""
        # Resume would continue paused operations
        return ControlResult(
            success=True,
            command="resume",
            message="System resume command sent (not implemented)"
        )
    
    # Agent controls
    def start_agent(self, agent_id: str) -> ControlResult:
        """Start a specific agent."""
        with self._lock:
            result = ControlResult(
                success=True,
                command="start_agent",
                message=f"Agent {agent_id} start command sent",
                details={"agent_id": agent_id}
            )
            self._command_history.append(result)
            self._notify_listeners(result)
            return result
    
    def stop_agent(self, agent_id: str) -> ControlResult:
        """Stop a specific agent."""
        with self._lock:
            result = ControlResult(
                success=True,
                command="stop_agent",
                message=f"Agent {agent_id} stop command sent",
                details={"agent_id": agent_id}
            )
            self._command_history.append(result)
            self._notify_listeners(result)
            return result
    
    def start_all_agents(self) -> ControlResult:
        """Start all agents."""
        with self._lock:
            result = ControlResult(
                success=True,
                command="start_all_agents",
                message="Start all agents command sent"
            )
            self._command_history.append(result)
            self._notify_listeners(result)
            return result
    
    def stop_all_agents(self) -> ControlResult:
        """Stop all agents."""
        with self._lock:
            result = ControlResult(
                success=True,
                command="stop_all_agents",
                message="Stop all agents command sent"
            )
            self._command_history.append(result)
            self._notify_listeners(result)
            return result
    
    # Optimization controls
    def start_optimization(self) -> ControlResult:
        """Start the optimization process."""
        with self._lock:
            try:
                if self.system:
                    self.system.optimize_now()
                    result = ControlResult(
                        success=True,
                        command="start_optimization",
                        message="Optimization started",
                        details={"status": "optimizing"}
                    )
                else:
                    result = ControlResult(
                        success=True,
                        command="start_optimization",
                        message="Optimization start command sent (no system attached)"
                    )
                
                self._command_history.append(result)
                self._notify_listeners(result)
                logger.info("Optimization start command executed")
                return result
                
            except Exception as e:
                result = ControlResult(
                    success=False,
                    command="start_optimization",
                    message="Failed to start optimization",
                    error=str(e)
                )
                self._command_history.append(result)
                return result
    
    def stop_optimization(self) -> ControlResult:
        """Stop the optimization process."""
        with self._lock:
            result = ControlResult(
                success=True,
                command="stop_optimization",
                message="Optimization stop command sent"
            )
            self._command_history.append(result)
            self._notify_listeners(result)
            return result
    
    def run_optimization_now(self) -> ControlResult:
        """Trigger immediate optimization."""
        return self.start_optimization()
    
    # AUTO mode controls
    def enable_auto_mode(self, allow_high_risk: bool = False) -> ControlResult:
        """Enable 24/7 AUTO mode for continuous self-improvement."""
        with self._lock:
            try:
                if self.system:
                    success = self.system.enable_auto_mode(allow_high_risk=allow_high_risk)
                    result = ControlResult(
                        success=success,
                        command="enable_auto",
                        message="AUTO mode enabled - 24/7 continuous self-improvement active" if success else "Failed to enable AUTO mode",
                        details={
                            "auto_mode": success,
                            "high_risk_allowed": allow_high_risk
                        }
                    )
                else:
                    result = ControlResult(
                        success=False,
                        command="enable_auto",
                        message="No system attached"
                    )
                
                self._command_history.append(result)
                self._notify_listeners(result)
                if result.success:
                    logger.info("AUTO MODE ENABLED via control panel")
                return result
                
            except Exception as e:
                result = ControlResult(
                    success=False,
                    command="enable_auto",
                    message="Failed to enable AUTO mode",
                    error=str(e)
                )
                self._command_history.append(result)
                return result
    
    def disable_auto_mode(self) -> ControlResult:
        """Disable 24/7 AUTO mode."""
        with self._lock:
            try:
                if self.system:
                    success = self.system.disable_auto_mode()
                    result = ControlResult(
                        success=success,
                        command="disable_auto",
                        message="AUTO mode disabled" if success else "Failed to disable AUTO mode"
                    )
                else:
                    result = ControlResult(
                        success=False,
                        command="disable_auto",
                        message="No system attached"
                    )
                
                self._command_history.append(result)
                self._notify_listeners(result)
                if result.success:
                    logger.info("AUTO MODE DISABLED via control panel")
                return result
                
            except Exception as e:
                result = ControlResult(
                    success=False,
                    command="disable_auto",
                    message="Failed to disable AUTO mode",
                    error=str(e)
                )
                self._command_history.append(result)
                return result
    
    def toggle_auto_mode(self, allow_high_risk: bool = False) -> ControlResult:
        """Toggle AUTO mode on/off."""
        with self._lock:
            try:
                if self.system:
                    new_state = self.system.toggle_auto_mode(allow_high_risk=allow_high_risk)
                    status = "enabled" if new_state else "disabled"
                    result = ControlResult(
                        success=True,
                        command="toggle_auto",
                        message=f"AUTO mode {status}",
                        details={"auto_mode": new_state, "high_risk_allowed": allow_high_risk}
                    )
                else:
                    result = ControlResult(
                        success=False,
                        command="toggle_auto",
                        message="No system attached"
                    )
                
                self._command_history.append(result)
                self._notify_listeners(result)
                logger.info(f"AUTO MODE TOGGLED: {status}")
                return result
                
            except Exception as e:
                result = ControlResult(
                    success=False,
                    command="toggle_auto",
                    message="Failed to toggle AUTO mode",
                    error=str(e)
                )
                self._command_history.append(result)
                return result
    
    def pause_auto_mode(self) -> ControlResult:
        """Pause AUTO mode temporarily."""
        with self._lock:
            try:
                if self.system:
                    success = self.system.pause_auto_mode()
                    result = ControlResult(
                        success=success,
                        command="pause_auto",
                        message="AUTO mode paused" if success else "Failed to pause AUTO mode"
                    )
                else:
                    result = ControlResult(
                        success=False,
                        command="pause_auto",
                        message="No system attached"
                    )
                
                self._command_history.append(result)
                self._notify_listeners(result)
                if result.success:
                    logger.info("AUTO MODE PAUSED via control panel")
                return result
                
            except Exception as e:
                result = ControlResult(
                    success=False,
                    command="pause_auto",
                    message="Failed to pause AUTO mode",
                    error=str(e)
                )
                self._command_history.append(result)
                return result
    
    def resume_auto_mode(self) -> ControlResult:
        """Resume AUTO mode after pause."""
        with self._lock:
            try:
                if self.system:
                    success = self.system.resume_auto_mode()
                    result = ControlResult(
                        success=success,
                        command="resume_auto",
                        message="AUTO mode resumed" if success else "Failed to resume AUTO mode"
                    )
                else:
                    result = ControlResult(
                        success=False,
                        command="resume_auto",
                        message="No system attached"
                    )
                
                self._command_history.append(result)
                self._notify_listeners(result)
                if result.success:
                    logger.info("AUTO MODE RESUMED via control panel")
                return result
                
            except Exception as e:
                result = ControlResult(
                    success=False,
                    command="resume_auto",
                    message="Failed to resume AUTO mode",
                    error=str(e)
                )
                self._command_history.append(result)
                return result
    
    def get_auto_mode_status(self) -> ControlResult:
        """Get the current AUTO mode status."""
        with self._lock:
            try:
                if self.system:
                    status = self.system.get_status()
                    auto_status = status.get("auto_mode", {})
                    
                    result = ControlResult(
                        success=True,
                        command="auto_status",
                        message="AUTO mode status retrieved",
                        details={
                            "active": auto_status.get("active", False),
                            "paused": auto_status.get("paused", False),
                            "cycles": auto_status.get("cycles", 0),
                            "uptime_seconds": auto_status.get("uptime_seconds", 0),
                            "changes_applied": auto_status.get("changes_applied", 0),
                            "improvements": auto_status.get("improvements", 0),
                            "models_created": auto_status.get("models_created", 0)
                        }
                    )
                else:
                    result = ControlResult(
                        success=False,
                        command="auto_status",
                        message="No system attached"
                    )
                
                self._command_history.append(result)
                return result
                
            except Exception as e:
                result = ControlResult(
                    success=False,
                    command="auto_status",
                    message="Failed to get AUTO mode status",
                    error=str(e)
                )
                self._command_history.append(result)
                return result
    
    # Self-modification controls
    def approve_change(self, change_id: str) -> ControlResult:
        """Approve a self-modification change."""
        with self._lock:
            try:
                if self.system:
                    success = self.system.apply_improvement(change_id)
                    result = ControlResult(
                        success=success,
                        command="approve_change",
                        message=f"Change {change_id} {'approved' if success else 'failed'}",
                        details={"change_id": change_id}
                    )
                else:
                    result = ControlResult(
                        success=False,
                        command="approve_change",
                        message="No system attached",
                        details={"change_id": change_id}
                    )
                
                self._command_history.append(result)
                self._notify_listeners(result)
                logger.info(f"Change {change_id} approval: {result.success}")
                return result
                
            except Exception as e:
                result = ControlResult(
                    success=False,
                    command="approve_change",
                    message=f"Failed to approve change {change_id}",
                    error=str(e),
                    details={"change_id": change_id}
                )
                self._command_history.append(result)
                return result
    
    def reject_change(self, change_id: str) -> ControlResult:
        """Reject a self-modification change."""
        with self._lock:
            try:
                if self.system:
                    success = self.system.rollback_improvement(change_id)
                    result = ControlResult(
                        success=success,
                        command="reject_change",
                        message=f"Change {change_id} {'rejected' if success else 'failed'}",
                        details={"change_id": change_id}
                    )
                else:
                    result = ControlResult(
                        success=False,
                        command="reject_change",
                        message="No system attached",
                        details={"change_id": change_id}
                    )
                
                self._command_history.append(result)
                self._notify_listeners(result)
                logger.info(f"Change {change_id} rejection: {result.success}")
                return result
                
            except Exception as e:
                result = ControlResult(
                    success=False,
                    command="reject_change",
                    message=f"Failed to reject change {change_id}",
                    error=str(e),
                    details={"change_id": change_id}
                )
                self._command_history.append(result)
                return result
    
    def rollback_all_changes(self) -> ControlResult:
        """Rollback all applied changes."""
        with self._lock:
            try:
                if self.system:
                    count = self.system.self_modifier.rollback_all()
                    result = ControlResult(
                        success=True,
                        command="rollback_all",
                        message=f"Rolled back {count} changes",
                        details={"count": count}
                    )
                else:
                    result = ControlResult(
                        success=False,
                        command="rollback_all",
                        message="No system attached"
                    )
                
                self._command_history.append(result)
                self._notify_listeners(result)
                logger.info(f"Rollback all: {result.message}")
                return result
                
            except Exception as e:
                result = ControlResult(
                    success=False,
                    command="rollback_all",
                    message="Failed to rollback all changes",
                    error=str(e)
                )
                self._command_history.append(result)
                return result
    
    # Emergency controls
    def emergency_stop(self) -> ControlResult:
        """Emergency stop - stop everything immediately."""
        with self._lock:
            try:
                results = []
                
                # Stop all agents
                results.append(self.stop_all_agents())
                
                # Stop system
                results.append(self.stop_system())
                
                # Stop optimization
                results.append(self.stop_optimization())
                
                success = all(r.success for r in results)
                result = ControlResult(
                    success=success,
                    command="emergency_stop",
                    message="Emergency stop executed",
                    details={
                        "results": [r.to_dict() for r in results],
                        "status": "emergency_stopped"
                    }
                )
                
                self._command_history.append(result)
                self._notify_listeners(result)
                logger.warning("EMERGENCY STOP executed")
                return result
                
            except Exception as e:
                result = ControlResult(
                    success=False,
                    command="emergency_stop",
                    message="Emergency stop failed",
                    error=str(e)
                )
                self._command_history.append(result)
                return result
    
    def reset_system(self) -> ControlResult:
        """Reset the entire system."""
        with self._lock:
            try:
                # Stop everything first
                self.emergency_stop()
                
                # Clear system state (implementation depends on system)
                result = ControlResult(
                    success=True,
                    command="reset_system",
                    message="System reset executed",
                    details={"status": "reset"}
                )
                
                self._command_history.append(result)
                self._notify_listeners(result)
                logger.warning("System RESET executed")
                return result
                
            except Exception as e:
                result = ControlResult(
                    success=False,
                    command="reset_system",
                    message="Failed to reset system",
                    error=str(e)
                )
                self._command_history.append(result)
                return result
    
    # Configuration controls
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        if self.system:
            # Return system config if available
            return self.system.config.to_dict() if hasattr(self.system.config, 'to_dict') else {}
        return {}
    
    def set_config(self, config: Dict[str, Any]) -> ControlResult:
        """Set configuration."""
        with self._lock:
            try:
                if self.system and hasattr(self.system, 'config'):
                    # Update system config
                    for key, value in config.items():
                        if hasattr(self.system.config, key):
                            setattr(self.system.config, key, value)
                    
                    result = ControlResult(
                        success=True,
                        command="set_config",
                        message="Configuration updated",
                        details={"config": config}
                    )
                else:
                    result = ControlResult(
                        success=False,
                        command="set_config",
                        message="No system or config attached"
                    )
                
                self._command_history.append(result)
                self._notify_listeners(result)
                return result
                
            except Exception as e:
                result = ControlResult(
                    success=False,
                    command="set_config",
                    message="Failed to set configuration",
                    error=str(e)
                )
                self._command_history.append(result)
                return result
    
    # History and status
    def get_command_history(self, count: int = 10) -> List[ControlResult]:
        """Get recent command history."""
        with self._lock:
            return list(reversed(self._command_history[-count:]))
    
    def get_status(self) -> Dict[str, Any]:
        """Get control panel status."""
        return {
            "commands_executed": len(self._command_history),
            "listeners": len(self._listeners),
            "system_attached": self.system is not None
        }
    
    # Listener management
    def add_listener(self, listener: Callable):
        """Add a listener for control events."""
        with self._lock:
            self._listeners.append(listener)
    
    def remove_listener(self, listener: Callable):
        """Remove a listener."""
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)
    
    def _notify_listeners(self, result: ControlResult):
        """Notify all listeners of a control event."""
        for listener in self._listeners:
            try:
                listener(result)
            except Exception as e:
                logger.error(f"Listener error: {e}")


# Global control panel
_global_control_panel = None


def get_control_panel(system=None) -> ControlPanel:
    """Get or create the global control panel."""
    global _global_control_panel
    if _global_control_panel is None:
        _global_control_panel = ControlPanel(system)
    return _global_control_panel


class CommandExecutor:
    """
    Executes commands from various sources (CLI, GUI, API).
    """
    
    def __init__(self, control_panel: ControlPanel = None):
        self.control_panel = control_panel or get_control_panel()
    
    def execute(self, command: str, *args, **kwargs) -> ControlResult:
        """Execute a command."""
        return self.control_panel.execute_command(command, *args, **kwargs)
    
    def parse_command(self, command_str: str) -> Dict[str, Any]:
        """Parse a command string."""
        parts = command_str.split()
        if not parts:
            return {"command": None, "args": [], "error": "Empty command"}
        
        command = parts[0]
        args = parts[1:]
        
        return {
            "command": command,
            "args": args,
            "raw": command_str
        }


if __name__ == "__main__":
    # Demo usage
    logger.info("Starting control panel demo...")
    
    # Create control panel
    panel = get_control_panel()
    
    # Add a listener
    def log_listener(result):
        print(f"Command executed: {result.command} - {'SUCCESS' if result.success else 'FAILED'}")
    
    panel.add_listener(log_listener)
    
    # Execute commands
    print("\nExecuting commands:")
    
    result1 = panel.start_system()
    print(f"1. Start: {result1.message}")
    
    result2 = panel.stop_system()
    print(f"2. Stop: {result2.message}")
    
    result3 = panel.restart_system()
    print(f"3. Restart: {result3.message}")
    
    result4 = panel.start_optimization()
    print(f"4. Optimize: {result4.message}")
    
    result5 = panel.start_all_agents()
    print(f"5. Start All: {result5.message}")
    
    # Get status
    print("\nControl Panel Status:")
    status = panel.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # Get history
    print("\nCommand History (last 3):")
    for i, result in enumerate(panel.get_command_history(3)):
        print(f"  {i+1}. {result.command}: {'SUCCESS' if result.success else 'FAILED'} - {result.message}")
    
    logger.info("Demo completed")
