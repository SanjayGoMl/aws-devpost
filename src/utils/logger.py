import logging
import os
from datetime import datetime
from typing import Optional

def setup_logger(name: str, log_file: Optional[str] = None, level: int = logging.INFO):
    """
    Setup logger with file and console handlers
    
    Args:
        name: Logger name
        log_file: Optional log file path
        level: Logging level
    
    Returns:
        Configured logger instance
    """
    
    logger = logging.getLogger(name)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
        
    logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if log_file is provided)
    if log_file:
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Failed to create file handler for {log_file}: {str(e)}")
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """Get or create logger with default settings"""
    return setup_logger(
        name=name,
        log_file=f'logs/{name.lower().replace(".", "_")}_{datetime.now().strftime("%Y-%m-%d")}.log'
    )

class LoggerMixin:
    """Mixin class to add logging capabilities to any class"""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class"""
        return get_logger(self.__class__.__name__)

def log_function_call(func):
    """Decorator to log function calls"""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.info(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.info(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            raise
    return wrapper

async def log_async_function_call(func):
    """Decorator to log async function calls"""
    async def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.info(f"Calling async {func.__name__}")
        try:
            result = await func(*args, **kwargs)
            logger.info(f"Async {func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Error in async {func.__name__}: {str(e)}")
            raise
    return wrapper
