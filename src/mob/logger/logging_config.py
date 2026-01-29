import sys

LOGGING_CONFIG = {
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
            "level": "DEBUG",
            "propagate": False,
        },
        # Uvicorn loggers
        "uvicorn.error": {
            "level": "INFO",
        },
        "uvicorn.access": {
            "level": "INFO",
        },
        # Module logger
        "mob": {
            "handlers": ["default"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
