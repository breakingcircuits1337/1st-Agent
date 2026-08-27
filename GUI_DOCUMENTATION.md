# GUI Documentation - 1st Agent Framework

## Overview

The **GUI Dashboard** provides a comprehensive interface for monitoring and controlling the 1st Agent autonomous multi-agent system. It offers real-time insights into system performance, agent status, optimization progress, and self-modification activities.

## Features

### 1. **Overview Tab**
- **System Status**: Visual indicator (color-coded) of system state
  - Green: Running
  - Yellow: Idle
  - Red: Stopped
  - Blue: Optimizing
  
- **Stat Cards**: Key metrics at a glance
  - Active Agents
  - Models Loaded
  - Queries Processed Today
  - Optimization Cycles Completed
  - Average Reward Score
  - Pending Changes

### 2. **Agents Tab**
- **Agent List**: Table view of all registered agents with:
  - Agent ID
  - Status (Active/Inactive)
  - Type
  - Domain
  - Capabilities
  - Model Path

- **Agent Details Panel**: Click an agent to view:
  - Full metadata
  - Configuration
  - Performance metrics
  - Last heartbeat

- **Toolbar Actions**:
  - Refresh: Update agent list
  - Start All: Start all agents
  - Stop All: Stop all agents

### 3. **Metrics Tab**
- **Performance Metrics**: Real-time values for:
  - Accuracy
  - Precision
  - Recall
  - F1 Score
  - Average Latency (ms)
  - Queries per Second

- **Reward Signal History Chart**: Visual representation of reward signal trends over time
  - Shows improvement/decline patterns
  - Helps identify optimization effectiveness

### 4. **Optimization Tab**
- **Status Indicator**: Current optimization state
- **Progress Bar**: Visual progress of ongoing optimization
- **Optimization History Table**:
  - ID
  - Timestamp
  - Type (Full Cycle, Partial, Targeted)
  - Duration
  - Improvement Percentage
  - Status

- **Controls**:
  - Run Optimization: Trigger immediate optimization cycle
  - Stop Optimization: Halt current optimization
  - Clear History: Remove optimization history

### 5. **Self-Modification Tab**
- **Status Indicator**: Current self-modification state
- **Pending Changes Table**: List of code changes requiring review:
  - Change ID
  - Type (bug_fix, performance, refactor, etc.)
  - Risk Level (LOW, MEDIUM, HIGH, CRITICAL)
  - File Path
  - Lines Affected
  - Timestamp

- **Change Review**:
  - Click a change to view the full diff
  - **View Diff**: Show the code changes
  - **Approve**: Apply the change to the system
  - **Reject**: Discard the change
  - **Refresh**: Update the changes list

- **Diff Viewer**: Syntax-highlighted display of:
  - Lines removed (red)
  - Lines added (green)
  - Context around changes

### 6. **Fine-Tuning Tab**
- **Model List**: Table of available fine-tuned models:
  - Model Name
  - Type (Needle)
  - Domain
  - Size (MB)
  - Created Date
  - Status

- **Fine-Tune Controls**: Form for creating new models:
  - Model Name (required)
  - Domain (required)
  - Number of Training Samples
  - Number of Epochs
  - Create Model: Start fine-tuning process
  - Evaluate: Test model performance
  - Delete: Remove model
  - Refresh: Update model list

- **Progress**: Progress bar and status for ongoing fine-tuning

### 7. **Logs Tab**
- **Real-time Log Display**: Scrollable text area showing:
  - System events
  - Agent activities
  - Optimization progress
  - Errors and warnings

- **Log Controls**:
  - Level Filter: Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  - Refresh: Update logs
  - Clear: Clear the log display

- **Auto-scroll**: New logs automatically scroll into view

### 8. **Feedback Tab**
- **Feedback Form**: Submit user feedback:
  - Subject
  - Type (Bug, Improvement, Question, Praise)
  - Message
  - Submit button

- **Rating System**: Rate system performance (1-5 stars) for:
  - Response Quality
  - Speed
  - Reliability
  - Ease of Use

- **Feedback History**: Table of previously submitted feedback

### 9. **Controls Tab**
- **System Control**:
  - Start System
  - Stop System
  - Restart System

- **System Status**:
  - Uptime
  - Memory Usage
  - CPU Usage

- **Configuration**: Toggle settings for:
  - Auto-Optimize
  - Auto Fine-Tune
  - Auto Self-Modify
  - Require Human Approval
  - Backup Before Changes
  - Save Configuration button

- **Emergency Controls** (with warnings):
  - Stop All Agents
  - Rollback All Changes
  - Reset System

## Installation

### Dependencies

The GUI requires:
- Python 3.7+
- tkinter (usually included with Python)
- psutil (for system monitoring): `pip install psutil`

### Optional Dependencies

For full functionality:
- All dependencies from the main framework
- cactus-needle for model operations

## Usage

### Quick Start

```bash
# Launch the GUI
python launch_gui.py

# Launch with simple mode (no system dependencies)
python launch_gui.py --simple

# Launch with light theme
python launch_gui.py --light

# Launch with debug logging
python launch_gui.py --debug
```

### Programmatic Usage

```python
# Import and run dashboard
from gui.dashboard import run_dashboard

# Run with default settings
run_dashboard()

# Run with system integration
from closed_loop_system import get_closed_loop_system

system = get_closed_loop_system()
run_dashboard(system)

# Run simple dashboard (no GUI dependencies)
run_dashboard(simple=True)
```

### Module Usage

Use individual GUI modules without the full dashboard:

```python
# System monitoring
from gui.monitor import get_monitor

monitor = get_monitor(interval=5.0)
monitor.start()

# Get system info
info = monitor.get_system_info()
print(info)

# Get current metrics
metrics = monitor.get_current_metrics()
print(f"CPU: {metrics.cpu_usage}%, Memory: {metrics.memory_usage}%")

monitor.stop()
```

```python
# Control panel
from gui.controls import get_control_panel

panel = get_control_panel()

# Execute commands
panel.start_system()
panel.stop_system()
panel.start_optimization()

# Get command history
history = panel.get_command_history()
for cmd in history:
    print(f"{cmd.command}: {cmd.message}")
```

```python
# Feedback management
from gui.feedback import get_feedback_manager
from gui.feedback import FeedbackType

manager = get_feedback_manager(user="john_doe")

# Submit feedback
fb_id = manager.submit_feedback(
    feedback_type=FeedbackType.BUG,
    subject="Dashboard crash",
    message="The dashboard crashes when I click the optimization tab.",
    priority=8
)

# Submit rating
manager.submit_rating("Response Quality", 4, "Generally good")

# Get statistics
stats = manager.get_statistics()
print(f"Average rating: {stats['avg_rating']:.2f}")
```

## Architecture

### Module Structure

```
gui/
├── __init__.py          # Package exports with graceful fallbacks
├── dashboard.py         # Main dashboard with all tabs
├── monitor.py           # System monitoring
├── controls.py          # Control panel for system operations
└── feedback.py          # Feedback and rating management
```

### Class Hierarchy

```
AgentDashboard (tk.Tk)
├── Config
│   ├── title
│   ├── width/height
│   ├── theme (dark/light)
│   └── fonts
├── StatusColors
│   └── COLORS dict (status -> color)
├── Widgets
│   ├── notebook (tabs)
│   ├── overview_tab
│   ├── agents_tab
│   ├── metrics_tab
│   ├── optimization_tab
│   ├── self_modification_tab
│   ├── finetune_tab
│   ├── logs_tab
│   └── feedback_tab
└── Background Thread
    └── Auto-refresh every N seconds

SystemMonitor
├── Metrics Collection
│   ├── CPU usage
│   ├── Memory usage
│   ├── Disk usage
│   ├── Network I/O
│   └── Process info
├── Health Checks
│   ├── CPU status
│   ├── Memory status
│   ├── Disk status
│   └── Alert generation
└── History
    ├── Metrics history
    └── Health check history

ControlPanel
├── Commands
│   ├── System commands (start, stop, restart)
│   ├── Agent commands (start, stop, create, delete)
│   └── Optimization commands (start, stop, pause)
├── Self-Modification
│   ├── Approve change
│   ├── Reject change
│   └── Rollback all
├── Emergency Controls
│   ├── Stop all agents
│   ├── Rollback all changes
│   └── Reset system
└── Configuration
    └── Get/set system configuration

FeedbackManager
├── Feedback
│   ├── Submit
│   ├── List
│   ├── Update status
│   └── Delete
└── Ratings
    ├── Submit
    ├── List
    └── Statistics
```

## Theming

### Dark Theme (Default)
- Background: Dark gray (#2D2D2D)
- Text: Light gray (#E0E0E0)
- Accent: Blue (#2196F3)
- Success: Green (#4CAF50)
- Warning: Yellow (#FFC107)
- Error: Red (#F44336)

### Light Theme
- Uses default Tkinter theme
- Clean, professional appearance

## Status Indicators

### System Status Colors
- **Running**: Green (#4CAF50)
- **Stopped**: Red (#F44336)
- **Idle**: Yellow (#FFC107)
- **Optimizing**: Blue (#2196F3)
- **Evaluating**: Purple (#9C27B0)
- **Applying**: Orange (#FF5722)
- **Error**: Red (#F44336)

### Risk Level Colors
- **Low**: Green (#4CAF50)
- **Medium**: Yellow (#FFC107)
- **High**: Orange (#FF5722)
- **Critical**: Red (#F44336)

## Alerting

The system monitor automatically generates alerts when:
- CPU usage > 90% (CRITICAL)
- CPU usage > 75% (WARNING)
- Memory usage > 90% (CRITICAL)
- Memory usage > 80% (WARNING)
- Disk usage > 90% (CRITICAL)
- Disk usage > 80% (WARNING)

Alerts are:
1. Logged to the console
2. Displayed in the logs tab
3. Can trigger notifications (future feature)

## Configuration

### Dashboard Configuration

```python
from gui.dashboard import DashboardConfig

config = DashboardConfig()
config.title = "My AI System"
config.width = 1600
config.height = 1000
config.refresh_interval = 1000  # 1 second
config.theme = "dark"  # or "light"
```

### System Monitor Configuration

```python
from gui.monitor import get_monitor

monitor = get_monitor(interval=5.0)  # Update every 5 seconds
```

## Workflow Examples

### Example 1: Monitoring System Performance

1. Launch the GUI: `python launch_gui.py`
2. Navigate to **Metrics** tab
3. Observe real-time performance metrics
4. Check the **Reward Signal History** chart for trends

### Example 2: Managing Agents

1. Navigate to **Agents** tab
2. View list of all agents and their status
3. Select an agent to see detailed information
4. Use toolbar buttons to start/stop all agents

### Example 3: Reviewing Self-Modifications

1. Navigate to **Self-Modification** tab
2. View list of pending changes
3. Select a change to see the diff
4. Click **Approve** to apply the change
5. Click **Reject** to discard the change

### Example 4: Creating Fine-Tuned Models

1. Navigate to **Fine-Tuning** tab
2. Fill in model details:
   - Model Name: "weather_expert"
   - Domain: "weather"
   - Samples: 500
   - Epochs: 15
3. Click **Create Model**
4. Monitor progress in the progress bar

### Example 5: Emergency Stop

1. Navigate to **Controls** tab
2. Click **Emergency Stop** button
3. Confirm the action
4. System will immediately:
   - Stop all agents
   - Stop the system
   - Stop optimization

## Keyboard Shortcuts

- **Ctrl+C**: Copy selected text
- **Ctrl+A**: Select all text
- **Delete**: Delete selected items
- **F5**: Refresh current tab
- **Esc**: Close dialogs

## Troubleshooting

### Common Issues

**Issue: Dashboard won't start**
- Check that tkinter is installed
- On Ubuntu: `sudo apt-get install python3-tk`
- On CentOS: `sudo yum install python3-tkinter`

**Issue: System metrics not updating**
- Install psutil: `pip install psutil`
- Check that you have permission to access system info

**Issue: Changes not appearing in Self-Modification tab**
- Ensure the system is running
- Check that self-modifier is enabled
- Verify that changes meet the risk threshold

**Issue: Models not appearing in Fine-Tuning tab**
- Check that model files exist in the models/ directory
- Verify file permissions
- Refresh the model list

### Debug Mode

Enable debug logging for detailed information:

```bash
python launch_gui.py --debug
```

This will:
- Log all system events to console
- Save logs to `dashboard.log`
- Show detailed error messages

## Performance

- **Refresh Interval**: Configurable (default: 2 seconds)
- **Memory Usage**: ~50-100MB
- **CPU Usage**: <5% when idle, <20% during updates
- **Startup Time**: 1-3 seconds

## Customization

### Adding Custom Tabs

```python
from gui.dashboard import AgentDashboard

class CustomDashboard(AgentDashboard):
    def _create_widgets(self):
        super()._create_widgets()
        # Add custom tab
        self._create_custom_tab()
    
    def _create_custom_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Custom", compound=tk.LEFT)
        # Add custom widgets to frame
```

### Adding Custom Metrics

```python
from gui.monitor import get_monitor

monitor = get_monitor()

# Add custom metric collection
def custom_metrics_callback(metrics, health_checks):
    # Process metrics
    custom_metric = calculate_custom_metric()
    # Store or display

monitor.on_metrics_update(custom_metrics_callback)
```

## Security

- **No Authentication**: The GUI is designed for local use only
- **File Access**: Only accesses files within the project directory
- **Command Execution**: All commands are validated before execution
- **No Network Access**: The GUI does not make external network calls by default

## Future Features

- **Web Interface**: Browser-based dashboard using Flask/FastAPI
- **Remote Monitoring**: Monitor systems on other machines
- **Notifications**: Email/Slack alerts for important events
- **Custom Dashboards**: Save and load dashboard layouts
- **Export Data**: Export metrics and logs to CSV/JSON
- **Multi-User**: User accounts with different permissions
- **Audit Log**: Track all user actions in the GUI

## API Reference

### dashboard.py

#### AgentDashboard
- `AgentDashboard(system=None, config=None)`: Create dashboard
- `start()`: Start the dashboard
- `stop()`: Stop the dashboard
- `mainloop()`: Run the main loop
- `get_config()`: Get dashboard configuration
- `set_config(config)`: Set dashboard configuration

#### SimpleDashboard
- `SimpleDashboard()`: Create simple dashboard
- `run()`: Run the dashboard

#### run_dashboard(system=None, simple=False)
- Run the appropriate dashboard

### monitor.py

#### SystemMonitor
- `SystemMonitor(interval=5.0)`: Create monitor
- `start()`: Start monitoring
- `stop()`: Stop monitoring
- `collect_metrics()`: Collect metrics manually
- `run_health_checks(metrics)`: Run health checks
- `get_current_metrics()`: Get latest metrics
- `get_metrics_history(count=10)`: Get metrics history
- `get_health_history(count=10)`: Get health check history
- `get_average_metrics(count=10)`: Get average metrics
- `get_system_info()`: Get system information
- `get_status()`: Get monitor status
- `on_metrics_update(callback)`: Register callback

#### get_monitor(interval=5.0)
- Get or create global monitor

### controls.py

#### ControlPanel
- `ControlPanel(system=None)`: Create control panel
- `execute_command(command, *args, **kwargs)`: Execute a command
- `start_system()`: Start the system
- `stop_system()`: Stop the system
- `restart_system()`: Restart the system
- `start_agent(agent_id)`: Start an agent
- `stop_agent(agent_id)`: Stop an agent
- `start_all_agents()`: Start all agents
- `stop_all_agents()`: Stop all agents
- `start_optimization()`: Start optimization
- `stop_optimization()`: Stop optimization
- `approve_change(change_id)`: Approve a change
- `reject_change(change_id)`: Reject a change
- `rollback_all_changes()`: Rollback all changes
- `emergency_stop()`: Emergency stop
- `reset_system()`: Reset system
- `get_config()`: Get configuration
- `set_config(config)`: Set configuration
- `get_command_history(count=10)`: Get command history
- `get_status()`: Get panel status
- `add_listener(listener)`: Add event listener
- `remove_listener(listener)`: Remove event listener

#### get_control_panel(system=None)
- Get or create global control panel

### feedback.py

#### FeedbackManager
- `FeedbackManager(storage_path="feedback.json", user="anonymous")`: Create manager
- `submit_feedback(feedback_type, subject, message, priority=0)`: Submit feedback
- `submit_rating(category, score, comments="")`: Submit rating
- `submit_suggestion(subject, message, priority=5)`: Submit suggestion
- `get_feedback(feedback_id)`: Get feedback by ID
- `list_feedback(feedback_type=None, status=None)`: List feedback
- `get_statistics()`: Get feedback statistics
- `update_feedback_status(feedback_id, status, resolution="")`: Update status
- `delete_feedback(feedback_id)`: Delete feedback
- `clear_all_feedback()`: Clear all feedback
- `get_feedback_trends()`: Get feedback trends

#### get_feedback_manager(user="anonymous")
- Get or create global feedback manager

## License

All GUI components are licensed under Apache 2.0, consistent with the rest of the framework.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues or questions:
1. Check this documentation
2. Check the logs (dashboard.log)
3. Run in debug mode for more details
4. Create an issue in the repository
