import os
import logging
import json
from datetime import datetime, timezone
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Union

class JsonFormatter(logging.Formatter):
    """Custom formatter that outputs log records as JSON objects."""
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "message": record.getMessage(),
            "level": record.levelname,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Include any exception information
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }

        # Include audit data if present in 'extra'
        if hasattr(record, 'audit_data') and isinstance(record.audit_data, dict):
            log_data["audit"] = record.audit_data
        elif isinstance(getattr(record, 'args', None), dict) and 'audit_data' in record.args:
            # Fallback check if passed directly in args - less common
            log_data["audit"] = record.args['audit_data']

        return json.dumps(log_data)

def configure_policy_audit_logging(
    log_file_path: str = "logs/policy_audit.log",
    log_level: Union[int, str] = logging.INFO,
    rotation_size_mb: int = 10,
    backup_count: int = 5
) -> logging.Logger:
    """
    Configures the policy audit logging system.

    Args:
        log_file_path: Path to the log file.
        log_level: Logging level (default: INFO).
        rotation_size_mb: Size in MB before rotating log file.
        backup_count: Number of backup files to keep.

    Returns:
        The configured logger instance.
    """
    try:
        # Create log directory if it doesn't exist
        log_dir = Path(log_file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # Get the specific logger
        audit_logger = logging.getLogger("policy_audit")
        audit_logger.setLevel(log_level)
        audit_logger.propagate = False # Don't send logs to the root logger

        # Remove existing handlers to avoid duplicates if called multiple times
        for handler in audit_logger.handlers[:]:
            handler.close()
            audit_logger.removeHandler(handler)

        # Create rotating file handler
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=rotation_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding='utf-8' # Specify encoding
        )

        # Set formatter
        formatter = JsonFormatter()
        file_handler.setFormatter(formatter)
        audit_logger.addHandler(file_handler)

        audit_logger.info(f"Policy audit logging initialized. Logging to {log_file_path}")
        return audit_logger

    except PermissionError:
        logging.error(f"Permission denied creating log directory or file at {log_file_path}. Audit logging disabled.", exc_info=True)
        # Return a dummy logger or raise?
        # For now, return the logger instance which might not have handlers.
        return logging.getLogger("policy_audit")
    except Exception as e:
        logging.error(f"Failed to configure policy audit logging: {e}", exc_info=True)
        # Return a dummy logger or raise?
        return logging.getLogger("policy_audit")

# Example of how this might be called at application startup:
# if __name__ == "__main__": # Or in your main FastAPI app setup
#     configure_policy_audit_logging()
#     # Now the 'policy_audit' logger is configured and ready for the PolicyEngine
#     audit_logger = logging.getLogger("policy_audit")
#     audit_logger.info("Test message", extra={"audit_data": {"key": "value"}}) 