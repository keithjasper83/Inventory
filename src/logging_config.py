"""Structured logging configuration for the application.

Provides structured JSON logging with correlation IDs for better traceability.
"""
import logging
import json
import sys
from datetime import datetime
from typing import Optional
import uuid


class StructuredFormatter(logging.Formatter):
    """Format log records as structured JSON."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON."""
        log_data = {
            "timestamp": datetime.now().astimezone().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add correlation ID if present
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id
        
        # Add extra fields
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def setup_logging(level: str = "INFO") -> None:
    """Setup structured logging for the application."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler with structured formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)


class CorrelationContext:
    """Context manager for correlation IDs in logs."""
    
    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.old_factory = None
    
    def __enter__(self):
        """Enter correlation context."""
        self.old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            record.correlation_id = self.correlation_id
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self.correlation_id
    
    def __exit__(self, *args):
        """Exit correlation context."""
        logging.setLogRecordFactory(self.old_factory)
