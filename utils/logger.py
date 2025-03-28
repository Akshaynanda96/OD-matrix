import logging
from typing import Optional


def configure_logger(name: str = None, log_level: int = logging.INFO) -> logging.Logger:
    """Configure and return a logger with standard formatting"""
    logger = logging.getLogger(name or __name__)

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)

    logger.setLevel(log_level)
    logger.addHandler(handler)

    return logger