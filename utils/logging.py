# utils/logging.py
import logging
from datetime import datetime
import os

def setup_logging(log_dir="logs"):
    """
    Configure application-wide logging with file and console output.
    
    Args:
        log_dir: Directory to store log files
        
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
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()  # Also output to console
        ]
    )
    
    # Reduce verbosity of external libraries
    logging.getLogger("moviepy").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("scholarly").setLevel(logging.WARNING)
    
    # Create and return application logger
    logger = logging.getLogger("paperbites")
    logger.info("Starting PaperBites application")
    return logger