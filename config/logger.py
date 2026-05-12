import logging
from logging.config import dictConfig
import os
from pydantic import BaseModel
os.makedirs("logs", exist_ok=True)

log_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(asctime)s - %(message)s",
        },
        "file": {
            "format": "%(levelname)s: %(asctime)s - %(name)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "formatter": "console",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "file": {
            "formatter": "file",
            "class": "logging.FileHandler",
            "filename": "logs/application.log",  # log file path
            "mode": "a",  # append mode
            "encoding": "utf-8"
        },
    },
    "loggers": {
        "application": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "rq": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn": {
            "handlers": ["console", "file"],
            "level": "WARNING",  # Suppress "change detected" and reload info
            "propagate": False,
        },
        "watchfiles": {
            "handlers": ["console", "file"],
            "level": "WARNING",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    }
}

dictConfig(log_config)
logger = logging.getLogger("llm-evaluation")