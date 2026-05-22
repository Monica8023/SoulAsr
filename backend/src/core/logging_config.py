import logging
from logging.config import dictConfig

from backend.src.core.config import settings
from backend.src.utils.file_ops import ensure_dir


def setup_logging():
    ensure_dir(settings.log_dir)
    log_file_path = f"{settings.log_dir.rstrip('/').rstrip(chr(92))}/{settings.log_file}"
    level = settings.log_level.upper()

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                },
                "access": {
                    "format": '%(asctime)s %(levelname)s [%(name)s] %(client_addr)s - "%(request_line)s" %(status_code)s',
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": level,
                    "formatter": "standard",
                },
                "file": {
                    "class": "logging.FileHandler",
                    "level": level,
                    "formatter": "standard",
                    "filename": log_file_path,
                    "encoding": "utf-8",
                },
            },
            "loggers": {
                "": {
                    "handlers": ["console", "file"],
                    "level": level,
                },
                "uvicorn": {
                    "handlers": ["console", "file"],
                    "level": level,
                    "propagate": False,
                },
                "uvicorn.error": {
                    "handlers": ["console", "file"],
                    "level": level,
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": ["console", "file"],
                    "level": level,
                    "propagate": False,
                },
            },
        }
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
