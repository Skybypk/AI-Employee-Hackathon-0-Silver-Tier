#!/usr/bin/env python3
"""
Cron Job Scheduler - Schedules and runs periodic tasks
Part of the Personal AI Employee Silver Tier implementation

This scheduler runs periodic tasks like:
- Checking for new emails
- Processing inbox items
- Generating plans
- Cleaning up old files
- Running diagnostics
"""

import os
import sys
import json
import time
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Callable, Optional
import threading
import signal

# Configuration
VAULT_BASE = Path(__file__).parent / "AI_Employee_Vault"
LOGS_DIR = VAULT_BASE / "Logs"
SCRIPTS_DIR = Path(__file__).parent / "scripts"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "scheduler.log" if LOGS_DIR.exists() else "scheduler.log")
    ]
)
logger = logging.getLogger(__name__)


class ScheduledTask:
    """Represents a scheduled task."""
    
    def __init__(
        self,
        name: str,
        func: Optional[Callable] = None,
        command: Optional[List[str]] = None,
        interval: int = 300,  # seconds
        enabled: bool = True,
        last_run: Optional[datetime] = None,
        next_run: Optional[datetime] = None,
        run_count: int = 0,
        error_count: int = 0,
    ):
        self.name = name
        self.func = func
        self.command = command
        self.interval = interval
        self.enabled = enabled
        self.last_run = last_run
        self.next_run = next_run or datetime.now()
        self.run_count = run_count
        self.error_count = error_count
    
    def should_run(self) -> bool:
        """Check if the task should run."""
        if not self.enabled:
            return False
        if self.next_run is None:
            return True
        return datetime.now() >= self.next_run
    
    def mark_run(self, success: bool):
        """Mark the task as run."""
        self.last_run = datetime.now()
        self.next_run = datetime.now()
        if self.interval > 0:
            from datetime import timedelta
            self.next_run += timedelta(seconds=self.interval)
        
        self.run_count += 1
        if not success:
            self.error_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for status reporting."""
        return {
            "name": self.name,
            "interval": self.interval,
            "enabled": self.enabled,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count,
            "error_count": self.error_count,
        }


class Scheduler:
    """Main scheduler class that manages and runs scheduled tasks."""
    
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.error_count = 0
        self.max_errors = 10
        
        # Ensure logs directory exists
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Register default tasks
        self._register_default_tasks()
    
    def _register_default_tasks(self):
        """Register default scheduled tasks."""
        # Gmail watcher check (every 60 seconds)
        self.register_task(
            name="gmail_check",
            command=[sys.executable, str(SCRIPTS_DIR / "gmail_watcher.py")],
            interval=60,
            enabled=False  # Disabled by default, enable with env var
        )
        
        # Filesystem watcher check (every 30 seconds)
        self.register_task(
            name="filesystem_check",
            command=[sys.executable, str(SCRIPTS_DIR / "filesystem_watcher.py")],
            interval=30,
            enabled=False
        )
        
        # Plan generation (every 5 minutes)
        self.register_task(
            name="generate_plans",
            command=[sys.executable, str(SCRIPTS_DIR / "claude_reasoning.py")],
            interval=300,
            enabled=True
        )
        
        # Approval workflow check (every 2 minutes)
        self.register_task(
            name="approval_check",
            command=[sys.executable, str(SCRIPTS_DIR / "approval_workflow.py"), "stats"],
            interval=120,
            enabled=True
        )
        
        # Cleanup old logs (every hour)
        self.register_task(
            name="cleanup_logs",
            func=self._cleanup_old_logs,
            interval=3600,
            enabled=True
        )
        
        # Health check (every 10 minutes)
        self.register_task(
            name="health_check",
            func=self._health_check,
            interval=600,
            enabled=True
        )
        
        # Update intervals from environment variables
        for task_name in list(self.tasks.keys()):
            env_var = f"SCHEDULER_INTERVAL_{task_name.upper()}"
            if env_var in os.environ:
                try:
                    new_interval = int(os.environ[env_var])
                    self.tasks[task_name].interval = new_interval
                    logger.info(f"Updated interval for {task_name}: {new_interval}s")
                except ValueError:
                    pass
    
    def register_task(
        self,
        name: str,
        func: Optional[Callable] = None,
        command: Optional[List[str]] = None,
        interval: int = 300,
        enabled: bool = True,
    ):
        """Register a new scheduled task."""
        if func is None and command is None:
            raise ValueError("Either func or command must be provided")
        
        self.tasks[name] = ScheduledTask(
            name=name,
            func=func,
            command=command,
            interval=interval,
            enabled=enabled,
        )
        logger.info(f"Registered task: {name} (interval: {interval}s)")
    
    def enable_task(self, name: str):
        """Enable a task."""
        if name in self.tasks:
            self.tasks[name].enabled = True
            logger.info(f"Enabled task: {name}")
    
    def disable_task(self, name: str):
        """Disable a task."""
        if name in self.tasks:
            self.tasks[name].enabled = False
            logger.info(f"Disabled task: {name}")
    
    def run_task(self, task: ScheduledTask) -> bool:
        """Run a single task."""
        logger.info(f"Running task: {task.name}")
        
        try:
            if task.func:
                # Run Python function
                result = task.func()
                logger.info(f"Task {task.name} completed: {result}")
                return True
            
            elif task.command:
                # Run external command
                result = subprocess.run(
                    task.command,
                    capture_output=True,
                    text=True,
                    timeout=min(task.interval - 1, 300),  # Max 5 min timeout
                )
                
                if result.returncode == 0:
                    logger.info(f"Task {task.name} completed successfully")
                    return True
                else:
                    logger.error(f"Task {task.name} failed: {result.stderr}")
                    return False
            
            return False
            
        except subprocess.TimeoutExpired:
            logger.error(f"Task {task.name} timed out")
            return False
        except Exception as e:
            logger.error(f"Task {task.name} error: {e}")
            return False
    
    def _cleanup_old_logs(self, days: int = 7) -> Dict[str, Any]:
        """Clean up old log files."""
        try:
            cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
            cleaned = 0
            
            for file_path in LOGS_DIR.glob("*.log"):
                if file_path.stat().st_mtime < cutoff:
                    file_path.unlink()
                    cleaned += 1
            
            logger.info(f"Cleaned up {cleaned} old log files")
            return {"cleaned": cleaned, "status": "success"}
            
        except Exception as e:
            logger.error(f"Error cleaning logs: {e}")
            return {"error": str(e), "status": "error"}
    
    def _health_check(self) -> Dict[str, Any]:
        """Run system health check."""
        try:
            health = {
                "timestamp": datetime.now().isoformat(),
                "status": "healthy",
                "checks": {},
            }
            
            # Check vault directories
            vault_dirs = ["Inbox", "Needs_Action", "Done", "Logs", "Plans", 
                         "Pending_Approval", "Approved", "Rejected"]
            for dir_name in vault_dirs:
                dir_path = VAULT_BASE / dir_name
                exists = dir_path.exists()
                health["checks"][dir_name] = "ok" if exists else "missing"
                if not exists:
                    health["status"] = "degraded"
            
            # Check disk space
            try:
                import shutil
                total, used, free = shutil.disk_usage(VAULT_BASE)
                health["checks"]["disk_space_gb"] = round(free / (1024**3), 2)
                if free < 1024**3:  # Less than 1GB
                    health["status"] = "warning"
            except:
                pass
            
            # Save health report
            health_file = LOGS_DIR / "health_check.json"
            with open(health_file, "w") as f:
                json.dump(health, f, indent=2)
            
            logger.info(f"Health check completed: {health['status']}")
            return health
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "running": self.running,
            "tasks": {name: task.to_dict() for name, task in self.tasks.items()},
            "timestamp": datetime.now().isoformat(),
        }
    
    def save_status(self):
        """Save current status to file."""
        try:
            status = self.get_status()
            status_file = LOGS_DIR / "scheduler_status.json"
            with open(status_file, "w") as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save status: {e}")
    
    def run(self):
        """Run the scheduler main loop."""
        logger.info("Starting scheduler...")
        self.running = True
        self.error_count = 0
        
        # Save initial status
        self.save_status()
        
        while self.running:
            try:
                # Check and run tasks
                for task in self.tasks.values():
                    if task.should_run():
                        success = self.run_task(task)
                        task.mark_run(success)
                        
                        if not success:
                            self.error_count += 1
                
                # Save status
                self.save_status()
                
                # Check for too many errors
                if self.error_count >= self.max_errors:
                    logger.error("Too many errors, scheduler may be unstable")
                    # Could implement backoff or alerting here
                
                # Sleep for a bit
                time.sleep(1)
                
            except KeyboardInterrupt:
                logger.info("Received interrupt, stopping scheduler...")
                self.running = False
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                self.error_count += 1
                time.sleep(5)  # Backoff on error
        
        logger.info("Scheduler stopped")
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False


def main():
    """Entry point for scheduler."""
    # Handle shutdown signals
    scheduler = Scheduler()
    
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        scheduler.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Check for command line args
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "status":
            # Just show status and exit
            status = scheduler.get_status()
            print(json.dumps(status, indent=2))
            return
        
        elif command == "run-task":
            # Run a specific task once
            if len(sys.argv) > 2:
                task_name = sys.argv[2]
                if task_name in scheduler.tasks:
                    success = scheduler.run_task(scheduler.tasks[task_name])
                    sys.exit(0 if success else 1)
                else:
                    print(f"Task not found: {task_name}")
                    sys.exit(1)
        
        elif command == "enable":
            if len(sys.argv) > 2:
                scheduler.enable_task(sys.argv[2])
        
        elif command == "disable":
            if len(sys.argv) > 2:
                scheduler.disable_task(sys.argv[2])
    
    # Run scheduler
    try:
        scheduler.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
