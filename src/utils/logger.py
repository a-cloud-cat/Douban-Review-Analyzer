import logging
import os
from typing import Optional

from src.utils.path_utils import get_logs_dir, ensure_dir

class Logger:
    """日志管理器，使用单例模式"""
    _instance = None
    
    def __new__(cls):
        """创建单例实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_logger()
        return cls._instance
    
    def _init_logger(self):
        """初始化日志配置"""
        logs_dir = get_logs_dir()
        ensure_dir(logs_dir)
        
        log_file = logs_dir / f"app_{os.getpid()}.log"
        
        # 配置根日志器
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(str(log_file), encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger("DoubanReviewAnalyzer")
    
    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """获取指定名称的logger
        
        Args:
            name: logger名称，可选
        
        Returns:
            logging.Logger: 日志器实例
        """
        if name:
            return self.logger.getChild(name)
        return self.logger


logger = Logger().get_logger()


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """获取日志器
    
    Args:
        name: logger名称，可选
    
    Returns:
        logging.Logger: 日志器实例
    """
    return Logger().get_logger(name)
