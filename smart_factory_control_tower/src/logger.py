"""
Structured logging configuration for the application.

Provides consistent logging across all modules with file and console handlers.
"""

from __future__ import annotations
import logging
import sys
from pathlib import Path
from datetime import datetime
from src.config import Config


def setup_logger(name: str = "smart_factory", level: str = None) -> logging.Logger:
    """
    Configure and return application logger.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger  # Already configured
    
    log_level = getattr(logging, level or Config.LOG_LEVEL, logging.INFO)
    logger.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler (if configured)
    if Config.LOG_FILE:
        log_dir = Config.LOG_FILE.parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(Config.LOG_FILE)
        file_handler.setLevel(log_level)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger


# Create default logger instance
logger = setup_logger()

