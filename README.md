# Douban-Insight 豆瓣图书评论数据分析系统

一套基于 Python 搭建的豆瓣图书评论采集、数据清洗、情感聚类分析完整工具，从数据爬取、预处理、模型分析到可视化展示，形成全流程落地方案。

---

## 目录说明

下载项目后，请在项目根目录下执行所有命令。

### 标准目录结构

```plaintext
d:\AMyProject\Douban-Insight\
├── src/
├── engines/
├── config/
├── scripts/
├── tests/
├── models/
├── init_db.py
├── main.py
├── requirements.txt
└── README.md
```

### 目录嵌套处理

如果解压后出现双层文件夹嵌套，请将内层所有文件和文件夹，直接移动到外层根目录。

**错误示例：**

```plaintext
d:\AMyProject\Douban-Insight/
└── Douban-Review-Analyzer-main/
        ├── requirements.txt
        └── main.py
```

**修正后：**

```plaintext
d:\AMyProject\Douban-Insight/
├── requirements.txt
├── main.py
└── 其余文件/文件夹
```

---

## 项目整体结构

```plaintext
Douban-Insight/
├── src/                   # 核心业务代码
│   ├── core/              # 项目全局配置
│   ├── db/                # 数据库连接、数据表模型
│   ├── crawler/           # 爬虫核心代码
│   ├── services/          # 数据读写业务逻辑
│   ├── api/               # 可视化看板接口与页面
│   ├── schemas/           # 通用数据结构定义
│   └── utils/             # 工具类、日志、路径处理等
├── engines/               # 算法处理模块
│   ├── preprocess/        # 文本数据清洗、分词
│   ├── clustering/        # K-Means 聚类、情感分析模型
│   └── classification/    # 监督学习分类器（SVM/逻辑回归/决策树）
├── config/                # 静态配置文件
│   ├── spider_config.txt  # 爬虫请求配置
│   ├── stopwords.txt      # 分词停用词库
│   └── user_dict.txt      # 分词自定义词典
├── models/                # 训练好的模型文件
├── scripts/               # 辅助执行脚本
│   ├── reset_db.py        # 数据库重置脚本
│   └── train_model.py     # 模型训练脚本
├── tests/                 # 单元测试文件
│   ├── test_cleaner.py    # 文本清洗测试
│   ├── test_db_performance.py # 数据库性能测试
│   ├── test_performance.py # 整体性能测试
│   └── test_spider.py     # 爬虫功能测试
├── init_db.py             # 数据库初始化入口
├── main.py                # 程序主入口
├── requirements.txt       # 项目依赖清单
└── README.md              # 项目说明文档
```

---

## 技术选型

| 分类 | 所用技术 | 版本要求 |
|------|----------|---------|
| 开发语言 | Python | 3.10 及以上 |
| 数据库 | MySQL | 8.0 及以上 |
| 数据爬取 | Requests + BeautifulSoup4 | 无特殊版本限制 |
| 中文分词 | jieba | 无特殊版本限制 |
| 机器学习 | scikit-learn | 无特殊版本限制 |
| 数据可视化 | Streamlit | 无特殊版本限制 |

---

## 快速上手（按顺序操作）

### 1. 进入项目根目录

打开命令行，切换到项目所在路径：

```bash
cd d:\AMyProject\Douban-Insight
```

### 2. 安装项目依赖

```bash
pip install -r requirements.txt
```

### 3. 数据库准备

启动本地 MySQL 服务（Windows 需以管理员身份运行命令行）：

```bash
net start MySQL80
```

也可以直接在系统服务中手动启动 MySQL。

**新建专用数据库**

登录 MySQL 客户端，执行下述语句创建数据库：

```sql
CREATE DATABASE IF NOT EXISTS douban_analysis CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

**配置数据库账号密码**

在项目根目录新建 .env 配置文件，写入以下内容，并修改为自己的 MySQL 登录密码：

```env
PROJECT_NAME=douban_insight
DEBUG=False
DB_USER=root
DB_PASS=你的MySQL密码
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=douban_analysis
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
```

提示：.env 文件包含敏感信息，请勿上传至公共代码仓库。

### 4. 初始化数据表

```bash
python init_db.py
```

### 5. 配置爬虫请求

打开 config/spider_config.txt，将浏览器抓包获取的 cURL 请求内容粘贴到文件中。

### 6. 启动主程序

```bash
python main.py
```

---

## 功能菜单说明

运行 main.py 后会显示交互式菜单，选择对应序号即可使用功能：

| 序号 | 功能 | 简要说明 |
|------|------|----------|
| 1 | 启动爬虫任务 | 抓取豆瓣评论，自动完成文本清洗与分词（串行爬取防反爬） |
| 2 | 执行聚类分析 | 运行 K-Means 聚类、基于评分的情感分析，结果支持导出 CSV |
| 3 | 启动可视化看板 | 打开 Streamlit 交互式数据页面，支持数据筛选查看 |
| 4 | 分类分析 | 训练 SVM/逻辑回归/决策树分类模型，支持 SMOTE 非平衡处理 |
| 5 | 重置数据库 | 清空库内所有数据（执行前会二次确认） |
| 6 | 日志管理 | 清理、压缩项目运行日志 |
| 7 | 运行测试 | 执行全套单元测试，校验各模块可用性 |
| 8 | 退出程序 | 结束运行 |

---

## 核心运行流程

### 1. 数据库初始化流程

读取 .env 配置 → 全局配置类解析参数 → 生成数据库连接信息 → 初始化数据库引擎与会话 → 加载数据表模型 → 执行建表操作。

### 2. 数据采集与处理流程

启动爬虫任务 → 发送网络请求获取页面源码 → 解析页面提取用户名、评论内容、星级评分等数据 → 数据存入数据库 → 批量清洗文本内容 → 结合分词库完成分词、停用词过滤 → 更新数据库内清洗后内容。

### 3. 聚类分析流程

调取分析功能 → 从数据库读取已完成清洗的评论数据 → 通过 TF-IDF 完成文本向量化 → 运行 K-Means 算法实现文本聚类 → 结合评分判断每组数据的情感倾向 → 将聚类、情感标签回写数据库 → 导出分析结果为 CSV 文件。

### 4. 可视化流程

启动可视化看板 → 读取数据库数据 → 加载至 Streamlit 页面 → 展示数据指标、分布图表、关键词云、明细表格，同时支持数据筛选与文件导出。

---

## 核心文件说明

### 配置与数据库

| 文件 | 类 / 函数 | 功能 |
|------|----------|------|
| src/core/config.py | Settings | 管理项目配置，拼接数据库连接地址 |
| src/db/base.py | engine, SessionLocal, Base | 数据库引擎、会话工厂、ORM 基类 |
| src/db/models.py | Review | 定义评论数据表结构 |
| init_db.py | init_db() | 执行数据表初始化创建 |

### 爬虫模块

| 文件 | 类 / 方法 | 功能 |
|------|----------|------|
| src/crawler/base_spider.py | BaseSpider | 基础爬虫类，统一处理网络请求 |
| src/crawler/douban_spider.py | DoubanSpider.fetch_data() | 单线程抓取豆瓣评论数据 |
| src/crawler/douban_spider.py | DoubanSpider.fetch_data_concurrent() | 多线程并发抓取多页评论 |
| src/crawler/douban_spider.py | _parse_html_logic() | 解析页面，提取有效评论信息 |

### 数据处理

| 文件 | 类 / 方法 | 功能 |
|------|----------|------|
| src/services/data_service.py | DataService.save_reviews() | 将评论数据写入数据库 |
| engines/preprocess/cleaner.py | DataCleaner.clean_text() | 清理文本中的无效特殊字符 |
| engines/preprocess/cleaner.py | DataCleaner.segment() | 基于 jieba 完成中文分词 |
| engines/preprocess/cleaner.py | process_uncleaned_reviews() | 批量处理库中未清洗的评论数据 |
| engines/clustering/k_means_model.py | KMeansAnalyzer.run_analysis() | 执行聚类分析与情感判定 |

### 可视化

| 文件 | 类 / 方法 | 功能 |
|------|----------|------|
| src/api/dashboard.py | load_data_from_db() | 从数据库读取数据用于可视化 |
| src/api/dashboard.py | Streamlit 组件 | 数据可视化展示（含筛选功能） |

---

## 常见问题

### 目录嵌套问题

现象：下载后文件在双层嵌套目录中

解决：将内层目录内容移动到外层，确保 requirements.txt 和 main.py 在项目根目录

### 数据库连接失败

现象：pymysql.err.OperationalError: (1045, "Access denied for user 'root'@'localhost'")

原因：.env 文件中密码为空或不正确、MySQL 服务未启动、数据库未创建

解决：确保 .env 文件配置正确，启动 MySQL 服务，创建 douban_analysis 数据库

### Streamlit 启动失败

现象：Fatal error in launcher: Unable to create process

解决：确保 Python 和 Streamlit 在系统 PATH 中，尝试使用 python -m streamlit run src/api/dashboard.py

---

## 注意事项

- 请遵守豆瓣网站的 robots.txt 规则
- 合理设置爬虫抓取频率，避免对服务器造成压力
- 数据库连接信息请妥善保管，不要提交到版本控制系统
- 定期清理日志文件，避免占用过多磁盘空间

---

## 许可证

MIT License
