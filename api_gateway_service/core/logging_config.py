import logging
import sys

# Basic configuration for JSON logging
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(module)s %(funcName)s %(lineno)d %(message)s %(request_id)s %(trace_id)s %(span_id)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S.%fZ", # ISO 8601 format
        },
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console_json": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": sys.stdout, # Log to stdout
        },
        # Optional: Keep a standard handler for specific needs or debugging
        # "console_standard": {
        #     "class": "logging.StreamHandler",
        #     "formatter": "standard",
        # },
    },
    "loggers": {
        "uvicorn": {
            "handlers": ["console_json"], # Ensure uvicorn uses JSON format
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["console_json"],
            "level": "INFO", # Adjust access log level if needed
            "propagate": False,
        },
        "fastapi": {
            "handlers": ["console_json"],
            "level": "INFO",
            "propagate": False,
        },
        "sqlalchemy.engine": { # Example: Log SQL queries (set to DEBUG for verbose output)
            "handlers": ["console_json"],
            "level": "WARNING",
            "propagate": False,
        },
        "httpx": { # Example: Log HTTP client requests
            "handlers": ["console_json"],
            "level": "WARNING", 
            "propagate": False,
        },
        # Add other library loggers as needed
    },
    "root": { # Root logger configuration
        "handlers": ["console_json"], # Default handler for all other logs
        "level": "INFO", # Set default root level (can be overridden by specific loggers)
    },
} 