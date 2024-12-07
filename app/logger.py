from loguru import logger
import sys
import os

def setup_logger():
    log_dir = 'app/logs'
    os.makedirs(log_dir, exist_ok=True)
    logger.remove()

    logger.add(sys.stdout, level="INFO", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | ===== | {message}")
    logger.add("app/logs/{time:YYYY-MM-DD}.log", rotation="1000 MB", level="DEBUG", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")

    return logger

logger = setup_logger()