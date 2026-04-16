import pytest
from sqlalchemy.orm import Session
from src.db.base import SessionLocal, engine
from src.db.models import Base
from src.utils.db_performance import DatabasePerformanceOptimizer


@pytest.fixture
def db_session():
    """创建数据库会话"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


def test_batch_insert(db_session):
    """测试批量插入"""
    optimizer = DatabasePerformanceOptimizer()
    items = [
        {"user_name": "test1", "content": "评论1", "star": 5},
        {"user_name": "test2", "content": "评论2", "star": 4}
    ]
    count = optimizer.batch_insert_reviews(db_session, "123456", items, batch_size=10)
    assert count == 2


def test_get_uncleaned_reviews(db_session):
    """测试获取未清洗评论"""
    optimizer = DatabasePerformanceOptimizer()
    items = [{"user_name": "test", "content": "评论", "star": 5}]
    optimizer.batch_insert_reviews(db_session, "123456", items)
    reviews = optimizer.get_uncleaned_reviews_batch(db_session, batch_size=10)
    assert len(reviews) == 1


def test_get_cleaned_reviews(db_session):
    """测试获取已清洗评论"""
    optimizer = DatabasePerformanceOptimizer()
    items = [{"user_name": "test", "content": "评论", "star": 5}]
    count = optimizer.batch_insert_reviews(db_session, "123456", items)
    
    from src.db.models import Review
    review = db_session.query(Review).first()
    review.cleaned_content = "评论 清洗"
    db_session.commit()
    
    reviews = optimizer.get_cleaned_reviews_batch(db_session, batch_size=10)
    assert len(reviews) == 1


def test_batch_update(db_session):
    """测试批量更新"""
    optimizer = DatabasePerformanceOptimizer()
    items = [{"user_name": "test", "content": "评论", "star": 5}]
    optimizer.batch_insert_reviews(db_session, "123456", items)
    
    from src.db.models import Review
    review = db_session.query(Review).first()
    
    updates = [{"id": review.id, "cluster_id": 1}]
    count = optimizer.batch_update_reviews(db_session, updates, batch_size=10)
    assert count == 1
    
    updated_review = db_session.query(Review).first()
    assert updated_review.cluster_id == 1
