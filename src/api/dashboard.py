import sys
import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from pathlib import Path

from src.utils.path_utils import get_project_root
from src.utils.logger import get_logger

# 获取日志器
logger = get_logger("dashboard")

root_dir = get_project_root()

if root_dir not in sys.path:
    sys.path.insert(0, str(root_dir))

try:
    from src.db.base import SessionLocal
    from src.db.models import Review
except ImportError as e:
    st.error(f"导入失败，请确保 src 目录下存在 __init__.py。错误: {e}")
    st.stop()

# ==========================================
# 页面配置
# ==========================================
st.set_page_config(
    page_title="Douban-Insight 大数据分析看板",
    page_icon="📊",
    layout="wide"
)

# 缓存数据，提升加载速度
@st.cache_data(ttl=30)
def load_data_from_db():
    """
    从数据库加载所有影评数据，并转换为 DataFrame 格式供可视化使用

    Args:
        无参数

    Returns:
        pd.DataFrame: 包含用户、评分、内容、分词结果、聚类ID的数据表

    Raises:
        无异常抛出，数据库连接在 finally 中自动关闭
    """
    db = SessionLocal()
    try:
        reviews = db.query(Review).all()
        data = []
        for r in reviews:
            data.append({
                "用户": r.user_name,
                "评分": r.star,
                "内容": r.content,
                "分词结果": r.cleaned_content,
                "聚类ID": r.cluster_id if r.cluster_id is not None else -1
            })
        return pd.DataFrame(data)
    finally:
        db.close()

# --- 侧边栏 ---
st.sidebar.title("🚀 控制面板")
st.sidebar.info("本系统用于豆瓣影评大数据分析。")
if st.sidebar.button("🔄 刷新数据"):
    st.cache_data.clear()
    st.rerun()

# --- 主界面 ---
st.title("🎬 豆瓣影评大数据分析看板")
df = load_data_from_db()

if df.empty:
    st.warning("⚠️ 数据库为空，请先运行爬虫采集数据。")
else:
    # 1. 顶部指标
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("总抓取样本量", len(df))
    with col_m2:
        # 只统计已经过训练的聚类（即 ID 不为 -1 的）
        trained_clusters = df[df['聚类ID'] != -1]['聚类ID'].nunique()
        st.metric("已识别聚类数", trained_clusters)
    with col_m3:
        avg_star = df['评分'].mean()
        st.metric("平均观众评分", f"{avg_star:.1f} ⭐")

    st.divider()

    # 2. 图表层
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("🤖 聚类人群画像分布")
        cluster_df = df[df['聚类ID'] != -1]
        if not cluster_df.empty:
            cluster_counts = cluster_df['聚类ID'].value_counts().sort_index()
            # 这里的 index 就是簇 ID，用于 x 轴
            st.bar_chart(cluster_counts)
            st.caption("注：ID 为 0, 1, 2... 代表不同的语义分簇。")
        else:
            st.info("💡 尚未执行 K-means 训练，请在终端运行：python scripts/train_model.py")

    with col_right:
        st.subheader("☁️ 热点关键词云图")
        # 提取分词结果
        text_data = " ".join(df['分词结果'].dropna().astype(str))
        if text_data.strip():
            # 解决中文乱码：优先匹配 Windows 自带微软雅黑
            font = "C:/Windows/Fonts/msyh.ttc"
            if not Path(font).exists():
                font = None # 容错

            # 修复：直接使用 .generate(text_data)，不加 all_text= 参数
            wc = WordCloud(
                font_path=font,
                width=800, height=500,
                background_color="white",
                colormap='viridis'
            ).generate(text_data)

            fig, ax = plt.subplots()
            ax.imshow(wc, interpolation="bilinear")
            ax.axis("off")
            st.pyplot(fig)
        else:
            st.info("暂无分词数据，请确保已执行清洗任务。")

    # 3. 数据表
    st.divider()
    st.subheader("🔍 原始数据明细")
    st.dataframe(df, width="stretch")

st.sidebar.markdown("---")
st.sidebar.write("✅ 系统状态：运行中")