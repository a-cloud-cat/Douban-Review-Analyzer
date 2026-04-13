import re
import jieba

class TextCleaner:
    def __init__(self):
        # 定义基础停用词
        self.stop_words = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "去", "这"}

    def clean_special_chars(self, text: str) -> str:
        """只保留中英文和数字"""
        if not text: return ""
        return re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", text)

    def segment(self, text: str) -> str:
        """执行：清洗 -> 分词 -> 去停用词"""
        cleaned_raw = self.clean_special_chars(text)
        words = jieba.lcut(cleaned_raw)
        # 过滤停用词和长度为 1 的无效词
        filtered = [w for w in words if w not in self.stop_words and len(w) > 1]
        return " ".join(filtered)

# 实例化导出
cleaner = TextCleaner()