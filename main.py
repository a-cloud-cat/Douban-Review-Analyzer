import sys
import json
import subprocess


from src.utils.path_utils import get_project_root, get_data_dir, get_config_dir, ensure_dir
from src.utils.logger import get_logger
from src.utils.log_manager import log_manager

PROJECT_ROOT = get_project_root()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.crawler.douban_spider import DoubanSpider
from src.services.data_service import data_service
from engines.preprocess.cleaner import cleaner
from engines.clustering.k_means_model import KMeansAnalyzer
from src.utils.path_utils import get_config_dir

# 获取日志器
logger = get_logger("main")

def load_config(file_name):
    config_path = get_config_dir() / file_name
    if not config_path.exists():
        logger.error(f"找不到配置文件 {config_path}")
        return None
    with open(config_path, 'r', encoding='utf-8') as f:
        return f.read().strip()

def start_spider_pipeline(douban_id):
    # 从配置文件中加载豆瓣电影ID
    # https://movie.douban.com/subject/36968879/ 即最后一串数字拿来标注用的
    logger.info(f"开始抓取任务 ID: {douban_id}")
    curl_string = load_config("spider_config.txt")
    if not curl_string: return
    spider = DoubanSpider()
    items = spider.fetch_data(curl_string)
    if items:
        raw_dir = ensure_dir(get_data_dir("raw"))
        with open(raw_dir / f"raw_{douban_id}.json", "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=4) # dump倾倒
        data_service.save_reviews(douban_id, items)
        cleaner.process_uncleaned_reviews(batch_size=500)
        logger.info("数据抓取与分词清洗完成！")

def start_clustering_pipeline():
    logger.info("开始执行聚类分析")
    analyzer = KMeansAnalyzer(n_clusters=3)
    analyzer.run_analysis()

def start_web_dashboard():
    logger.info("启动可视化看板，正在打开浏览器...")
    dashboard_path = PROJECT_ROOT / "src" / "api" / "dashboard.py"

    try:
        subprocess.run(["streamlit", "run", dashboard_path])
    except KeyboardInterrupt:
        logger.info("看板服务已停止。")

def clear_data():
    from src.db.base import engine
    from src.db.models import Base
    logger.warning("正在重置数据库...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    logger.info("数据库已重置。")

# 独立封装日志管理菜单函数
def log_manager_menu():
    logger.info("检查日志文件...")
    stats = log_manager.get_log_statistics()
    logger.info(f"当前日志文件数量: {stats.get('total_files', 0)}")
    logger.info(f"日志文件总大小: {stats.get('total_size_human', '0 B')}")
    
    while True:
        print(f"\n{'#'*30}")
        print("   日志管理")
        print(f"{'#'*30}")
        print("1. 清理所有旧日志")
        print("2. 按天数清理日志")
        print("3. 压缩日志文件")
        print("4. 返回主菜单")
        print("-" * 30)
        log_choice = input("请输入选项序号: ").strip()
        
        if log_choice == '1':
            deleted = log_manager.clean_logs()
            logger.info(f"日志清理完成，删除了 {deleted} 个文件")
        elif log_choice == '2':
            try:
                days = int(input("请输入要保留的天数: ").strip())
                deleted = log_manager.clean_logs(keep_days=days)
                logger.info(f"日志清理完成，删除了 {deleted} 个文件")
            except ValueError:
                logger.error("请输入有效的数字")
        elif log_choice == '3':
            compressed = log_manager.compress_logs()
            logger.info(f"日志压缩完成，压缩了 {compressed} 个文件")
        elif log_choice == '4':
            logger.info("返回主菜单")
            break
        else:
            print("无效选项，请重新输入")

def main_menu():
    default_id = "36968879"
    user_input = input(f"请输入要爬的豆瓣电影ID（默认：{default_id}）：").strip()
    TARGET_ID = user_input if user_input else default_id
    while True:
        print(f"\n{'#'*30}")
        print(f"   豆瓣数据分析工具 (ID: {TARGET_ID})")
        print(f"{'#'*30}")
        print("1.启动爬虫任务 (抓取 + 清洗)")
        print("2.执行聚类分析 (K-Means + 导出)")
        print("3.启动可视化看板 (浏览器打开)")
        print("4.重置数据库 (清空所有记录)")
        print("5.日志管理功能")
        print("6.退出程序")
        print("-" * 30)
        choice = input("请输入选项序号: ").strip()

        if choice == '1': 
            start_spider_pipeline(TARGET_ID)
        elif choice == '2': 
            start_clustering_pipeline()
        elif choice == '3': 
            start_web_dashboard()
        elif choice == '4':
            if input("确定清空吗？(y/n): ").lower() == 'y': 
                clear_data()
        elif choice == '5': 
            log_manager_menu()
        elif choice == '6': 
            logger.info("程序已退出。")
            break
        else:
            print("无效选项，请重新输入")

if __name__ == "__main__":
    logger.info("Douban-Insight 系统启动")
    main_menu()