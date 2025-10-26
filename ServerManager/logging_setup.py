"""Logging setup for server workers and application."""
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime


LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)


def get_server_logger(server_name: str) -> logging.Logger:
    """Get or create a logger for a specific server."""
    logger_name = f"server.{server_name}"
    logger = logging.getLogger(logger_name)
    
    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    
    # Create log filename with date
    date_str = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(LOGS_DIR, f"{server_name}-{date_str}.log")
    
    # Rotating file handler - 10 MB max, 5 backups
    handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    logger.propagate = False  # Don't propagate to root logger
    
    return logger


def get_app_logger() -> logging.Logger:
    """Get application-level logger."""
    logger = logging.getLogger("app")
    
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    
    log_file = os.path.join(LOGS_DIR, "app.log")
    handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger


def get_log_file_path(server_name: str) -> str:
    """Get the current log file path for a server."""
    date_str = datetime.now().strftime("%Y%m%d")
    return os.path.join(LOGS_DIR, f"{server_name}-{date_str}.log")
