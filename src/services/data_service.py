from src.db.models import Review
from src.utils.logger import get_logger
from src.utils.db_utils import DatabaseSessionManager
from src.utils.db_performance import DatabasePerformanceOptimizer

logger = get_logger("data_service")

class DataService:
    def __init__(self):
        pass

    @staticmethod
    def save_reviews(douban_id, items):
        try:
            with DatabaseSessionManager.get_session() as db:
                count = DatabasePerformanceOptimizer.batch_insert_reviews(
                    db=db,
                    douban_id=douban_id,
                    items=items,
                    batch_size=50
                )

            logger.info(f"存入成功！电影 ID: {douban_id} 新增 {count} 条评论。")
            return count
        except Exception as e:
            logger.error(f"数据库写入异常: {e}")
            return 0


data_service = DataService()