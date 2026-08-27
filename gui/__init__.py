"""
GUI Package - Dashboard for 1st Agent Framework

This package provides a comprehensive GUI for:
- Monitoring system status and metrics
- Controlling agents and operations
- Reviewing and approving self-modification changes
- Tracking optimization progress
- Viewing performance history

Main Components:
- AgentDashboard: Main dashboard window with all tabs
- SystemMonitor: Real-time system health monitoring
- ControlPanel: Central control for system operations
- FeedbackManager: User feedback and ratings collection

Usage:
    # Run the full dashboard
    from gui.dashboard import run_dashboard
    run_dashboard()
    
    # Or run with system integration
    from closed_loop_system import get_closed_loop_system
    from gui.dashboard import run_dashboard
    
    system = get_closed_loop_system()
    run_dashboard(system)
    
    # Or use individual modules without GUI
    from gui.monitor import get_monitor
    from gui.controls import get_control_panel
    from gui.feedback import get_feedback_manager
"""

# Try to import all modules, but handle missing dependencies gracefully
try:
    from .dashboard import AgentDashboard, SimpleDashboard, run_dashboard, DashboardConfig, StatusColors
    _HAS_DASHBOARD = True
except ImportError as e:
    _HAS_DASHBOARD = False
    # tkinter or other GUI dependencies missing

try:
    from .monitor import SystemMonitor, HealthStatus, SystemMetrics, HealthCheck, get_monitor
    _HAS_MONITOR = True
except ImportError:
    _HAS_MONITOR = False

try:
    from .controls import ControlPanel, ControlCommand, AgentCommand, OptimizationCommand, ControlResult, get_control_panel, CommandExecutor
    _HAS_CONTROLS = True
except ImportError:
    _HAS_CONTROLS = False

try:
    from .feedback import FeedbackManager, Feedback, FeedbackType, FeedbackStatus, Rating, get_feedback_manager, FeedbackGUI
    _HAS_FEEDBACK = True
except ImportError:
    _HAS_FEEDBACK = False

# Build __all__ based on what's available
__all__ = []

if _HAS_DASHBOARD:
    __all__.extend([
        "AgentDashboard",
        "SimpleDashboard", 
        "run_dashboard",
        "DashboardConfig",
        "StatusColors"
    ])

if _HAS_MONITOR:
    __all__.extend([
        "SystemMonitor",
        "HealthStatus",
        "SystemMetrics", 
        "HealthCheck",
        "get_monitor"
    ])

if _HAS_CONTROLS:
    __all__.extend([
        "ControlPanel",
        "ControlCommand",
        "AgentCommand",
        "OptimizationCommand",
        "ControlResult",
        "get_control_panel",
        "CommandExecutor"
    ])

if _HAS_FEEDBACK:
    __all__.extend([
        "FeedbackManager",
        "Feedback",
        "FeedbackType",
        "FeedbackStatus",
        "Rating",
        "get_feedback_manager",
        "FeedbackGUI"
    ])

__version__ = "1.0.0"
