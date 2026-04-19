import pandas as pd # 用于处理（csv /excel）等
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
    """

    def __init__(self, n_clusters=3):
        """
        初始化 K-Means 聚类分析器

        Args:
            n_clusters: 聚类的分组数量（簇数），默认值为 3
        """
        self.n_clusters = n_clusters
        # Vectorizer矢量化器，本处指只取最重要的 1000 个词
        self.vectorizer = TfidfVectorizer(max_features=1000)
        # 创建 K-Means 聚类模型（自动分组工具）：分三组，使用++优化模型，固定随机种子，试十次取最优
        self.model = KMeans(n_clusters=self.n_clusters, init='k-means++', random_state=42, n_init=10)

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

                # 准备批量更新数据
                updates = []
                for index, row in df.iterrows():
                    updates.append({
                        "id": int(row['id']),
                        "cluster_id": int(row['cluster'])
                    })
                
                # 批量更新聚类结果
                if updates:
                    logger.info("正在同步 cluster_id 到数据库字段...")
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

        except Exception as e:
            logger.error(f"聚类异常: {e}")

k_means_analyzer = KMeansAnalyzer(n_clusters=3)