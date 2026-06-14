import pandas as pd # 用于处理（csv /excel）等
from sklearn.feature_extraction.text import TfidfVectorizer
from src.utils.path_utils import get_data_dir, ensure_dir
from sklearn.cluster import KMeans
from src.utils.logger import get_logger
from src.utils.db_utils import DatabaseSessionManager
from src.utils.db_performance import DatabasePerformanceOptimizer


logger = get_logger("kmeans")


# 情感词典 - 用于辅助判断情感倾向
POSITIVE_WORDS = {
    '精彩', '推荐', '好看', '喜欢', '不错', '好', '棒', '赞', '优秀', '经典',
    '感人', '深刻', '震撼', '值得', '完美', '满意', '惊喜', '惊艳', '出色',
    '完美', '有趣', '生动', '细腻', '真实', '温暖', '感动', '深刻', '难忘',
    '精彩绝伦', '爱不释手', '回味无穷', '受益匪浅', '引人入胜', '发人深省'
}

NEGATIVE_WORDS = {
    '差', '烂', '糟糕', '失望', '垃圾', '无聊', '难看', '恶心', '浪费',
    '不值', '上当', '坑', '骗', '假', '差强人意', '毫无', '枯燥', '乏味',
    '混乱', '难懂', '错误', '虚假', '抄袭', '粗制滥造', '不知所云', '虎头蛇尾',
    '浪费时间', '毫无意义', '令人失望', '惨不忍睹', '一塌糊涂'
}


class KMeansAnalyzer:
    """
    K-Means 聚类分析器，负责对清洗后的评论文本进行自动分组
    支持文本向量化、聚类计算、结果回写数据库、导出CSV文件
    输出正面/负面两个情感标签
    """

    def __init__(self, n_clusters=2):
        """
        初始化 K-Means 聚类分析器

        Args:
            n_clusters: 聚类的分组数量（簇数），默认值为 2（正面、负面）
        """
        self.n_clusters = n_clusters
        # Vectorizer矢量化器，本处指只取最重要的 1000 个词
        self.vectorizer = TfidfVectorizer(max_features=1000)
        # 创建 K-Means 聚类模型（自动分组工具）：分两组（正面/负面），使用++优化模型，固定随机种子，试十次取最优
        self.model = KMeans(n_clusters=self.n_clusters, init='k-means++', random_state=42, n_init=10)
        self.cluster_sentiment = {}  # 存储簇ID到情感标签的映射

    def _count_sentiment_words(self, text):
        """
        统计文本中正面和负面词汇的数量
        
        Args:
            text: 评论文本
            
        Returns:
            tuple: (正面词数量, 负面词数量)
        """
        positive_count = 0
        negative_count = 0
        
        for word in POSITIVE_WORDS:
            if word in text:
                positive_count += 1
        
        for word in NEGATIVE_WORDS:
            if word in text:
                negative_count += 1
        
        return positive_count, negative_count

    def _determine_sentiment(self, df):
        """
        根据评分直接判断情感倾向（更准确）
        
        规则：
        - 4-5星 → 正面
        - 1-2星 → 负面
        - 3星 → 根据关键词判断
        
        Args:
            df: 包含 cluster 和 star 字段的 DataFrame
        """
        # 直接根据评分标记情感
        def get_sentiment_from_rating(star, text):
            if star >= 4:
                return '正面'
            elif star <= 2:
                return '负面'
            else:
                # 3星根据关键词判断
                pos, neg = self._count_sentiment_words(str(text))
                if pos > neg:
                    return '正面'
                elif neg > pos:
                    return '负面'
                else:
                    # 关键词也无法判断，默认标记为负面（保守策略）
                    return '负面'
        
        # 先直接根据评分标记
        df['sentiment'] = df.apply(lambda row: get_sentiment_from_rating(row['star'], row['text']), axis=1)
        
        # 统计结果
        sentiment_counts = df['sentiment'].value_counts().to_dict()
        logger.info(f"基于评分的情感分布: {sentiment_counts}")
        
        # 由于我们现在直接在df上标记情感，不需要cluster_sentiment映射
        # 但为了保持兼容性，仍然设置一个空映射
        self.cluster_sentiment = {0: '正面', 1: '负面'}
        
        return df

    def run_analysis(self):
        """
        执行完整的聚类分析流程：加载数据、向量化、模型训练、结果入库并导出文件

        Returns:
            无返回值

        Raises:
            Exception: 数据库操作或聚类过程中发生的异常
        """
        try:
            with DatabaseSessionManager.get_session() as db:
                reviews = DatabasePerformanceOptimizer.get_cleaned_reviews_batch(
                    db=db,
                    batch_size=1000
                )
                data = [{"id": r.id, "text": r.cleaned_content, "user": r.user_name, "star": r.star}
                        for r in reviews]

                if len(data) < self.n_clusters:
                    logger.warning(f"数据量不足（当前有效数据: {len(data)}），无法进行聚类。")
                    return

                df = pd.DataFrame(data) # 形成一个excel表

                # TF-IDF 向量化：将文本转为机器能理解的数值特征
                logger.info("正在生成 TF-IDF 特征矩阵...")
                tfidf_matrix = self.vectorizer.fit_transform(df['text'])

                # 运行 K-means 算法：寻找数据的自然聚拢点
                logger.info(f"正在计算 {self.n_clusters} 个分簇结果...")
                self.model.fit(tfidf_matrix)
                 # df[名字]=【加列】，加行要完整写。本处是将处理结果加入表格
                df['cluster'] = self.model.labels_

                # 根据评分直接判断情感倾向（改进后的方法）
                logger.info("正在根据评分分析情感倾向...")
                df = self._determine_sentiment(df)

                # 准备批量更新数据（包含情感标签）
                updates = []
                for index, row in df.iterrows():
                    updates.append({
                        "id": int(row['id']),
                        "cluster_id": int(row['cluster']),
                        "sentiment": row['sentiment']
                    })

                # 批量更新聚类结果和情感标签
                if updates:
                    logger.info("正在同步 cluster_id 和 sentiment 到数据库字段...")
                    DatabasePerformanceOptimizer.batch_update_reviews(
                        db=db,
                        updates=updates,
                        batch_size=50
                    )

            processed_dir = ensure_dir(get_data_dir("processed"))
            export_path = processed_dir / "clustered_reviews.csv"
            df.to_csv(export_path, index=False, encoding='utf-8-sig')

            logger.info(f"聚类成功！结果已保存至: {export_path}")
            logger.info("各簇分布统计:")
            logger.info(df['cluster'].value_counts().to_dict())
            logger.info("情感分布统计:")
            logger.info(df['sentiment'].value_counts().to_dict())

        except Exception as e:
            logger.error(f"聚类异常: {e}")

k_means_analyzer = KMeansAnalyzer(n_clusters=2)