from src.utils.logger import get_logger
from src.utils.db_utils import DatabaseSessionManager
from src.utils.db_performance import DatabasePerformanceOptimizer
from src.db.models import CrawlUrl

logger = get_logger("data_service")

class DataService:
    def __init__(self):
        pass

    @staticmethod
    def save_reviews(book_name, items):
        try:
            with DatabaseSessionManager.get_session() as db:
                count = DatabasePerformanceOptimizer.batch_insert_reviews(
                    db=db,
                    douban_id=book_name,
                    items=items,
                    batch_size=50
                )

                # 保存评论后更新图书统计信息
                if count > 0:
                    DatabasePerformanceOptimizer.update_book_review_stats(db, book_name, count)

                db.commit()

            logger.info(f"存入成功，图书: {book_name} 新增 {count} 条评论。")
            return count
        except Exception as e:
            logger.error(f"数据库写入异常: {e}")
            return 0

    @staticmethod
    def get_active_urls():
        """
        获取所有可用的爬取URL
        
        Returns:
            list: URL列表，每个元素为字典
        """
        try:
            with DatabaseSessionManager.get_session() as db:
                urls = db.query(CrawlUrl).filter(CrawlUrl.status == 'active').order_by(CrawlUrl.id).all()
                result = []
                for url in urls:
                    result.append({
                        'id': url.id,
                        'url': url.url,
                        'book_name': url.book_name,
                        'source': url.source
                    })
                return result
        except Exception as e:
            logger.error(f"获取URL列表异常: {e}")
            return []

    @staticmethod
    def add_crawl_url(url, book_name, source='book'):
        """
        添加新的爬取URL
        
        Args:
            url: 爬取URL
            book_name: 图书名称
            source: 来源类型
            
        Returns:
            bool: 是否添加成功
        """
        try:
            with DatabaseSessionManager.get_session() as db:
                # 检查是否已存在
                existing = db.query(CrawlUrl).filter(CrawlUrl.url == url).first()
                if existing:
                    logger.warning(f"URL已存在: {url}")
                    return False
                
                new_url = CrawlUrl(
                    url=url,
                    book_name=book_name,
                    source=source,
                    status='active'
                )
                db.add(new_url)
                db.commit()
                logger.info(f"添加URL成功: {book_name} - {url}")
                return True
        except Exception as e:
            logger.error(f"添加URL异常: {e}")
            return False


data_service = DataService()