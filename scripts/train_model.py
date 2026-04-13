import sys
import os
import joblib

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.base import SessionLocal
from src.db.models import Review
from engines.clustering.k_means_model import k_means_analyzer

def run_offline_training():
    print("离线训练任务开始")
    db = SessionLocal()
    try:
        reviews = db.query(Review).filter(Review.cleaned_content is not None).all()
        if not reviews:
            print("错误：数据库中没有清洗后的数据")
            return

        print(f"📦 已加载 {len(reviews)} 条记录进行聚类...")

        k_means_analyzer.run_analysis()

        # 拿到算法算出的所有分类标签（比如 0, 1, 2），labels是k算法自带的
        labels = k_means_analyzer.model.labels_

        # 结果回填
        for i, r in enumerate(reviews): # enumerate枚举 循环列表时，同时拿到序号（下标）+元素本身
            r.cluster_id = int(labels[i])

        db.commit()
        print(f"训练完成！聚类标签已同步至数据库字段 cluster_id。")


        model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "engines", "models")
        os.makedirs(model_dir, exist_ok=True) # 文件夹存在就跳过不存在创建
        joblib.dump(k_means_analyzer.model, os.path.join(model_dir, "k_means_latest.pkl"))

        print(f"模型已序列化至: {model_dir}")

    except Exception as e:
        print(f"训练失败: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_offline_training()