import re        # 正则表达式
import requests  # 网络请求
import concurrent.futures
import time
from typing import List, Dict, Any, Optional
from src.utils.logger import get_logger

# 获取日志器
logger = get_logger("base_spider")

class BaseSpider:
    """
    基础爬虫工具类，提供 curl 解析、HTTP 请求、网页/接口数据获取功能
    """

    def __init__(self):
        """
        初始化基础爬虫，设置默认请求头伪装浏览器
        """
        #伪装HTTP 头部 (Headers)：这是应用层协议。用浏览器访问豆瓣时，浏览器会发送一段文字给服务器，说：“我是 Chrome，我想看这个网页”。
        self.default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.max_workers = 5  # 最大并发数

    def _parse_curl(self, curl_str: str):
        """
        从浏览器复制的 curl 命令中解析出 URL、请求头、Cookies

        Args:
            curl_str: 浏览器复制的原始 curl 字符串

        Returns:
            tuple: (url, headers, cookies)

        Raises:
            Exception: 解析失败时抛出异常
        """
        #re.search(正则规则, 要搜索的文本)
        url_match = re.search(r"['\"](?P<url>https?://[^'\"]+)['\"]", curl_str)
        target_url = url_match.group("url") if url_match else re.search(r"https?://[^\s'\"]+", curl_str).group(0)

        headers = {}
        #re.search 只找第一个匹配结果就停，re.findall 会把字符串里所有符合规则的内容全部找出来，返回一个列表。
        header_matches = re.findall(r"-H\s+['\"]([^'\"]+): ([^'\"]+)['\"]", curl_str)
        for k, v in header_matches:
            headers[k] = v

        cookies = {}
        cookie_match = re.search(r"-b\s+['\"]([^'\"]+)['\"]", curl_str)

        if cookie_match:
            # group是正则匹配结果专用，比如group(1)表示匹配的第一个()。
            cookie_content = cookie_match.group(1)
            # Cookie 是用分号分隔的一串，所以用 split(';') 切开变成列表
            for item in cookie_content.split(';'):
                if '=' in item:
                    k, v = item.strip().split('=', 1)
                    cookies[k] = v

        return target_url, headers, cookies

    def get_html_by_curl(self, raw_curl: str):
        """
        通过 curl 命令自动发送 GET 请求，获取网页 HTML 或 JSON 中的 html 字段

        Args:
            raw_curl: 浏览器复制的完整 curl 字符串

        Returns:
            str: 网页 HTML 内容，请求失败返回 None

        Raises:
            requests.RequestException: 网络请求异常
            Exception: 其他解析异常
        """
        try:
            url, headers, cookies = self._parse_curl(raw_curl)
            logger.info(f"正在请求 URL: {url}")
            
            # update:将后来的字典合并进前面的字典，相同覆盖不同追加
            headers.update(self.default_headers)
            response = requests.get(url, headers=headers, cookies=cookies, timeout=15)
            response.raise_for_status()  # 检查HTTP状态码
            
            logger.info(f"请求成功，状态码: {response.status_code}")
            
            if "application/json" in response.headers.get("Content-Type", ""):
                return response.json().get("html", "")

            # 如果是标准的网页返回，直接把 response 里的 text（也就是网页 HTML 源代码）返回
            return response.text
        except requests.RequestException as e:
            logger.error(f"网络请求失败: {e}")
            return None
        except Exception as e:
            logger.error(f"解析响应失败: {e}")
            return None
    
    def get_htmls_by_curls(self, raw_curls: List[str]) -> List[Optional[str]]:
        """
        并发处理多个 curl 命令，获取多个网页的 HTML 内容

        Args:
            raw_curls: 浏览器复制的完整 curl 字符串列表

        Returns:
            List[Optional[str]]: 网页 HTML 内容列表，请求失败返回 None
        """
        results = []
        
        def fetch_curl(raw_curl):
            """单个 curl 请求的处理函数"""
            return self.get_html_by_curl(raw_curl)
        
        logger.info(f"开始并发请求 {len(raw_curls)} 个页面")
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_curl = {executor.submit(fetch_curl, curl): curl for curl in raw_curls}
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_curl):
                curl = future_to_curl[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"处理 curl 请求时发生异常: {e}")
                    results.append(None)
        
        end_time = time.time()
        logger.info(f"并发请求完成，耗时: {end_time - start_time:.2f} 秒")
        return results