import logging

def get_logger(name: str = "matthews_order_backend") -> logging.Logger:
    logger = logging.getLogger(name)
    return logger
