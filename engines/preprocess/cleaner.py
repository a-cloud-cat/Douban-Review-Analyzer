import re
import jieba
from pathlib import Path
from src.db.base import SessionLocal
from src.db.models import Review

class DataCleaner:
    def __init__(self):
        self.BASE_DIR = Path(__file__).resolve().parent.parent.parent

        user_dict_path = self.BASE_DIR / "config" / "user_dict.txt"
        if user_dict_path.exists():
            jieba.load_userdict(str(user_dict_path))
            print(f"已加载自定义词典: {user_dict_path.name}")

        self.stop_words = self._load_stopwords()
        print(f"已加载停用词，数量：{len(self.stop_words)}")

    def _load_stopwords(self):
        stop_words = set() # set（集合）查找速度快,且自动去重
        stop_path = self.BASE_DIR / "config" / "stopwords.txt"

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
        if not text: return ""
        text = text.replace('\n', ' ').replace('\r', ' ')
        text = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9\s]", "", text) # 只保留中文、英文、数字、空格
        return text.strip()

    def segment(self, text: str) -> str:
        cleaned = self.clean_text(text)
        words = jieba.lcut(cleaned)
        filtered = [w for w in words if w not in self.stop_words and len(w.strip()) > 1]
        return " ".join(filtered)

    def process_uncleaned_reviews(self, batch_size=100):
        db = SessionLocal()
        try:
            query = db.query(Review).filter(
                (Review.cleaned_content.is_(None)) | (Review.cleaned_content == "")
            )
            reviews = query.limit(batch_size).all()

            if not reviews:
                print("✨ 评论均已清洗完毕。")
                return

            for r in reviews:
                r.cleaned_content = self.segment(r.content)

            db.commit()
            print(f"✅ 成功更新 {len(reviews)} 条数据")

        except Exception as e:
            db.rollback() # 回滚放弃刚刚所有修改
            print(f"❌ 异常: {e}")
        finally:
            db.close()

cleaner = DataCleaner()