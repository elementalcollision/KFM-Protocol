import logging
import sys
from pythonjsonlogger import jsonlogger
from contextvars import ContextVar
import datetime
from opentelemetry import trace # Import trace

# Context variable for request ID (will be set by middleware)
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get('timestamp'):
            # Use ISO format time
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            log_record['timestamp'] = now
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname

        # Add request_id if available in contextvar
        request_id = request_id_var.get()
        if request_id:
            log_record['request_id'] = request_id

        # Add OpenTelemetry Trace and Span IDs if available
        span = trace.get_current_span()
        if span != trace.INVALID_SPAN:
            trace_id = span.get_span_context().trace_id
            span_id = span.get_span_context().span_id
            log_record['trace_id'] = format(trace_id, '032x') # Format as hex string
            log_record['span_id'] = format(span_id, '016x')   # Format as hex string

# Basic logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": CustomJsonFormatter,
            # Example format: "%(timestamp)s %(level)s [%(name)s] [%(filename)s:%(lineno)d] %(message)s"
            "format": "%(asctime)s %(levelname)s %(name)s %(module)s %(funcName)s %(lineno)d %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S%z",
        },
        "standard": {
            "format": "%(levelname)-8s [%(asctime)s] [%(name)s:%(lineno)d] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console_json": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": sys.stdout, # Log to stdout
        },
         "console_standard": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "stream": sys.stdout,
        },
    },
    "loggers": {
        "uvicorn": {
            "handlers": ["console_json"], # Use JSON for uvicorn logs
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.error": {
            "handlers": ["console_json"], # Use JSON for uvicorn errors
            "level": "INFO", # Or WARNING/ERROR
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["console_json"], # Use JSON for uvicorn access logs
            "level": "INFO",
            "propagate": False,
        },
        "sqlalchemy.engine": { # Example: Quieter SQLAlchemy logs
            "handlers": ["console_json"],
            "level": "WARNING",
            "propagate": False,
        },
        "agent_registry_service": { # Our application logger
            "handlers": ["console_json"], # Use JSON for our app logs
            "level": "INFO", # Default level for our app
            "propagate": False,
        },
        "": { # Root logger configuration (optional, handles others)
            "handlers": ["console_json"],
            "level": "WARNING",
        },
    },
}

# Import datetime inside the function where it's used
import datetime 