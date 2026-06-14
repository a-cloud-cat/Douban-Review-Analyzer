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
    page_title="Douban-Insight 数据分析看板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 大厂风格 CSS 样式
# ==========================================
st.markdown("""
<style>
    /* 全局样式 */
    * {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    /* 页面背景 */
    .stApp {
        background-color: #f8fafc;
    }
    
    /* 卡片样式 */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0, 0, 0, 0.06);
        border: 1px solid #e2e8f0;
    }
    
    .metric-card:hover {
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1), 0 2px 4px rgba(0, 0, 0, 0.06);
        transition: box-shadow 0.2s ease;
    }
    
    /* 指标数值 */
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 4px;
    }
    
    .metric-label {
        font-size: 13px;
        color: #64748b;
        font-weight: 500;
    }
    
    /* 侧边栏样式 */
    .css-1d391kg {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
    
    /* 标题样式 */
    .main-title {
        font-size: 24px;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 8px;
    }
    
    .section-title {
        font-size: 16px;
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 16px;
    }
    
    /* 按钮样式 */
    .stButton>button {
        background-color: #3b82f6;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 500;
        transition: background-color 0.2s ease;
    }
    
    .stButton>button:hover {
        background-color: #2563eb;
    }
    
    /* 数据表格 */
    .dataframe-container {
        background: white;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
        border: 1px solid #e2e8f0;
    }
    
    /* 分割线 */
    .divider {
        border-top: 1px solid #e2e8f0;
        margin: 24px 0;
    }
    
    /* 状态标签 */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 500;
    }
    
    .status-running {
        background-color: #dcfce7;
        color: #166534;
    }
    
    .status-pending {
        background-color: #fef3c7;
        color: #92400e;
    }
</style>
""", unsafe_allow_html=True)

def load_data_from_db():
    """
    从数据库加载所有评论数据，并转换为 DataFrame 格式供可视化使用
    """
    try:
        with DatabaseSessionManager.get_session() as db:
            reviews = db.query(Review).all()
            data = []
            for r in reviews:
                data.append({
                    "图书名": r.douban_id,
                    "用户": r.user_name,
                    "评分": r.star,
                    "内容": r.content,
                    "分词结果": r.cleaned_content,
                    "聚类ID": r.cluster_id if r.cluster_id is not None else -1,
                    "情感": r.sentiment if r.sentiment else "未分析"
                })
            return pd.DataFrame(data)
    except Exception as ex:
        logger.error(f"加载数据失败: {ex}")
        return pd.DataFrame()

def load_book_comparison_data():
    """
    从数据库加载图书比较数据
    """
    try:
        with DatabaseSessionManager.get_session() as db:
            reviews = db.query(Review).all()
            if not reviews:
                return pd.DataFrame()
            
            df = pd.DataFrame([{
                "图书名": r.douban_id,
                "评分": r.star,
                "聚类ID": r.cluster_id if r.cluster_id is not None else -1,
                "情感": r.sentiment if r.sentiment else "未分析"
            } for r in reviews])
            
            # 按图书名分组统计
            comparison_df = df.groupby("图书名").agg(
                评论总数=('图书名', 'count'),
                平均评分=('评分', 'mean'),
                聚类0数量=('聚类ID', lambda x: (x == 0).sum()),
                聚类1数量=('聚类ID', lambda x: (x == 1).sum()),
                聚类2数量=('聚类ID', lambda x: (x == 2).sum()),
                正面占比=('情感', lambda x: (x == '正面').mean() * 100),
                负面占比=('情感', lambda x: (x == '负面').mean() * 100)
            ).reset_index()
            
            return comparison_df
    except Exception as ex:
        logger.error(f"加载比较数据失败: {ex}")
        return pd.DataFrame()

# --- 侧边栏 ---
with st.sidebar:
    st.markdown("""
        <div style="padding: 16px 0;">
            <div style="font-size: 18px; font-weight: 700; color: #0f172a; margin-bottom: 4px;">
                Douban-Insight
            </div>
            <div style="font-size: 12px; color: #64748b;">
                豆瓣图书数据分析平台
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # 页面选择
    st.subheader("页面导航")
    page_options = ["数据概览", "图书比较"]
    selected_page = st.selectbox("选择页面", page_options)
    
    if selected_page == "数据概览":
        st.subheader("数据筛选", help="筛选显示的数据范围")
        
        # 评分范围筛选
        star_min, star_max = st.slider(
            "评分范围", 
            min_value=0, 
            max_value=5, 
            value=(0, 5),
            step=1
        )
        
        # 情感筛选
        sentiment_options = ["全部", "正面", "负面", "未分析"]
        selected_sentiment = st.selectbox("情感类型", sentiment_options)
        
        # 聚类筛选
        df_for_filter = load_data_from_db()
        if not df_for_filter.empty:
            cluster_options = ["全部"] + sorted(df_for_filter['聚类ID'].unique().tolist())
            selected_cluster = st.selectbox("聚类分组", cluster_options)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    if st.button("刷新数据", use_container_width=True):
        st.rerun()
    
    st.markdown("""
        <div style="margin-top: 24px;">
            <span class="status-badge status-running">系统运行中</span>
        </div>
    """, unsafe_allow_html=True)

# --- 主界面 ---
if selected_page == "数据概览":
    st.markdown('<div class="main-title">数据分析看板</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size: 14px; color: #64748b; margin-bottom: 24px;">实时监控豆瓣图书评论数据，洞察用户情感趋势</div>', unsafe_allow_html=True)
    
    df = load_data_from_db()
    
    if df.empty:
        st.markdown("""
            <div style="background: white; border-radius: 12px; padding: 40px; text-align: center; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);">
                <div style="font-size: 48px; margin-bottom: 16px;">📋</div>
                <div style="font-size: 16px; color: #334155; font-weight: 500; margin-bottom: 8px;">数据库为空</div>
                <div style="font-size: 14px; color: #64748b;">请先运行爬虫采集数据</div>
            </div>
        """, unsafe_allow_html=True)
    else:
        # 应用筛选条件
        filtered_df = df.copy()
        if 'star_min' in locals() and (star_min > 0 or star_max < 5):
            filtered_df = filtered_df[(filtered_df['评分'] >= star_min) & (filtered_df['评分'] <= star_max)]
        
        if 'selected_sentiment' in locals() and selected_sentiment != "全部":
            filtered_df = filtered_df[filtered_df['情感'] == selected_sentiment]
        
        if 'selected_cluster' in locals() and selected_cluster != "全部":
            filtered_df = filtered_df[filtered_df['聚类ID'] == selected_cluster]
        
        # 1. 顶部指标卡片
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
                <div class="metric-card">
                    <div class="metric-value">{:,}</div>
                    <div class="metric-label">总样本量</div>
                </div>
            """.format(len(filtered_df)), unsafe_allow_html=True)
        
        with col2:
            trained_clusters = filtered_df[filtered_df['聚类ID'] != -1]['聚类ID'].nunique()
            st.markdown("""
                <div class="metric-card">
                    <div class="metric-value">{}</div>
                    <div class="metric-label">聚类数量</div>
                </div>
            """.format(trained_clusters), unsafe_allow_html=True)
        
        with col3:
            avg_star = filtered_df['评分'].mean()
            st.markdown("""
                <div class="metric-card">
                    <div class="metric-value">{:.1f}</div>
                    <div class="metric-label">平均评分</div>
                </div>
            """.format(avg_star), unsafe_allow_html=True)
        
        with col4:
            positive_rate = (filtered_df['情感'] == '正面').mean() * 100
            st.markdown("""
                <div class="metric-card">
                    <div class="metric-value">{:.1f}%</div>
                    <div class="metric-label">正面情感占比</div>
                </div>
            """.format(positive_rate), unsafe_allow_html=True)
        
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        
        # 2. 图表区域
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown('<div class="section-title">聚类分布</div>', unsafe_allow_html=True)
            cluster_df = filtered_df[filtered_df['聚类ID'] != -1]
            
            if not cluster_df.empty:
                cluster_counts = cluster_df['聚类ID'].value_counts().sort_index()
                
                # 创建带样式的条形图
                chart_data = pd.DataFrame({
                    '聚类ID': cluster_counts.index,
                    '数量': cluster_counts.values
                })
                
                st.bar_chart(
                    chart_data,
                    x='聚类ID',
                    y='数量',
                    color='#3b82f6',
                    use_container_width=True
                )
                
                st.markdown('<div style="font-size: 12px; color: #64748b; margin-top: 8px;">注：不同聚类代表不同语义分组</div>', unsafe_allow_html=True)
            else:
                st.markdown("""
                    <div style="background: white; border-radius: 8px; padding: 24px; text-align: center; border: 1px solid #e2e8f0;">
                        <div style="font-size: 24px; margin-bottom: 8px;">🔍</div>
                        <div style="font-size: 14px; color: #64748b;">暂无聚类数据</div>
                        <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">请先执行聚类分析</div>
                    </div>
                """, unsafe_allow_html=True)
        
        with col_right:
            st.markdown('<div class="section-title">情感分布</div>', unsafe_allow_html=True)
            
            sentiment_counts = filtered_df['情感'].value_counts()
            if not sentiment_counts.empty:
                fig, ax = plt.subplots(figsize=(6, 4))
                
                colors = {
                    '正面': '#10b981',
                    '负面': '#ef4444',
                    '未分析': '#94a3b8'
                }
                
                ax.pie(
                    sentiment_counts.values,
                    labels=sentiment_counts.index,
                    autopct='%1.1f%%',
                    colors=[colors.get(label, '#94a3b8') for label in sentiment_counts.index],
                    startangle=90,
                    textprops={'fontsize': 12}
                )
                ax.axis('equal')
                
                st.pyplot(fig, use_container_width=True)
            else:
                st.markdown("""
                    <div style="background: white; border-radius: 8px; padding: 24px; text-align: center; border: 1px solid #e2e8f0;">
                        <div style="font-size: 24px; margin-bottom: 8px;">📊</div>
                        <div style="font-size: 14px; color: #64748b;">暂无情感数据</div>
                    </div>
                """, unsafe_allow_html=True)
        
        # 3. 词云和评分分布
        col_wc, col_score = st.columns(2)
        
        with col_wc:
            st.markdown('<div class="section-title">热点关键词</div>', unsafe_allow_html=True)
            text_data = " ".join(filtered_df['分词结果'].dropna().astype(str))
            
            if text_data.strip():
                font = "C:/Windows/Fonts/msyh.ttc"
                if not Path(font).exists():
                    font = None
                
                wc = WordCloud(
                    font_path=font,
                    width=600,
                    height=400,
                    background_color="white",
                    colormap='Blues',
                    prefer_horizontal=0.9,
                    scale=2
                ).generate(text_data)
                
                fig, ax = plt.subplots(figsize=(6, 4))
                ax.imshow(wc, interpolation="bilinear")
                ax.axis("off")
                plt.tight_layout(pad=0)
                st.pyplot(fig, use_container_width=True)
            else:
                st.markdown("""
                    <div style="background: white; border-radius: 8px; padding: 24px; text-align: center; border: 1px solid #e2e8f0;">
                        <div style="font-size: 24px; margin-bottom: 8px;">📝</div>
                        <div style="font-size: 14px; color: #64748b;">暂无分词数据</div>
                    </div>
                """, unsafe_allow_html=True)
        
        with col_score:
            st.markdown('<div class="section-title">评分分布</div>', unsafe_allow_html=True)
            
            score_counts = filtered_df['评分'].value_counts().sort_index()
            if not score_counts.empty:
                chart_data = pd.DataFrame({
                    '评分': score_counts.index,
                    '数量': score_counts.values
                })
                
                st.bar_chart(
                    chart_data,
                    x='评分',
                    y='数量',
                    color='#8b5cf6',
                    use_container_width=True
                )
                
                st.markdown('<div style="font-size: 12px; color: #64748b; margin-top: 8px;">1-5星评分分布情况</div>', unsafe_allow_html=True)
            else:
                st.markdown("""
                    <div style="background: white; border-radius: 8px; padding: 24px; text-align: center; border: 1px solid #e2e8f0;">
                        <div style="font-size: 24px; margin-bottom: 8px;">⭐</div>
                        <div style="font-size: 14px; color: #64748b;">暂无评分数据</div>
                    </div>
                """, unsafe_allow_html=True)
        
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        
        # 4. 数据表格
        st.markdown('<div class="section-title">数据明细</div>', unsafe_allow_html=True)
        
        # 准备显示数据
        display_df = filtered_df[['图书名', '用户', '评分', '情感', '内容']].copy()
        display_df.index = display_df.index + 1
        
        # 添加评分星级显示
        display_df['评分'] = display_df['评分'].apply(lambda x: '⭐' * x if x > 0 else '-')
        
        # 添加情感标签样式
        def format_sentiment(sentiment):
            if sentiment == '正面':
                return '<span style="color: #10b981; font-weight: 500;">正面</span>'
            elif sentiment == '负面':
                return '<span style="color: #ef4444; font-weight: 500;">负面</span>'
            else:
                return '<span style="color: #94a3b8;">未分析</span>'
        
        display_df['情感'] = display_df['情感'].apply(format_sentiment)
        
        # 限制内容长度
        display_df['内容'] = display_df['内容'].apply(lambda x: x[:50] + '...' if len(str(x)) > 50 else x)
        
        # 自定义表格显示
        st.dataframe(
            display_df,
            column_config={
                "图书名": st.column_config.TextColumn("图书名", width="small"),
                "用户": st.column_config.TextColumn("用户", width="small"),
                "评分": st.column_config.TextColumn("评分", width="small"),
                "情感": st.column_config.TextColumn("情感", width="small"),
                "内容": st.column_config.TextColumn("评论内容", width="large")
            },
            use_container_width=True,
            hide_index=False
        )
        
        # 数据导出
        csv_data = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 导出数据",
            data=csv_data,
            file_name="douban_reviews.csv",
            mime="text/csv",
            use_container_width=True
        )

elif selected_page == "图书比较":
    st.markdown('<div class="main-title">图书数据比较</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size: 14px; color: #64748b; margin-bottom: 24px;">对比分析不同图书的评论数据特征</div>', unsafe_allow_html=True)
    
    comparison_df = load_book_comparison_data()
    
    if comparison_df.empty:
        st.markdown("""
            <div style="background: white; border-radius: 12px; padding: 40px; text-align: center; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);">
                <div style="font-size: 48px; margin-bottom: 16px;">📚</div>
                <div style="font-size: 16px; color: #334155; font-weight: 500; margin-bottom: 8px;">暂无图书数据</div>
                <div style="font-size: 14px; color: #64748b;">请先运行爬虫采集图书评论数据</div>
            </div>
        """, unsafe_allow_html=True)
    else:
        # 1. 比较数据表格
        st.markdown('<div class="section-title">图书比较概览</div>', unsafe_allow_html=True)
        
        display_comparison = comparison_df.copy()
        display_comparison['平均评分'] = display_comparison['平均评分'].apply(lambda x: f'{x:.1f}')
        display_comparison['正面占比'] = display_comparison['正面占比'].apply(lambda x: f'{x:.1f}%')
        display_comparison['负面占比'] = display_comparison['负面占比'].apply(lambda x: f'{x:.1f}%')
        
        st.dataframe(
            display_comparison,
            column_config={
                "图书名": st.column_config.TextColumn("图书名", width="medium"),
                "评论总数": st.column_config.NumberColumn("评论总数", width="small"),
                "平均评分": st.column_config.TextColumn("平均评分", width="small"),
                "聚类0数量": st.column_config.NumberColumn("聚类0", width="small"),
                "聚类1数量": st.column_config.NumberColumn("聚类1", width="small"),
                "聚类2数量": st.column_config.NumberColumn("聚类2", width="small"),
                "正面占比": st.column_config.TextColumn("正面占比", width="small"),
                "负面占比": st.column_config.TextColumn("负面占比", width="small")
            },
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        
        # 2. 可视化比较图表
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="section-title">平均评分对比</div>', unsafe_allow_html=True)
            chart_data = comparison_df[['图书名', '平均评分']]
            st.bar_chart(
                chart_data,
                x='图书名',
                y='平均评分',
                color='#3b82f6',
                use_container_width=True
            )
        
        with col2:
            st.markdown('<div class="section-title">评论数量对比</div>', unsafe_allow_html=True)
            chart_data = comparison_df[['图书名', '评论总数']]
            st.bar_chart(
                chart_data,
                x='图书名',
                y='评论总数',
                color='#10b981',
                use_container_width=True
            )
        
        col3, col4 = st.columns(2)
        
        with col3:
            st.markdown('<div class="section-title">正面情感占比</div>', unsafe_allow_html=True)
            chart_data = comparison_df[['图书名', '正面占比']]
            st.bar_chart(
                chart_data,
                x='图书名',
                y='正面占比',
                color='#10b981',
                use_container_width=True
            )
        
        with col4:
            st.markdown('<div class="section-title">聚类分布对比</div>', unsafe_allow_html=True)
            chart_data = comparison_df.melt(
                id_vars=['图书名'],
                value_vars=['聚类0数量', '聚类1数量', '聚类2数量'],
                var_name='聚类',
                value_name='数量'
            )
            st.bar_chart(
                chart_data,
                x='图书名',
                y='数量',
                color='聚类',
                use_container_width=True
            )