# AUTO MODE - 24/7 Continuous Self-Improvement

## Overview

AUTO MODE is a toggleable operating mode that enables **24/7 continuous autonomous self-improvement** for the 1st Agent framework. When enabled, the system automatically:

1. **Evaluates** performance metrics continuously
2. **Optimizes** system configuration and agent behavior
3. **Self-modifies** code with automatic application (within safety limits)
4. **Fine-tunes** models based on reward signals
5. **Creates** new model variants and promotes the best ones
6. **Reports** progress through the communication layer

## Features

### Continuous Improvement Loop

```
AUTO MODE CYCLE (runs every 5 minutes by default):
├── Evaluation Cycle
│   ├── Run comprehensive test suite
│   ├── Calculate metrics (accuracy, precision, recall, F1)
│   └── Generate reward signal (0.0-2.0)
│
├── Optimization Cycle (triggered if reward < threshold)
│   ├── Monitor system performance
│   ├── Detect weaknesses
│   └── Auto-train agents
│
├── Self-Modification Cycle
│   ├── Analyze all code for improvements
│   ├── Generate validated changes
│   ├── Apply changes automatically (with rate limiting)
│   └── Track all modifications
│
└── Fine-Tuning Cycle
    ├── Create new model variants
    ├── Evaluate new models
    └── Promote best performers
```

### Safety Features

- **Rate Limiting**: Maximum 20 changes per hour (configurable)
- **Risk Assessment**: Only LOW and MEDIUM risk changes auto-apply by default
- **Validation**: All changes are validated before application
- **Backups**: Automatic backups created before modifications
- **Rollback**: Instant rollback capability for any change
- **Pause/Resume**: Temporarily pause AUTO mode without losing state

## Usage

### Command Line

```bash
# Start in AUTO mode
python closed_loop_system.py --auto

# Start in AUTO mode with high risk changes allowed
python closed_loop_system.py --auto --high-risk

# Or use the run_auto_mode function
python -c "from closed_loop_system import run_auto_mode; run_auto_mode(allow_high_risk=True)"
```

### Python API

```python
from closed_loop_system import ClosedLoopSystem, ClosedLoopConfig

# Create system with AUTO mode enabled
config = ClosedLoopConfig(
    auto_mode=True,
    auto_mode_interval=300.0,  # 5 minutes between cycles
    auto_modify_in_auto_mode=True,
    auto_mode_allow_high_risk=False,  # Safety first
    auto_mode_max_changes_per_hour=20
)

system = ClosedLoopSystem(config)

# Enable AUTO mode
system.enable_auto_mode()

# Or toggle it
system.toggle_auto_mode()

# Pause temporarily
system.pause_auto_mode()

# Resume after pause
system.resume_auto_mode()

# Disable completely
system.disable_auto_mode()

# Check status
status = system.get_status()
print(f"AUTO mode active: {status['auto_mode']['active']}")
```

### GUI Dashboard

The GUI dashboard has a dedicated **AUTO MODE** control panel with:

- **Enable/Disable** toggle button
- **Pause/Resume** controls
- **High Risk Mode** checkbox (requires explicit enable)
- Real-time status display:
  - AUTO MODE: ON/OFF/PAUSED
  - Uptime counter
  - Cycle counter

## Configuration Options

### ClosedLoopConfig Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `auto_mode` | bool | False | Master switch for AUTO mode |
| `auto_mode_interval` | float | 300.0 | Seconds between AUTO mode cycles |
| `auto_modify_in_auto_mode` | bool | True | Enable auto-apply in AUTO mode |
| `auto_mode_allow_high_risk` | bool | False | Allow HIGH/CRITICAL risk changes |
| `auto_mode_max_changes_per_hour` | int | 20 | Maximum changes per hour |

### Runtime Control

```python
# Update configuration at runtime
system.config.auto_mode_interval = 600.0  # 10 minutes
system.config.auto_mode_max_changes_per_hour = 10

# Save configuration
# (Configuration persists for the current session)
```

## Monitoring

### Event Topics

AUTO mode publishes events to the communication layer:

- `system.auto_mode` - Status changes (enabled/disabled/paused/resumed)
- `auto_mode.cycle_complete` - Each cycle completion with metrics
- `auto_mode.change_applied` - When a change is auto-applied
- `auto_mode.model_created` - When a new model is created
- `auto_mode.error` - When an error occurs in AUTO mode

### Metrics Tracking

AUTO mode tracks these metrics:

```python
metrics = system.get_metrics()
print(f"AUTO mode cycles: {metrics.auto_mode_cycles}")
print(f"AUTO mode uptime: {metrics.auto_mode_start_time}")
print(f"Changes applied: {metrics.auto_mode_changes_applied}")
print(f"Improvements: {metrics.auto_mode_improvements}")
print(f"Models created: {metrics.auto_mode_models_created}")
print(f"Consecutive success: {metrics.consecutive_success_cycles}")
print(f"Consecutive failures: {metrics.consecutive_failure_cycles}")
```

## Safety Warnings

### ⚠️ HIGH RISK MODE

Enabling `auto_mode_allow_high_risk=True` allows the system to automatically apply HIGH and CRITICAL risk changes without human review. This can include:

- Modifications to core system files
- Changes to communication layer
- Updates to the AUTO mode itself
- Any change that could affect system stability

**Recommendations:**
- Only enable high risk mode in isolated test environments
- Monitor closely when enabled
- Have rollback procedures ready
- Consider setting up external monitoring

### Rate Limiting

The default rate limit of 20 changes per hour prevents runaway modifications. If you need faster iteration:

1. Start with a small limit (5-10 changes/hour)
2. Monitor system stability
3. Gradually increase as confidence grows
4. Always have backups ready

## Integration with Other Components

### Closed-Loop System

AUTO mode integrates seamlessly with the existing closed-loop system:

- Uses the **Evaluation Agent** for reward signal generation
- Uses the **Self-Modifier** for code improvements
- Uses the **Fine-Tune Factory** for model creation
- Uses the **Communication Layer** for event publishing
- Respects all existing safety configurations

### Existing Features

All existing features continue to work in AUTO mode:

- Manual task execution via `run_task()`
- Manual optimization via `optimize_now()`
- Manual self-modification via `propose_improvement()` and `apply_improvement()`
- Full GUI functionality

## Troubleshooting

### AUTO mode won't start

- Check that the system is running: `system.start()`
- Check for errors in the logs
- Verify configuration: `system.config.auto_mode = True`

### Changes not being applied

- Check risk level threshold: `auto_mode_allow_high_risk`
- Check rate limiting: `auto_mode_max_changes_per_hour`
- Verify validation is passing

### High CPU/Memory usage

- Increase `auto_mode_interval` to slow down cycles
- Reduce `max_modifications_per_cycle`
- Reduce `auto_mode_max_changes_per_hour`

### System instability

- Disable AUTO mode immediately: `system.disable_auto_mode()`
- Check recent changes: `system.self_modifier.get_change_history()`
- Rollback changes: `system.rollback_improvement(change_id)`

## Best Practices

1. **Start Small**: Begin with conservative settings and monitor closely
2. **Use Backups**: Ensure backups are enabled before enabling AUTO mode
3. **Monitor Metrics**: Watch reward signals and error rates
4. **Gradual Rollout**: Start with LOW/MEDIUM risk only, then expand
5. **Regular Reviews**: Periodically review auto-applied changes
6. **Set Alerts**: Configure notifications for AUTO mode events
7. **Test First**: Run in test environment before production

## Example: Production Deployment

```python
from closed_loop_system import ClosedLoopSystem, ClosedLoopConfig
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Production-safe configuration
config = ClosedLoopConfig(
    auto_mode=True,
    auto_mode_interval=3600.0,  # 1 hour between cycles
    auto_modify_in_auto_mode=True,
    auto_mode_allow_high_risk=False,  # Never allow high risk in production
    auto_mode_max_changes_per_hour=5,  # Conservative rate limit
    backup_before_modification=True,
    require_human_approval=True  # Extra safety
)

# Create and start system
system = ClosedLoopSystem(config)
system.start()

# Enable AUTO mode
system.enable_auto_mode()

# Keep running
try:
    while True:
        import time
        time.sleep(60)
        
        # Periodically log status
        status = system.get_status()
        print(f"AUTO mode: {status['auto_mode']['cycles']} cycles, "
              f"{status['auto_mode']['changes_applied']} changes")
              
except KeyboardInterrupt:
    system.stop()
```

## API Reference

### ClosedLoopSystem Methods

| Method | Description |
|--------|-------------|
| `enable_auto_mode(allow_high_risk=False)` | Enable AUTO mode |
| `disable_auto_mode()` | Disable AUTO mode |
| `toggle_auto_mode(allow_high_risk=False)` | Toggle AUTO mode |
| `pause_auto_mode()` | Pause AUTO mode |
| `resume_auto_mode()` | Resume AUTO mode |
| `is_auto_mode_active()` | Check if AUTO mode is active |
| `is_auto_mode_paused()` | Check if AUTO mode is paused |

### ControlPanel Methods (GUI)

| Method | Description |
|--------|-------------|
| `enable_auto_mode(allow_high_risk=False)` | Enable AUTO mode via GUI |
| `disable_auto_mode()` | Disable AUTO mode via GUI |
| `toggle_auto_mode(allow_high_risk=False)` | Toggle AUTO mode via GUI |
| `pause_auto_mode()` | Pause AUTO mode via GUI |
| `resume_auto_mode()` | Resume AUTO mode via GUI |
| `get_auto_mode_status()` | Get AUTO mode status |

## Files Modified/Added

- `closed_loop_system.py` - Added AUTO mode functionality
- `gui/controls.py` - Added AUTO mode controls
- `gui/dashboard.py` - Added AUTO mode UI panel
- `AUTO_MODE.md` - This documentation file
