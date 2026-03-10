import sys


def build_logging_config(log_level: str | None) -> dict:
    resolved_level = (log_level or "INFO").upper()
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": sys.stdout,
            },
        },
        "loggers": {
            # Root logger
            "": {
                "handlers": ["default"],
                "level": resolved_level,
                "propagate": False,
            },
            # Uvicorn loggers
            "uvicorn.error": {
                "level": resolved_level,
            },
            "uvicorn.access": {
                "level": resolved_level,
            },
            # Module logger
            "mob": {
                "handlers": ["default"],
                "level": resolved_level,
                "propagate": False,
            },
        },
    }
