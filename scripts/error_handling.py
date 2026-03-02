#!/usr/bin/env python3
"""
Error Handling Utilities
Comprehensive error handling with automatic recovery
Part of the Personal AI Employee Silver Tier implementation
"""

import os
import sys
import time
import logging
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Callable, Any, Dict, List, Type
from functools import wraps

# Configuration
VAULT_BASE = Path(__file__).parent / "AI_Employee_Vault"
LOGS_DIR = VAULT_BASE / "Logs"
ERRORS_DIR = LOGS_DIR / "Errors"

# Ensure directories exist
ERRORS_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging
logger = logging.getLogger(__name__)


class ErrorCategory:
    """Error categories for classification."""
    TRANSIENT = "transient"      # Network issues, rate limits
    CONFIGURATION = "configuration"  # Missing config, invalid settings
    DATA = "data"               # Invalid input, parsing errors
    SYSTEM = "system"           # Disk full, permissions
    EXTERNAL = "external"       # Third-party API failures
    UNKNOWN = "unknown"


class RecoveryStrategy:
    """Recovery strategies for different error types."""
    RETRY = "retry"                    # Retry with backoff
    RETRY_WITH_BACKOFF = "backoff"     # Retry with exponential backoff
    FALLBACK = "fallback"              # Use fallback implementation
    SKIP = "skip"                      # Skip and continue
    ALERT = "alert"                    # Alert and pause
    RESTART = "restart"                # Restart component


class ErrorHandler:
    """Comprehensive error handler with automatic recovery."""
    
    def __init__(
        self,
        name: str = "default",
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
    ):
        self.name = name
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.error_count = 0
        self.success_count = 0
        self.last_error: Optional[Exception] = None
        self.last_error_time: Optional[datetime] = None
        
        # Strategy mapping
        self.strategies: Dict[Type[Exception], RecoveryStrategy] = {
            ConnectionError: RecoveryStrategy.RETRY_WITH_BACKOFF,
            TimeoutError: RecoveryStrategy.RETRY_WITH_BACKOFF,
            FileNotFoundError: RecoveryStrategy.FALLBACK,
            PermissionError: RecoveryStrategy.ALERT,
            OSError: RecoveryStrategy.RETRY_WITH_BACKOFF,
        }
    
    def classify_error(self, error: Exception) -> ErrorCategory:
        """Classify an error into a category."""
        if isinstance(error, (ConnectionError, TimeoutError)):
            return ErrorCategory.TRANSIENT
        elif isinstance(error, (ValueError, TypeError, KeyError)):
            return ErrorCategory.DATA
        elif isinstance(error, (FileNotFoundError, PermissionError)):
            return ErrorCategory.SYSTEM
        elif isinstance(error, OSError):
            return ErrorCategory.SYSTEM
        else:
            return ErrorCategory.UNKNOWN
    
    def get_recovery_strategy(self, error: Exception) -> RecoveryStrategy:
        """Get the recovery strategy for an error."""
        # Check specific mappings
        for error_type, strategy in self.strategies.items():
            if isinstance(error, error_type):
                return strategy
        
        # Default based on category
        category = self.classify_error(error)
        
        if category == ErrorCategory.TRANSIENT:
            return RecoveryStrategy.RETRY_WITH_BACKOFF
        elif category == ErrorCategory.CONFIGURATION:
            return RecoveryStrategy.FALLBACK
        elif category == ErrorCategory.DATA:
            return RecoveryStrategy.SKIP
        elif category == ErrorCategory.SYSTEM:
            return RecoveryStrategy.ALERT
        else:
            return RecoveryStrategy.RETRY_WITH_BACKOFF
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry with exponential backoff."""
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)
    
    def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        level: int = logging.ERROR,
    ):
        """Log an error with context."""
        self.last_error = error
        self.last_error_time = datetime.now()
        self.error_count += 1
        
        # Log to file
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {},
            "component": self.name,
        }
        
        # Write to error log
        error_file = ERRORS_DIR / f"error_{int(time.time())}_{self.name}.json"
        try:
            import json
            with open(error_file, "w") as f:
                json.dump(log_entry, f, indent=2)
        except:
            pass
        
        # Log with logging module
        logger.log(level, f"Error in {self.name}: {error}")
        if context:
            logger.debug(f"Context: {context}")
    
    def should_retry(self, attempt: int, error: Exception) -> bool:
        """Determine if we should retry."""
        if attempt >= self.max_retries:
            return False
        
        strategy = self.get_recovery_strategy(error)
        return strategy in [
            RecoveryStrategy.RETRY,
            RecoveryStrategy.RETRY_WITH_BACKOFF,
        ]
    
    def execute_with_recovery(
        self,
        func: Callable,
        *args,
        fallback: Optional[Callable] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Any:
        """Execute a function with automatic recovery."""
        attempt = 0
        
        while True:
            try:
                result = func(*args, **kwargs)
                self.success_count += 1
                return result
                
            except Exception as e:
                attempt += 1
                self.log_error(e, context)
                
                # Check if we should retry
                if self.should_retry(attempt - 1, e):
                    delay = self.calculate_delay(attempt - 1)
                    logger.warning(
                        f"Attempt {attempt} failed, retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    continue
                
                # Try fallback if available
                strategy = self.get_recovery_strategy(e)
                if strategy == RecoveryStrategy.FALLBACK and fallback:
                    logger.info(f"Using fallback for {self.name}")
                    try:
                        return fallback(*args, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"Fallback also failed: {fallback_error}")
                
                # Skip or alert
                if strategy == RecoveryStrategy.SKIP:
                    logger.warning(f"Skipping operation due to error: {e}")
                    return None
                
                # Raise if we can't recover
                logger.error(f"Max retries exceeded or unrecoverable error: {e}")
                raise
    
    def reset(self):
        """Reset error counters."""
        self.error_count = 0
        self.last_error = None
        self.last_error_time = None
    
    def get_status(self) -> Dict[str, Any]:
        """Get error handler status."""
        return {
            "name": self.name,
            "error_count": self.error_count,
            "success_count": self.success_count,
            "last_error": str(self.last_error) if self.last_error else None,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
        }


def with_error_handling(
    name: Optional[str] = None,
    max_retries: int = 3,
    fallback: Optional[Callable] = None,
):
    """Decorator for automatic error handling."""
    def decorator(func: Callable) -> Callable:
        func_name = name or func.__name__
        handler = ErrorHandler(func_name, max_retries)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return handler.execute_with_recovery(
                func, *args, fallback=fallback, **kwargs
            )
        
        wrapper.error_handler = handler  # type: ignore
        return wrapper
    
    return decorator


class CircuitBreaker:
    """Circuit breaker pattern for external service calls."""
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half-open
    
    def record_success(self):
        """Record a successful call."""
        self.failures = 0
        self.state = "closed"
    
    def record_failure(self):
        """Record a failed call."""
        self.failures += 1
        self.last_failure_time = datetime.now()
        
        if self.failures >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker {self.name} opened")
    
    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            if self.last_failure_time:
                elapsed = datetime.now() - self.last_failure_time
                if elapsed.total_seconds() >= self.recovery_timeout:
                    self.state = "half-open"
                    logger.info(f"Circuit breaker {self.name} half-open")
                    return True
            return False
        
        # half-open
        return True
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute with circuit breaker protection."""
        if not self.can_execute():
            raise Exception(f"Circuit breaker {self.name} is open")
        
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state,
            "failures": self.failures,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None,
        }


class HealthChecker:
    """System health checker with automatic recovery suggestions."""
    
    def __init__(self):
        self.checks: List[Dict[str, Any]] = []
        self.last_check: Optional[datetime] = None
    
    def register_check(
        self,
        name: str,
        func: Callable[[], bool],
        critical: bool = False,
    ):
        """Register a health check."""
        self.checks.append({
            "name": name,
            "func": func,
            "critical": critical,
            "last_status": None,
            "last_error": None,
        })
    
    def run_checks(self) -> Dict[str, Any]:
        """Run all health checks."""
        results = {
            "timestamp": datetime.now().isoformat(),
            "healthy": True,
            "checks": {},
        }
        
        for check in self.checks:
            try:
                status = check["func"]()
                check["last_status"] = "pass" if status else "fail"
                check["last_error"] = None
                
                results["checks"][check["name"]] = {
                    "status": "pass" if status else "fail",
                    "critical": check["critical"],
                }
                
                if not status and check["critical"]:
                    results["healthy"] = False
                    
            except Exception as e:
                check["last_status"] = "error"
                check["last_error"] = str(e)
                
                results["checks"][check["name"]] = {
                    "status": "error",
                    "error": str(e),
                    "critical": check["critical"],
                }
                
                if check["critical"]:
                    results["healthy"] = False
        
        self.last_check = datetime.now()
        return results
    
    def get_recommendations(self) -> List[str]:
        """Get recommendations based on health check results."""
        recommendations = []
        
        for check in self.checks:
            if check["last_status"] == "fail":
                recommendations.append(
                    f"Check '{check['name']}' failed - review configuration"
                )
            elif check["last_status"] == "error":
                recommendations.append(
                    f"Check '{check['name']}' error: {check['last_error']}"
                )
        
        return recommendations


# Global error handler for unhandled exceptions
def setup_global_error_handler():
    """Set up global error handler for unhandled exceptions."""
    def exception_handler(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.critical(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        
        # Save to crash report
        crash_report = {
            "timestamp": datetime.now().isoformat(),
            "type": exc_type.__name__,
            "message": str(exc_value),
            "traceback": traceback.format_exc(),
        }
        
        try:
            import json
            crash_file = ERRORS_DIR / f"crash_{int(time.time())}.json"
            with open(crash_file, "w") as f:
                json.dump(crash_report, f, indent=2)
        except:
            pass
    
    sys.excepthook = exception_handler


# Initialize global error handler
setup_global_error_handler()
