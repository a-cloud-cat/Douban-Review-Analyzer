import sys
from src.utils.path_utils import get_project_root
from src.utils.logger import get_logger

root_path = get_project_root()

if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from src.db.base import engine, Base

logger = get_logger("reset_db")


def reset_database():
    """
    重置数据库：删除所有表并重新创建空表，实现数据清空


    Returns:
        无返回值

    Raises:
        Exception: 数据库连接异常、表删除/创建失败时抛出
    """
    logger.info("正在连接数据库进行重置操作")

    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("旧数据与物理表已成功删除。")

        Base.metadata.create_all(bind=engine)
        logger.info("数据库结构已重新初始化（当前为空表状态）。")

    except Exception as e:
        logger.error(f"重置失败，请检查数据库连接或是否被占用: {e}")