from typing import List, Dict, Any, Optional, Generator
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.db.models import Review, BookReviewStats
from src.utils.logger import get_logger

logger = get_logger("db_performance")

class DatabasePerformanceOptimizer:
    """数据库性能优化器
    
    提供数据库操作的性能优化功能，包括：
    - 批量操作- 分页查询- 索引优化- 高效统计
    """
    
    @staticmethod
    def batch_insert_reviews(db: Session, douban_id: str, items: List[Dict[str, Any]], batch_size: int = 50) -> int:
        """批量插入评论数据
        
        Args:
            db: 数据库会话
            douban_id: 豆瓣电影ID
            items: 评论数据列表
            batch_size: 每批插入的数量
        
        Returns:
            int: 成功插入的记录数
        """
        total_count = 0
        
        # 批量插入
        for i in range(0, len(items), batch_size):
            batch = items[i:i+batch_size]
            
            reviews = []
            for item in batch:
                review = Review(
                    douban_id=douban_id,
                    user_name=item.get('user_name', '匿名'),
                    star=item.get('star', 0),
                    content=item.get('content', ''),
                )
                reviews.append(review)
            
            db.add_all(reviews)
            db.flush()  # 立即执行SQL但不提交
            total_count += len(reviews)
            
            logger.info(f"已插入 {total_count} 条评论")
        
        return total_count
    
    @staticmethod
    def get_reviews_with_pagination(db: Session, douban_id: Optional[str] = None, 
                                   offset: int = 0, limit: int = 100) -> Generator[Review, None, None]:
        """分页获取评论数据
        
        Args:
            db: 数据库会话
            douban_id: 豆瓣电影ID
            offset: 偏移量
            limit: 每页数量
        
        Yields:
            Review: 评论对象
        """
        query = db.query(Review)
        
        if douban_id:
            query = query.filter(Review.douban_id == douban_id)
        
        # 分页查询
        reviews = query.offset(offset).limit(limit).all()
        for review in reviews:
            yield review
    
    @staticmethod
    def get_uncleaned_reviews_batch(db: Session, batch_size: int = 100) -> List[Review]:
        """批量获取未清洗的评论
        
        Args:
            db: 数据库会话
            batch_size: 批量大小
        
        Returns:
            List[Review]: 未清洗的评论列表
        """
        return db.query(Review).filter(
            (Review.cleaned_content.is_(None)) | (Review.cleaned_content == "")
        ).limit(batch_size).all()
    
    @staticmethod
    def get_cleaned_reviews_batch(db: Session, batch_size: int = 100) -> List[Review]:
        """批量获取已清洗的评论
        
        Args:
            db: 数据库会话
            batch_size: 批量大小
        
        Returns:
            List[Review]: 已清洗的评论列表
        """
        return db.query(Review).filter(
            (Review.cleaned_content.is_not(None)) & (Review.cleaned_content != "")
        ).limit(batch_size).all()
    
    @staticmethod
    def batch_update_reviews(db: Session, updates: List[Dict[str, Any]], batch_size: int = 50) -> int:
        """批量更新评论
        
        Args:
            db: 数据库会话
            updates: 更新数据列表，每个元素是字典 {"id": id, "field": value}
            batch_size: 批量大小
        
        Returns:
            int: 成功更新的记录数
        """
        total_count = 0
        
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i+batch_size]
            if not batch:
                continue
            
            for update in batch:
                review_id = update.get("id")
                if not review_id:
                    continue
                
                update_fields = {k: v for k, v in update.items() if k != "id"}
                if not update_fields:
                    continue
                
                db.query(Review).filter(Review.id == review_id).update(update_fields)
            
            total_count += len(batch)
            logger.info(f"已更新 {total_count} 条评论")
        
        return total_count
    
    @staticmethod
    def get_review_statistics(db: Session, douban_id: Optional[str] = None) -> Dict[str, Any]:
        """获取评论统计信息
        
        Args:
            db: 数据库会话
            douban_id: 豆瓣电影ID
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        query = db.query(
            func.count(Review.id).label('total'),
            func.avg(Review.star).label('avg_star'),
            func.count(func.distinct(Review.user_name)).label('unique_users')
        )
        
        if douban_id:
            query = query.filter(Review.douban_id == douban_id)
        
        result = query.first()
        
        return {
            'total_reviews': result.total or 0,
            'average_star': float(result.avg_star) if result.avg_star else 0.0,
            'unique_users': result.unique_users or 0
        }
    
    @staticmethod
    def delete_reviews_by_douban_id(db: Session, douban_id: str) -> int:
        """删除指定电影的所有评论
        
        Args:
            db: 数据库会话
            douban_id: 豆瓣电影ID
        
        Returns:
            int: 删除的记录数
        """
        deleted = db.query(Review).filter(Review.douban_id == douban_id).delete()
        logger.info(f"已删除 {deleted} 条评论")
        return deleted

    @staticmethod
    def update_book_review_stats(db: Session, book_name: str, review_count: int) -> bool:
        """更新图书评论统计信息
        
        Args:
            db: 数据库会话
            book_name: 图书名称
            review_count: 新增评论数量
        
        Returns:
            bool: 是否更新成功
        """
        try:
            # 获取当前图书最新的评论ID范围
            min_id = db.query(func.min(Review.id)).filter(Review.douban_id == book_name).scalar()
            max_id = db.query(func.max(Review.id)).filter(Review.douban_id == book_name).scalar()
            total_count = db.query(func.count(Review.id)).filter(Review.douban_id == book_name).scalar()

            if min_id is None or max_id is None:
                logger.warning(f"未找到图书 {book_name} 的评论数据")
                return False

            # 查询是否已存在该图书的统计记录
            existing_stats = db.query(BookReviewStats).filter(BookReviewStats.book_name == book_name).first()

            if existing_stats:
                # 更新现有记录
                existing_stats.start_row = min_id
                existing_stats.end_row = max_id
                existing_stats.review_count = total_count
                logger.info(f"更新图书统计: {book_name} - 起始行:{min_id}, 终止行:{max_id}, 评论数:{total_count}")
            else:
                # 创建新记录
                new_stats = BookReviewStats(
                    book_name=book_name,
                    start_row=min_id,
                    end_row=max_id,
                    review_count=total_count
                )
                db.add(new_stats)
                logger.info(f"创建图书统计: {book_name} - 起始行:{min_id}, 终止行:{max_id}, 评论数:{total_count}")

            return True
        except Exception as e:
            logger.error(f"更新图书统计时发生错误: {e}")
            return False

    @staticmethod
    def refresh_all_book_stats(db: Session) -> int:
        """刷新所有图书的统计信息
        
        Args:
            db: 数据库会话
        
        Returns:
            int: 刷新的图书数量
        """
        try:
            # 获取所有不重复的图书名称
            book_names = db.query(Review.douban_id).distinct().all()
            
            count = 0
            for (book_name,) in book_names:
                if DatabasePerformanceOptimizer.update_book_review_stats(db, book_name, 0):
                    count += 1
            
            logger.info(f"成功刷新 {count} 本图书的统计信息")
            return count
        except Exception as e:
            logger.error(f"刷新图书统计时发生错误: {e}")
            return 0

db_perf_optimizer = DatabasePerformanceOptimizer()
