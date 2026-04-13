from sqlalchemy import Column, Integer, String, Text, DateTime, func
from src.db.base import Base

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)

    douban_id = Column(String(20), index=True, nullable=False, comment="豆瓣电影/条目唯一ID")

    user_name = Column(String(50), comment="用户名")

    star = Column(Integer, comment="评分星级")

    content = Column(Text, nullable=False, comment="原始评论内容")

    cleaned_content = Column(Text, nullable=True, comment="清洗分词后的内容")

    cluster_id = Column(Integer, default=-1, index=True, comment="聚类簇标签")

    created_at = Column(DateTime, server_default=func.now(), comment="入库时间")

# Representation"（表现/表达）展示添加的数据（按照标准的格式）
    def __repr__(self):
        return f"<Review(id={self.id}, douban_id='{self.douban_id}', star={self.star}, cluster={self.cluster_id})>"