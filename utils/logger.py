"""
Logging utilities for the job scraper project.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional


def setup_logger(name: str, 
                log_file: Optional[str] = None, 
                level: int = logging.INFO,
                max_size_mb: int = 10,
                backup_count: int = 5,
                console_output: bool = True) -> logging.Logger:
    """
    Set up a logger with file and console handlers.
    
    Args:
        name: Logger name
        log_file: Path to log file (None for auto-generated)
        level: Logging level
        max_size_mb: Maximum log file size in MB
        backup_count: Number of backup files to keep
        console_output: Whether to output to console
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use rotating file handler to manage log file size
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_size_mb * 1024 * 1024,  # Convert MB to bytes
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get an existing logger by name"""
    return logging.getLogger(name)


def set_log_level(logger_name: str, level: int):
    """Set log level for an existing logger"""
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    
    # Update all handlers
    for handler in logger.handlers:
        handler.setLevel(level)


def main():
    """Test the logging utilities"""
    print("📝 Testing Logging Utilities")
    print("=" * 30)
    
    # Test basic logger
    logger = setup_logger('test_logger', 'test_logs/test.log')
    logger.info("This is a test info message")
    logger.warning("This is a test warning message")
    logger.error("This is a test error message")
    
    # Test with file and console output
    logger = setup_logger(
        "test_logger", 
        log_file="test_logs/test.log", 
        level=logging.DEBUG
    )
    
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    print("\n✅ Logging test completed. Check the 'test_logs' directory for log files.")


if __name__ == "__main__":
    main()
