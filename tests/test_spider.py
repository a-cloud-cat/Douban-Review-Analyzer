import pytest
from src.crawler.base_spider import BaseSpider
from src.crawler.douban_spider import DoubanSpider
from src.utils.path_utils import get_config_dir


def load_config(file_name):
    """加载配置文件，与 main.py 中的实现一致"""
    config_path = get_config_dir() / file_name
    if not config_path.exists():
        return None
    with open(config_path, 'r', encoding='utf-8') as f:
        return f.read().strip()


def test_curl_parsing():
    """测试 curl 命令解析"""
    spider = BaseSpider()
    curl_str = load_config("spider_config.txt")
    if not curl_str:
        pytest.skip("配置文件不存在，跳过此测试")
    
    url, headers, cookies = spider._parse_curl(curl_str)
    assert url is not None
    has_user_agent = any(key.lower() == 'user-agent' for key in headers)
    assert has_user_agent, "Headers 中未包含 User-Agent"


def test_html_parsing():
    """测试 HTML 解析（使用与 main.py 相同的配置）"""
    spider = DoubanSpider()

    curl_str = load_config("spider_config.txt")
    
    if not curl_str:
        pytest.skip("配置文件不存在，跳过此测试")
    
    html = spider.get_html_by_curl(curl_str)
    if not html:
        pytest.skip("未能获取到页面内容，跳过此测试")
    
    result = spider._parse_html_logic(html)
    if len(result) == 0:
        pytest.skip("未能解析到评论，跳过此测试")
    
    for item in result:
        assert "user_name" in item
        assert "content" in item
        assert "star" in item
        assert len(item["content"]) > 0


def test_json_parsing():
    """测试 JSON 解析（使用与 main.py 相同的配置）"""
    spider = DoubanSpider()
    curl_str = load_config("spider_config.txt")
    
    if not curl_str:
        pytest.skip("配置文件不存在，跳过此测试")
    
    result = spider.fetch_data(curl_str)
    if len(result) == 0:
        pytest.skip("未能获取到评论数据，跳过此测试")
    
    for item in result:
        assert "user_name" in item
        assert "content" in item
        assert "star" in item
        assert len(item["content"]) > 0
