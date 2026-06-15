import pandas as pd
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger("sentiment_v2")

MODELS_DIR = Path(__file__).parent.parent.parent / "models"
BERT_MODEL_PATH = MODELS_DIR / "bert-sentiment-model"


class SentimentAnalyzerV2:
    """
    基于 BERT 的情感分析器（使用 uer/roberta-base-finetuned-dianping-chinese）
    必须先运行 download_bert_model.py 下载模型
    
    模型说明：
    - 输入：中文文本（最长512 token）
    - 输出：0=负面, 1=正面（二分类）
    - 准确率：约92-95%（在中文评论语料上）
    """

    def __init__(self, use_gpu=True):
        """
        初始化 BERT 分析器
        
        Args:
            use_gpu: 是否使用 GPU
        """
        self.use_gpu = use_gpu
        self.model = None
        self.tokenizer = None
        self._load_model()

    def _load_model(self):
        """加载本地模型（不下载）"""
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch

            logger.info("正在加载本地 BERT 模型...")

            # 检查模型是否存在
            if not BERT_MODEL_PATH.exists():
                logger.error("模型文件不存在: {}".format(BERT_MODEL_PATH))
                logger.error("请先运行: python scripts/download_bert_model.py")
                raise FileNotFoundError("模型不存在，请先下载")

            # 检查必要文件（支持 safetensors 格式）
            required_files = ['config.json', 'model.safetensors', 'tokenizer.json']
            missing_files = []
            for f in required_files:
                if not (BERT_MODEL_PATH / f).exists():
                    missing_files.append(f)
            
            if missing_files:
                logger.error("模型文件不完整，缺少: {}".format(', '.join(missing_files)))
                logger.error("请重新运行: python scripts/download_bert_model.py")
                raise FileNotFoundError("模型文件不完整")

            logger.info("从本地加载模型: {}".format(BERT_MODEL_PATH))
            
            # 从本地加载（transformers 会自动识别 safetensors 格式）
            self.tokenizer = AutoTokenizer.from_pretrained(str(BERT_MODEL_PATH))
            self.model = AutoModelForSequenceClassification.from_pretrained(
                str(BERT_MODEL_PATH),
                from_tf=False,
                local_files_only=True
            )

            # 移到 GPU
            if self.use_gpu and torch.cuda.is_available():
                self.model = self.model.to("cuda")
                logger.info("模型已加载到 GPU")
            else:
                logger.info("模型运行在 CPU 模式（较慢，建议有 GPU）")

            self.model.eval()
            logger.info("BERT 模型加载成功！")

        except FileNotFoundError as e:
            logger.error("模型文件不存在: {}".format(e))
            raise
        except Exception as e:
            logger.error("模型加载失败: {}".format(e))
            raise

    def analyze(self, text):
        """
        分析单条评论
        
        Returns:
            tuple: ('正面'/'负面'/'中立', 置信度 0-1)
        """
        if not text or not self.model:
            return '中立', 0.5

        try:
            import torch
            
            text = str(text).strip()[:512]

            # 分词和编码
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                max_length=512,
                truncation=True,
                padding=True
            )

            # 移到同一设备
            if self.use_gpu and torch.cuda.is_available():
                inputs = {k: v.to("cuda") for k, v in inputs.items()}

            # 预测
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits[0]
                probs = torch.softmax(logits, dim=-1)

            # uer/roberta-base-finetuned-dianping-chinese 模型输出：
            # 0 = negative（负面）, 1 = positive（正面）
            neg_prob = probs[0].item()  # 负面概率
            pos_prob = probs[1].item()  # 正面概率
            
            # 决策逻辑：考虑置信度
            confidence = max(pos_prob, neg_prob)
            
            if confidence < 0.6:
                # 置信度太低，返回中立
                sentiment = '中立'
                confidence = 0.5
            elif pos_prob > neg_prob:
                sentiment = '正面'
            else:
                sentiment = '负面'

            return sentiment, confidence

        except Exception as e:
            logger.error("模型推理失败: {}".format(e))
            return '中立', 0.5

    def batch_analyze(self, texts, batch_size=16):
        """批量分析"""
        results = []
        total = len(texts)

        for i in range(0, total, batch_size):
            batch = texts[i : i + batch_size]
            
            for text in batch:
                sentiment, confidence = self.analyze(text)
                results.append({'sentiment': sentiment, 'confidence': confidence})
            
            if (i + batch_size) < total:
                logger.info("处理进度: {}/{}".format(i + batch_size, total))

        return pd.DataFrame(results)


# 全局实例
sentiment_analyzer_v2 = None

def get_bert_analyzer(use_gpu=True):
    """获取 BERT 分析器实例（懒初始化）"""
    global sentiment_analyzer_v2
    if sentiment_analyzer_v2 is None:
        sentiment_analyzer_v2 = SentimentAnalyzerV2(use_gpu=use_gpu)
    return sentiment_analyzer_v2
