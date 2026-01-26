import logging

def get_logger(name: str = "mob") -> logging.Logger:
    logger = logging.getLogger(name)
    return logger
