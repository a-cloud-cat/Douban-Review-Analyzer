import sys
import joblib

from src.utils.path_utils import get_project_root, ensure_dir
from src.utils.logger import get_logger

PROJECT_ROOT = get_project_root()

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.db.base import SessionLocal
from src.db.models import Review
from engines.clustering.k_means_model import k_means_analyzer

# 获取日志器
logger = get_logger("train_model")

def run_offline_training():
    logger.info("离线训练任务开始")
    db = SessionLocal()
    try:
        reviews = db.query(Review).filter(Review.cleaned_content is not None).all()
        if not reviews:
            logger.error("数据库中没有清洗后的数据")
            return

        logger.info(f"已加载 {len(reviews)} 条记录进行聚类...")

        k_means_analyzer.run_analysis()

        # 拿到算法算出的所有分类标签（比如 0, 1, 2），labels是k算法自带的
        labels = k_means_analyzer.model.labels_

        # 结果回填
        for i, r in enumerate(reviews): # enumerate枚举 循环列表时，同时拿到序号（下标）+元素本身
            r.cluster_id = int(labels[i])

        db.commit()
        logger.info("训练完成！聚类标签已同步至数据库字段 cluster_id。")


        model_dir = ensure_dir(PROJECT_ROOT / "engines" / "models")
        joblib.dump(k_means_analyzer.model, model_dir / "k_means_latest.pkl")

        logger.info(f"模型已序列化至: {model_dir}")

    except Exception as e:
        logger.error(f"训练失败: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_offline_training()