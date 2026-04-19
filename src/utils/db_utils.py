from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import Session
from src.db.base import SessionLocal
from src.utils.logger import get_logger

logger = get_logger("db_utils")

class DatabaseSessionManager:
    """数据库会话管理器
    
    提供标准化的数据库会话管理，包括：- 会话创建- 自动释放- 异常处理- 事务管理
    """
    
    @staticmethod
    @contextmanager
    def get_session() -> Generator[Session, None, None]:
        """获取数据库会话的上下文管理器
        
        Yields:
            Session: 数据库会话实例
        """
        db = SessionLocal()
        try:
            yield db
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            db.close()
    
    @staticmethod
    #只需在函数定义时添加 @execute_with_session 装饰器，即可自动获得会话管理功能
    def execute_with_session(func):
        """装饰器：在数据库会话中执行函数
        
        Args:
            func: 要执行的函数，第一个参数必须是 db: Session
        
        Returns:
            函数执行结果
        """
        def wrapper(*args, **kwargs):
            with DatabaseSessionManager.get_session() as db:
                return func(db, *args, **kwargs)
        return wrapper
    
    @staticmethod
    def bulk_update(db: Session, model, update_data: list, batch_size: int = 100):
        """批量更新数据
        
        Args:
            db: 数据库会话
            model: 数据模型类
            update_data: 更新数据列表，每个元素是字典 {"id": id, "field": value}
            batch_size: 批量大小
        """
        from sqlalchemy import update
        
        for i in range(0, len(update_data), batch_size):
            batch = update_data[i:i+batch_size]
            
            for item in batch:
                stmt = update(model).where(model.id == item["id"])
                update_fields = {k: v for k, v in item.items() if k != "id"}
                stmt = stmt.values(**update_fields)
                db.execute(stmt)
            
            db.commit()
            logger.info(f"Bulk updated {len(batch)} records")

def get_db() -> Generator[Session, None, None]:
    """获取数据库会话的生成器（FastAPI 依赖注入使用）
    
    Yields:
        Session: 数据库会话实例
    """
    with DatabaseSessionManager.get_session() as db:
        yield db


db_manager = DatabaseSessionManager()
