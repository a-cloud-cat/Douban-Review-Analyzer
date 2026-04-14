import re        # 正则表达式
import requests  # 网络请求
from src.utils.logger import get_logger

# 获取日志器
logger = get_logger("base_spider")

class BaseSpider:
    def __init__(self):
        #伪装HTTP 头部 (Headers)：这是应用层协议。用浏览器访问豆瓣时，浏览器会发送一段文字给服务器，说：“我是 Chrome，我想看这个网页”。
        self.default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    #获取 网址 URL、请求头 headers、登录凭证 cookies
    @staticmethod
    def _parse_curl(curl_str: str):
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
        try:
            url, headers, cookies = self._parse_curl(raw_curl)
            logger.info(f"正在请求 URL: {url}")
            
            headers.update(self.default_headers) # update:将后来的字典合并进前面的字典，相同覆盖不同追加
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