import re
import jieba
from pathlib import Path
from src.db.models import Review
from src.utils.path_utils import get_project_root, get_config_dir
from src.utils.logger import get_logger
from src.utils.db_utils import DatabaseSessionManager
from src.utils.db_performance import DatabasePerformanceOptimizer

# 获取日志器
logger = get_logger("cleaner")


class DataCleaner:
    """
    数据清洗器，负责对豆瓣评论内容进行文本清洗、中文分词、去停用词，并更新数据库
    """

    def __init__(self):
        """
        初始化数据清洗器，加载自定义词典、停用词表
        """
        self.BASE_DIR = get_project_root()
        self.config_dir = get_config_dir()

        user_dict_path = self.config_dir / "user_dict.txt"
        if user_dict_path.exists():
            jieba.load_userdict(str(user_dict_path))
            logger.info(f"已加载自定义词典: {user_dict_path.name}")

        self.stop_words = self._load_stopwords()
        logger.info(f"已加载停用词，数量：{len(self.stop_words)}")

    def _load_stopwords(self):
        """从配置文件加载停用词集合
        
        Returns:
            set: 停用词集合
        """
        # set（集合）查找速度快,且自动去重
        stop_words = set()
        stop_path = self.config_dir / "stopwords.txt"

        #读取停用词
        if stop_path.exists():
            with open(stop_path, 'r', encoding='utf-8') as f:
                for line in f:
                    word = line.strip()
                    if word:
                        stop_words.add(word)
        return stop_words

    @staticmethod
    def clean_text(text: str) -> str:
        """
        清洗原始文本，去除换行符、特殊符号，只保留中英文、数字、空格

        Args:
            text: 原始评论文本

        Returns:
            str: 清洗后的纯文本

        Raises:
            无异常抛出
        """
        if not text: return ""
        text = text.replace('\n', ' ').replace('\r', ' ')
        # 只保留中文、英文、数字、空格
        text = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9\s]", "", text)
        return text.strip()

    def segment(self, text: str) -> str:
        """
        执行完整文本处理流程：清洗 -> 分词 -> 去停用词 -> 空格拼接

        Args:
            text: 原始文本

        Returns:
            str: 分词并过滤后的结果字符串

        Raises:
            无异常抛出
        """
        cleaned = self.clean_text(text)
        words = jieba.lcut(cleaned)
        filtered = [w for w in words if w not in self.stop_words and len(w.strip()) > 1]
        return " ".join(filtered)

    def process_uncleaned_reviews(self, batch_size=100):
        """
        批量处理数据库中未清洗的评论，自动分词并更新 cleaned_content 字段

        Args:
            batch_size: 每批次处理的最大条数，默认100

        Returns:
            无返回值

        Raises:
            Exception: 数据库操作或文本处理异常
        """
        try:
            with DatabaseSessionManager.get_session() as db:
                reviews = DatabasePerformanceOptimizer.get_uncleaned_reviews_batch(
                    db=db,
                    batch_size=batch_size
                )

                if not reviews:
                    logger.info("评论均已清洗完毕。")
                    return

                for r in reviews:
                    r.cleaned_content = self.segment(r.content)

            logger.info(f"成功更新 {len(reviews)} 条数据")

        except Exception as e:
            logger.error(f"异常: {e}")

cleaner = DataCleaner()