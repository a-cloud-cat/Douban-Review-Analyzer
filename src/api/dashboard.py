import sys
import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from pathlib import Path

root_dir = Path(__file__).parent.parent.parent

if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.utils.logger import get_logger


logger = get_logger("dashboard")

# 预定义变量以避免导入失败时的作用域问题
Review = None
DatabaseSessionManager = None
try:
    from src.db.models import Review
    from src.utils.db_utils import DatabaseSessionManager
except ImportError as import_error:
    st.error(f"导入失败，请确保 src 目录下存在 __init__.py。错误: {import_error}")
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
    """
    try:
        with DatabaseSessionManager.get_session() as db:
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
    except Exception as ex:
        logger.error(f"加载数据失败: {ex}")
        return pd.DataFrame()

# --- 侧边栏 ---
st.sidebar.title("控制面板")
st.sidebar.info("本系统用于豆瓣影评大数据分析。")
if st.sidebar.button("刷新数据"):
    st.cache_data.clear()
    st.rerun()

# --- 主界面 ---
st.title("豆瓣影评大数据分析看板")
df = load_data_from_db()

if df.empty:
    st.warning("数据库为空，请先运行爬虫采集数据。")
else:
    # 1. 顶部指标
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("总抓取样本量", len(df))
    with col_m2:
        trained_clusters = df[df['聚类ID'] != -1]['聚类ID'].nunique()
        st.metric("已识别聚类数", trained_clusters)
    with col_m3:
        avg_star = df['评分'].mean()
        st.metric("平均观众评分", f"{avg_star:.1f} ⭐")

    st.divider()

    # 2. 图表层
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("聚类人群画像分布")
        cluster_df = df[df['聚类ID'] != -1]
        if not cluster_df.empty:
            cluster_counts = cluster_df['聚类ID'].value_counts().sort_index()
            st.bar_chart(cluster_counts)
            st.caption("注：ID 为 0, 1, 2... 代表不同的语义分簇。")
        else:
            st.info("尚未执行 K-means 训练，请在终端运行：python scripts/train_model.py")

    with col_right:
        st.subheader("热点关键词云图")
        text_data = " ".join(df['分词结果'].dropna().astype(str))
        if text_data.strip():
            font = "C:/Windows/Fonts/msyh.ttc"
            if not Path(font).exists():
                font = None

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
    st.subheader("原始数据明细")
    df_display = df.copy()
    df_display.index = df_display.index + 1
    st.dataframe(df_display, width="stretch")

st.sidebar.markdown("---")
st.sidebar.write("系统状态：运行中")