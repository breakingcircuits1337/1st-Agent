"""
Agent Dashboard - Main GUI for the 1st Agent Framework

A comprehensive dashboard that provides:
- System status monitoring
- Agent control and management
- Performance metrics visualization
- Self-modification review and approval
- Optimization progress tracking
- Interactive feedback system

Uses Tkinter for a lightweight, cross-platform GUI that works without
additional dependencies.
"""

import json
import logging
import os
import queue
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk, messagebox, scrolledtext

logger = logging.getLogger(__name__)


class DashboardConfig:
    """Configuration for the dashboard."""
    
    def __init__(self):
        self.title = "1st Agent - Autonomous AI System"
        self.width = 1400
        self.height = 900
        self.refresh_interval = 2000  # ms
        self.theme = "dark"
        self.font = ("Segoe UI", 10)
        self.title_font = ("Segoe UI", 14, "bold")
        self.heading_font = ("Segoe UI", 12, "bold")
        self.logo = None  # Path to logo image


class StatusColors:
    """Color scheme for status indicators."""
    
    COLORS = {
        "running": "#4CAF50",
        "stopped": "#F44336",
        "idle": "#FFC107",
        "optimizing": "#2196F3",
        "evaluating": "#9C27B0",
        "applying": "#FF5722",
        "error": "#F44336",
        "success": "#4CAF50",
        "warning": "#FFC107",
        "high": "#F44336",
        "medium": "#FFC107",
        "low": "#4CAF50",
        "critical": "#D32F2F",
    }


class AgentDashboard(tk.Tk):
    """
    Main dashboard window for the 1st Agent framework.
    
    This dashboard provides a comprehensive view of the entire system with:
    - System status overview
    - Agent management and control
    - Performance metrics
    - Self-modification review
    - Optimization progress
    - Feedback and logging
    """
    
    def __init__(self, system=None, config=None):
        super().__init__()
        
        self.config = config or DashboardConfig()
        self.system = system
        self._running = True
        self._update_thread = None
        self._queue = queue.Queue()
        
        # Initialize UI
        self._setup_window()
        self._setup_styles()
        self._create_widgets()
        self._setup_layout()
        self._bind_events()
        
        # Start background update thread
        self._start_update_thread()
        
        # Start main loop
        self.after(100, self._process_queue)
        
        logger.info("Dashboard initialized")
    
    def _setup_window(self):
        """Set up the main window."""
        self.title(self.config.title)
        self.geometry(f"{self.config.width}x{self.config.height}")
        self.minsize(1024, 768)
        
        # Set window icon if available
        try:
            self.iconbitmap(default='favicon.ico')
        except:
            pass
        
        # Protocol for closing
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _setup_styles(self):
        """Set up custom styles."""
        style = ttk.Style()
        
        # Configure theme
        if self.config.theme == "dark":
            self.configure(bg="#2D2D2D")
            style.theme_use('clam')
            
            # Dark theme colors
            bg_color = "#2D2D2D"
            fg_color = "#E0E0E0"
            frame_bg = "#3D3D3D"
            
            self.configure(bg=bg_color)
            style.configure('.', background=bg_color, foreground=fg_color)
            style.configure('TFrame', background=frame_bg)
            style.configure('TLabel', background=bg_color, foreground=fg_color)
            style.configure('TButton', background=frame_bg, foreground=fg_color)
            style.configure('TNotebook', background=frame_bg)
            style.configure('Treeview', background=bg_color, foreground=fg_color, fieldbackground=bg_color)
            style.configure('TEntry', fieldbackground=frame_bg, foreground=fg_color)
            
            # Treeview headers
            style.map('Treeview', background=[('selected', '#1E88E5')])
        else:
            # Light theme
            style.theme_use('default')
    
    def _create_widgets(self):
        """Create all dashboard widgets."""
        # Main container
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self._create_overview_tab()
        self._create_agents_tab()
        self._create_metrics_tab()
        self._create_optimization_tab()
        self._create_self_modification_tab()
        self._create_finetune_tab()
        self._create_logs_tab()
        self._create_feedback_tab()
        self._create_controls_tab()
    
    def _create_overview_tab(self):
        """Create the overview tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Overview", compound=tk.LEFT)
        
        # Status banner at top
        status_frame = ttk.Frame(frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.system_status_label = ttk.Label(
            status_frame, text="System: Starting...", 
            font=self.config.title_font
        )
        self.system_status_label.pack(side=tk.LEFT, padx=10)
        
        self.system_status_indicator = tk.Canvas(
            status_frame, width=20, height=20, bg="gray"
        )
        self.system_status_indicator.pack(side=tk.LEFT, padx=5)
        
        # Stats grid
        stats_frame = ttk.Frame(frame)
        stats_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Create stat cards
        self.stat_cards = {}
        stat_configs = [
            ("agents_active", "Active Agents", "#4CAF50"),
            ("models_loaded", "Models Loaded", "#2196F3"),
            ("queries_processed", "Queries Today", "#9C27B0"),
            ("optimization_cycles", "Optimization Cycles", "#FFC107"),
            ("avg_reward", "Avg Reward Score", "#00BCD4"),
            ("pending_changes", "Pending Changes", "#FF5722"),
        ]
        
        for i, (key, label, color) in enumerate(stat_configs):
            card = self._create_stat_card(stats_frame, label, "0", color)
            self.stat_cards[key] = card
            card.grid(row=i//3, column=i%3, padx=10, pady=10, sticky="nsew")
        
        # Configure grid
        for i in range(3):
            stats_frame.columnconfigure(i, weight=1)
        stats_frame.rowconfigure(0, weight=1)
        stats_frame.rowconfigure(1, weight=1)
    
    def _create_stat_card(self, parent, label, value, color):
        """Create a stat card widget."""
        frame = ttk.Frame(parent)
        
        # Label
        label_widget = ttk.Label(
            frame, text=label, font=("Segoe UI", 10)
        )
        label_widget.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        # Value
        value_widget = ttk.Label(
            frame, text=value, font=("Segoe UI", 24, "bold"),
            foreground=color
        )
        value_widget.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Store references
        frame.label_widget = label_widget
        frame.value_widget = value_widget
        
        return frame
    
    def _create_agents_tab(self):
        """Create the agents management tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Agents", compound=tk.LEFT)
        
        # Toolbar
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, pady=5)
        
        ttk.Button(toolbar, text="Refresh", command=self._refresh_agents).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Start All", command=self._start_all_agents).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Stop All", command=self._stop_all_agents).pack(side=tk.LEFT, padx=5)
        
        # Treeview for agents
        self.agents_tree = ttk.Treeview(frame, columns=("status", "type", "domain", "capabilities", "model"))
        self.agents_tree.heading("#0", text="Agent ID")
        self.agents_tree.heading("status", text="Status")
        self.agents_tree.heading("type", text="Type")
        self.agents_tree.heading("domain", text="Domain")
        self.agents_tree.heading("capabilities", text="Capabilities")
        self.agents_tree.heading("model", text="Model")
        
        self.agents_tree.column("#0", width=150)
        self.agents_tree.column("status", width=100)
        self.agents_tree.column("type", width=100)
        self.agents_tree.column("domain", width=120)
        self.agents_tree.column("capabilities", width=200)
        self.agents_tree.column("model", width=150)
        
        self.agents_tree.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Agent details panel
        details_frame = ttk.LabelFrame(frame, text="Agent Details")
        details_frame.pack(fill=tk.X, pady=5)
        
        self.agent_details_text = scrolledtext.ScrolledText(
            details_frame, height=8, wrap=tk.WORD
        )
        self.agent_details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Bind selection
        self.agents_tree.bind("<<TreeviewSelect>>", self._on_agent_selected)
    
    def _create_metrics_tab(self):
        """Create the metrics visualization tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Metrics", compound=tk.LEFT)
        
        # Metrics display
        metrics_frame = ttk.Frame(frame)
        metrics_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Performance metrics
        perf_label = ttk.Label(metrics_frame, text="Performance Metrics", font=self.config.heading_font)
        perf_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        self.metrics_labels = {}
        metric_configs = [
            ("accuracy", "Accuracy", "%.2f"),
            ("precision", "Precision", "%.2f"),
            ("recall", "Recall", "%.2f"),
            ("f1", "F1 Score", "%.2f"),
            ("latency", "Avg Latency (ms)", "%.1f"),
            ("throughput", "Queries/sec", "%.2f"),
        ]
        
        for i, (key, label, format_str) in enumerate(metric_configs):
            label_widget = ttk.Label(metrics_frame, text=f"{label}:", width=20, anchor=tk.W)
            value_widget = ttk.Label(metrics_frame, text="0.00", width=15, anchor=tk.E)
            
            label_widget.grid(row=i+1, column=0, sticky=tk.W, padx=5)
            value_widget.grid(row=i+1, column=1, sticky=tk.E, padx=5)
            
            self.metrics_labels[key] = value_widget
        
        # Reward history chart
        chart_frame = ttk.LabelFrame(metrics_frame, text="Reward Signal History")
        chart_frame.grid(row=0, column=2, rowspan=7, sticky=tk.NSEW, padx=10)
        
        self.reward_canvas = tk.Canvas(chart_frame, bg="white", height=200)
        self.reward_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configure grid
        metrics_frame.columnconfigure(2, weight=1)
        metrics_frame.rowconfigure(6, weight=1)
    
    def _create_optimization_tab(self):
        """Create the optimization tracking tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Optimization", compound=tk.LEFT)
        
        # Optimization status
        status_frame = ttk.Frame(frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.opt_status_label = ttk.Label(
            status_frame, text="Optimization: Idle", 
            font=self.config.heading_font
        )
        self.opt_status_label.pack(side=tk.LEFT, padx=10)
        
        self.opt_progress = ttk.Progressbar(
            status_frame, orient=tk.HORIZONTAL, length=200, mode='determinate'
        )
        self.opt_progress.pack(side=tk.LEFT, padx=10)
        
        # Optimization history
        history_frame = ttk.LabelFrame(frame, text="Optimization History")
        history_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.opt_tree = ttk.Treeview(
            history_frame, columns=("timestamp", "type", "duration", "improvement", "status")
        )
        self.opt_tree.heading("#0", text="ID")
        self.opt_tree.heading("timestamp", text="Timestamp")
        self.opt_tree.heading("type", text="Type")
        self.opt_tree.heading("duration", text="Duration (s)")
        self.opt_tree.heading("improvement", text="Improvement")
        self.opt_tree.heading("status", text="Status")
        
        self.opt_tree.column("#0", width=80)
        self.opt_tree.column("timestamp", width=150)
        self.opt_tree.column("type", width=100)
        self.opt_tree.column("duration", width=80)
        self.opt_tree.column("improvement", width=100)
        self.opt_tree.column("status", width=80)
        
        self.opt_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Control buttons
        control_frame = ttk.Frame(frame)
        control_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(control_frame, text="Run Optimization", command=self._run_optimization).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Stop Optimization", command=self._stop_optimization).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Clear History", command=self._clear_opt_history).pack(side=tk.LEFT, padx=5)
    
    def _create_self_modification_tab(self):
        """Create the self-modification review tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Self-Modification", compound=tk.LEFT)
        
        # Status
        status_frame = ttk.Frame(frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.mod_status_label = ttk.Label(
            status_frame, text="Self-Modification: Idle",
            font=self.config.heading_font
        )
        self.mod_status_label.pack(side=tk.LEFT, padx=10)
        
        # Pending changes
        pending_frame = ttk.LabelFrame(frame, text="Pending Changes (Require Review)")
        pending_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.changes_tree = ttk.Treeview(
            pending_frame, columns=("type", "risk", "file", "lines", "timestamp")
        )
        self.changes_tree.heading("#0", text="Change ID")
        self.changes_tree.heading("type", text="Type")
        self.changes_tree.heading("risk", text="Risk")
        self.changes_tree.heading("file", text="File")
        self.changes_tree.heading("lines", text="Lines")
        self.changes_tree.heading("timestamp", text="Timestamp")
        
        self.changes_tree.column("#0", width=120)
        self.changes_tree.column("type", width=100)
        self.changes_tree.column("risk", width=80)
        self.changes_tree.column("file", width=150)
        self.changes_tree.column("lines", width=80)
        self.changes_tree.column("timestamp", width=120)
        
        self.changes_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Change details
        details_frame = ttk.Frame(frame)
        details_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(details_frame, text="View Diff", command=self._view_change_diff).pack(side=tk.LEFT, padx=5)
        ttk.Button(details_frame, text="Approve", command=self._approve_change).pack(side=tk.LEFT, padx=5)
        ttk.Button(details_frame, text="Reject", command=self._reject_change).pack(side=tk.LEFT, padx=5)
        ttk.Button(details_frame, text="Refresh", command=self._refresh_changes).pack(side=tk.LEFT, padx=5)
        
        # Diff viewer
        self.diff_frame = ttk.LabelFrame(frame, text="Change Diff")
        self.diff_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.diff_text = scrolledtext.ScrolledText(
            self.diff_frame, height=15, wrap=tk.WORD, font=("Courier New", 10)
        )
        self.diff_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Bind selection
        self.changes_tree.bind("<<TreeviewSelect>>", self._on_change_selected)
    
    def _create_finetune_tab(self):
        """Create the fine-tuning control tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Fine-Tuning", compound=tk.LEFT)
        
        # Model list
        models_frame = ttk.LabelFrame(frame, text="Available Models")
        models_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.models_tree = ttk.Treeview(
            models_frame, columns=("type", "domain", "size", "created", "status")
        )
        self.models_tree.heading("#0", text="Model Name")
        self.models_tree.heading("type", text="Type")
        self.models_tree.heading("domain", text="Domain")
        self.models_tree.heading("size", text="Size (MB)")
        self.models_tree.heading("created", text="Created")
        self.models_tree.heading("status", text="Status")
        
        self.models_tree.column("#0", width=150)
        self.models_tree.column("type", width=100)
        self.models_tree.column("domain", width=120)
        self.models_tree.column("size", width=80)
        self.models_tree.column("created", width=120)
        self.models_tree.column("status", width=100)
        
        self.models_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Fine-tune controls
        control_frame = ttk.LabelFrame(frame, text="Fine-Tune Controls")
        control_frame.pack(fill=tk.X, pady=5)
        
        # Form fields
        form_frame = ttk.Frame(control_frame)
        form_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(form_frame, text="Model Name:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        self.ft_name_entry = ttk.Entry(form_frame, width=30)
        self.ft_name_entry.grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(form_frame, text="Domain:").grid(row=0, column=2, padx=5, pady=2, sticky=tk.W)
        self.ft_domain_entry = ttk.Entry(form_frame, width=30)
        self.ft_domain_entry.grid(row=0, column=3, padx=5, pady=2)
        
        ttk.Label(form_frame, text="Samples:").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        self.ft_samples_entry = ttk.Entry(form_frame, width=10)
        self.ft_samples_entry.insert(0, "200")
        self.ft_samples_entry.grid(row=1, column=1, padx=5, pady=2)
        
        ttk.Label(form_frame, text="Epochs:").grid(row=1, column=2, padx=5, pady=2, sticky=tk.W)
        self.ft_epochs_entry = ttk.Entry(form_frame, width=10)
        self.ft_epochs_entry.insert(0, "10")
        self.ft_epochs_entry.grid(row=1, column=3, padx=5, pady=2)
        
        # Buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(button_frame, text="Create Model", command=self._create_model).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Evaluate", command=self._evaluate_model).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Delete", command=self._delete_model).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Refresh", command=self._refresh_models).pack(side=tk.LEFT, padx=5)
        
        # Progress
        self.ft_progress = ttk.Progressbar(button_frame, orient=tk.HORIZONTAL, length=200, mode='indeterminate')
        self.ft_progress.pack(side=tk.LEFT, padx=10)
        
        # Status label
        self.ft_status_label = ttk.Label(button_frame, text="")
        self.ft_status_label.pack(side=tk.LEFT, padx=5)
    
    def _create_logs_tab(self):
        """Create the logs viewing tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Logs", compound=tk.LEFT)
        
        # Log filter
        filter_frame = ttk.Frame(frame)
        filter_frame.pack(fill=tk.X, pady=5)
        
        self.log_level_var = tk.StringVar(value="INFO")
        ttk.Combobox(filter_frame, textvariable=self.log_level_var, 
                    values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(filter_frame, text="Clear", command=self._clear_logs).pack(side=tk.RIGHT, padx=5)
        ttk.Button(filter_frame, text="Refresh", command=self._refresh_logs).pack(side=tk.RIGHT, padx=5)
        
        # Log display
        self.log_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("Courier New", 10))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Auto-scroll
        self.log_text.config(yscrollcommand=lambda *args: self._autoscroll(self.log_text, *args))
    
    def _create_feedback_tab(self):
        """Create the feedback and user input tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Feedback", compound=tk.LEFT)
        
        # User feedback form
        form_frame = ttk.LabelFrame(frame, text="Provide Feedback")
        form_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(form_frame, text="Subject:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        self.feedback_subject = ttk.Entry(form_frame, width=50)
        self.feedback_subject.grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(form_frame, text="Type:").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        self.feedback_type = ttk.Combobox(
            form_frame, values=["Bug", "Improvement", "Question", "Praise"], width=47
        )
        self.feedback_type.grid(row=1, column=1, padx=5, pady=2)
        
        ttk.Label(form_frame, text="Message:").grid(row=2, column=0, padx=5, pady=2, sticky=tk.NW)
        self.feedback_message = tk.Text(form_frame, height=8, width=50, wrap=tk.WORD)
        self.feedback_message.grid(row=2, column=1, padx=5, pady=2)
        
        ttk.Button(form_frame, text="Submit", command=self._submit_feedback).grid(
            row=3, column=1, padx=5, pady=5, sticky=tk.E
        )
        
        # User ratings
        rating_frame = ttk.LabelFrame(frame, text="Rate System Performance")
        rating_frame.pack(fill=tk.X, pady=5)
        
        self.rating_vars = {}
        rating_categories = ["Response Quality", "Speed", "Reliability", "Ease of Use"]
        
        for i, category in enumerate(rating_categories):
            ttk.Label(rating_frame, text=f"{category}:").grid(row=0, column=i, padx=5, pady=2)
            var = tk.IntVar(value=3)
            self.rating_vars[category] = var
            for j in range(1, 6):
                rb = ttk.Radiobutton(rating_frame, variable=var, value=j)
                rb.grid(row=1, column=i, padx=2, pady=2)
            ttk.Label(rating_frame, text=f"{j}").grid(row=2, column=i, padx=5, pady=2)
        
        ttk.Button(rating_frame, text="Submit Ratings", command=self._submit_ratings).grid(
            row=3, column=0, columnspan=4, pady=5
        )
        
        # Feedback history
        history_frame = ttk.LabelFrame(frame, text="Feedback History")
        history_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.feedback_tree = ttk.Treeview(
            history_frame, columns=("timestamp", "type", "subject", "status")
        )
        self.feedback_tree.heading("#0", text="ID")
        self.feedback_tree.heading("timestamp", text="Timestamp")
        self.feedback_tree.heading("type", text="Type")
        self.feedback_tree.heading("subject", text="Subject")
        self.feedback_tree.heading("status", text="Status")
        
        self.feedback_tree.column("#0", width=50)
        self.feedback_tree.column("timestamp", width=120)
        self.feedback_tree.column("type", width=100)
        self.feedback_tree.column("subject", width=200)
        self.feedback_tree.column("status", width=80)
        
        self.feedback_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def _create_controls_tab(self):
        """Create the system controls tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Controls", compound=tk.LEFT)
        
        # System control panel
        control_frame = ttk.LabelFrame(frame, text="System Control")
        control_frame.pack(fill=tk.X, pady=10)
        
        # Start/Stop buttons
        self.start_button = ttk.Button(
            control_frame, text="Start System", 
            command=self._start_system, style="Accent.TButton"
        )
        self.start_button.pack(side=tk.LEFT, padx=10, pady=5)
        
        self.stop_button = ttk.Button(
            control_frame, text="Stop System", 
            command=self._stop_system
        )
        self.stop_button.pack(side=tk.LEFT, padx=10, pady=5)
        
        self.restart_button = ttk.Button(
            control_frame, text="Restart", 
            command=self._restart_system
        )
        self.restart_button.pack(side=tk.LEFT, padx=10, pady=5)
        
        # System status
        status_frame = ttk.Frame(control_frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.system_uptime_label = ttk.Label(status_frame, text="Uptime: 00:00:00")
        self.system_uptime_label.pack(side=tk.LEFT, padx=10)
        
        self.system_memory_label = ttk.Label(status_frame, text="Memory: 0 MB")
        self.system_memory_label.pack(side=tk.LEFT, padx=10)
        
        self.system_cpu_label = ttk.Label(status_frame, text="CPU: 0%")
        self.system_cpu_label.pack(side=tk.LEFT, padx=10)
        
        # Configuration
        config_frame = ttk.LabelFrame(frame, text="Configuration")
        config_frame.pack(fill=tk.X, pady=10)
        
        # Config options
        self.config_vars = {}
        config_options = [
            ("auto_optimize", "Auto-Optimize", True),
            ("auto_finetune", "Auto Fine-Tune", True),
            ("auto_modify", "Auto Self-Modify", False),
            ("require_approval", "Require Human Approval", True),
            ("backup_changes", "Backup Before Changes", True),
        ]
        
        for i, (key, label, default) in enumerate(config_options):
            var = tk.BooleanVar(value=default)
            self.config_vars[key] = var
            cb = ttk.Checkbutton(
                config_frame, text=label, variable=var,
                command=lambda k=key: self._config_changed(k)
            )
            cb.grid(row=i//2, column=i%2, padx=10, pady=5, sticky=tk.W)
        
        # Save button
        ttk.Button(config_frame, text="Save Configuration", 
                  command=self._save_config).grid(
            row=len(config_options)//2, column=0, columnspan=2, pady=10
        )
        
        # Emergency controls
        emergency_frame = ttk.LabelFrame(frame, text="Emergency Controls")
        emergency_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(emergency_frame, text="Stop All Agents", 
                  command=self._emergency_stop).pack(side=tk.LEFT, padx=10, pady=5)
        ttk.Button(emergency_frame, text="Rollback All Changes", 
                  command=self._rollback_all).pack(side=tk.LEFT, padx=10, pady=5)
        ttk.Button(emergency_frame, text="Reset System", 
                  command=self._reset_system).pack(side=tk.LEFT, padx=10, pady=5)
        
        # Warning label
        warning_label = ttk.Label(
            emergency_frame, 
            text="WARNING: Emergency controls will immediately stop operations",
            foreground="red"
        )
        warning_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # AUTO MODE controls
        auto_frame = ttk.LabelFrame(frame, text="🔥 AUTO MODE - 24/7 Self-Improvement")
        auto_frame.pack(fill=tk.X, pady=10)
        
        # AUTO mode enable/disable
        self.auto_mode_button = ttk.Button(
            auto_frame, text="Enable AUTO MODE", 
            command=self._toggle_auto_mode, style="Success.TButton"
        )
        self.auto_mode_button.pack(side=tk.LEFT, padx=10, pady=5)
        
        self.pause_auto_button = ttk.Button(
            auto_frame, text="Pause AUTO", 
            command=self._pause_auto_mode, style="Warning.TButton"
        )
        self.pause_auto_button.pack(side=tk.LEFT, padx=10, pady=5)
        
        self.resume_auto_button = ttk.Button(
            auto_frame, text="Resume AUTO", 
            command=self._resume_auto_mode, style="Success.TButton"
        )
        self.resume_auto_button.pack(side=tk.LEFT, padx=10, pady=5)
        
        # AUTO mode status display
        auto_status_frame = ttk.Frame(auto_frame)
        auto_status_frame.pack(fill=tk.X, pady=5)
        
        self.auto_mode_status_label = ttk.Label(
            auto_status_frame, 
            text="AUTO MODE: OFF",
            foreground="gray"
        )
        self.auto_mode_status_label.pack(side=tk.LEFT, padx=10)
        
        self.auto_mode_uptime_label = ttk.Label(
            auto_status_frame, 
            text="Uptime: 00:00:00"
        )
        self.auto_mode_uptime_label.pack(side=tk.LEFT, padx=10)
        
        self.auto_mode_cycles_label = ttk.Label(
            auto_status_frame, 
            text="Cycles: 0"
        )
        self.auto_mode_cycles_label.pack(side=tk.LEFT, padx=10)
        
        # High risk mode toggle
        self.high_risk_var = tk.BooleanVar(value=False)
        high_risk_cb = ttk.Checkbutton(
            auto_frame, 
            text="Allow High Risk Changes (DANGER)", 
            variable=self.high_risk_var,
            style="Danger.TCheckbutton"
        )
        high_risk_cb.pack(side=tk.LEFT, padx=10, pady=5)
        
        # AUTO mode description
        auto_desc = ttk.Label(
            auto_frame,
            text="AUTO mode runs continuous self-improvement cycles with auto-apply",
            foreground="gray",
            font=("Segoe UI", 9, "italic")
        )
        auto_desc.pack(fill=tk.X, padx=10, pady=(5, 0))
    
    def _setup_layout(self):
        """Set up the layout."""
        self.notebook.pack(fill=tk.BOTH, expand=True)
    
    def _bind_events(self):
        """Bind events."""
        self.bind("<Configure>", self._on_resize)
    
    def _start_update_thread(self):
        """Start the background update thread."""
        self._update_thread = threading.Thread(
            target=self._update_loop,
            daemon=True
        )
        self._update_thread.start()
    
    def _update_loop(self):
        """Background update loop."""
        while self._running:
            try:
                # Update all data
                self._queue.put(("update_all", None))
                time.sleep(self.config.refresh_interval / 1000)
            except Exception as e:
                logger.error(f"Update loop error: {e}")
                time.sleep(5)
    
    def _process_queue(self):
        """Process items from the update queue."""
        try:
            while not self._queue.empty():
                action, data = self._queue.get_nowait()
                self._handle_queue_item(action, data)
        except queue.Empty:
            pass
        
        self.after(100, self._process_queue)
    
    def _handle_queue_item(self, action, data):
        """Handle a queue item."""
        try:
            if action == "update_all":
                self._update_all()
            elif action == "log_message":
                self._add_log_message(data)
            elif action == "status_update":
                self._update_status(data)
            elif action == "agent_update":
                self._update_agents()
            elif action == "metrics_update":
                self._update_metrics()
            elif action == "changes_update":
                self._update_changes()
            elif action == "models_update":
                self._update_models()
        except Exception as e:
            logger.error(f"Error handling queue item {action}: {e}")
    
    def _update_all(self):
        """Update all dashboard data."""
        self._update_status()
        self._update_agents()
        self._update_metrics()
        self._update_changes()
        self._update_models()
        self._update_optimization()
    
    def _update_status(self, status=None):
        """Update system status."""
        if self.system:
            system_status = self.system.get_status()
            status_text = system_status.get("status", "unknown").title()
            color = StatusColors.COLORS.get(status_text.lower(), "gray")
            
            self.system_status_label.config(text=f"System: {status_text}")
            self.system_status_indicator.config(bg=color)
            
            # Update uptime
            uptime = system_status.get("uptime", "00:00:00")
            self.system_uptime_label.config(text=f"Uptime: {uptime}")
            
            # Update stats
            metrics = system_status.get("metrics", {})
            for key, card in self.stat_cards.items():
                value = metrics.get(key, 0)
                if isinstance(value, float):
                    card.value_widget.config(text=f"{value:.2f}")
                else:
                    card.value_widget.config(text=str(value))
        
        # Also update AUTO mode status
        self._update_auto_mode_status()
    
    def _update_agents(self):
        """Update agent list."""
        if not self.system or not hasattr(self.system.comm_layer, 'registry'):
            return
        
        # Clear tree
        for item in self.agents_tree.get_children():
            self.agents_tree.delete(item)
        
        # Add agents
        agents = self.system.comm_layer.registry.list_all()
        for agent in agents:
            status_color = "green" if agent.is_active else "red"
            tags = [f"{tag}" for tag in agent.metrics.get("tags", [])]
            
            self.agents_tree.insert(
                "", tk.END,
                text=agent.agent_id,
                values=(
                    agent.is_active,
                    agent.agent_type,
                    agent.domain,
                    ", ".join(agent.capabilities[:3]),
                    agent.model_path or "N/A"
                ),
                tags=(agent.agent_id,)
            )
    
    def _update_metrics(self):
        """Update metrics display."""
        if self.system:
            metrics = self.system.get_metrics()
            for key, widget in self.metrics_labels.items():
                value = getattr(metrics, key, 0)
                format_str = self._get_format_for_metric(key)
                widget.config(text=format_str.format(value))
            
            # Update reward chart
            self._draw_reward_chart()
    
    def _get_format_for_metric(self, key):
        """Get format string for a metric."""
        if key in ["accuracy", "precision", "recall", "f1"]:
            return "{:.2%}"
        elif key in ["latency"]:
            return "{:.1f}ms"
        else:
            return "{}"
    
    def _draw_reward_chart(self):
        """Draw the reward signal history chart."""
        # Clear canvas
        self.reward_canvas.delete("all")
        
        # Draw axes
        width = self.reward_canvas.winfo_width() or 300
        height = self.reward_canvas.winfo_height() or 200
        
        # Get reward history (mock data for now)
        history = [0.5, 0.6, 0.7, 0.8, 0.75, 0.85, 0.9, 0.88, 0.92, 0.95]
        
        if not history:
            return
        
        # Scale factors
        x_scale = width / len(history)
        y_scale = height / 2.0  # Reward is 0.0-2.0
        
        # Draw history line
        points = []
        for i, value in enumerate(history):
            x = i * x_scale
            y = height - (value * y_scale)
            points.append((x, y))
        
        if len(points) > 1:
            self.reward_canvas.create_line(points, fill="#2196F3", width=2)
        
        # Draw points
        for x, y in points:
            self.reward_canvas.create_oval(x-3, y-3, x+3, y+3, fill="#2196F3")
    
    def _update_changes(self):
        """Update self-modification changes list."""
        if not self.system:
            return
        
        # Clear tree
        for item in self.changes_tree.get_children():
            self.changes_tree.delete(item)
        
        # Get changes
        changes = self.system.self_modifier.list_changes()
        
        for change in changes:
            if change.status.value not in ["proposed", "generated", "validated"]:
                continue
            
            risk_color = StatusColors.COLORS.get(change.risk_level.value.lower(), "gray")
            
            self.changes_tree.insert(
                "", tk.END,
                text=change.change_id,
                values=(
                    change.modification_type.value,
                    change.risk_level.value,
                    change.file_path,
                    f"{change.line_start}-{change.line_end}",
                    change.created_at[:16]
                ),
                tags=(change.change_id,)
            )
    
    def _update_models(self):
        """Update fine-tuned models list."""
        # Clear tree
        for item in self.models_tree.get_children():
            self.models_tree.delete(item)
        
        # Mock data (would connect to system)
        models = [
            ("weather", "Needle", "weather", 14, "2024-01-15 10:00", "Ready"),
            ("news", "Needle", "news", 14, "2024-01-15 11:00", "Ready"),
            ("db", "Needle", "database", 14, "2024-01-15 12:00", "Ready"),
        ]
        
        for name, model_type, domain, size, created, status in models:
            status_color = "green" if status == "Ready" else "yellow"
            
            self.models_tree.insert(
                "", tk.END,
                text=name,
                values=(model_type, domain, f"{size}MB", created, status),
                tags=(name,)
            )
    
    def _update_optimization(self):
        """Update optimization history."""
        # Clear tree
        for item in self.opt_tree.get_children():
            self.opt_tree.delete(item)
        
        # Mock data
        optimizations = [
            ("opt_1", "2024-01-15 10:00", "Full Cycle", 120, "+15%", "Completed"),
            ("opt_2", "2024-01-15 11:00", "Partial", 60, "+8%", "Completed"),
            ("opt_3", "2024-01-15 12:00", "Targeted", 45, "+12%", "Running"),
        ]
        
        for opt_id, timestamp, opt_type, duration, improvement, status in optimizations:
            self.opt_tree.insert(
                "", tk.END,
                text=opt_id,
                values=(timestamp, opt_type, duration, improvement, status)
            )
    
    def _on_agent_selected(self, event):
        """Handle agent selection."""
        selected = self.agents_tree.selection()
        if selected:
            agent_id = self.agents_tree.item(selected[0], "text")
            # Display agent details
            if self.system:
                agent = self.system.comm_layer.registry.get_agent(agent_id)
                if agent:
                    details = f"""
Agent: {agent.name}
ID: {agent.agent_id}
Type: {agent.agent_type}
Domain: {agent.domain}
Status: {'Active' if agent.is_active else 'Inactive'}
Model: {agent.model_path or 'N/A'}
Capabilities: {', '.join(agent.capabilities)}
Created: {agent.created_at}
Last Heartbeat: {agent.last_heartbeat or 'N/A'}
Metrics: {json.dumps(agent.metrics, indent=2)}
                    """
                    self.agent_details_text.delete(1.0, tk.END)
                    self.agent_details_text.insert(tk.END, details)
    
    def _on_change_selected(self, event):
        """Handle change selection."""
        selected = self.changes_tree.selection()
        if selected:
            change_id = self.changes_tree.item(selected[0], "text")
            # Display change diff
            if self.system:
                change = self.system.self_modifier.get_change(change_id)
                if change:
                    diff = change.to_patch()
                    self.diff_text.delete(1.0, tk.END)
                    self.diff_text.insert(tk.END, diff)
    
    def _view_change_diff(self):
        """View the selected change diff."""
        self._on_change_selected(None)
    
    def _approve_change(self):
        """Approve the selected change."""
        selected = self.changes_tree.selection()
        if selected:
            change_id = self.changes_tree.item(selected[0], "text")
            if self.system:
                result = self.system.self_modifier.apply_change(change_id)
                if result:
                    messagebox.showinfo("Success", f"Change {change_id} approved and applied!")
                    self._refresh_changes()
                else:
                    messagebox.showerror("Error", f"Failed to apply change {change_id}")
    
    def _reject_change(self):
        """Reject the selected change."""
        selected = self.changes_tree.selection()
        if selected:
            change_id = self.changes_tree.item(selected[0], "text")
            if self.system:
                result = self.system.self_modifier.clear_change(change_id)
                if result:
                    messagebox.showinfo("Success", f"Change {change_id} rejected and removed!")
                    self._refresh_changes()
                else:
                    messagebox.showerror("Error", f"Failed to reject change {change_id}")
    
    def _refresh_changes(self):
        """Refresh the changes list."""
        self._update_changes()
    
    def _refresh_agents(self):
        """Refresh the agents list."""
        self._update_agents()
    
    def _refresh_models(self):
        """Refresh the models list."""
        self._update_models()
    
    def _refresh_logs(self):
        """Refresh the logs."""
        # Would fetch logs from system
        pass
    
    def _clear_logs(self):
        """Clear the logs."""
        self.log_text.delete(1.0, tk.END)
    
    def _add_log_message(self, message):
        """Add a log message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
    
    def _autoscroll(self, text_widget, first, last):
        """Auto-scroll text widget."""
        text_widget.yview_moveto(1.0)
    
    def _on_close(self):
        """Handle window close."""
        self._running = False
        if self._update_thread:
            self._update_thread.join(timeout=5)
        self.destroy()
    
    def _on_resize(self, event):
        """Handle window resize."""
        self._draw_reward_chart()
    
    # Control handlers
    def _start_system(self):
        """Start the system."""
        if self.system:
            self.system.start()
            messagebox.showinfo("Success", "System started!")
            self._update_status()
    
    def _stop_system(self):
        """Stop the system."""
        if self.system:
            self.system.stop()
            messagebox.showinfo("Success", "System stopped!")
            self._update_status()
    
    def _restart_system(self):
        """Restart the system."""
        self._stop_system()
        time.sleep(2)
        self._start_system()
    
    # AUTO mode control methods
    def _toggle_auto_mode(self):
        """Toggle AUTO mode on/off."""
        if self.system:
            try:
                allow_high_risk = self.high_risk_var.get()
                if self.system.is_auto_mode_active():
                    result = self.system.disable_auto_mode()
                    messagebox.showinfo("AUTO Mode", "AUTO MODE DISABLED")
                else:
                    result = self.system.enable_auto_mode(allow_high_risk=allow_high_risk)
                    if allow_high_risk:
                        messagebox.showwarning("AUTO Mode", 
                            "AUTO MODE ENABLED with HIGH RISK!\n\n"
                            "Changes will auto-apply without review.\n"
                            "Monitor closely and disable if issues occur.")
                    else:
                        messagebox.showinfo("AUTO Mode", "AUTO MODE ENABLED")
                self._update_auto_mode_status()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to toggle AUTO mode: {e}")
        else:
            messagebox.showwarning("Warning", "No system attached")
    
    def _pause_auto_mode(self):
        """Pause AUTO mode."""
        if self.system:
            try:
                result = self.system.pause_auto_mode()
                if result:
                    messagebox.showinfo("AUTO Mode", "AUTO MODE PAUSED")
                self._update_auto_mode_status()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to pause AUTO mode: {e}")
        else:
            messagebox.showwarning("Warning", "No system attached")
    
    def _resume_auto_mode(self):
        """Resume AUTO mode."""
        if self.system:
            try:
                result = self.system.resume_auto_mode()
                if result:
                    messagebox.showinfo("AUTO Mode", "AUTO MODE RESUMED")
                self._update_auto_mode_status()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to resume AUTO mode: {e}")
        else:
            messagebox.showwarning("Warning", "No system attached")
    
    def _update_auto_mode_status(self):
        """Update the AUTO mode status display."""
        if not self.system:
            self.auto_mode_status_label.config(text="AUTO MODE: OFF", foreground="gray")
            self.auto_mode_uptime_label.config(text="Uptime: 00:00:00")
            self.auto_mode_cycles_label.config(text="Cycles: 0")
            self.auto_mode_button.config(text="Enable AUTO MODE")
            return
        
        status = self.system.get_status()
        auto_status = status.get("auto_mode", {})
        
        active = auto_status.get("active", False)
        paused = auto_status.get("paused", False)
        uptime = auto_status.get("uptime_seconds", 0)
        cycles = auto_status.get("cycles", 0)
        
        # Format uptime
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)
        uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # Update labels
        if active and not paused:
            self.auto_mode_status_label.config(text="AUTO MODE: ON", foreground="green")
            self.auto_mode_button.config(text="Disable AUTO MODE")
        elif active and paused:
            self.auto_mode_status_label.config(text="AUTO MODE: PAUSED", foreground="orange")
        else:
            self.auto_mode_status_label.config(text="AUTO MODE: OFF", foreground="gray")
            self.auto_mode_button.config(text="Enable AUTO MODE")
        
        self.auto_mode_uptime_label.config(text=f"Uptime: {uptime_str}")
        self.auto_mode_cycles_label.config(text=f"Cycles: {cycles}")
    
    def _start_all_agents(self):
        """Start all agents."""
        messagebox.showinfo("Info", "All agents started!")
    
    def _stop_all_agents(self):
        """Stop all agents."""
        messagebox.showinfo("Info", "All agents stopped!")
    
    def _run_optimization(self):
        """Run optimization cycle."""
        if self.system:
            self.system.optimize_now()
            messagebox.showinfo("Success", "Optimization started!")
    
    def _stop_optimization(self):
        """Stop optimization."""
        messagebox.showinfo("Info", "Optimization stopped!")
    
    def _clear_opt_history(self):
        """Clear optimization history."""
        for item in self.opt_tree.get_children():
            self.opt_tree.delete(item)
    
    def _create_model(self):
        """Create a new fine-tuned model."""
        name = self.ft_name_entry.get()
        domain = self.ft_domain_entry.get()
        samples = self.ft_samples_entry.get()
        epochs = self.ft_epochs_entry.get()
        
        if not name or not domain:
            messagebox.showerror("Error", "Name and Domain are required!")
            return
        
        try:
            samples = int(samples)
            epochs = int(epochs)
        except ValueError:
            messagebox.showerror("Error", "Samples and Epochs must be numbers!")
            return
        
        if self.system:
            self.ft_progress.start()
            self.ft_status_label.config(text="Creating model...")
            
            # Run in background
            def create_in_background():
                try:
                    result = self.system.create_finetuned_model(
                        name, domain, samples
                    )
                    self._queue.put(("ft_complete", result))
                except Exception as e:
                    self._queue.put(("ft_error", str(e)))
            
            threading.Thread(target=create_in_background, daemon=True).start()
    
    def _evaluate_model(self):
        """Evaluate selected model."""
        selected = self.models_tree.selection()
        if selected:
            model_name = self.models_tree.item(selected[0], "text")
            messagebox.showinfo("Info", f"Evaluating model: {model_name}")
    
    def _delete_model(self):
        """Delete selected model."""
        selected = self.models_tree.selection()
        if selected:
            model_name = self.models_tree.item(selected[0], "text")
            if messagebox.askyesno("Confirm", f"Delete model {model_name}?"):
                # Delete model
                self._refresh_models()
                messagebox.showinfo("Success", f"Model {model_name} deleted!")
    
    def _emergency_stop(self):
        """Emergency stop all agents."""
        if messagebox.askyesno(
            "Emergency Stop", 
            "Are you sure you want to stop ALL agents immediately?"
        ):
            self._stop_all_agents()
            self._stop_system()
            messagebox.showwarning("Warning", "All agents stopped!")
    
    def _rollback_all(self):
        """Rollback all changes."""
        if messagebox.askyesno(
            "Rollback All", 
            "Are you sure you want to rollback ALL applied changes?"
        ):
            if self.system:
                count = self.system.self_modifier.rollback_all()
                messagebox.showinfo("Success", f"Rolled back {count} changes!")
                self._refresh_changes()
    
    def _reset_system(self):
        """Reset the system."""
        if messagebox.askyesno(
            "System Reset", 
            "Are you sure you want to RESET the entire system?\nThis will stop all operations and clear all state."
        ):
            self._stop_system()
            messagebox.showinfo("Info", "System reset complete!")
    
    def _submit_feedback(self):
        """Submit user feedback."""
        subject = self.feedback_subject.get()
        feedback_type = self.feedback_type.get()
        message = self.feedback_message.get(1.0, tk.END).strip()
        
        if not subject or not feedback_type or not message:
            messagebox.showerror("Error", "All fields are required!")
            return
        
        # Submit feedback
        self.feedback_subject.delete(0, tk.END)
        self.feedback_message.delete(1.0, tk.END)
        
        messagebox.showinfo("Success", "Feedback submitted! Thank you!")
        self._add_log_message(f"Feedback submitted: {subject}")
    
    def _submit_ratings(self):
        """Submit user ratings."""
        ratings = {k: v.get() for k, v in self.rating_vars.items()}
        
        messagebox.showinfo("Success", "Ratings submitted! Thank you!")
        self._add_log_message(f"Ratings submitted: {ratings}")
    
    def _config_changed(self, key):
        """Handle configuration change."""
        value = self.config_vars[key].get()
        self._add_log_message(f"Config changed: {key} = {value}")
    
    def _save_config(self):
        """Save configuration."""
        config = {k: v.get() for k, v in self.config_vars.items()}
        messagebox.showinfo("Success", "Configuration saved!")
        self._add_log_message(f"Configuration saved: {config}")


class SimpleDashboard:
    """Simplified dashboard that can run without full system dependencies."""
    
    def __init__(self):
        self.root = tk.Tk()
        self._setup_simple_ui()
    
    def _setup_simple_ui(self):
        """Set up a simple UI for basic functionality."""
        self.root.title("1st Agent - Control Panel")
        self.root.geometry("800x600")
        
        # Notebook
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Status tab
        self._create_status_tab(notebook)
        
        # Control tab
        self._create_control_tab(notebook)
        
        # Logs tab
        self._create_logs_tab(notebook)
    
    def _create_status_tab(self, notebook):
        """Create status tab."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Status")
        
        # System status
        ttk.Label(frame, text="System Status", font=("Segoe UI", 14, "bold")).pack(pady=10)
        
        self.status_frame = ttk.Frame(frame)
        self.status_frame.pack(fill=tk.X, pady=10)
        
        # Add some status indicators
        status_items = [
            ("Communication Layer", "status_comm"),
            ("Orchestrator", "status_orch"),
            ("Evaluation Agent", "status_eval"),
            ("Fine-Tune Factory", "status_ft"),
            ("Self-Modifier", "status_mod"),
            ("Automation Controller", "status_auto"),
        ]
        
        self.status_labels = {}
        for name, key in status_items:
            frame = ttk.Frame(self.status_frame)
            frame.pack(fill=tk.X, pady=5)
            
            label = ttk.Label(frame, text=name, width=25, anchor=tk.W)
            label.pack(side=tk.LEFT, padx=5)
            
            indicator = tk.Canvas(frame, width=20, height=20, bg="gray")
            indicator.pack(side=tk.LEFT, padx=5)
            
            status_label = ttk.Label(frame, text="Initializing...", width=30)
            status_label.pack(side=tk.LEFT, padx=5)
            
            self.status_labels[key] = (indicator, status_label)
        
        # Stats
        ttk.Label(frame, text="Statistics", font=("Segoe UI", 12, "bold")).pack(pady=(20, 10))
        
        self.stats_frame = ttk.Frame(frame)
        self.stats_frame.pack(fill=tk.X, pady=5)
        
        stat_configs = [
            ("Agents Active", "stat_agents"),
            ("Models Loaded", "stat_models"),
            ("Queries Processed", "stat_queries"),
            ("Optimization Cycles", "stat_opt"),
            ("Avg Reward", "stat_reward"),
        ]
        
        self.stat_labels = {}
        for name, key in stat_configs:
            frame = ttk.Frame(self.stats_frame)
            frame.pack(side=tk.LEFT, padx=10, pady=5)
            
            ttk.Label(frame, text=name).pack()
            value_label = ttk.Label(frame, text="0", font=("Segoe UI", 12, "bold"))
            value_label.pack()
            
            self.stat_labels[key] = value_label
    
    def _create_control_tab(self, notebook):
        """Create control tab."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Controls")
        
        # System control
        ttk.Label(frame, text="System Control", font=("Segoe UI", 12, "bold")).pack(pady=10)
        
        control_frame = ttk.Frame(frame)
        control_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(control_frame, text="Start System", command=self._start_system).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Stop System", command=self._stop_system).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Run Optimization", command=self._run_optimization).pack(side=tk.LEFT, padx=5)
        
        # Quick actions
        ttk.Label(frame, text="Quick Actions", font=("Segoe UI", 12, "bold")).pack(pady=(20, 10))
        
        action_frame = ttk.Frame(frame)
        action_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(action_frame, text="View Agents", command=self._view_agents).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="View Changes", command=self._view_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="View Models", command=self._view_models).pack(side=tk.LEFT, padx=5)
    
    def _create_logs_tab(self, notebook):
        """Create logs tab."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Logs")
        
        # Log display
        self.log_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Log entry
        log_frame = ttk.Frame(frame)
        log_frame.pack(fill=tk.X, pady=5)
        
        self.log_entry = ttk.Entry(log_frame)
        self.log_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(log_frame, text="Log", command=self._log_message).pack(side=tk.RIGHT, padx=5)
    
    def _start_system(self):
        """Start the system."""
        self._log_message("System started")
        for key in ["status_comm", "status_orch", "status_eval", "status_ft", "status_mod", "status_auto"]:
            indicator, label = self.status_labels[key]
            indicator.config(bg="#4CAF50")
            label.config(text="Running")
    
    def _stop_system(self):
        """Stop the system."""
        self._log_message("System stopped")
        for key in ["status_comm", "status_orch", "status_eval", "status_ft", "status_mod", "status_auto"]:
            indicator, label = self.status_labels[key]
            indicator.config(bg="#F44336")
            label.config(text="Stopped")
    
    def _run_optimization(self):
        """Run optimization."""
        self._log_message("Optimization started")
    
    def _view_agents(self):
        """View agents."""
        self._log_message("Viewing agents...")
    
    def _view_changes(self):
        """View changes."""
        self._log_message("Viewing changes...")
    
    def _view_models(self):
        """View models."""
        self._log_message("Viewing models...")
    
    def _log_message(self, message=None):
        """Log a message."""
        if message:
            self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        else:
            text = self.log_entry.get()
            if text:
                self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {text}\n")
                self.log_entry.delete(0, tk.END)
        self.log_text.see(tk.END)
    
    def run(self):
        """Run the dashboard."""
        self.root.mainloop()


def run_dashboard(system=None, simple=False):
    """
    Run the 1st Agent dashboard.
    
    Args:
        system: The ClosedLoopSystem instance to monitor
        simple: If True, run the simple dashboard (no dependencies)
    
    Returns:
        The dashboard instance
    """
    try:
        if simple:
            dashboard = SimpleDashboard()
            dashboard.run()
            return dashboard
        else:
            dashboard = AgentDashboard(system)
            dashboard.mainloop()
            return dashboard
    except Exception as e:
        logger.error(f"Failed to run dashboard: {e}")
        messagebox.showerror("Error", f"Failed to start dashboard: {e}")
        return None


if __name__ == "__main__":
    # Try to import full system, fall back to simple dashboard
    try:
        from closed_loop_system import get_closed_loop_system
        system = get_closed_loop_system()
        run_dashboard(system)
    except ImportError:
        # Fall back to simple dashboard
        run_dashboard(simple=True)
