import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE
from src.utils.logger import get_logger
from src.utils.path_utils import get_project_root, ensure_dir
from src.utils.db_utils import DatabaseSessionManager
from src.utils.db_performance import DatabasePerformanceOptimizer
from engines.preprocess.cleaner import cleaner
import os

logger = get_logger("classifier")


class SentimentClassifier:
    """
    情感分类器，支持多种分类算法（SVM、逻辑回归、决策树）
    支持非平衡处理和数据归一化
    """

    def __init__(self, model_type='svm', use_smote=False, use_scaler=False):
        """
        初始化分类器
        
        Args:
            model_type: 模型类型，可选 'svm', 'logistic', 'tree'
            use_smote: 是否使用SMOTE处理不平衡数据
            use_scaler: 是否使用数据归一化
        """
        self.model_type = model_type
        self.use_smote = use_smote
        self.use_scaler = use_scaler
        self.vectorizer = TfidfVectorizer(max_features=1000)
        self.scaler = StandardScaler(with_mean=False) if use_scaler else None
        self.model = self._create_model()
        self.model_path = get_project_root() / "models"

    def _create_model(self):
        """根据选择的类型创建分类模型"""
        if self.model_type == 'svm':
            return SVC(kernel='linear', random_state=42, probability=True)
        elif self.model_type == 'logistic':
            return LogisticRegression(random_state=42, max_iter=1000)
        elif self.model_type == 'tree':
            return DecisionTreeClassifier(random_state=42)
        else:
            raise ValueError(f"不支持的模型类型: {self.model_type}")

    def load_data_from_db(self):
        """从数据库加载已标注情感的数据"""
        try:
            with DatabaseSessionManager.get_session() as db:
                reviews = DatabasePerformanceOptimizer.get_cleaned_reviews_batch(
                    db=db,
                    batch_size=1000
                )
                data = [{
                    "text": r.cleaned_content,
                    "sentiment": r.sentiment
                } for r in reviews if r.cleaned_content and r.sentiment]
                
                if not data:
                    logger.warning("数据库中没有已标注情感的数据，请先运行聚类分析")
                    return None, None, "数据库中没有已标注情感的数据，请先运行聚类分析"
                
                # 检查数据量
                if len(data) < 10:
                    logger.warning(f"训练数据太少（{len(data)}条），建议至少收集50条以上评论")
                    return None, None, f"训练数据太少（{len(data)}条），建议至少收集50条以上评论"
                
                df = pd.DataFrame(data)
                texts = df['text'].tolist()
                labels = df['sentiment'].apply(lambda x: 1 if x == '正面' else 0).tolist()
                
                # 检查类别分布
                positive_count = sum(labels)
                negative_count = len(labels) - positive_count
                if positive_count == 0 or negative_count == 0:
                    logger.warning(f"类别分布不均衡：正面={positive_count}, 负面={negative_count}")
                    return None, None, f"类别分布不均衡，需要同时有正面和负面数据"
                
                logger.info(f"加载数据: {len(texts)} 条评论")
                logger.info(f"类别分布: 正面={positive_count}, 负面={negative_count}")
                
                return texts, labels, None
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            return None, None, str(e)
            return None, None

    def train(self, texts=None, labels=None):
        """
        训练分类模型
        
        Args:
            texts: 文本数据列表（可选，不传则从数据库加载）
            labels: 标签列表（可选，不传则从数据库加载）
        
        Returns:
            dict: 训练结果指标
        """
        # 如果没有提供数据，从数据库加载
        if texts is None or labels is None:
            texts, labels, error_msg = self.load_data_from_db()
            if texts is None:
                self.last_error = error_msg
                return None
        
        # 1. 文本向量化
        logger.info("正在生成 TF-IDF 特征...")
        X = self.vectorizer.fit_transform(texts)
        y = labels
        
        # 2. 非平衡处理（SMOTE）
        if self.use_smote:
            logger.info("正在使用 SMOTE 处理不平衡数据...")
            smote = SMOTE(random_state=42)
            X, y = smote.fit_resample(X, y)
            logger.info(f"SMOTE 处理后: 样本数={len(y)}, 正面={sum(y)}, 负面={len(y)-sum(y)}")
        
        # 3. 数据归一化
        if self.use_scaler:
            logger.info("正在进行数据归一化...")
            X = self.scaler.fit_transform(X)
        
        # 4. 划分训练集和测试集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # 5. 训练模型
        logger.info(f"正在训练 {self.model_type.upper()} 模型...")
        self.model.fit(X_train, y_train)
        
        # 6. 评估模型
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        logger.info(f"训练完成！准确率: {accuracy:.4f}")
        logger.info("\n分类报告:")
        logger.info(classification_report(y_test, y_pred, target_names=['负面', '正面']))
        logger.info("\n混淆矩阵:")
        logger.info(confusion_matrix(y_test, y_pred))
        
        return {
            'accuracy': accuracy,
            'classification_report': classification_report(y_test, y_pred, target_names=['负面', '正面']),
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist()
        }

    def predict(self, text):
        """
        预测单条评论的情感
        
        Args:
            text: 评论文本（原始文本，会自动进行分词清洗）
        
        Returns:
            dict: {'sentiment': '正面'/'负面', 'confidence': 概率值}
        """
        if not self.model:
            raise Exception("模型尚未训练或加载")
        
        # 检查文本是否为空
        if not text or not text.strip():
            return {'sentiment': '负面', 'confidence': 0.5}
        
        try:
            # 对输入文本进行预处理（分词和清洗），与训练数据保持一致
            cleaned_text = cleaner.clean_text(text)
            
            logger.debug(f"原始文本: {text[:20]}...")
            logger.debug(f"清洗后文本: {cleaned_text[:20]}...")
            
            # 向量化
            X = self.vectorizer.transform([cleaned_text])
            
            # 归一化（如果启用）
            if self.use_scaler:
                X = self.scaler.transform(X)
            
            # 预测
            prediction = self.model.predict(X)[0]
            probabilities = self.model.predict_proba(X)[0]
            probability = round(max(probabilities), 4)
            
            logger.debug(f"预测结果: {prediction}, 概率: {probabilities}")
            
            return {
                'sentiment': '正面' if prediction == 1 else '负面',
                'confidence': probability
            }
        except Exception as e:
            logger.error(f"预测失败: {e}")
            return {'sentiment': '负面', 'confidence': 0.5}

    def batch_predict(self, texts):
        """批量预测多条评论"""
        results = []
        for text in texts:
            result = self.predict(text)
            result['text'] = text
            results.append(result)
        return results

    def save_model(self, filename=None):
        """保存模型到文件"""
        ensure_dir(self.model_path)
        
        if filename is None:
            filename = f"sentiment_{self.model_type}.pkl"
        
        model_data = {
            'model': self.model,
            'vectorizer': self.vectorizer,
            'scaler': self.scaler,
            'model_type': self.model_type,
            'use_smote': self.use_smote,
            'use_scaler': self.use_scaler
        }
        
        joblib.dump(model_data, self.model_path / filename)
        logger.info(f"模型已保存到: {self.model_path / filename}")
        return str(self.model_path / filename)

    def load_model(self, filename=None):
        """从文件加载模型"""
        if filename is None:
            filename = f"sentiment_{self.model_type}.pkl"
        
        model_path = self.model_path / filename
        if not model_path.exists():
            logger.error(f"模型文件不存在: {model_path}")
            return False
        
        model_data = joblib.load(model_path)
        self.model = model_data['model']
        self.vectorizer = model_data['vectorizer']
        self.scaler = model_data['scaler']
        self.model_type = model_data['model_type']
        self.use_smote = model_data['use_smote']
        self.use_scaler = model_data['use_scaler']
        
        logger.info(f"模型已从 {model_path} 加载")
        return True

    def run_analysis(self):
        """执行完整的分类分析流程"""
        logger.info(f"开始分类分析 (模型: {self.model_type}, SMOTE: {self.use_smote}, 归一化: {self.use_scaler})")
        
        # 训练模型
        result = self.train()
        if result is None:
            return False
        
        # 保存模型
        self.save_model()
        
        # 测试预测
        test_texts = [
            "这本书非常精彩，强烈推荐！",
            "内容很枯燥，不建议购买",
            "情节跌宕起伏，人物刻画细腻"
        ]
        
        logger.info("\n测试预测:")
        for text in test_texts:
            pred = self.predict(text)
            logger.info(f"评论: {text}")
            logger.info(f"预测结果: {pred['sentiment']} (置信度: {pred['confidence']})\n")
        
        return True


# 创建全局实例
sentiment_classifier = SentimentClassifier(model_type='svm', use_smote=False, use_scaler=False)
