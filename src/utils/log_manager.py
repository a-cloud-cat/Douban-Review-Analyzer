import os
import shutil
from pathlib import Path
from typing import List, Optional
from src.utils.path_utils import get_logs_dir, ensure_dir
from src.utils.logger import get_logger

# 获取日志器
logger = get_logger("log_manager")

class LogManager:
    """日志管理器
    
    提供日志文件的管理功能，包括：
    - 清理日志文件
    - 日志文件统计
    - 日志文件压缩
    """
    
    def __init__(self):
        """初始化日志管理器"""
        self.logs_dir = get_logs_dir()
        ensure_dir(self.logs_dir)
    
    def clean_logs(self, keep_days: Optional[int] = None, pattern: str = "*.log") -> int:
        """清理日志文件
        
        Args:
            keep_days: 保留最近几天的日志，None表示清理所有日志
            pattern: 日志文件匹配模式，默认 "*.log"
        
        Returns:
            int: 成功删除的日志文件数量
        """
        try:
            deleted_count = 0
            log_files = list(self.logs_dir.glob(pattern))
            
            if not log_files:
                logger.info("没有找到符合条件的日志文件")
                return 0
            
            # 获取当前进程ID，避免删除当前进程的日志文件
            current_pid = str(os.getpid())
            
            for log_file in log_files:
                # 检查文件是否为日志文件
                if not log_file.is_file():
                    continue
                
                # 跳过当前进程的日志文件
                if current_pid in log_file.name:
                    logger.info(f"跳过当前进程的日志文件: {log_file.name}")
                    continue
                
                # 检查是否需要保留
                if keep_days is not None:
                    import time
                    file_mtime = log_file.stat().st_mtime
                    current_time = time.time()
                    days_since_modified = (current_time - file_mtime) / (24 * 3600)
                    
                    if days_since_modified < keep_days:
                        continue
                
                # 尝试删除文件
                try:
                    log_file.unlink()
                    deleted_count += 1
                    logger.info(f"已删除日志文件: {log_file.name}")
                except Exception as e:
                    logger.error(f"删除日志文件失败 {log_file.name}: {e}")
            
            logger.info(f"共删除 {deleted_count} 个日志文件")
            return deleted_count
        
        except Exception as e:
            logger.error(f"清理日志文件时发生错误: {e}")
            return 0
    
    def get_log_files(self, pattern: str = "*.log") -> List[Path]:
        """获取所有日志文件
        
        Args:
            pattern: 日志文件匹配模式，默认 "*.log"
        
        Returns:
            List[Path]: 日志文件路径列表
        """
        try:
            log_files = list(self.logs_dir.glob(pattern))
            # 按修改时间排序，最新的在前
            log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return log_files
        except Exception as e:
            logger.error(f"获取日志文件列表时发生错误: {e}")
            return []
    
    def get_log_statistics(self) -> dict:
        """获取日志文件统计信息
        
        Returns:
            dict: 日志文件统计信息
        """
        try:
            log_files = self.get_log_files()
            total_size = sum(f.stat().st_size for f in log_files if f.is_file())
            
            return {
                "total_files": len(log_files),
                "total_size": total_size,
                "total_size_human": self._format_size(total_size),
                "logs_dir": str(self.logs_dir)
            }
        except Exception as e:
            logger.error(f"获取日志统计信息时发生错误: {e}")
            return {}
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小
        
        Args:
            size_bytes: 文件大小（字节）
        
        Returns:
            str: 格式化后的文件大小
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    def compress_logs(self, pattern: str = "*.log", keep_original: bool = False) -> int:
        """压缩日志文件
        
        Args:
            pattern: 日志文件匹配模式，默认 "*.log"
            keep_original: 是否保留原始文件
        
        Returns:
            int: 成功压缩的日志文件数量
        """
        try:
            import zipfile
            compressed_count = 0
            log_files = self.get_log_files(pattern)
            
            for log_file in log_files:
                if not log_file.is_file():
                    continue
                
                # 创建压缩文件路径
                zip_path = log_file.with_suffix('.zip')
                
                # 检查压缩文件是否已存在
                if zip_path.exists():
                    logger.warning(f"压缩文件已存在: {zip_path.name}")
                    continue
                
                # 压缩文件
                try:
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        zipf.write(log_file, log_file.name)
                    
                    compressed_count += 1
                    logger.info(f"已压缩日志文件: {log_file.name} -> {zip_path.name}")
                    
                    # 删除原始文件（如果不需要保留）
                    if not keep_original:
                        try:
                            log_file.unlink()
                            logger.info(f"已删除原始日志文件: {log_file.name}")
                        except Exception as e:
                            logger.error(f"删除原始日志文件失败 {log_file.name}: {e}")
                
                except Exception as e:
                    logger.error(f"压缩日志文件失败 {log_file.name}: {e}")
            
            logger.info(f"共压缩 {compressed_count} 个日志文件")
            return compressed_count
        
        except ImportError:
            logger.error("压缩功能需要 zipfile 模块")
            return 0
        except Exception as e:
            logger.error(f"压缩日志文件时发生错误: {e}")
            return 0

# 全局日志管理器实例
log_manager = LogManager()
