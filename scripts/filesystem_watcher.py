#!/usr/bin/env python3
"""
Filesystem Watcher - Monitors local file system for changes using watchdog
Part of the Personal AI Employee Silver Tier implementation
"""

import os
import sys
import json
import time
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Set
import threading

# Try to import watchdog, provide fallback
try:
    from watchdog.observers import Observer
    from watchdog.events import (
        FileSystemEventHandler,
        FileCreatedEvent,
        FileModifiedEvent,
        FileMovedEvent,
        FileDeletedEvent,
        DirCreatedEvent,
        DirDeletedEvent,
        DirMovedEvent
    )
    WATCHDOG_AVAILABLE = True
except ImportError as e:
    print(f"Warning: watchdog not installed: {e}")
    print("Install with: pip install watchdog")
    WATCHDOG_AVAILABLE = False

# Configuration
VAULT_BASE = Path(__file__).parent / "AI_Employee_Vault"
INBOX_DIR = VAULT_BASE / "Inbox"
NEEDS_ACTION_DIR = VAULT_BASE / "Needs_Action"
DONE_DIR = VAULT_BASE / "Done"
LOGS_DIR = VAULT_BASE / "Logs"
WATCHED_DIRS = [
    Path(__file__).parent / "watched",  # Default watched directory
]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "filesystem_watcher.log" if LOGS_DIR.exists() else "filesystem_watcher.log")
    ]
)
logger = logging.getLogger(__name__)


class FileChangeHandler(FileSystemEventHandler):
    """Handles file system events and routes files to appropriate vaults."""
    
    def __init__(self, watcher: "FilesystemWatcher"):
        super().__init__()
        self.watcher = watcher
        self._debounce: Dict[str, threading.Timer] = {}
        self._debounce_delay = 0.5  # seconds
    
    def _debounce_event(self, path: str, callback):
        """Debounce rapid file events."""
        if path in self._debounce:
            self._debounce[path].cancel()
        
        timer = threading.Timer(self._debounce_delay, callback, args=[path])
        self._debounce[path] = timer
        timer.start()
    
    def _process_file(self, filepath: str, event_type: str):
        """Process a file change event."""
        try:
            path = Path(filepath)
            
            # Skip hidden files and temporary files
            if path.name.startswith(".") or path.name.startswith("~"):
                logger.debug(f"Skipping hidden/temp file: {path.name}")
                return
            
            # Skip log files from the watcher itself
            if "filesystem_watcher" in path.name:
                return
            
            # Ensure directories exist
            INBOX_DIR.mkdir(parents=True, exist_ok=True)
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            
            # Create file event record
            event_record = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "file_path": str(path),
                "file_name": path.name,
                "file_size": path.stat().st_size if path.exists() else 0,
                "is_directory": path.is_dir() if path.exists() else False,
                "processed": False
            }
            
            # Handle based on file type and location
            if path.exists() and path.is_file():
                self._handle_file(path, event_record)
            elif path.exists() and path.is_dir():
                self._handle_directory(path, event_record)
            elif event_type == "deleted":
                self._handle_deletion(path, event_record)
            
            # Log the event
            self._log_event(event_record)
            
        except Exception as e:
            logger.error(f"Error processing file event: {e}")
            self._log_error(filepath, event_type, str(e))
    
    def _handle_file(self, path: Path, event_record: Dict[str, Any]):
        """Handle a file event."""
        try:
            # Determine destination based on file type
            dest_dir = self._classify_file(path)
            
            if dest_dir != INBOX_DIR:
                # Copy to classified directory
                dest_path = dest_dir / path.name
                shutil.copy2(path, dest_path)
                logger.info(f"Copied {path.name} to {dest_dir.name}")
                event_record["destination"] = str(dest_path)
                event_record["classification"] = dest_dir.name
            else:
                # Copy to inbox for review
                dest_path = INBOX_DIR / path.name
                shutil.copy2(path, dest_path)
                logger.info(f"New file {path.name} added to inbox")
                event_record["destination"] = str(dest_path)
                event_record["classification"] = "Inbox"
            
            event_record["processed"] = True
            
        except Exception as e:
            logger.error(f"Error handling file {path}: {e}")
            event_record["error"] = str(e)
    
    def _handle_directory(self, path: Path, event_record: Dict[str, Any]):
        """Handle a directory event."""
        logger.info(f"Directory event: {path.name} ({event_record['event_type']})")
        event_record["processed"] = True
    
    def _handle_deletion(self, path: Path, event_record: Dict[str, Any]):
        """Handle a file deletion event."""
        logger.info(f"File deleted: {path.name}")
        event_record["processed"] = True
    
    def _classify_file(self, path: Path) -> Path:
        """Classify a file and determine its destination."""
        suffix = path.suffix.lower()
        name = path.name.lower()
        
        # Configuration files -> Needs Action
        if suffix in [".env", ".config", ".ini", ".yaml", ".yml", ".toml"]:
            return NEEDS_ACTION_DIR
        
        # Log files -> Logs
        if suffix in [".log"] or "log" in name:
            return LOGS_DIR
        
        # Data files -> Inbox for review
        if suffix in [".json", ".csv", ".xml", ".txt", ".md"]:
            return INBOX_DIR
        
        # Documents -> Inbox for review
        if suffix in [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"]:
            return INBOX_DIR
        
        # Images -> Done (archived)
        if suffix in [".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp"]:
            return DONE_DIR
        
        # Default to Inbox
        return INBOX_DIR
    
    def _log_event(self, event_record: Dict[str, Any]):
        """Log an event to the logs directory."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d")
            log_file = LOGS_DIR / f"filesystem_events_{timestamp}.jsonl"
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event_record) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging event: {e}")
    
    def _log_error(self, filepath: str, event_type: str, error: str):
        """Log an error to the logs directory."""
        try:
            error_record = {
                "timestamp": datetime.now().isoformat(),
                "filepath": filepath,
                "event_type": event_type,
                "error": error
            }
            
            log_file = LOGS_DIR / f"filesystem_errors_{int(time.time())}.json"
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(error_record, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error logging error: {e}")
    
    # Event handlers
    def on_created(self, event):
        """Handle file creation events."""
        if isinstance(event, FileCreatedEvent):
            self._debounce_event(event.src_path, lambda p: self._process_file(p, "created"))
    
    def on_modified(self, event):
        """Handle file modification events."""
        if isinstance(event, FileModifiedEvent):
            self._debounce_event(event.src_path, lambda p: self._process_file(p, "modified"))
    
    def on_moved(self, event):
        """Handle file move events."""
        if isinstance(event, FileMovedEvent):
            self._debounce_event(event.dest_path, lambda p: self._process_file(p, "moved"))
    
    def on_deleted(self, event):
        """Handle file deletion events."""
        if isinstance(event, FileDeletedEvent):
            self._debounce_event(event.src_path, lambda p: self._process_file(p, "deleted"))


class FilesystemWatcher:
    """Watches specified directories for file changes."""
    
    def __init__(self, watch_dirs: Optional[list] = None):
        self.watch_dirs = watch_dirs or WATCHED_DIRS
        self.observer: Optional[Observer] = None
        self.handler: Optional[FileChangeHandler] = None
        self.running = False
        self.error_count = 0
        self.max_errors = 5
        self.status: Dict[str, Any] = {}
        
    def start(self):
        """Start watching directories."""
        if not WATCHDOG_AVAILABLE:
            logger.error("watchdog not available, running in demo mode")
            self._run_demo_mode()
            return
        
        try:
            # Ensure directories exist
            for dir_path in self.watch_dirs:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
                logger.info(f"Watching directory: {dir_path}")
            
            # Create handler and observer
            self.handler = FileChangeHandler(self)
            self.observer = Observer()
            
            # Schedule watches
            for dir_path in self.watch_dirs:
                self.observer.schedule(self.handler, str(dir_path), recursive=False)
            
            # Start observer
            self.observer.start()
            self.running = True
            self.error_count = 0
            
            logger.info(f"Filesystem watcher started, monitoring {len(self.watch_dirs)} directories")
            self._update_status("running", "Monitoring directories")
            
            # Keep running
            while self.running:
                time.sleep(1)
                self._update_status("running", f"Monitoring {len(self.watch_dirs)} directories")
            
        except Exception as e:
            logger.error(f"Error starting filesystem watcher: {e}")
            self.error_count += 1
            self._handle_error(e)
    
    def _run_demo_mode(self):
        """Run in demo mode without watchdog."""
        logger.info("Running in demo mode - simulating file watcher")
        self.running = True
        
        while self.running:
            self._update_status("demo", "Demo mode - watchdog not installed")
            time.sleep(60)
    
    def _handle_error(self, error: Exception):
        """Handle errors with auto-recovery."""
        logger.warning(f"Error count: {self.error_count}/{self.max_errors}")
        
        if self.error_count >= self.max_errors:
            logger.error("Max errors reached, attempting recovery...")
            self.error_count = 0
            
            # Attempt to restart observer
            try:
                if self.observer:
                    self.observer.stop()
                    self.observer.join()
                self.start()
            except Exception as e:
                logger.error(f"Recovery failed: {e}")
                self._update_status("error", str(e))
    
    def _update_status(self, status: str, message: str):
        """Update status file."""
        try:
            self.status = {
                "timestamp": datetime.now().isoformat(),
                "status": status,
                "message": message,
                "watched_directories": [str(d) for d in self.watch_dirs],
                "error_count": self.error_count,
                "watchdog_available": WATCHDOG_AVAILABLE
            }
            
            status_file = LOGS_DIR / "filesystem_watcher_status.json"
            with open(status_file, "w") as f:
                json.dump(self.status, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to update status: {e}")
    
    def stop(self):
        """Stop watching directories."""
        logger.info("Stopping filesystem watcher...")
        self.running = False
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("Observer stopped")
        
        self._update_status("stopped", "Watcher stopped by user")


def main():
    """Entry point for Filesystem Watcher."""
    import signal
    
    # Get watched directories from environment or use defaults
    watched_dirs = WATCHED_DIRS
    if os.environ.get("WATCHED_DIRS"):
        watched_dirs = [Path(p.strip()) for p in os.environ.get("WATCHED_DIRS", "").split(",")]
    
    watcher = FilesystemWatcher(watch_dirs=watched_dirs)
    
    # Handle shutdown signals
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        watcher.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start watching
    try:
        watcher.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        watcher.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
