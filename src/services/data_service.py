from src.db.base import SessionLocal
from src.db.models import Review

class DataService:
    def __init__(self):
        pass

    @staticmethod
    def save_reviews(douban_id, items):
        db = SessionLocal()  # 打开一个数据库会话
        count = 0
        try:
            for item in items:
                new_review = Review(
                    douban_id=douban_id,
                    user_name=item.get('user_name', '匿名'),
                    star=item.get('star', 0),
                    content=item.get('content', ''),
                )
                db.add(new_review)  # 放到“待提交”区域
                count += 1

            db.commit()
            print(f"存入成功！电影 ID: {douban_id} 新增 {count} 条评论。")
            return count
        except Exception as e:
            db.rollback()
            print(f"数据库写入异常: {e}")
            return 0
        finally:
            db.close()

data_service = DataService()