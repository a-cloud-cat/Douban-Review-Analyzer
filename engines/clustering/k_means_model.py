import pandas as pd # 用于处理（csv /excel）等
from sklearn.feature_extraction.text import TfidfVectorizer
from src.utils.path_utils import get_data_dir, ensure_dir
from sklearn.cluster import KMeans
from src.db.base import SessionLocal
from src.db.models import Review

class KMeansAnalyzer:
    def __init__(self, n_clusters=3): # clusters簇
        self.n_clusters = n_clusters
        self.vectorizer = TfidfVectorizer(max_features=1000) # Vectorizer矢量化器，本处指只取最重要的 1000 个词
        # 创建 K-Means 聚类模型（自动分组工具）：分三组，使用++优化模型，固定随机种子，试十次取最优
        self.model = KMeans(n_clusters=self.n_clusters, init='k-means++', random_state=42, n_init=10)

    def run_analysis(self):
        db = SessionLocal()
        try:
            reviews = db.query(Review).filter(
                (Review.cleaned_content.is_not(None)) & (Review.cleaned_content != "")
            ).all()
            data = [{"id": r.id, "text": r.cleaned_content, "user": r.user_name, "star": r.star}
                    for r in reviews]

            if len(data) < self.n_clusters:
                print(f"数据量不足（当前有效数据: {len(data)}），无法进行聚类。")
                return

            df = pd.DataFrame(data) # 形成一个excel表

            # TF-IDF 向量化：将文本转为机器能理解的数值特征
            print(f"正在生成 TF-IDF 特征矩阵...")
            tfidf_matrix = self.vectorizer.fit_transform(df['text'])

            # 运行 K-means 算法：寻找数据的自然聚拢点
            print(f"正在计算 {self.n_clusters} 个分簇结果...")
            self.model.fit(tfidf_matrix)
            df['cluster'] = self.model.labels_ # df[名字]=【加列】，加行要完整写。本处是将处理结果加入表格

            print("正在同步 cluster_id 到数据库字段...")
            for index, row in df.iterrows():
                db.query(Review).filter(Review.id == int(row['id'])).update(
                    {"cluster_id": int(row['cluster'])}
                )
            db.commit()

            processed_dir = ensure_dir(get_data_dir("processed"))
            export_path = processed_dir / "clustered_reviews.csv"
            df.to_csv(export_path, index=False, encoding='utf-8-sig')

            print(f"聚类成功！结果已保存至: {export_path}")
            print("\n各簇分布统计:")
            print(df['cluster'].value_counts())

        except Exception as e:
            db.rollback()
            print(f"聚类异常: {e}")
        finally:
            db.close()

k_means_analyzer = KMeansAnalyzer(n_clusters=3)