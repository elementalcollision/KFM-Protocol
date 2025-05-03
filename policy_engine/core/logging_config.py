import logging
import sys

# Basic configuration for JSON logging
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(module)s %(funcName)s %(lineno)d %(message)s %(request_id)s %(trace_id)s %(span_id)s %(policy_id)s",
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
    },
    "loggers": {
        "uvicorn": {
            "handlers": ["console_json"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["console_json"],
            "level": "INFO",
            "propagate": False,
        },
        "fastapi": {
            "handlers": ["console_json"],
            "level": "INFO",
            "propagate": False,
        },
        "opa": {
            "handlers": ["console_json"],
            "level": "INFO",
            "propagate": False,
        },
        "httpx": {
            "handlers": ["console_json"],
            "level": "WARNING",
            "propagate": False,
        },
    },
    "root": { # Root logger configuration
        "handlers": ["console_json"],
        "level": "INFO",
    },
} 