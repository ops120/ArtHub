import logging
import os
from pathlib import Path
from datetime import datetime


def setup_logging(log_level: str = "INFO", log_dir: str = "logs"):
    logs_dir = Path(log_dir)
    logs_dir.mkdir(exist_ok=True)
    
    log_file = logs_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    level = level_map.get(log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)


class Logger:
    _instance = None
    _logger = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def init(self, name: str = "ai_client", level: str = "INFO"):
        if self._logger is None:
            self._logger = logging.getLogger(name)
            self._logger = setup_logging(level)
        return self._logger
    
    @property
    def logger(self):
        if self._logger is None:
            self.init()
        return self._logger
    
    def debug(self, msg: str):
        self.logger.debug(msg)
    
    def info(self, msg: str):
        self.logger.info(msg)
    
    def warning(self, msg: str):
        self.logger.warning(msg)
    
    def error(self, msg: str):
        self.logger.error(msg)
    
    def critical(self, msg: str):
        self.logger.critical(msg)


app_logger = Logger()
