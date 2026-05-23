import os
import logging
from logging.handlers import RotatingFileHandler
from shared.config.settings import settings

def setup_logger(name: str, log_file: str, level=None) -> logging.Logger:
    """Configures a rotating file logger and console output."""
    if level is None:
        level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        
    # Ensure logs directory exists
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
        
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers if logger is already configured
    if not logger.handlers:
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s [%(name)s:%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Rotating File Handler (Max 10MB, keep 5 backups)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    return logger

# Global logger instances
api_logger = setup_logger("api_service", "logs/api.log")
customer_logger = setup_logger("customer_recommender", "customer_recommender/logs/customer.log")
owner_logger = setup_logger("owner_recommender", "owner_recommender/logs/owner.log")
db_logger = setup_logger("database_service", "logs/database.log")
