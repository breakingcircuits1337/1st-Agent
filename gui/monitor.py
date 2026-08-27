"""
System Monitor - Monitors system health and performance.

This module provides:
- Real-time system monitoring
- Performance metrics collection
- Health checks
- Alerting
"""

import logging
import platform
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

# Try to import psutil, but make it optional
try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False
    psutil = None

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class SystemMetrics:
    """System performance metrics."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    memory_total: float = 0.0
    disk_usage: float = 0.0
    disk_total: float = 0.0
    uptime: float = 0.0
    process_count: int = 0
    thread_count: int = 0
    network_io: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "memory_total": self.memory_total,
            "disk_usage": self.disk_usage,
            "disk_total": self.disk_total,
            "uptime": self.uptime,
            "process_count": self.process_count,
            "thread_count": self.thread_count,
            "network_io": self.network_io
        }


@dataclass
class HealthCheck:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "details": self.details
        }


class SystemMonitor:
    """
    Monitors system health and performance.
    
    This class:
    - Collects system metrics (CPU, memory, disk, etc.)
    - Runs health checks
    - Tracks performance over time
    - Generates alerts for issues
    """
    
    def __init__(self, interval: float = 5.0):
        self.interval = interval  # seconds between updates
        self._metrics_history: List[SystemMetrics] = []
        self._health_history: List[HealthCheck] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._callbacks: List[Callable] = []
        self._start_time = datetime.now()
        
        # Alert thresholds
        self._alert_thresholds = {
            "cpu_usage": 90.0,
            "memory_usage": 85.0,
            "disk_usage": 90.0
        }
        
        logger.info("System monitor initialized")
    
    def start(self):
        """Start the monitoring thread."""
        with self._lock:
            if self._running:
                return
            
            self._running = True
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._thread.start()
            logger.info("System monitor started")
    
    def stop(self):
        """Stop the monitoring thread."""
        with self._lock:
            self._running = False
            if self._thread:
                self._thread.join(timeout=5)
            logger.info("System monitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                # Collect metrics
                metrics = self.collect_metrics()
                self._metrics_history.append(metrics)
                
                # Run health checks
                health_checks = self.run_health_checks(metrics)
                self._health_history.extend(health_checks)
                
                # Check for alerts
                self._check_alerts(metrics, health_checks)
                
                # Notify callbacks
                self._notify_callbacks(metrics, health_checks)
                
                # Retain only recent history (last 100 entries)
                with self._lock:
                    self._metrics_history = self._metrics_history[-100:]
                    self._health_history = self._health_history[-100:]
                
                time.sleep(self.interval)
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                time.sleep(5)
    
    def collect_metrics(self) -> SystemMetrics:
        """Collect system metrics."""
        try:
            if not _HAS_PSUTIL:
                # Return basic metrics without psutil
                uptime = (datetime.now() - self._start_time).total_seconds()
                return SystemMetrics(
                    cpu_usage=0.0,
                    memory_usage=0.0,
                    memory_total=0.0,
                    disk_usage=0.0,
                    disk_total=0.0,
                    uptime=uptime,
                    process_count=0,
                    thread_count=0,
                    network_io={}
                )
            
            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # Memory
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            memory_total = memory.total / (1024 * 1024)  # MB
            
            # Disk
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent
            disk_total = disk.total / (1024 * 1024 * 1024)  # GB
            
            # Uptime
            uptime = (datetime.now() - self._start_time).total_seconds()
            
            # Process info
            process = psutil.Process()
            process_count = len(psutil.pids())
            thread_count = process.num_threads()
            
            # Network
            net_io = psutil.net_io_counters()
            network_io = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv
            }
            
            return SystemMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                memory_total=memory_total,
                disk_usage=disk_usage,
                disk_total=disk_total,
                uptime=uptime,
                process_count=process_count,
                thread_count=thread_count,
                network_io=network_io
            )
            
        except Exception as e:
            logger.warning(f"Failed to collect metrics: {e}")
            return SystemMetrics()
    
    def run_health_checks(self, metrics: SystemMetrics) -> List[HealthCheck]:
        """Run health checks on system metrics."""
        checks = []
        
        # CPU check
        cpu_status = HealthStatus.HEALTHY
        if metrics.cpu_usage > 90:
            cpu_status = HealthStatus.CRITICAL
        elif metrics.cpu_usage > 75:
            cpu_status = HealthStatus.WARNING
        
        checks.append(HealthCheck(
            name="CPU Usage",
            status=cpu_status,
            message=f"CPU at {metrics.cpu_usage:.1f}%",
            details={"usage": metrics.cpu_usage}
        ))
        
        # Memory check
        mem_status = HealthStatus.HEALTHY
        if metrics.memory_usage > 90:
            mem_status = HealthStatus.CRITICAL
        elif metrics.memory_usage > 80:
            mem_status = HealthStatus.WARNING
        
        checks.append(HealthCheck(
            name="Memory Usage",
            status=mem_status,
            message=f"Memory at {metrics.memory_usage:.1f}%",
            details={"usage": metrics.memory_usage, "total": metrics.memory_total}
        ))
        
        # Disk check
        disk_status = HealthStatus.HEALTHY
        if metrics.disk_usage > 90:
            disk_status = HealthStatus.CRITICAL
        elif metrics.disk_usage > 80:
            disk_status = HealthStatus.WARNING
        
        checks.append(HealthCheck(
            name="Disk Usage",
            status=disk_status,
            message=f"Disk at {metrics.disk_usage:.1f}%",
            details={"usage": metrics.disk_usage, "total": metrics.disk_total}
        ))
        
        # Uptime check
        checks.append(HealthCheck(
            name="System Uptime",
            status=HealthStatus.HEALTHY,
            message=f"Uptime: {metrics.uptime:.0f}s",
            details={"uptime": metrics.uptime}
        ))
        
        return checks
    
    def _check_alerts(self, metrics: SystemMetrics, health_checks: List[HealthCheck]):
        """Check for alert conditions."""
        alerts = []
        
        for check in health_checks:
            if check.status in [HealthStatus.CRITICAL, HealthStatus.WARNING]:
                alerts.append(check)
        
        for alert in alerts:
            logger.warning(f"ALERT: {alert.name} - {alert.message}")
    
    def _notify_callbacks(self, metrics: SystemMetrics, health_checks: List[HealthCheck]):
        """Notify registered callbacks."""
        for callback in self._callbacks:
            try:
                callback(metrics, health_checks)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def on_metrics_update(self, callback: Callable):
        """Register a callback for metrics updates."""
        self._callbacks.append(callback)
    
    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """Get the most recent metrics."""
        with self._lock:
            return self._metrics_history[-1] if self._metrics_history else None
    
    def get_metrics_history(self, count: int = 10) -> List[SystemMetrics]:
        """Get recent metrics history."""
        with self._lock:
            return list(reversed(self._metrics_history[-count:]))
    
    def get_health_history(self, count: int = 10) -> List[HealthCheck]:
        """Get recent health check history."""
        with self._lock:
            return list(reversed(self._health_history[-count:]))
    
    def get_average_metrics(self, count: int = 10) -> Dict[str, float]:
        """Get average metrics over a period."""
        with self._lock:
            recent = self._metrics_history[-count:]
            if not recent:
                return {}
            
            avg = SystemMetrics()
            for metrics in recent:
                avg.cpu_usage += metrics.cpu_usage
                avg.memory_usage += metrics.memory_usage
                avg.disk_usage += metrics.disk_usage
            
            count = len(recent)
            return {
                "cpu_usage": avg.cpu_usage / count,
                "memory_usage": avg.memory_usage / count,
                "disk_usage": avg.disk_usage / count
            }
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "machine": platform.machine(),
            "node_name": platform.node()
        }
        
        if _HAS_PSUTIL:
            try:
                # Get more detailed info
                info["cpu_cores"] = psutil.cpu_count(logical=True)
                info["cpu_frequency"] = psutil.cpu_freq().max if psutil.cpu_freq() else 0
                
                memory = psutil.virtual_memory()
                info["total_memory_mb"] = memory.total / (1024 * 1024)
                
                disk = psutil.disk_usage('/')
                info["total_disk_gb"] = disk.total / (1024 * 1024 * 1024)
                
            except Exception:
                pass
        
        return info
    
    def get_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        return {
            "running": self._running,
            "interval": self.interval,
            "metrics_count": len(self._metrics_history),
            "health_checks_count": len(self._health_history),
            "current_metrics": self.get_current_metrics().to_dict() if self.get_current_metrics() else {},
            "system_info": self.get_system_info()
        }


# Global monitor instance
_global_monitor = None


def get_monitor(interval: float = 5.0) -> SystemMonitor:
    """Get or create the global system monitor."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = SystemMonitor(interval)
    return _global_monitor


if __name__ == "__main__":
    # Demo usage
    logger.info("Starting system monitor demo...")
    
    # Create monitor
    monitor = get_monitor(interval=2.0)
    
    # Start monitoring
    monitor.start()
    
    # Collect metrics manually
    metrics = monitor.collect_metrics()
    print("Current Metrics:")
    print(f"  CPU Usage: {metrics.cpu_usage:.1f}%")
    print(f"  Memory Usage: {metrics.memory_usage:.1f}%")
    print(f"  Disk Usage: {metrics.disk_usage:.1f}%")
    print(f"  Uptime: {metrics.uptime:.0f}s")
    print(f"  Process Count: {metrics.process_count}")
    print(f"  Thread Count: {metrics.thread_count}")
    
    # Run health checks
    checks = monitor.run_health_checks(metrics)
    print("\nHealth Checks:")
    for check in checks:
        print(f"  {check.name}: {check.status.value} - {check.message}")
    
    # Get system info
    info = monitor.get_system_info()
    print("\nSystem Info:")
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    # Run for a while
    time.sleep(5)
    
    # Stop monitoring
    monitor.stop()
    
    # Get history
    print("\nMetrics History:")
    for i, m in enumerate(monitor.get_metrics_history(3)):
        print(f"  {i+1}. CPU: {m.cpu_usage:.1f}%, Memory: {m.memory_usage:.1f}%")
    
    logger.info("Demo completed")
