import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from src.utils.path_utils import get_data_dir, ensure_dir
from sklearn.cluster import KMeans
from src.utils.logger import get_logger
from src.utils.db_utils import DatabaseSessionManager
from src.utils.db_performance import DatabasePerformanceOptimizer


logger = get_logger("kmeans")


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
        self.vectorizer = TfidfVectorizer(max_features=1000)
        self.model = KMeans(n_clusters=self.n_clusters, init='k-means++', random_state=42, n_init=10)
        self.cluster_sentiment = {}
        self.use_bert = True  # 默认使用 BERT

    def _determine_sentiment(self, df):
        """
        使用改进的情感分析器判断情感倾向
        优先使用 BERT，如果失败则回退到词典方法
        
        Args:
            df: 包含 text 和 star 字段的 DataFrame
            
        Returns:
            df: 添加 sentiment 列的 DataFrame
        """
        # 尝试使用 BERT
        if self.use_bert:
            try:
                logger.info("正在使用 V2 方案（BERT）分析情感...")
                from engines.clustering.sentiment_analyzer_v2 import get_bert_analyzer
                sentiment_analyzer = get_bert_analyzer(use_gpu=True)
                use_bert_analyzer = True
            except Exception as e:
                logger.warning("BERT 模型加载失败: {}".format(e))
                logger.info("回退到 V1 方案（词典方法）")
                use_bert_analyzer = False
                self.use_bert = False
        else:
            use_bert_analyzer = False
        
        if not use_bert_analyzer:
            # 使用词典方法
            from engines.clustering.sentiment_analyzer_v1 import sentiment_analyzer_v1
            sentiment_analyzer = sentiment_analyzer_v1

        sentiments = []
        for idx, row in df.iterrows():
            text = str(row['text']).strip()
            sentiment, confidence = sentiment_analyzer.analyze(text)
            
            # 如果置信度太低或者是中立，结合评分判断
            if confidence < 0.6 or sentiment == '中立':
                star = row['star']
                if star >= 4:
                    sentiment = '正面'
                elif star <= 2:
                    sentiment = '负面'
            
            sentiments.append(sentiment)
            
            if (idx + 1) % 50 == 0:
                logger.info("已处理 {}/{} 条评论".format(idx + 1, len(df)))
        
        df['sentiment'] = sentiments
        
        sentiment_counts = df['sentiment'].value_counts().to_dict()
        logger.info("情感分布: {}".format(sentiment_counts))
        
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
                    logger.warning("数据量不足（当前有效数据: {}），无法进行聚类。".format(len(data)))
                    return

                df = pd.DataFrame(data)

                logger.info("正在生成 TF-IDF 特征矩阵...")
                tfidf_matrix = self.vectorizer.fit_transform(df['text'])

                logger.info("正在计算 {} 个分簇结果...".format(self.n_clusters))
                self.model.fit(tfidf_matrix)
                df['cluster'] = self.model.labels_

                logger.info("正在分析情感倾向...")
                df = self._determine_sentiment(df)

                updates = []
                for index, row in df.iterrows():
                    updates.append({
                        "id": int(row['id']),
                        "cluster_id": int(row['cluster']),
                        "sentiment": row['sentiment']
                    })

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

            logger.info("聚类成功！结果已保存至: {}".format(export_path))
            logger.info("各簇分布统计:")
            logger.info(df['cluster'].value_counts().to_dict())
            logger.info("情感分布统计:")
            logger.info(df['sentiment'].value_counts().to_dict())

        except Exception as e:
            logger.error("聚类异常: {}".format(e))
            import traceback
            logger.error("详细错误信息: {}".format(traceback.format_exc()))


k_means_analyzer = KMeansAnalyzer(n_clusters=2)
