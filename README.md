# Douban-Insight 豆瓣影评大数据分析系统

基于 Python 的工业级豆瓣评论采集、清洗及情感聚类分析系统，提供完整的数据分析 pipeline 和可视化展示。

## 📂 项目结构

```
Douban-Insight/
├── src/                   # 核心源码
│   ├── core/              # 配置管理 (config.py)
│   ├── db/                # 数据库层 (base.py, models.py)
│   ├── crawler/           # 爬虫模块 (base_spider.py, douban_spider.py)
│   ├── services/          # 业务服务 (data_service.py)
│   ├── api/               # 可视化接口 (dashboard.py, endpoints.py)
│   ├── schemas/           # 数据模型 (item_schema.py)
│   └── utils/             # 工具函数 (logger.py, path_utils.py, etc.)
├── engines/               # 算法引擎
│   ├── preprocess/        # 数据预处理 (cleaner.py)
│   └── clustering/        # 聚类分析 (k_means_model.py)
├── config/                # 配置文件
│   ├── spider_config.txt  # 爬虫 cURL 配置
│   ├── stopwords.txt      # 停用词表
│   └── user_dict.txt      # 自定义词典
├── scripts/               # 脚本工具
│   ├── reset_db.py        # 重置数据库
│   └── train_model.py     # 训练模型
├── tests/                 # 测试文件
│   ├── test_cleaner.py    # 清洗模块测试
│   ├── test_db_performance.py # 数据库性能测试
│   ├── test_performance.py # 性能测试
│   └── test_spider.py     # 爬虫测试
├── init_db.py             # 数据库初始化入口
├── main.py                # 主程序入口
├── requirements.txt       # 依赖管理
└── README.md              # 项目文档
```

## 🛠️ 技术栈

- **后端**: Python 3.10 + FastAPI + SQLAlchemy (ORM)
- **数据库**: MySQL 8.0
- **爬虫**: Requests + BeautifulSoup4 + Uncurl
- **NLP 处理**: jieba 分词
- **机器学习**: scikit-learn (K-means 聚类)
- **数据处理**: pandas + numpy
- **可视化**: Streamlit + matplotlib + wordcloud
- **测试**: pytest

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置环境变量
创建 `.env` 文件，配置数据库连接信息：
```env
PROJECT_NAME=douban_insight
DEBUG=False
DB_USER=root
DB_PASS=your_password
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=douban_analysis
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
```

### 3. 初始化数据库
```bash
python init_db.py
```

### 4. 配置爬虫
在 `config/spider_config.txt` 文件中添加从浏览器复制的 cURL 请求，用于抓取豆瓣评论。

### 5. 运行主程序
```bash
python main.py
```

## 📋 功能菜单

运行 `main.py` 后，会显示交互式菜单：

| 选项 | 功能 | 说明 |
|------|------|------|
| 1 | 启动爬虫任务 | 抓取豆瓣评论 + 自动清洗分词 |
| 2 | 执行聚类分析 | K-Means 聚类 + 导出 CSV |
| 3 | 启动可视化看板 | Streamlit 数据展示 |
| 4 | 重置数据库 | 清空所有记录（需确认） |
| 5 | 日志管理功能 | 清理、压缩日志文件 |
| 6 | 运行测试 | 执行项目测试套件 |
| 7 | 退出程序 | - |

## 🔀 运行流程详解

### 1. 数据库初始化流程
```
.env 配置文件 
    ↓ (读取环境变量)
config.py:Settings 类 
    ↓ (组装 DATABASE_URL)
base.py:create_engine 
    ↓ (创建 Engine + Session + Base)
models.py:Review 类 
    ↓ (继承 Base，注册表结构)
init_db.py 
    ↓ (调用 Base.metadata.create_all)
MySQL 物理表
```

### 2. 数据采集与处理流程
```
main.py:start_spider_pipeline(douban_id)
    ↓
DoubanSpider.fetch_data(curl_string)
    ↓
BaseSpider.get_html_by_curl()  →  发送 HTTP 请求
    ↓
DoubanSpider._parse_html_logic()  →  BeautifulSoup 解析 HTML
    ↓
提取: 用户名 + 评论内容 + 星级评分
    ↓
data_service.save_reviews()  →  存入 MySQL
    ↓
cleaner.process_uncleaned_reviews()  →  批量清洗
    ↓
cleaner.segment()  →  jieba 分词 + 停用词过滤
    ↓
更新数据库: cleaned_content 字段
```

### 3. 聚类分析流程
```
main.py:start_clustering_pipeline()
    ↓
KMeansAnalyzer.run_analysis()
    ↓
从数据库读取已清洗的评论 (cleaned_content IS NOT NULL)
    ↓
TfidfVectorizer.fit_transform()  →  文本转数值特征
    ↓
KMeans.fit()  →  执行聚类 (默认 3 个簇)
    ↓
更新数据库: cluster_id 字段
    ↓
导出: data/processed/clustered_reviews.csv
```

### 4. 可视化流程
```
main.py:start_web_dashboard()
    ↓
subprocess.run(["streamlit", "run", "src/api/dashboard.py"])
    ↓
dashboard.py:load_data_from_db()  →  读取评论数据
    ↓
Streamlit 界面展示:
    - 总样本量 / 聚类数 / 平均评分
    - 聚类分布柱状图
    - 词云图
    - 原始数据明细表
```

## 📁 核心文件说明

### 配置与数据库

| 文件 | 类/函数 | 功能 |
|------|---------|------|
| `src/core/config.py` | `Settings` | 管理项目配置，生成 DATABASE_URL |
| `src/db/base.py` | `engine`, `SessionLocal`, `Base` | 数据库引擎、会话工厂、ORM 基类 |
| `src/db/models.py` | `Review` | 评论数据模型，定义表结构 |
| `init_db.py` | `init_db()` | 初始化数据库表结构 |

### 爬虫模块

| 文件 | 类/方法 | 功能 |
|------|---------|------|
| `src/crawler/base_spider.py` | `BaseSpider` | 基础爬虫，处理 HTTP 请求 |
| `src/crawler/douban_spider.py` | `DoubanSpider.fetch_data()` | 抓取豆瓣评论 |
| `src/crawler/douban_spider.py` | `DoubanSpider.fetch_data_concurrent()` | 并发抓取多个页面评论 |
| `src/crawler/douban_spider.py` | `_parse_html_logic()` | 解析 HTML，提取评论信息 |

### 数据处理

| 文件 | 类/方法 | 功能 |
|------|---------|------|
| `src/services/data_service.py` | `DataService.save_reviews()` | 保存评论到数据库 |
| `engines/preprocess/cleaner.py` | `DataCleaner.clean_text()` | 清洗文本 |
| `engines/preprocess/cleaner.py` | `DataCleaner.segment()` | jieba 分词 |
| `engines/preprocess/cleaner.py` | `process_uncleaned_reviews()` | 批量处理未清洗数据 |
| `engines/clustering/k_means_model.py` | `KMeansAnalyzer.run_analysis()` | K-means 聚类分析 |

### 可视化

| 文件 | 类/方法 | 功能 |
|------|---------|------|
| `src/api/dashboard.py` | `load_data_from_db()` | 从数据库加载数据 |
| `src/api/dashboard.py` | Streamlit 组件 | 数据可视化展示 |

### 主程序

| 文件 | 函数 | 功能 |
|------|------|------|
| `main.py` | `main_menu()` | 主菜单，用户交互 |
| `main.py` | `start_spider_pipeline()` | 启动爬虫任务 |
| `main.py` | `start_clustering_pipeline()` | 启动聚类分析 |
| `main.py` | `start_web_dashboard()` | 启动可视化看板 |
| `main.py` | `clear_data()` | 重置数据库 |
| `main.py` | `run_tests()` | 运行测试套件 |
| `main.py` | `log_manager_menu()` | 日志管理功能 |

## 🔄 完整调用链

```
用户选择菜单选项
    │
    ├── 选项 1: 爬虫任务
    │       └── start_spider_pipeline(TARGET_ID)
    │               ├── load_config() → 读取 spider_config.txt
    │               ├── DoubanSpider().fetch_data(curl_string)
    │               │       ├── get_html_by_curl() → HTTP 请求
    │               │       └── _parse_html_logic() → 解析 HTML
    │               ├── data_service.save_reviews() → 存入数据库
    │               └── cleaner.process_uncleaned_reviews() → 清洗分词
    │
    ├── 选项 2: 聚类分析
    │       └── start_clustering_pipeline()
    │               └── KMeansAnalyzer(n_clusters=3).run_analysis()
    │                       ├── 读取已清洗数据
    │                       ├── TfidfVectorizer.fit_transform()
    │                       ├── KMeans.fit()
    │                       ├── 更新 cluster_id
    │                       └── 导出 CSV
    │
    ├── 选项 3: 可视化看板
    │       └── start_web_dashboard()
    │               └── subprocess.run(["streamlit", "run", ...])
    │                       └── dashboard.py
    │                               └── load_data_from_db()
    │                                       └── Streamlit 展示
    │
    ├── 选项 4: 重置数据库
    │       └── clear_data()
    │               ├── Base.metadata.drop_all()
    │               └── Base.metadata.create_all()
    │
    ├── 选项 5: 日志管理
    │       └── log_manager_menu()
    │               └── 日志清理/压缩功能
    │
    └── 选项 6: 运行测试
            └── run_tests()
                    └── pytest 测试套件
```

## 📊 数据流向

```
[豆瓣网站]
    ↓ (HTTP 请求)
[DoubanSpider 爬虫]
    ↓ (解析 HTML)
[原始数据字典]
    ↓ (data_service)
[MySQL 数据库: reviews 表]
    ↓ (cleaner 清洗)
[cleaned_content 字段]
    ↓ (KMeans 聚类)
[cluster_id 字段]
    ↓ (dashboard 读取)
[Streamlit 可视化看板]
```

## 🎯 核心功能

### 1. 智能爬虫
- 支持从浏览器复制的 cURL 请求
- 自动识别 JSON 接口和普通 HTML 页面
- 并发抓取多个页面，提高采集效率
- 提取用户名、评论内容、星级评分等关键信息

### 2. 数据清洗与分词
- 自动清洗文本，去除特殊字符
- 使用 jieba 进行中文分词
- 支持自定义词典和停用词表
- 批量处理未清洗数据，优化数据库性能

### 3. 聚类分析
- 使用 K-means 算法对评论进行自动分组
- TF-IDF 文本向量化，提取关键特征
- 结果自动更新到数据库
- 导出 CSV 格式分析结果

### 4. 可视化看板
- Streamlit 交互式界面
- 总样本量、聚类数、平均评分等关键指标
- 聚类分布柱状图
- 热点关键词云图
- 原始数据明细表

### 5. 日志管理
- 自动记录系统运行日志
- 支持清理和压缩日志文件
- 按天数保留日志

### 6. 测试套件
- 完整的单元测试和性能测试
- 确保系统稳定性和可靠性
- 使用真实的爬取数据进行测试

## 📁 配置文件说明

### 1. spider_config.txt
- 存储从浏览器复制的 cURL 请求
- 用于爬虫抓取豆瓣评论数据

### 2. stopwords.txt
- 存储停用词列表
- 用于文本分词时过滤无意义词汇

### 3. user_dict.txt
- 存储自定义词典
- 提高分词准确性

## 🚀 部署与运行

### 本地开发环境
1. 安装依赖：`pip install -r requirements.txt`
2. 配置 `.env` 文件
3. 初始化数据库：`python init_db.py`
4. 运行主程序：`python main.py`

### 生产环境部署
1. 配置环境变量
2. 设置 MySQL 数据库
3. 部署应用（可使用 uvicorn 或 gunicorn）
4. 定时执行爬虫任务

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 开启 Pull Request

## 📝 注意事项

- 请遵守豆瓣网站的 robots.txt 规则
- 合理设置爬虫抓取频率，避免对服务器造成压力
- 数据库连接信息请妥善保管，不要提交到版本控制系统
- 定期清理日志文件，避免占用过多磁盘空间

## 📄 许可证

MIT License

## 📞 联系我们

如有问题或建议，请通过 GitHub Issues 提交。
