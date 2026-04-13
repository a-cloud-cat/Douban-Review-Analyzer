import sys
import os
import json
import subprocess

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.crawler.douban_spider import DoubanSpider
from src.services.data_service import data_service
from engines.preprocess.cleaner import cleaner
from engines.clustering.k_means_model import KMeansAnalyzer

def load_config(file_path):
    if not os.path.exists(file_path):
        print(f"错误：找不到配置文件 {file_path}")
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read().strip()

def start_spider_pipeline(douban_id): # https://movie.douban.com/subject/36968879/ 即最后一串数字拿来标注用的
    print(f"\n[开始抓取任务] ID: {douban_id}")
    curl_string = load_config("config/spider_config.txt")
    if not curl_string: return
    spider = DoubanSpider()
    items = spider.fetch_data(curl_string)
    if items:
        os.makedirs("data/raw", exist_ok=True)
        with open(f"data/raw/raw_{douban_id}.json", "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=4) # dump倾倒
        data_service.save_reviews(douban_id, items)
        cleaner.process_uncleaned_reviews(batch_size=500)
        print("数据抓取与分词清洗完成！")

def start_clustering_pipeline():
    analyzer = KMeansAnalyzer(n_clusters=3)
    analyzer.run_analysis()

def start_web_dashboard():
    print("\n[启动可视化看板] 正在打开浏览器...")
    dashboard_path = os.path.join("src", "api", "dashboard.py")

    try:
        subprocess.run(["streamlit", "run", dashboard_path])
    except KeyboardInterrupt:
        print("\n看板服务已停止。")

def clear_data():
    from src.db.base import engine
    from src.db.models import Base
    print("\n[警告] 正在重置数据库...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("数据库已重置。")

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
        print("5.退出程序")
        print("-" * 30)
        choice = input("请输入选项序号: ").strip()

        if choice == '1': start_spider_pipeline(TARGET_ID)
        elif choice == '2': start_clustering_pipeline()
        elif choice == '3': start_web_dashboard()
        elif choice == '4':
            if input("确定清空吗？(y/n): ").lower() == 'y': clear_data()
        elif choice == '5': break

if __name__ == "__main__":
    main_menu()