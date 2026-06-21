import sys
import json
import subprocess
import pandas as pd

from src.utils.path_utils import get_project_root, get_data_dir, get_config_dir, ensure_dir
from src.utils.logger import get_logger
from src.utils.log_manager import log_manager
from src.utils.db_utils import DatabaseSessionManager
from src.utils.db_performance import DatabasePerformanceOptimizer

PROJECT_ROOT = get_project_root()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


logger = get_logger("main")

def start_spider_pipeline():
    from src.crawler.douban_spider import DoubanSpider
    from src.services.data_service import data_service
    from engines.preprocess.cleaner import cleaner
    
    logger.info("开始抓取豆瓣图书评论")
    
    urls = data_service.get_active_urls()
    
    if not urls:
        print("数据库中没有可用的URL，请先在Navicat中添加URL到 crawl_urls 表")
        return
    
    print("\n可用的图书URL列表：")
    for i, url_info in enumerate(urls, 1):
        print("{}. {}".format(i, url_info['book_name']))
    
    while True:
        url_index = input("请选择要爬取的图书序号: ").strip()
        try:
            index = int(url_index) - 1
            if 0 <= index < len(urls):
                selected_url = urls[index]
                book_name = selected_url['book_name']
                url = selected_url['url']
                curl_string = "curl \"{}\"".format(url)
                break
            else:
                print("无效的序号，请重新输入")
        except ValueError:
            print("请输入有效的数字")
    
    while True:
        page_input = input("请输入要抓取的页数（默认 1，每页20条评论）：").strip()
        if not page_input:
            max_pages = 1
            break
        try:
            max_pages = int(page_input)
            if max_pages < 1:
                print("页数必须大于等于1，请重新输入")
                continue
            break
        except ValueError:
            print("请输入有效的数字")
    
    spider = DoubanSpider()
    items = spider.fetch_data(curl_string, max_pages=max_pages)
    if items:
        raw_dir = ensure_dir(get_data_dir("raw"))
        safe_book_name = ''.join(c for c in book_name if c.isalnum() or c in (' ', '_')).rstrip()
        with open(raw_dir / "raw_{}.json".format(safe_book_name), "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=4)
        data_service.save_reviews(book_name, items)
        cleaner.process_uncleaned_reviews(batch_size=500)
        logger.info("数据抓取与分词清洗完成，共获取 {} 条评论".format(len(items)))

def start_clustering_pipeline():
    from engines.clustering.k_means_model import KMeansAnalyzer
    
    logger.info("开始执行聚类分析")
    analyzer = KMeansAnalyzer(n_clusters=3)
    analyzer.run_analysis()

def start_classification_pipeline():
    from engines.classification.classifier import SentimentClassifier
    
    logger.info("开始执行分类分析")
    
    while True:
        print("\n{}".format('#'*30))
        print("   分类算法选择")
        print("{}".format('#'*30))
        print("1. SVM (支持向量机)")
        print("2. 逻辑回归")
        print("3. 决策树")
        print("4. 返回主菜单")
        print("-" * 30)
        model_choice = input("请选择分类算法: ").strip()
        
        if model_choice == '1':
            model_type = 'svm'
            break
        elif model_choice == '2':
            model_type = 'logistic'
            break
        elif model_choice == '3':
            model_type = 'tree'
            break
        elif model_choice == '4':
            return
        else:
            print("无效选项，请重新输入")
    
    use_smote = input("是否使用 SMOTE 非平衡处理？(y/n): ").lower() == 'y'
    use_scaler = input("是否使用数据归一化？(y/n): ").lower() == 'y'
    
    classifier = SentimentClassifier(model_type=model_type, use_smote=use_smote, use_scaler=use_scaler)
    classifier.run_analysis()

def start_bert_direct_analysis():
    """直接使用预训练 BERT 模型进行情感分析（不训练自己的分类器）"""
    logger.info("开始使用预训练 BERT 模型进行情感分析")
    
    try:
        from engines.clustering.sentiment_analyzer_v2 import get_bert_analyzer
        
        print("\n{}".format('#'*30))
        print("   预训练 BERT 情感分析")
        print("{}".format('#'*30))
        
        # 加载 BERT 模型
        print("正在加载预训练 BERT 模型...")
        analyzer = get_bert_analyzer(use_gpu=True)
        print("✅ BERT 模型加载成功！")
        
        # 获取数据库中的评论
        with DatabaseSessionManager.get_session() as db:
            reviews = DatabasePerformanceOptimizer.get_cleaned_reviews_batch(
                db=db,
                batch_size=1000
            )
            
            if not reviews:
                print("❌ 数据库中没有清洗后的评论数据")
                print("请先运行 爬虫任务 抓取并清洗数据")
                return
            
            print("\n正在分析 {} 条评论...".format(len(reviews)))
            
            # 执行情感分析
            results = []
            for idx, review in enumerate(reviews, 1):
                text = str(review.cleaned_content).strip()
                sentiment, confidence = analyzer.analyze(text)
                
                results.append({
                    'id': review.id,
                    'user_name': review.user_name,
                    'star': review.star,
                    'cleaned_content': text[:50] + "..." if len(text) > 50 else text,
                    'sentiment': sentiment,
                    'confidence': confidence
                })
                
                if idx % 50 == 0:
                    print("已分析: {}/{}".format(idx, len(reviews)))
            
            # 保存结果到数据库
            print("\n正在将分析结果保存到数据库...")
            updates = []
            for r in results:
                updates.append({
                    "id": r['id'],
                    "sentiment": r['sentiment']
                })
            
            if updates:
                DatabasePerformanceOptimizer.batch_update_reviews(
                    db=db,
                    updates=updates,
                    batch_size=50
                )
            
            # 导出到 CSV
            df = pd.DataFrame(results)
            processed_dir = ensure_dir(get_data_dir("processed"))
            export_path = processed_dir / "bert_sentiment_results.csv"
            df.to_csv(export_path, index=False, encoding='utf-8-sig')
            
            # 统计结果
            sentiment_counts = df['sentiment'].value_counts().to_dict()
            total = len(df)
            
            print("\n{}".format('='*40))
            print("分析结果统计")
            print("{}".format('='*40))
            print("总评论数: {}".format(total))
            for sentiment, count in sentiment_counts.items():
                percentage = (count / total) * 100
                print("{}: {} 条 ({:.1f}%)".format(sentiment, count, percentage))
            print("\n结果已保存到: {}".format(export_path))
            
            # 显示一些示例
            print("\n{}".format('='*40))
            print("分析示例")
            print("{}".format('='*40))
            sample_results = df.sample(min(5, len(df))).to_dict('records')
            for sample in sample_results:
                print("\n评论: {}".format(sample['cleaned_content']))
                print("评分: {}星".format(sample['star']))
                print("情感: {} (置信度: {:.2f})".format(sample['sentiment'], sample['confidence']))
        
    except Exception as e:
        logger.error("BERT 分析失败: {}".format(e))
        import traceback
        logger.error("详细错误: {}".format(traceback.format_exc()))
        print("\n❌ 分析失败: {}".format(e))

def start_web_dashboard():
    logger.info("启动可视化看板，正在打开浏览器...")
    dashboard_path = PROJECT_ROOT / "src" / "api" / "dashboard.py"

    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", dashboard_path])
    except KeyboardInterrupt:
        logger.info("看板服务已停止。")

def clear_data():
    from src.db.base import engine
    from src.db.models import Base, Review, BookReviewStats
    logger.warning("正在重置数据库（保留URL配置）...")
    
    # 只删除评论相关的表，保留URL配置表
    Review.__table__.drop(bind=engine, checkfirst=True)
    BookReviewStats.__table__.drop(bind=engine, checkfirst=True)
    
    # 重新创建表
    Review.__table__.create(bind=engine, checkfirst=True)
    BookReviewStats.__table__.create(bind=engine, checkfirst=True)
    
    logger.info("数据库已重置（URL配置表已保留）。")

def run_tests():
    logger.info("开始运行测试...")
    try:
        logger.info("Python 路径: {}".format(sys.executable))
        
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v"],
            capture_output=True,
            text=True,
            cwd=get_project_root()
        )
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)

        if "No module named pytest" in result.stderr:
            logger.error("未安装 pytest，请先运行: pip install -r requirements.txt")
        elif result.returncode == 0:
            logger.info("测试通过！")
        else:
            logger.error("测试失败，退出码: {}".format(result.returncode))
    except Exception as e:
        logger.error("运行测试时发生错误: {}".format(e))
        import traceback
        logger.error("详细错误信息: {}".format(traceback.format_exc()))

def log_manager_menu():
    logger.info("检查日志文件...")
    stats = log_manager.get_log_statistics()
    logger.info("当前日志文件数量: {}".format(stats.get('total_files', 0)))
    logger.info("日志文件总大小: {}".format(stats.get('total_size_human', '0 B')))
    
    while True:
        print("\n{}".format('#'*30))
        print("   日志管理")
        print("{}".format('#'*30))
        print("1. 清理所有旧日志")
        print("2. 按天数清理日志")
        print("3. 压缩日志文件")
        print("4. 返回主菜单")
        print("-" * 30)
        log_choice = input("请输入选项序号: ").strip()
        
        if log_choice == '1':
            deleted = log_manager.clean_logs()
            logger.info("日志清理完成，删除了 {} 个文件".format(deleted))
        elif log_choice == '2':
            try:
                days = int(input("请输入要保留的天数: ").strip())
                deleted = log_manager.clean_logs(keep_days=days)
                logger.info("日志清理完成，删除了 {} 个文件".format(deleted))
            except ValueError:
                logger.error("请输入有效的数字")
        elif log_choice == '3':
            compressed = log_manager.compress_logs()
            logger.info("日志压缩完成，压缩了 {} 个文件".format(compressed))
        elif log_choice == '4':
            logger.info("返回主菜单")
            break
        else:
            print("无效选项，请重新输入")

def main_menu():
    while True:
        print("\n{}".format('#'*30))
        print("   豆瓣图书数据分析工具")
        print("{}".format('#'*30))
        print("1.启动爬虫任务 (抓取 + 清洗)")
        print("2.执行聚类分析 (K-Means + 情感标注)")
        print("3.执行分类分析 (SVM/逻辑回归/决策树)")
        print("4.使用BERT分析")
        print("5.启动可视化看板 (浏览器打开)")
        print("6.重置数据库 (清空所有记录)")
        print("7.日志管理功能")
        print("8.运行测试")
        print("9.退出程序")
        print("-" * 30)
        choice = input("请输入选项序号: ").strip()

        if choice == '1': 
            start_spider_pipeline()
        elif choice == '2': 
            start_clustering_pipeline()
        elif choice == '3': 
            start_classification_pipeline()
        elif choice == '4': 
            start_bert_direct_analysis()
        elif choice == '5': 
            start_web_dashboard()
        elif choice == '6':
            if input("确定清空吗？(y/n): ").lower() == 'y': 
                clear_data()
        elif choice == '7': 
            log_manager_menu()
        elif choice == '8': 
            run_tests()
        elif choice == '9': 
            logger.info("程序已退出。")
            break
        else:
            print("无效选项，请重新输入")

if __name__ == "__main__":
    logger.info("Douban-Insight 系统启动")
    main_menu()
