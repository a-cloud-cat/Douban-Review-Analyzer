import time
import pytest
from src.crawler.douban_spider import DoubanSpider
from engines.preprocess.cleaner import DataCleaner
from src.utils.path_utils import get_config_dir


def load_config(file_name):
    """加载配置文件，与 main.py 中的实现一致"""
    config_path = get_config_dir() / file_name
    if not config_path.exists():
        return None
    with open(config_path, 'r', encoding='utf-8') as f:
        return f.read().strip()


def test_spider_performance():
    """测试爬虫性能"""
    curl_str = load_config("spider_config.txt")
    if not curl_str:
        pytest.skip("配置文件不存在，跳过此测试")
    
    spider = DoubanSpider()
    
    start_time = time.time()
    result = spider.fetch_data(curl_str)
    end_time = time.time()
    
    if not result:
        pytest.skip("未能获取到评论数据，跳过此测试")
    
    print(f"爬取 {len(result)} 条评论耗时: {end_time - start_time:.2f} 秒")


def test_cleaner_performance():
    """测试文本处理性能（使用真实数据）"""
    curl_str = load_config("spider_config.txt")
    if not curl_str:
        pytest.skip("配置文件不存在，跳过此测试")
    
    cleaner = DataCleaner()
    spider = DoubanSpider()
    comments = spider.fetch_data(curl_str)
    
    if not comments:
        pytest.skip("未能获取到评论数据，跳过此测试")
    
    test_texts = [comment["content"] for comment in comments[:100]]
    
    start_time = time.time()
    for text in test_texts:
        cleaner.segment(text)
    end_time = time.time()
    
    print(f"处理 {len(test_texts)} 条文本耗时: {end_time - start_time:.2f} 秒")


def test_batch_performance():
    """测试批量处理性能（使用真实数据）"""
    curl_str = load_config("spider_config.txt")
    if not curl_str:
        pytest.skip("配置文件不存在，跳过此测试")
    
    cleaner = DataCleaner()
    spider = DoubanSpider()
    comments = spider.fetch_data(curl_str)
    
    if not comments:
        pytest.skip("未能获取到评论数据，跳过此测试")
    
    test_texts = []
    for comment in comments:
        test_texts.extend([comment["content"]] * 20)
    
    if len(test_texts) < 100:
        pytest.skip("数据不足，跳过此测试")
    else:
        test_texts = test_texts[:1000]
    
    start_time = time.time()
    results = [cleaner.segment(text) for text in test_texts]
    end_time = time.time()
    
    print(f"批量处理 {len(test_texts)} 条文本耗时: {end_time - start_time:.2f} 秒")
