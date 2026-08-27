#!/usr/bin/env python3
"""
1st Agent Framework - GUI Launcher

This script launches the GUI dashboard for monitoring and controlling
the autonomous multi-agent system.

Features:
- Real-time system monitoring
- Agent management and control
- Performance metrics visualization
- Self-modification review and approval
- Optimization progress tracking
- Interactive feedback system
- Emergency controls

Usage:
    python launch_gui.py              # Launch with default settings
    python launch_gui.py --simple     # Launch simple dashboard (no dependencies)
    python launch_gui.py --dark       # Launch with dark theme
    python launch_gui.py --port 8080  # Launch with web interface (future feature)

Dependencies:
    - tkinter (usually included with Python)
    - psutil (for system monitoring) - pip install psutil
"""

import argparse
import logging
import sys
import threading
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)


def setup_logging(level=logging.INFO):
    """Set up logging configuration."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('dashboard.log')
        ]
    )


def check_dependencies():
    """Check if required dependencies are installed."""
    missing = []
    
    try:
        import tkinter
    except ImportError:
        missing.append("tkinter")
    
    try:
        import psutil
    except ImportError:
        missing.append("psutil")
    
    return missing


def run_full_gui(simple=False, dark_theme=True):
    """Run the full GUI dashboard."""
    try:
        # Import GUI modules
        if simple:
            from gui.dashboard import SimpleDashboard
            logger.info("Launching simple dashboard...")
            dashboard = SimpleDashboard()
            dashboard.run()
        else:
            # Try to import system modules
            try:
                from closed_loop_system import get_closed_loop_system, ClosedLoopConfig
                from gui.dashboard import AgentDashboard
                
                # Create system with safe defaults
                config = ClosedLoopConfig(
                    auto_optimize=False,  # Don't auto-start optimization
                    auto_modify=False,    # Don't auto-modify code
                    auto_finetune=False,  # Don't auto-finetune
                    require_human_approval=True
                )
                system = get_closed_loop_system(config)
                
                # Configure dashboard
                from gui.dashboard import DashboardConfig
                dashboard_config = DashboardConfig()
                dashboard_config.theme = "dark" if dark_theme else "light"
                
                # Create and run dashboard
                logger.info("Launching full dashboard with system integration...")
                dashboard = AgentDashboard(system, dashboard_config)
                dashboard.mainloop()
                
            except ImportError as e:
                logger.warning(f"Could not import system modules: {e}")
                logger.info("Falling back to simple dashboard...")
                from gui.dashboard import SimpleDashboard
                dashboard = SimpleDashboard()
                dashboard.run()
                
    except Exception as e:
        logger.error(f"Failed to launch GUI: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="1st Agent Framework - GUI Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python launch_gui.py              # Launch full dashboard
  python launch_gui.py --simple     # Launch simple dashboard
  python launch_gui.py --light      # Launch with light theme
  python launch_gui.py --debug      # Launch with debug logging
        """
    )
    
    parser.add_argument(
        '--simple',
        action='store_true',
        help='Use simple dashboard without system dependencies'
    )
    
    parser.add_argument(
        '--dark',
        action='store_true',
        default=True,
        help='Use dark theme (default)'
    )
    
    parser.add_argument(
        '--light',
        action='store_true',
        help='Use light theme'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        help='Port for web interface (future feature)'
    )
    
    args = parser.parse_args()
    
    # Set theme
    dark_theme = args.dark and not args.light
    
    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(log_level)
    
    # Check dependencies
    missing = check_dependencies()
    if missing:
        if not args.simple:
            logger.warning(f"Missing dependencies: {', '.join(missing)}")
            logger.warning("Falling back to simple dashboard. Install with: pip install " + " ".join(missing))
            args.simple = True
    
    # Launch GUI
    logger.info("Starting 1st Agent GUI Dashboard...")
    
    # Run in a thread to keep the main thread available
    gui_thread = threading.Thread(
        target=run_full_gui,
        args=(args.simple, dark_theme),
        daemon=True
    )
    gui_thread.start()
    
    # Wait for GUI to complete
    gui_thread.join()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
