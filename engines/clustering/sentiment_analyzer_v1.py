import re
import pandas as pd
from src.utils.logger import get_logger

logger = get_logger("sentiment_v1")


class SentimentAnalyzerV1:
    """
    基于词典和否定词的情感分析器（改进版）
    优点：快速、无需下载模型、准确率 70-80%
    """

    def __init__(self):
        # 扩展的正面词典
        self.positive_words = {
            '精彩', '推荐', '好看', '喜欢', '不错', '好', '棒', '赞', '优秀', '经典',
            '感人', '深刻', '震撼', '值得', '完美', '满意', '惊喜', '惊艳', '出色',
            '有趣', '生动', '细腻', '真实', '温暖', '感动', '难忘', '超级',
            '爱不释手', '回味无穷', '受益匪浅', '引人入胜', '发人深省',
            '精彩绝伦', '很好', '太好', '相当', '绝对', '必读', '经典之作', '必看',
            '认同', '赞同', '同意', '支持', '欣赏', '钦佩', '敬服', '崇拜',
            '激动', '高兴', '开心', '愉快', '兴奋', '欣喜', '快乐', '满足',
            '有内涵', '有意义', '有价值', '有收获', '受启发', '学到',
            '逻辑严密', '层次分明', '条理清晰', '表达清楚', '写得好',
            '特别', '尤其', '格外', '分外', '倍感', '印象深刻', '颇为'
        }

        # 扩展的负面词典
        self.negative_words = {
            '差', '烂', '糟糕', '失望', '垃圾', '无聊', '难看', '恶心', '浪费',
            '不值', '上当', '坑', '骗', '假', '差强人意', '毫无', '枯燥', '乏味',
            '混乱', '难懂', '错误', '虚假', '抄袭', '粗制滥造', '不知所云', '虎头蛇尾',
            '浪费时间', '毫无意义', '令人失望', '惨不忍睹', '一塌糊涂',
            '简直', '太差', '完全', '根本', '很烂', '非常差', '极差',
            '讨厌', '厌烦', '反感', '厌恶', '恼怒', '气愤', '愤怒', '生气',
            '痛苦', '难受', '郁闷', '沮丧', '沉闷', '压抑', '黯淡',
            '无趣', '乏味', '死板', '呆板', '生硬', '僵硬', '刻板',
            '粗糙', '粗陋', '简陋', '草率', '匆匆', '仓促', '仓皇',
            '拖沓', '冗长', '啰嗦', '重复', '堆砌', '铺垫', '废话',
            '逻辑混乱', '前后不一', '自相矛盾', '颠三倒四', '莫名其妙'
        }

        # 否定词（会反转情感）
        self.negation_words = {'不', '没', '无', '非', '从不', '并未', '并不', '绝非', '不是'}

        # 强度词（加强情感）
        self.intensifier_words = {'非常', '很', '太', '极', '格外', '特别', '相当', '十分', '异常', '尤其'}

    def _has_negation_before(self, text, word_pos, window=6):
        """检查单词前是否有否定词"""
        start = max(0, word_pos - window)
        before_text = text[start:word_pos]
        for neg in self.negation_words:
            if neg in before_text:
                return True
        return False

    def _has_intensifier_before(self, text, word_pos, window=4):
        """检查单词前是否有强度词"""
        start = max(0, word_pos - window)
        before_text = text[start:word_pos]
        for intensifier in self.intensifier_words:
            if intensifier in before_text:
                return True
        return False

    def analyze(self, text):
        """
        分析单条评论的情感倾向
        
        Args:
            text: 评论文本
            
        Returns:
            tuple: ('正面'/'负面'/'中立', 置信度 0-1)
        """
        if not text:
            return '中立', 0.5

        text = str(text).strip()
        pos_score = 0
        neg_score = 0

        # 检查正面词
        for word in self.positive_words:
            positions = [m.start() for m in re.finditer(re.escape(word), text)]
            for pos in positions:
                if self._has_negation_before(text, pos):
                    # 否定反转，变成负面
                    neg_score += 2
                elif self._has_intensifier_before(text, pos):
                    # 强度词加强
                    pos_score += 2
                else:
                    pos_score += 1

        # 检查负面词
        for word in self.negative_words:
            positions = [m.start() for m in re.finditer(re.escape(word), text)]
            for pos in positions:
                if self._has_negation_before(text, pos):
                    # 否定反转，变成正面
                    pos_score += 2
                elif self._has_intensifier_before(text, pos):
                    # 强度词加强
                    neg_score += 2
                else:
                    neg_score += 1

        total = pos_score + neg_score

        if total == 0:
            # 没有找到关键词，返回中立
            return '中立', 0.5

        pos_ratio = pos_score / total

        if pos_ratio >= 0.6:
            return '正面', pos_ratio
        elif pos_ratio <= 0.4:
            return '负面', 1 - pos_ratio
        else:
            return '中立', 0.5

    def batch_analyze(self, texts):
        """批量分析"""
        results = []
        for text in texts:
            sentiment, confidence = self.analyze(text)
            results.append({'sentiment': sentiment, 'confidence': confidence})
        return pd.DataFrame(results)


# 全局实例
sentiment_analyzer_v1 = SentimentAnalyzerV1()