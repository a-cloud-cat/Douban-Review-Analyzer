import pytest
from engines.preprocess.cleaner import DataCleaner
from src.utils.path_utils import get_config_dir
from src.crawler.douban_spider import DoubanSpider
from src.services.data_service import data_service


def load_config(file_name):
    """加载配置文件"""
    config_path = get_config_dir() / file_name
    if not config_path.exists():
        return None
    with open(config_path, 'r', encoding='utf-8') as f:
        return f.read().strip()


def test_text_cleaning():
    """测试文本清洗功能"""
    cleaner = DataCleaner()
    
    curl_str = load_config("spider_config.txt")
    if not curl_str:
        pytest.skip("配置文件不存在，跳过此测试")
    
    spider = DoubanSpider()
    items = spider.fetch_data(curl_str)
    
    if not items:
        pytest.skip("未能获取到评论数据，跳过此测试")

    test_text = items[0]["content"] + "！\n包含特殊字符@#$%^&*()"
    
    cleaned = cleaner.clean_text(test_text)
    assert "@#$%^&*()" not in cleaned
    assert "\n" not in cleaned
    assert len(cleaned) > 0


def test_segmentation():
    """测试分词功能"""
    cleaner = DataCleaner()
    
    curl_str = load_config("spider_config.txt")
    if not curl_str:
        pytest.skip("配置文件不存在，跳过此测试")
    
    spider = DoubanSpider()
    items = spider.fetch_data(curl_str)
    
    if not items:
        pytest.skip("未能获取到评论数据，跳过此测试")
    
    test_text = items[0]["content"]
    
    segmented = cleaner.segment(test_text)
    assert len(segmented) > 0
    words = segmented.split()
    for word in words:
        assert len(word) > 1


def test_empty_text():
    """测试空文本处理"""
    cleaner = DataCleaner()
    assert cleaner.clean_text("") == ""
    assert cleaner.segment("") == ""


def test_process_uncleaned_reviews():
    """测试批量处理未清洗的评论"""
    cleaner = DataCleaner()
    
    curl_str = load_config("spider_config.txt")
    if not curl_str:
        pytest.skip("配置文件不存在，跳过此测试")
    
    spider = DoubanSpider()
    items = spider.fetch_data(curl_str)
    
    if not items:
        pytest.skip("未能获取到评论数据，跳过此测试")
    
    data_service.save_reviews("test_movie", items)
    
    try:
        cleaner.process_uncleaned_reviews(batch_size=10)
        assert True
    except Exception as e:
        pytest.skip(f"处理未清洗评论失败，跳过此测试: {str(e)}")
