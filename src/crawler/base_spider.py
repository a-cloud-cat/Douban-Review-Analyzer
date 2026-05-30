import re
import random
import requests  # 网络请求
import concurrent.futures
import time
from typing import List,Optional
from src.utils.path_utils import get_config_dir
from src.utils.logger import get_logger


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
        self.default_headers = {}
        self.max_workers = 2
        self.agent_list = self._load_user_agents()  # 从配置文件加载 User-Agent 列表
        
        # 丰富了请求头字段池
        self.accept_list = [
            "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "application/json, text/javascript, */*; q=0.01",
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
        ]
        
        self.referer_list = [
            "https://movie.douban.com/",
            "https://www.douban.com/",
            "https://www.google.com/",
            "https://www.baidu.com/",
            "https://www.bing.com/",
            "https://movie.douban.com/subject/35197858/comments"
        ]
        
        self.accept_language_list = [
            "zh-CN,zh;q=0.9,en;q=0.8",
            "zh-CN,zh;q=0.9",
            "zh;q=1.0,en;q=0.5"
        ]
        
        self.accept_encoding_list = [
            "gzip, deflate, br",
            "gzip, deflate",
            "br, gzip, deflate"
        ]
        
        self.ch_ua_list = [
            "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Google Chrome\";v=\"120\"",
            "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"119\", \"Google Chrome\";v=\"119\"",
            "\"Microsoft Edge\";v=\"120\", \"Chromium\";v=\"120\""
        ]
        
        self.ch_ua_platform_list = [
            "\"Windows\"",
            "\"macOS\"",
            "\"Linux\""
        ]

    def _load_user_agents(self) -> List[str]:
        """
        从配置文件加载 User-Agent 列表
        
        Returns:
            List[str]: User-Agent 列表，如果加载失败则返回默认列表
        """
        config_path = get_config_dir() / "user_agents.txt"
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                agents = [line.strip() for line in f if line.strip()]
            if agents:
                logger.info(f"成功从配置文件加载 {len(agents)} 个 User-Agent")
                return agents
            else:
                logger.warning("配置文件中没有有效的 User-Agent，使用默认列表")
        except FileNotFoundError:
            logger.warning(f"User-Agent 配置文件未找到: {config_path}，使用默认列表")
        except Exception as e:
            logger.error(f"加载 User-Agent 配置文件失败: {e}，使用默认列表")
        
        # 返回默认 User-Agent 列表
        return [
            "Mozilla/5.0 (Linux; U; Android 2.3.6; en-us; Nexus S Build/GRK39F) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
            "Avant Browser/1.2.789rel1 (http://www.avantbrowser.com)",
            "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/532.5 (KHTML, like Gecko) Chrome/4.0.249.0 Safari/532.5",
            "Mozilla/5.0 (Windows; U; Windows NT 5.2; en-US) AppleWebKit/532.9 (KHTML, like Gecko) Chrome/5.0.310.0 Safari/532.9",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]

    def _get_random_agent(self):
        """
        随机获取一个 User-Agent
        """
        return random.choice(self.agent_list)
    
    def _get_random_headers(self):
        """
        生成随机请求头，模拟真实浏览器
        """
        return {
            "User-Agent": self._get_random_agent(),
            "Referer": random.choice(self.referer_list),
            "Accept": random.choice(self.accept_list),
            "Accept-Language": random.choice(self.accept_language_list),
            "Accept-Encoding": random.choice(self.accept_encoding_list),
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
            "Sec-Ch-Ua": random.choice(self.ch_ua_list),
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": random.choice(self.ch_ua_platform_list),
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }

    @staticmethod
    def _parse_curl(curl_str: str):
        """
        从浏览器复制的 curl 命令中解析出 URL、请求头、Cookies

        Args:
            curl_str: 浏览器复制的原始 curl 字符串

        Returns:
            tuple: (url, headers, cookies)

        Raises:
            Exception: 解析失败时抛出异常
        """
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

    def _send_request(self, url: str, headers: dict, cookies: dict, max_retries: int = 3):
        """
        内部方法：发送单个 HTTP 请求，支持自动重试
        
        Args:
            url: 请求的 URL
            headers: 请求头
            cookies: Cookies
            max_retries: 最大重试次数，默认为 3
            
        Returns:
            str: 响应内容，如果请求失败返回 None
        """
        # 指数退避延迟配置（秒）
        retry_delays = [1, 2, 4, 8, 16]
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, cookies=cookies, timeout=15)
                
                # 检测反爬状态码
                if response.status_code == 429:
                    # 请求过快，等待后重试
                    wait_time = int(response.headers.get("Retry-After", retry_delays[attempt]))
                    logger.warning(f"请求过快 (429)，等待 {wait_time} 秒后重试 (第 {attempt+1}/{max_retries} 次)")
                    time.sleep(wait_time)
                    # 更换请求头重试
                    headers.update(self._get_random_headers())
                    continue
                    
                elif response.status_code == 403:
                    # 被封禁，等待更长时间并重试
                    wait_time = retry_delays[attempt] * 5
                    logger.warning(f"访问被拒绝 (403)，等待 {wait_time} 秒后重试 (第 {attempt+1}/{max_retries} 次)")
                    time.sleep(wait_time)
                    # 更换请求头重试
                    headers.update(self._get_random_headers())
                    continue
                    
                elif response.status_code == 503:
                    # 服务不可用，等待后重试
                    wait_time = retry_delays[attempt] * 2
                    logger.warning(f"服务不可用 (503)，等待 {wait_time} 秒后重试 (第 {attempt+1}/{max_retries} 次)")
                    time.sleep(wait_time)
                    continue
                    
                response.raise_for_status()
                
                if "application/json" in response.headers.get("Content-Type", ""):
                    return response.json().get("html", "")
                
                return response.text
                
            except requests.RequestException as e:
                logger.error(f"网络请求失败 (第 {attempt+1}/{max_retries} 次): {e}")
                
                if attempt < max_retries - 1:
                    # 计算退避时间（指数退避 + 随机抖动）
                    base_delay = retry_delays[attempt]
                    jitter = random.uniform(0, base_delay * 0.5)
                    wait_time = base_delay + jitter
                    
                    logger.info(f"等待 {wait_time:.2f} 秒后重试")
                    time.sleep(wait_time)
                    
                    # 更换请求头重试
                    headers.update(self._get_random_headers())
                    continue
                    
            except Exception as e:
                logger.error(f"解析响应失败 (第 {attempt+1}/{max_retries} 次): {e}")
                
                if attempt < max_retries - 1:
                    wait_time = retry_delays[attempt]
                    logger.info(f"等待 {wait_time} 秒后重试")
                    time.sleep(wait_time)
                    headers.update(self._get_random_headers())
                    continue
        
        logger.error(f"请求 {url} 失败，已达最大重试次数 ({max_retries})")
        return None

    def get_html_by_curl(self, raw_curl: str, double_check: bool = False):
        """
        通过 curl 命令自动发送 GET 请求，获取网页 HTML 或 JSON 中的 html 字段

        Args:
            raw_curl: 浏览器复制的完整 curl 字符串
            double_check: 是否启用双重请求验证，默认关闭

        Returns:
            str: 网页 HTML 内容，请求失败返回 None

        Raises:
            requests.RequestException: 网络请求异常
            Exception: 其他解析异常
        """
        url, headers, cookies = self._parse_curl(raw_curl)
        
        if double_check:
            logger.info(f"启用双重请求验证，正在请求 URL: {url}")
            
            # 第一次请求
            headers_copy1 = headers.copy()
            headers_copy1.update(self._get_random_headers())  # 使用随机请求头
            result1 = self._send_request(url, headers_copy1, cookies)
            
            if result1 is None:
                logger.warning("第一次请求失败，跳过双重验证")
                return None
            
            # 等待一段时间后进行第二次请求
            time.sleep(random.uniform(1, 3))  
            
            # 第二次请求（使用不同的请求头）
            headers_copy2 = headers.copy()
            headers_copy2.update(self._get_random_headers()) 
            result2 = self._send_request(url, headers_copy2, cookies)
            
            if result2 is None:
                logger.warning("第二次请求失败，使用第一次请求结果")
                return result1
            
            # 比较两次结果
            if result1 == result2:
                logger.info("两次请求结果相同，验证通过")
                return result2
            else:
                logger.info("两次请求结果不同，以第二次请求结果为准")
                return result2
        else:
            # 普通模式：单次请求
            logger.info(f"正在请求 URL: {url}")
            headers.update(self._get_random_headers())  
            return self._send_request(url, headers, cookies)
    
    def get_htmls_by_curls(self, raw_curls: List[str], double_check: bool = False) -> List[Optional[str]]:
        """
        处理多个 curl 命令，获取多个网页的 HTML 内容

        Args:
            raw_curls: 浏览器复制的完整 curl 字符串列表
            double_check: 是否启用双重请求验证，启用后将串行处理

        Returns:
            List[Optional[str]]: 网页 HTML 内容列表，请求失败返回 None
        """
        results = []
        
        if double_check:
            # 双重验证模式：串行处理，确保每个链接验证完成后再进入下一个
            logger.info(f"启用双重请求验证模式，开始串行处理 {len(raw_curls)} 个页面")
            start_time = time.time()
            
            for i, raw_curl in enumerate(raw_curls):
                logger.info(f"处理第 {i+1}/{len(raw_curls)} 个链接")
                result = self.get_html_by_curl(raw_curl, double_check=True)
                results.append(result)
                
                # 在进入下一个链接前添加随机延迟
                if i < len(raw_curls) - 1:
                    delay = self._get_human_like_delay()
                    logger.info(f"等待 {delay:.2f} 秒后进入下一个链接")
                    time.sleep(delay)
            
            end_time = time.time()
            logger.info(f"串行请求完成，耗时: {end_time - start_time:.2f} 秒")
        else:
            # 普通模式：并发处理
            def fetch_curl(raw_curl):
                """单个 curl 请求的处理函数"""
                time.sleep(self._get_human_like_delay())
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
    
    def _get_human_like_delay(self):
        """
        生成人类行为模拟的随机延迟
        - 基础延迟：3-7秒（模拟阅读时间）
        - 10%概率添加额外"思考"时间（5-15秒）
        """
        delay = random.uniform(3, 7)  # 基础延迟
        
        # 10%概率更长延迟
        if random.random() < 0.1:
            extra_delay = random.uniform(5, 15)
            logger.debug(f"添加额外思考时间 {extra_delay:.2f} 秒")
            delay += extra_delay
        
        return delay