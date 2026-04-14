import sys
from pathlib import Path
import logging

from src.utils.path_utils import get_project_root
ROOT_DIR = get_project_root()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

#先规定root_dir的地图/路径，然后通过地图来导入其他文件模块
from src.core.config import settings
from src.db.base import Base, engine

logger = logging.getLogger(settings.PROJECT_NAME)

def init_db():
    logger.info(f"--- [{settings.PROJECT_NAME}] 正在初始化数据库表结构 ---")

    try:
        # Base.metadata.create_all ：
        # 1. 检查 bind 绑定的数据库连接。
        # 2. 扫描所有已加载到内存中、继承了 Base 的类（即 models.py 里的类）。
        # 3. 发送 'CREATE TABLE IF NOT EXISTS' 指令，若表已存在则跳过，不破坏原有数据。
        Base.metadata.create_all(bind=engine)

        logger.info("成功：数据库初始化完成，所有表结构已就绪。")

    except Exception as e:
        # 记录详细错误日志，回溯是权限问题还是网络问题
        logger.error(f"错误：建表失败。可能原因：MySQL 未启动、数据库不存在或 .env 配置有误。")
        logger.error(f"堆栈详情: {e}")
        #程序成功会留下0，1退出告诉机器出错终止
        sys.exit(1)

if __name__ == "__main__":
    init_db()