# Douban-Insight 豆瓣影评大数据分析系统

基于 Python 的工业级豆瓣评论采集、清洗及情感聚类分析系统。

## 📂 项目结构

```
Douban-Insight/
├── src/                   # 核心源码
│   ├── core/              # 配置管理 (config.py)
│   ├── db/                # 数据库层 (base.py, models.py)
│   ├── crawler/           # 爬虫模块 (base_spider.py, douban_spider.py)
│   ├── services/          # 业务服务 (data_service.py)
│   ├── api/               # 可视化接口 (dashboard.py)
│   └── schemas/           # 数据模型 (item_schema.py)
├── engines/               # 算法引擎
│   ├── preprocess/        # 数据预处理 (cleaner.py)
│   ├── clustering/        # 聚类分析 (k_means_model.py)
│   └── classification/    # 情感分类 (sentiment_clf.py)
├── data/                  # 数据存储
│   ├── raw/               # 原始数据 (raw_xxx.json)
│   └── processed/         # 处理后数据 (clustered_reviews.csv)
├── config/                # 配置文件
│   ├── spider_config.txt  # 爬虫 cURL 配置
│   ├── stopwords.txt      # 停用词表
│   └── user_dict.txt      # 自定义词典
├── scripts/               # 脚本工具
│   ├── reset_db.py        # 重置数据库
│   └── train_model.py     # 训练模型
├── init_db.py             # 数据库初始化入口
├── main.py                # 主程序入口
└── requirements.txt       # 依赖管理
```

## 🛠️ 技术栈

- **后端**: Python 3.10 + FastAPI + SQLAlchemy (ORM)
- **数据库**: MySQL 8.0
- **爬虫**: Requests + BeautifulSoup4
- **NLP 处理**: jieba 分词
- **机器学习**: scikit-learn (K-means 聚类)
- **数据处理**: pandas
- **可视化**: Streamlit + matplotlib + wordcloud

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

### 4. 运行主程序
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
| 5 | 退出程序 | - |

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
| `src/crawler/douban_spider.py` | `_parse_html_logic()` | 解析 HTML，提取评论信息 |

### 数据处理

| 文件 | 类/方法 | 功能 |
|------|---------|------|
| `src/services/data_service.py` | `DataService.save_reviews()` | 保存评论到数据库 |
| `engines/preprocess/cleaner.py` | `DataCleaner.clean_text()` | 清洗文本 |
| `engines/preprocess/cleaner.py` | `DataCleaner.segment()` | jieba 分词 |
| `engines/preprocess/cleaner.py` | `process_uncleaned_reviews()` | 批量处理未清洗数据 |
| `engines/clustering/k_means_model.py` | `KMeansAnalyzer.run_analysis()` | K-means 聚类分析 |

### 主程序

| 文件 | 函数 | 功能 |
|------|------|------|
| `main.py` | `main_menu()` | 主菜单，用户交互 |
| `main.py` | `start_spider_pipeline()` | 启动爬虫任务 |
| `main.py` | `start_clustering_pipeline()` | 启动聚类分析 |
| `main.py` | `start_web_dashboard()` | 启动可视化看板 |
| `main.py` | `clear_data()` | 重置数据库 |

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
    └── 选项 4: 重置数据库
            └── clear_data()
                    ├── Base.metadata.drop_all()
                    └── Base.metadata.create_all()
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

---

## 一. 理解的运行步骤（详细版）

### 数据库初始化
```
.env 配置路径(读取字符串) 
    → config配置(组装 URL) 
    → base配置(生成 Base&Engine) 
    → models表配置(登记表结构)
    → init_db（Base.metadata通过 Engine 发送 SQL落地）
    → MySQL 物理表
```

### 数据采集
```
spider_config.txt 存放 cURL 
    → main.py 读取并传入爬虫
    → BaseSpider 解析 cURL 提取 URL/Headers/Cookies
    → get_html_by_curl 补全 UA 并发送 requests 请求获取原始响应
    → DoubanSpider.fetch_data 判断响应类型，JSON 则提取内部 html，HTML 直接使用
    → 传入_parse_html_logic 通过 BeautifulSoup 解析
    → CSS 选择器定位评论节点、用户名、正文、星级标签
    → 正则提取星级数字并转换为 1-5 星
    → 封装为字典列表 parsed_items 返回
    → data_service.save_reviews 存入数据库
    → cleaner.process_uncleaned_reviews 清洗分词
```

### 聚类分析
```
KMeansAnalyzer.run_analysis
    → 从数据库读取 cleaned_content 不为空的记录
    → TfidfVectorizer 将文本转为 TF-IDF 特征矩阵
    → KMeans.fit 执行聚类
    → 更新数据库 cluster_id 字段
    → 导出 data/processed/clustered_reviews.csv
```

---

## 二. 一些知识点

(1). Python类中方法的第一个参数`self`代表实例对象本身，作用是让方法能访问类里的属性和方法，是固定写法约定。

(2). 正则表达式：
- 字符`?` = 前面那个可有可无
- `()` = 分组抓内容
- `(?P<名字>)` = 分组起名字
- `[]` = 里面字符任选一个
- `[^字符]` = 除了它，别的全都要
- `+` = 一直抓、抓到底
- `\s` = 空白空格

(3). 修饰静态方法（`@staticmethod`）后和实例对象无关，不用 new 对象就能直接调用，使用需要加括号。

修饰器(`@property`)，作用：把函数变成属性，调用写法：`xxx.方法` → 不用加括号

(4). `class xxx(父类)`。区别于java的extend 父类

(5). 网页处理：BeautifulSoup处理后会返回Tag对象内容，该对象自带查找功能：`select`; `select_one`; `find`; `find_all`

(6). 健壮性：`try()` ; `except`(可以写比如`except (ValueError, AttributeError):` 执行句子，这样来避免系统报错，`as e`的话就是所有错误类型) ; `else` ; `finally`

(7). 语法糖：
- 1. 列表推导：`[结果 for 循环 if 判断]`; 没有if部分也可以，结果是数组或者字典也可以
- 2. if三元运算符：`变量 = 满足条件时的值 if 条件 else 不满足时的值`

(8). 链式调用：如`db.query().filter().all()`

(9). 函数参数的设置，默认值一般放右边

(10). 拼路径不要用`.../xxx/xxx`，可能在window(用`\`)和Mac/Linux(用`/`)不兼容，要用特定path库

---

## 三. 模块详解

### (1) 数据库模块
```
.env 配置路径 
    → pathlib 定位文件 + load_dotenv 搬运变量 
    → config 配置 
    → os.getenv 提取 + 类型转换 + 拼接符合 SQLAlchemy 协议的地址 
    → base 配置 
    → 实例化 Engine(连接水管) 与 Base(登记簿) 
    → models 表配置 
    → 通过类继承将 Column 定义注册到 Base.metadata 
    → init_db 入口 
    → import models 激活表结构 + create_all 发送建表 SQL 
    → MySQL 物理表
```

### (2) 爬虫模块
```
spider_config.txt 存放 cURL 
    → main.py 读取并传入爬虫
    → BaseSpider 解析 cURL 提取 URL/Headers/Cookies
    → get_html_by_curl 补全 UA 并发送 requests 请求获取原始响应
    → DoubanSpider.fetch_data 判断响应类型，JSON 则提取内部 html，HTML 直接使用
    → 传入_parse_html_logic 通过 BeautifulSoup 解析
    → CSS 选择器定位评论节点、用户名、正文、星级标签
    → 正则提取星级数字并转换为 1-5 星
    → 封装为字典列表 parsed_items 返回
    → 供后续入库使用
```

### (3) 数据处理模块
```
DataCleaner 类
    → __init__ 加载自定义词典和停用词
    → clean_text 清洗文本（去除特殊字符，保留中英文数字）
    → segment 分词（jieba.lcut + 停用词过滤）
    → process_uncleaned_reviews 批量处理未清洗数据
```

### (4) 聚类模块
```
KMeansAnalyzer 类
    → __init__ 初始化 TfidfVectorizer 和 KMeans 模型
    → run_analysis 执行完整分析流程
        → 读取已清洗数据
        → TF-IDF 向量化
        → K-Means 聚类
        → 更新数据库
        → 导出 CSV
```
