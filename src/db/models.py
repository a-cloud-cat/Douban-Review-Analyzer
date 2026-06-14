from sqlalchemy import Column, Integer, String, Text, DateTime, func
from src.db.base import Base

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)

    douban_id = Column(String(255), index=True, nullable=False, comment="图书名称")

    user_name = Column(String(50), comment="用户名")

    star = Column(Integer, comment="评分星级")

    content = Column(Text, nullable=False, comment="原始评论内容")

    cleaned_content = Column(Text, nullable=True, comment="清洗分词后的内容")

    cluster_id = Column(Integer, default=-1, index=True, comment="聚类簇标签")

    sentiment = Column(String(10), comment="情感标签：正面/负面")

    created_at = Column(DateTime, server_default=func.now(), comment="入库时间")

    def __repr__(self):
        return f"<Review(id={self.id}, douban_id='{self.douban_id}', star={self.star}, cluster={self.cluster_id})>"

class BookReviewStats(Base):
    __tablename__ = "book_review_stats"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="编号")

    book_name = Column(String(255), unique=True, nullable=False, comment="图书名")

    start_row = Column(Integer, nullable=False, comment="起始行")

    end_row = Column(Integer, nullable=False, comment="终止行")

    review_count = Column(Integer, default=0, comment="评论数")

    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<BookReviewStats(id={self.id}, book_name='{self.book_name}', start_row={self.start_row}, end_row={self.end_row})>"

class CrawlUrl(Base):
    __tablename__ = "crawl_urls"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="编号")

    url = Column(Text, nullable=False, comment="爬取URL")

    book_name = Column(String(255), comment="图书名称")

    source = Column(String(50), comment="来源类型：book/movie")

    status = Column(String(20), default="active", comment="状态：active/inactive")

    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    def __repr__(self):
        return f"<CrawlUrl(id={self.id}, book_name='{self.book_name}', status='{self.status}')>"