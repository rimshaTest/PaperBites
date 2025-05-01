# utils/logging.py
import logging
from datetime import datetime
import os
import sys

def setup_logging(log_dir="logs", level=logging.INFO):
    """
    Configure application-wide logging with file and console output.
    
    Args:
        log_dir: Directory to store log files
        level: Logging level
        
    Returns:
        Logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Create timestamped log filename
    log_filename = os.path.join(
        log_dir, 
        f"paperbites_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )
    
    # Configure root logger
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Setup file handler
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(level)
    file_handler.setFormatter(file_formatter)
    
    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Reduce verbosity of external libraries
    logging.getLogger("moviepy").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("scholarly").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    
    # Create and return application logger
    logger = logging.getLogger("paperbites")
    logger.info("Starting PaperBites application")
    logger.info(f"Logging to {log_filename}")
    
    return logger