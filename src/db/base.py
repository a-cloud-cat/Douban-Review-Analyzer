from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.core.config import settings
import logging

#非自动打印，需调用日志
logger = logging.getLogger(settings.PROJECT_NAME)

#实例化engine（因为在db.base里面，所以肯定是数据库的engine，故无需叫db_engine）
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=3600,
    #防止连接坏死，一小时后回收连接
    pool_pre_ping=True,
    # 每次取连接前先“空测”，避免拿到失效连接，一般会发送一个SELECT 1
    echo=settings.DEBUG
)

# 创建 Session 工厂（SessionLocal 就是一个专门生产 Session 实例的工厂。/即打开一个数据库对话）
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明 ORM 基类，内含metadata：负责物理描述。它是一个专门的对象（MetaData 类的实例），它只记录纯粹的数据库信息（表名、约束、主键），在init_db被调用
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        raise#增加，举起。理解成举牌示意
    finally:
        db.close()