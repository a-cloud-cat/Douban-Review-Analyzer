from src.db.models import Review
from src.utils.logger import get_logger
from src.utils.db_utils import DatabaseSessionManager

logger = get_logger("data_service")

class DataService:
    def __init__(self):
        pass

    @staticmethod
    def save_reviews(douban_id, items):
        count = 0
        try:
            with DatabaseSessionManager.get_session() as db:
                for item in items:
                    new_review = Review(
                        douban_id=douban_id,
                        user_name=item.get('user_name', '匿名'),
                        star=item.get('star', 0),
                        content=item.get('content', ''),
                    )
                    db.add(new_review)  # 放到“待提交”区域
                    count += 1

            logger.info(f"存入成功！电影 ID: {douban_id} 新增 {count} 条评论。")
            return count
        except Exception as e:
            logger.error(f"数据库写入异常: {e}")
            return 0


data_service = DataService()