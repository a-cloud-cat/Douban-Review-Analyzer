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


logger = get_logger("main")

def start_spider_pipeline():
    logger.info("开始抓取豆瓣图书评论")
    
    # 获取数据库中的URL列表
    urls = data_service.get_active_urls()
    
    if not urls:
        print("数据库中没有可用的URL，请先在Navicat中添加URL到 crawl_urls 表")
        return
    
    print("\n可用的图书URL列表：")
    for i, url_info in enumerate(urls, 1):
        print(f"{i}. {url_info['book_name']}")
    
    while True:
        url_index = input("请选择要爬取的图书序号: ").strip()
        try:
            index = int(url_index) - 1
            if 0 <= index < len(urls):
                selected_url = urls[index]
                book_name = selected_url['book_name']
                url = selected_url['url']
                # 将URL转换为curl格式
                curl_string = f"curl \"{url}\""
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
        # 使用图书名称作为文件名（移除特殊字符）
        safe_book_name = ''.join(c for c in book_name if c.isalnum() or c in (' ', '_')).rstrip()
        with open(raw_dir / f"raw_{safe_book_name}.json", "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=4)
        data_service.save_reviews(book_name, items)
        cleaner.process_uncleaned_reviews(batch_size=500)
        logger.info(f"数据抓取与分词清洗完成，共获取 {len(items)} 条评论")

def start_clustering_pipeline():
    logger.info("开始执行聚类分析")
    analyzer = KMeansAnalyzer(n_clusters=3)
    analyzer.run_analysis()

def start_web_dashboard():
    logger.info("启动可视化看板，正在打开浏览器...")
    dashboard_path = PROJECT_ROOT / "src" / "api" / "dashboard.py"

    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", dashboard_path])
    except KeyboardInterrupt:
        logger.info("看板服务已停止。")

def clear_data():
    from src.db.base import engine
    from src.db.models import Base
    logger.warning("正在重置数据库...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    logger.info("数据库已重置。")

def run_tests():
    """运行测试"""
    logger.info("开始运行测试...")
    try:
        logger.info(f"Python 路径: {sys.executable}")
        
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v"],
            capture_output=True,
            text=True,
            cwd=get_project_root()
        )
        
        # 输出测试结果
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)

        if "No module named pytest" in result.stderr:
            logger.error("未安装 pytest，请先运行: pip install -r requirements.txt")
        elif result.returncode == 0:
            logger.info("测试通过！")
        else:
            logger.error(f"测试失败，退出码: {result.returncode}")
    except Exception as e:
        logger.error(f"运行测试时发生错误: {e}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")

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
    while True:
        print(f"\n{'#'*30}")
        print("   豆瓣图书数据分析工具")
        print(f"{'#'*30}")
        print("1.启动爬虫任务 (抓取 + 清洗)")
        print("2.执行聚类分析 (K-Means + 导出)")
        print("3.启动可视化看板 (浏览器打开)")
        print("4.重置数据库 (清空所有记录)")
        print("5.日志管理功能")
        print("6.运行测试")
        print("7.退出程序")
        print("-" * 30)
        choice = input("请输入选项序号: ").strip()

        if choice == '1': 
            start_spider_pipeline()
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
            run_tests()
        elif choice == '7': 
            logger.info("程序已退出。")
            break
        else:
            print("无效选项，请重新输入")

if __name__ == "__main__":
    logger.info("Douban-Insight 系统启动")
    main_menu()