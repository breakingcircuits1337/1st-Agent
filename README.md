# 1st Agent Framework

**A Self-Optimizing, Closed-Loop Multi-Agent System with Continuous Goal Execution**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Status: Production Ready](https://img.shields.io/badge/status-production%20ready-green.svg)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)]()

---

## 🚀 Overview

**1st Agent** is an advanced, autonomous multi-agent framework that combines:

- **Dual-Model Architecture** (Researcher + Production Needle models)
- **Closed-Loop Optimization** (Evaluation → Reward → Improvement → Repeat)
- **Self-Modification** (Autonomous code improvement)
- **Continuous Goal Execution** (DAG-based task decomposition and execution)
- **24/7 AUTO Mode** (Toggleable continuous self-improvement)

The system **learns from its own execution**, **improves its own code**, and **optimizes its own models** — creating a truly self-evolving AI framework.

---

## 🎯 Core Capabilities

### 1. Continuous Goal Execution Loop ✨ NEW

Execute complex macro-objectives through an intelligent, self-optimizing pipeline:

```
MACRO OBJECTIVE
       ↓
┌─────────────────────────┐
│  Goal Decomposition      │  ← Breaks into Execution DAG
│  & State Graphing        │  ← Verifiable sub-milestones
└─────────────────────────┘
       ↓
┌─────────────────────────┐
│  Sub-Agent Execution      │  ← Needle 2 models execute
│  (Micro-tasks)           │  ← Targeted node processing
└─────────────────────────┘
       ↓
┌─────────────────────────┐
│  State Validation        │  ← Observer checks results
│  & Feedback              │  ← Success: Advance node
└─────────────────────────┘
       ↓
┌─────────────────────────┐
│  Failure?                │────NO────▶ TERMINAL CONVERGENCE
│  → Retraining Queue      │             (All nodes pass)
│  → Hot-Swap .cact        │
│  → Sub-agent Retry       │
└─────────────────────────┘
```

**Guardrails:**
- ✅ Goal Drift Circuit Breaker (read-only root objective)
- ✅ Perfection Bias Cap (stops if Δ < 0.5% for 5 iterations)
- ✅ Execution Hard Stops (max 20 retries, max 50 GPU epochs)

### 2. Closed-Loop Self-Optimization

```
┌─────────────────────────────────────────────────────────────┐
│                    CLOSED-LOOP SYSTEM                          │
├─────────────────────────────────────────────────────────────┤
│                                                                  │
│  Agents Execute → Evaluation → Reward Signal → Optimization  │
│                       ↓                                             │
│  Self-Modifier → Code Analysis → Improvement → Validation   │
│                       ↓                                             │
│  Fine-Tune Factory → Model Creation → Testing → Promotion    │
│                       ↓                                             │
│  ←────────────────── FEEDBACK LOOP ──────────────────→         │
│                                                                  │
└─────────────────────────────────────────────────────────────┘
```

### 3. 24/7 AUTO Mode

Toggle continuous, autonomous self-improvement:

```python
# Enable AUTO mode
system.enable_auto_mode()

# Or from command line
python closed_loop_system.py --auto
```

AUTO mode runs **continuous cycles** of:
- ✅ Evaluation (metrics, reward signals)
- ✅ Optimization (system tuning)
- ✅ Self-Modification (code improvements with auto-apply)
- ✅ Fine-Tuning (new model creation)
- ✅ Convergence checking

**Safety:** Rate-limited to 20 changes/hour, LOW/MEDIUM risk only by default.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           1ST AGENT FRAMEWORK                                   │
├─────────────────────┬─────────────────────┬─────────────────────┬────────────┤
│  Communication       │  Dual-Model          │  Goal Execution      │  Closed-    │
│  Layer               │  Architecture        │  Engine              │  Loop       │
│  - Pub/Sub          │  - Researcher Model  │  - Goal Decomposer  │  System     │
│  - Request/Response  │  - Production Model  │  - DAG Execution     │             │
│  - Agent Registry    │  - Query Routing     │  - State Validator   │             │
│  - Broadcast         │  - Response Formatting│  - Retraining        │             │
└─────────────────────┴─────────────────────┴─────────────────────┴────────────┘
                              │              │                     │              │
                              ▼              ▼                     ▼              │
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EVALUATION LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  Evaluation Agent │  Self-Optimizer  │  Fine-Tune Factory                     │
│  - Test Suites    │  - Monitor        │  - Model Creation                       │
│  - Metrics       │  - Weakness       │  - LoRA Fine-Tuning                     │
│  - Reward Signal │    Detection     │  - .cact Building                       │
│  - Performance   │  - Auto-Trainer   │  - Closed-Loop Optimization            │
│    Tracking      │                  │                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                              │                                              │
                              ▼                                              │
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SELF-MODIFICATION LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  Self-Modifier │  Code Analyzer  │  Change Manager  │  Risk Assessor       │
│  - Improve     │  - Analyze       │  - Validate        │  - Assess            │
│  - Apply       │  - Suggest       │  - Syntax Check    │  - Score             │
│  - Track       │  - Complexity   │  - Import Check    │  - Classify          │
└─────────────────────────────────────────────────────────────────────────────┘
                              │                                              │
                              ▼                                              │
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SPECIALIZED AGENTS                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  WeatherAgent │  NewsAgent  │  DBAgent  │  Custom Agents                       │
└─────────────────────────────────────────────────────────────────────────────┘
                              │                                              │
                              ▼                                              │
                    ┌───────────────────────┐                               │
                    │      GUI DASHBOARD     │                               │
                    │  - Overview            │                               │
                    │  - Agents              │                               │
                    │  - Metrics             │                               │
                    │  - Optimization        │                               │
                    │  - Self-Modification   │                               │
                    │  - Fine-Tuning         │                               │
                    │  - Logs                │                               │
                    │  - Feedback            │                               │
                    │  - Controls (AUTO)     │                               │
                    └───────────────────────┘
```

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-repo/1st-agent.git
cd 1st-agent

# Install dependencies (requires Python 3.10+)
pip install -r requirements.txt

# Install Needle models (for production)
pip install cactus-needle[gpu] needle
```

### Run the System

```bash
# Option 1: Start the GUI dashboard
python launch_gui.py

# Option 2: Start in interactive mode
python orchestrator.py --interactive

# Option 3: Start in AUTO mode (24/7 self-improvement)
python closed_loop_system.py --auto

# Option 4: Start AUTO mode with high risk allowed
python closed_loop_system.py --auto --high-risk
```

---

## 📚 Usage Examples

### Basic Query Execution

```python
from orchestrator import Orchestrator

orch = Orchestrator()

# Ask a question
response = orch.query("What's the weather in Lagos?")
print(response.answer)

# Or use the researcher model for R&D
response = orch.query("Analyze these results", use_researcher=True)
```

### Goal Execution (NEW)

```python
from goal_execution_engine import GoalExecutionEngine, Goal

engine = GoalExecutionEngine()

# Define a complex goal
goal = Goal(
    objective="Deploy a production-ready weather prediction system",
    pass_criteria={
        "accuracy": 0.95,
        "latency": 0.5,
        "coverage": 1.0
    },
    domain="weather"
)

# Execute autonomously
report = engine.execute_goal(goal, max_iterations=100)

print(f"Status: {report.status}")
print(f"Convergence achieved: {report.convergence_achieved}")
print(f"Nodes completed: {report.nodes_completed}")
print(f"Failures: {len(report.failures)}")
```

### Fine-Tuning a Model

```python
from orchestrator import Orchestrator

orch = Orchestrator()

# Create a fine-tuned model for a custom domain
model = orch.create_finetuned_model(
    name="custom_weather",
    domain="weather",
    tools_schema=[{"name": "get_weather", "description": "Get weather data"}],
    num_samples=200,
    epochs=10
)

print(f"Model created at: {model.model_path}")
```

### AUTO Mode (24/7 Self-Improvement)

```python
from closed_loop_system import ClosedLoopSystem, ClosedLoopConfig

# Create configuration
config = ClosedLoopConfig(
    auto_mode=True,
    auto_mode_interval=300.0,  # 5 minutes between cycles
    auto_modify_in_auto_mode=True,
    auto_mode_allow_high_risk=False,  # Safety first
    auto_mode_max_changes_per_hour=20
)

# Create and start system
system = ClosedLoopSystem(config)
system.start()

# Enable AUTO mode
system.enable_auto_mode()

# Let it run autonomously
# It will continuously:
# 1. Evaluate performance
# 2. Detect weaknesses
# 3. Apply code improvements
# 4. Fine-tune models
# 5. Optimize itself

# Later, disable AUTO mode
system.disable_auto_mode()
system.stop()
```

### Self-Modification

```python
from self_modification import SelfModifier

modifier = SelfModifier(project_root=".")

# Analyze code and suggest improvements
results = modifier.improve(
    focus_areas=["performance", "code_quality"],
    max_changes=5,
    auto_validate=True,
    auto_apply=False  # Review before applying
)

# Review proposed changes
for change in results.changes:
    print(f"Change: {change['description']}")
    print(f"Risk: {change['risk_level']}")
    print(f"File: {change['file_path']}")

# Apply a change
modifier.apply_change(results.changes[0]["change_id"])
```

---

## 📊 Features

### Core Framework

| Feature | Description | Status |
|---------|-------------|--------|
| Dual-Model Architecture | Researcher + Production Needle models | ✅ |
| Agent Orchestration | Route queries to specialized agents | ✅ |
| Fine-Tuning | LoRA fine-tuning with .cact output | ✅ |
| Evaluation | Comprehensive test suites & metrics | ✅ |
| Closed-Loop | Feedback-driven self-optimization | ✅ |

### Self-Improvement

| Feature | Description | Status |
|---------|-------------|--------|
| Self-Modification | Autonomous code improvement | ✅ |
| Code Analysis | Static analysis, complexity metrics | ✅ |
| Risk Assessment | Evaluate change safety before applying | ✅ |
| Change Management | Validate, apply, rollback changes | ✅ |
| Weakness Detection | Identify system performance issues | ✅ |
| Auto-Training | Automatically fine-tune underperforming agents | ✅ |

### Goal Execution (NEW)

| Feature | Description | Status |
|---------|-------------|--------|
| Goal Decomposition | Break macro objectives into execution DAG | ✅ |
| DAG Execution | Execute nodes in topological order | ✅ |
| State Validation | Observer checks results after each node | ✅ |
| Failure Handling | Capture context, queue for retraining | ✅ |
| Autonomous Retraining | Generate synthetic data, retrain models | ✅ |
| Hot-Swap | Replace .cact binaries in place | ⚠️ Stub |
| Terminal Convergence | Exit when all nodes pass criteria | ✅ |

### Guardrails (NEW)

| Guardrail | Description | Status |
|-----------|-------------|--------|
| Goal Drift Circuit Breaker | Lock root objective in read-only | ✅ |
| Perfection Bias Cap | Stop if gains < 0.5% for 5 iterations | ✅ |
| Execution Hard Stops | Max 20 retries, max 50 GPU epochs | ✅ |
| Rate Limiting | Max 20 changes/hour in AUTO mode | ✅ |
| Risk Gating | Only LOW/MEDIUM risk changes auto-apply | ✅ |

### AUTO Mode

| Feature | Description | Status |
|---------|-------------|--------|
| Continuous Execution | Runs 24/7 without human intervention | ✅ |
| Toggleable | Enable/disable with one command | ✅ |
| Pause/Resume | Temporarily pause without losing state | ✅ |
| Monitoring | Real-time status, uptime, metrics | ✅ |
| High Risk Mode | Optional: allow HIGH/CRITICAL changes | ✅ |

### GUI Dashboard

| Feature | Description | Status |
|---------|-------------|--------|
| System Overview | Real-time status, metrics | ✅ |
| Agent Management | View, control specialized agents | ✅ |
| Performance Metrics | Charts, trends, history | ✅ |
| Optimization | View optimization progress | ✅ |
| Self-Modification | Review and approve changes | ✅ |
| Fine-Tuning | Monitor model creation | ✅ |
| AUTO Mode Controls | Enable/disable, pause/resume, status | ✅ |
| Logs | View system logs | ✅ |
| Feedback | Provide feedback, rate responses | ✅ |

---

## 📁 Project Structure

```
1st-agent/
├── README.md                    # This file
├── README_NEW.md                # New README (this file)
├── SYSTEM_OVERVIEW.md           # System architecture overview
├── AUTO_MODE.md                 # AUTO mode documentation
├── AUTO_MODE_SUMMARY.md         # AUTO mode quick reference
├── GOAL_EXECUTION_ARCHITECTURE.md # Goal execution documentation
├── IMPROVEMENTS_APPLIED.md      # Detailed improvement log
│
├── closed_loop_system.py        # Unified closed-loop integration
├── communication_layer.py       # Inter-agent messaging
├── orchestrator.py              # Main orchestrator + Goal Execution
├── self_optimizer.py            # Self-optimization system
├── evaluation_agent.py          # Testing and metrics
├── finetune_factory.py          # Model fine-tuning
├── automation.py                # Pipeline automation
│
├── goal_execution_engine.py     # ✨ NEW: Goal execution loop
│
├── self_modification/           # Self-modification package
│   ├── __init__.py
│   ├── code_analyzer.py
│   ├── code_generator.py
│   ├── change_manager.py
│   ├── risk_assessor.py
│   └── self_modifier.py
│
├── gui/                         # GUI dashboard
│   ├── __init__.py
│   ├── dashboard.py
│   ├── controls.py
│   ├── monitor.py
│   └── feedback.py
│
├── agents/                      # Specialized agents
│   ├── __init__.py
│   ├── weather_agent.py
│   ├── news_agent.py
│   └── db_agent.py
│
├── autogen-main/                # Legacy: autogen integration
├── 1st-Agent-main/              # Legacy: original main
│
├── models/                      # Fine-tuned models
├── datasets/                    # Training data
├── checkpoints/                 # Training checkpoints
├── backups/                     # Self-modification backups
│
├── launch_gui.py                # Launch GUI dashboard
├── requirements.txt              # Dependencies
└── .env.example                 # Environment configuration
```

---

## 🎯 Key Concepts

### Execution DAG

A **Directed Acyclic Graph** that represents a decomposed goal:

- **Nodes**: Verifiable sub-milestones with pass criteria
- **Edges**: Dependencies between nodes
- **Execution**: Nodes executed in topological order
- **Convergence**: All nodes must meet their pass criteria

```python
from goal_execution_engine import Goal, GoalExecutionEngine

engine = GoalExecutionEngine()

goal = Goal(
    objective="Build a news summarization API",
    pass_criteria={"accuracy": 0.9, "latency": 0.3}
)

# Decompose into DAG
dag = engine.decompose_goal(goal, use_llm=True)
# dag.nodes = {
#     "node_0": ExecutionNode(action="design_architecture", ...),
#     "node_1": ExecutionNode(action="implement_core", dependencies=["node_0"], ...),
#     "node_2": ExecutionNode(action="add_features", dependencies=["node_1"], ...),
#     ...
# }

# Execute
report = engine.execute_dag(dag)
```

### Closed-Loop Optimization

The system continuously improves itself through feedback:

```
1. AGENTS EXECUTE tasks
   ↓
2. EVALUATION AGENT measures performance
   ↓
3. REWARD SIGNAL generated (0.0-2.0)
   ↓
4. SELF-OPTIMIZER detects weaknesses
   ↓
5. SELF-MODIFIER generates code improvements
   ↓
6. CHANGES VALIDATED and applied
   ↓
7. Back to step 1 (with improved code)
```

### AUTO Mode

24/7 continuous self-improvement mode:

```python
# Enable
system.enable_auto_mode()

# The system now:
# - Runs evaluation every 5 minutes
# - Optimizes based on reward signals
# - Applies code changes (within limits)
# - Creates new models
# - All autonomously!

# Disable
system.disable_auto_mode()
```

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file:

```bash
# Model paths
RESEARCHER_MODEL_PATH=models/researcher.cact
PRODUCTION_MODEL_PATH=models/production.cact
BASE_CHECKPOINT=models/base

# GPU settings
USE_GPU=true

# Directories
MODELS_DIR=models
DATASETS_DIR=datasets
CHECKPOINTS_DIR=checkpoints
BACKUPS_DIR=backups

# Logging
LOG_LEVEL=INFO
```

### Closed-Loop Configuration

```python
from closed_loop_system import ClosedLoopConfig

config = ClosedLoopConfig(
    # Self-optimization
    auto_optimize=True,
    optimization_interval=3600.0,  # 1 hour
    max_optimizations_per_cycle=5,
    
    # Self-modification
    auto_modify=False,  # Safety: disabled by default
    modification_risk_threshold="HIGH",
    max_modifications_per_cycle=3,
    
    # AUTO mode
    auto_mode=False,  # Master switch
    auto_mode_interval=300.0,  # 5 minutes
    auto_modify_in_auto_mode=True,
    auto_mode_allow_high_risk=False,  # Safety
    auto_mode_max_changes_per_hour=20,
    
    # Evaluation
    evaluation_interval=600.0,  # 10 minutes
    metrics_threshold=0.8,
    
    # Fine-tuning
    auto_finetune=True,
    finetune_iterations=3,
    
    # Safety
    require_human_approval=True,
    backup_before_modification=True,
    max_rollback_attempts=3
)
```

---

## 🛡️ Safety Features

### Self-Modification Safety

- ✅ **Auto-modification disabled by default** (`auto_modify=False`)
- ✅ **Human approval required** for high-risk changes
- ✅ **Automatic backups** before any modification
- ✅ **Instant rollback** capability
- ✅ **Multi-layer validation** (syntax, imports, tests)
- ✅ **Risk assessment** for every change

### AUTO Mode Safety

- ✅ **Rate limiting**: Max 20 changes/hour
- ✅ **Risk gating**: Only LOW/MEDIUM risk changes auto-apply
- ✅ **Validation**: All changes validated before application
- ✅ **Goal drift prevention**: Objectives locked in read-only
- ✅ **Perfection cap**: Stops if improvements < 0.5% for 5 iterations
- ✅ **Hard stops**: Max 20 retries, max 50 GPU epochs

### Goal Execution Safety

- ✅ **Goal Drift Circuit Breaker**: Root objective cannot be modified
- ✅ **Perfection Bias Cap**: Prevents infinite fine-tuning
- ✅ **Execution Hard Stops**: Prevents runaway processes
- ✅ **Backups**: All models and code backed up before changes
- ✅ **Validation**: Every node must meet pass criteria

---

## 📊 Performance

| Component | Performance | Notes |
|-----------|-------------|-------|
| Needle Models | ~28MB each | 14MB models available |
| Query Latency | < 1 second | Typical for cached models |
| Fine-Tuning | ~1-5 min | Depending on data size |
| Self-Modification | ~10-60 sec | Per change cycle |
| AUTO Mode Cycle | ~2-10 min | Configurable interval |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .

# Run tests
python -m pytest tests/
```

---

## 🐛 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: needle` | Install: `pip install cactus-needle[gpu] needle` |
| GPU not detected | Install JAX with GPU: `pip install --upgrade jax jaxlib` |
| Slow execution | Use smaller models (14MB Needle) |
| Memory errors | Reduce batch size, use CPU mode |
| Permission errors | Check file permissions, use virtual environment |

### AUTO Mode Issues

| Issue | Solution |
|-------|----------|
| AUTO mode won't start | Check `system.start()` was called |
| Changes not applying | Check risk threshold, enable `auto_mode_allow_high_risk` |
| High CPU usage | Increase `auto_mode_interval` |
| System instability | Disable AUTO mode: `system.disable_auto_mode()` |

### Goal Execution Issues

| Issue | Solution |
|-------|----------|
| Goal won't decompose | Check LLM is available, use template mode |
| Nodes stuck | Check dependencies, reduce max_retries |
| Convergence not achieved | Check pass criteria, increase max_iterations |

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built on [Cactus Needle](https://github.com/huggingface/needle) for efficient LLM inference
- Inspired by [AutoGen](https://github.com/microsoft/autogen) for multi-agent patterns
- Uses [NetworkX](https://networkx.org/) for DAG operations
- Special thanks to the open-source AI community

---

## 📞 Support

- **Documentation**: [docs/](docs/) (coming soon)
- **Issues**: [GitHub Issues](https://github.com/your-repo/1st-agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/1st-agent/discussions)
- **Email**: your-email@example.com

---

## 🎉 Getting Started

Ready to build your own self-improving AI system?

```bash
# Install
git clone https://github.com/your-repo/1st-agent.git
cd 1st-agent
pip install -r requirements.txt

# Launch GUI
python launch_gui.py

# Or run in AUTO mode
python closed_loop_system.py --auto
```

**The system will start learning and improving itself immediately!**

---

**Built with ❤️ for the future of autonomous AI systems**
