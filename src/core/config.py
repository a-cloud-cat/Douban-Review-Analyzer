import os
from dotenv import load_dotenv

from src.utils.path_utils import get_project_root
BASE_DIR = get_project_root()
env_path = BASE_DIR / ".env"

if env_path.exists():
# dotenv是python的一个库，用于加载环境变量，作用是解析内容与os.getenv配合：比如 DB_USER=root 变成了键（Key）为 DB_USER，值（Value）为 "root"
    load_dotenv(dotenv_path=env_path)
else:
    print(f"Warning: .env file not found at {env_path}")

#若env有则以env为准，若env无则以此处setting的默认配置为准
class Settings:
    """
    系统全局配置管理类，从环境变量或 .env 文件加载配置
    提供项目名称、调试模式、数据库连接等核心配置
    """

    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "douban_insight")

    # os.getenv 拿到的全是字符串，而py中非空字符串的bool值为true
    # 故添加判断 ==“true”，否则 "False" 这个非空字符串在 Python 判断中会永远为 True，导致 Debug 关不掉。
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    DB_USER = os.getenv("DB_USER", "root")
    DB_PASS = os.getenv("DB_PASS")
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "douban_analysis")

    #在配置加载阶段将连接池参数提前转换为整型，避免重复类型转换，提升性能与代码效率
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 5))
    DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", 10))

    @property
    def database_url(self) -> str:
        """
        构建 SQLAlchemy 数据库连接 URL

        Returns:
            str: 完整的 MySQL 连接字符串

        Raises:
            无异常抛出
        """
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASS}@"
            f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            "?charset=utf8mb4&binary_prefix=true"
        )


settings = Settings()