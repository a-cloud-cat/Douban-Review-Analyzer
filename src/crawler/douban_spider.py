import json
import re
import time
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from src.crawler.base_spider import BaseSpider
from src.utils.logger import get_logger


logger = get_logger("douban_spider")


class DoubanSpider(BaseSpider):
    """
    豆瓣电影评论爬虫，继承自 BaseSpider，支持解析 HTML / JSON 异步接口
    自动提取用户名、评论内容、评分星级，支持自动翻页
    包含反爬检测机制
    """
    
    def __init__(self):
        super().__init__()
        self.captcha_keywords = [
            "captcha", "验证码", "请输入验证码",
            "人机验证", "security check", "verify",
            "验证", "验证中心", "安全验证"
        ]

        self.blocked_keywords = [
            "访问被拒绝", "403", "forbidden",
            "您的访问过于频繁", "请求过于频繁",
            "暂时无法访问", "系统检测到异常"
        ]

    def _detect_anti_spider(self, html_content: str) -> str:
        """
        检测页面是否包含反爬措施
        
        Args:
            html_content: HTML内容
            
        Returns:
            str: 
                - "normal": 正常页面
                - "captcha": 包含验证码
                - "blocked": 被封禁
                - "empty": 内容异常（可能被封）
        """
        if not html_content or not html_content.strip():
            logger.warning("检测到空响应，可能被封禁")
            return "empty"
        
        soup = BeautifulSoup(html_content, "html.parser")
        page_text = soup.get_text().lower()
        
        # 检测验证码
        for keyword in self.captcha_keywords:
            if keyword.lower() in page_text:
                logger.warning(f"检测到验证码关键词: {keyword}")
                return "captcha"
        
        # 检测封禁提示
        for keyword in self.blocked_keywords:
            if keyword.lower() in page_text:
                logger.warning(f"检测到封禁关键词: {keyword}")
                return "blocked"
        
        # 检测验证码图片/表单
        if soup.select_one("#captcha") or soup.select_one(".captcha-image"):
            logger.warning("检测到验证码图片")
            return "captcha"
        
        if soup.select_one('input[type="text"][placeholder*="验证码"]'):
            logger.warning("检测到验证码输入框")
            return "captcha"
        
        # 检测异常页面（内容过短）
        text_length = len(page_text.strip())
        if text_length < 150:
            logger.warning(f"页面内容异常（仅 {text_length} 字符），可能被封禁")
            return "empty"
        
        return "normal"
    
    def _handle_anti_spider(self, detect_result: str) -> bool:
        """
        处理反爬检测结果
        
        Args:
            detect_result: 检测结果（normal/captcha/blocked/empty）
            
        Returns:
            bool: 是否应该继续执行
        """
        if detect_result == "captcha":
            logger.error("检测到验证码，建议手动处理或暂停一段时间")
            # 可以在这里添加暂停逻辑或发送通知
            return False
            
        elif detect_result == "blocked":
            logger.error("检测到被封禁，建议暂停较长时间或更换IP")
            # 暂停一段时间（5分钟）
            pause_time = 300
            logger.info(f"暂停 {pause_time} 秒后继续...")
            time.sleep(pause_time)
            return False
            
        elif detect_result == "empty":
            logger.warning("页面内容异常，跳过当前页面")
            return False
            
        return True
    
    def fetch_data(self, raw_curl: str, max_pages: int = 1) -> List[Dict[str, Any]]:
        """
        根据 curl 命令抓取豆瓣评论数据，自动识别 JSON 接口 / 普通 HTML 页面
        支持自动翻页获取多页评论

        Args:
            raw_curl: 浏览器复制的完整 curl 请求字符串
            max_pages: 最大翻页数，默认 1

        Returns:
            list: 解析后的评论数据列表，每条为字典格式

        Raises:
            无异常抛出，内部已捕获处理
        """
        if max_pages == 1:
            raw_response = self.get_html_by_curl(raw_curl)

            if not raw_response:
                logger.error("未能获取到任何响应内容。 怀疑：网络链接失败等")
                return []
            
            # 检测反爬
            detect_result = self._detect_anti_spider(raw_response)
            if not self._handle_anti_spider(detect_result):
                return []

            try:
                clean_content = raw_response.strip()
                # json.loads 把字符串转成 Python 的字典
                data = json.loads(clean_content)
                # 豆瓣的异步接口会把 HTML 塞在一个叫 "html" 的字段里
                if isinstance(data, dict) and "html" in data:
                    logger.info("成功识别：这是一个 JSON 异步接口，正在解析内部 HTML 片段...")
                    # 递归：把 JSON 里的那部分 HTML 提取出来再解析
                    return self._parse_html_logic(data["html"])
            except (json.JSONDecodeError, TypeError):
                # 如果报错，说明抓回来的不是 JSON（是普通网页），直接跳过异常处理
                pass

            # 默认处理：如果不是 JSON，就当作普通 HTML 页面处理
            logger.info("成功识别：这是一个常规 HTML 页面...")
            return self._parse_html_logic(raw_response)
        else:
            # 抓取多页，使用自动翻页逻辑
            return self.fetch_data_with_pagination(raw_curl, max_pages)
    
    def fetch_data_with_pagination(self, raw_curl: str, max_pages: int) -> List[Dict[str, Any]]:
        """
        自动翻页抓取多页评论数据

        Args:
            raw_curl: 浏览器复制的完整 curl 请求字符串
            max_pages: 最大翻页数

        Returns:
            list: 解析后的评论数据列表，每条为字典格式
        """
        # 生成多页的 curl 请求
        page_curls = self._generate_page_curls(raw_curl, max_pages)
        if not page_curls:
            logger.error("无法生成多页 curl 请求")
            return []
        
        # 使用并发抓取多页数据
        return self.fetch_data_concurrent(page_curls)
    
    def _generate_page_curls(self, raw_curl: str, max_pages: int) -> List[str]:
        """
        根据原始 curl 生成多页的 curl 请求

        Args:
            raw_curl: 浏览器复制的完整 curl 请求字符串
            max_pages: 最大翻页数

        Returns:
            list: 多页的 curl 请求列表
        """
        try:
            # 解析原始 curl 获取 URL
            url, headers, cookies = self._parse_curl(raw_curl)
            
            # 生成多页 URL
            page_urls = self._generate_page_urls(url, max_pages)
            if not page_urls:
                logger.error("无法生成多页 URL")
                return []
            
            # 为每个 URL 重新生成 curl 请求
            page_curls = []
            for page_url in page_urls:
                # 重新构建 curl 请求
                curl_parts = [f"curl \"{page_url}\""]
                
                # 添加 headers
                for key, value in headers.items():
                    curl_parts.append(f"-H \"{key}: {value}\"")
                
                # 添加 cookies
                if cookies:
                    cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
                    curl_parts.append(f"-b \"{cookie_str}\"")
                
                page_curls.append(" ".join(curl_parts))
            
            logger.info(f"成功生成 {len(page_curls)} 个页面的 curl 请求")
            return page_curls
        except Exception as e:
            logger.error(f"生成多页 curl 请求时发生错误: {e}")
            return []
    
    @staticmethod
    def _generate_page_urls(url: str, max_pages: int) -> List[str]:
        """
        根据原始 URL 生成多页 URL

        Args:
            url: 原始 URL
            max_pages: 最大翻页数

        Returns:
            list: 多页 URL 列表
        """
        page_urls = []
        
        # 分析 URL 结构，识别翻页参数
        if "start=" in url:
            # 已经有 start 参数，替换它
            base_url = re.sub(r"start=\d+", "start={}", url)
        else:
            # 没有 start 参数，添加它
            if "?" in url:
                base_url = url + "&start={}"
            else:
                base_url = url + "?start={}"
        
        # 生成多页 URL
        for page in range(max_pages):
            start = page * 20
            page_url = base_url.format(start)
            page_urls.append(page_url)
        
        logger.info(f"成功生成 {len(page_urls)} 个页面的 URL")
        return page_urls
    
    def fetch_data_concurrent(self, raw_curls: List[str], double_check: bool = False) -> List[Dict[str, Any]]:
        """
        抓取多个页面的评论数据

        Args:
            raw_curls: 浏览器复制的完整 curl 请求字符串列表
            double_check: 是否启用双重请求验证，启用后将串行处理

        Returns:
            list: 解析后的评论数据列表，每条为字典格式

        Raises:
            无异常抛出，内部已捕获处理
        """
        all_comments = []
        
        # 获取所有页面的 HTML（根据 double_check 参数决定串行或并发）
        htmls = self.get_htmls_by_curls(raw_curls, double_check)
        

        for i, html in enumerate(htmls):
            if not html:
                logger.warning(f"第 {i+1} 个页面获取失败，跳过解析")
                continue
            
            try:
                # 尝试解析 JSON
                clean_content = html.strip()
                data = json.loads(clean_content)
                if isinstance(data, dict) and "html" in data:
                    comments = self._parse_html_logic(data["html"])
                else:
                    comments = self._parse_html_logic(html)
                
                all_comments.extend(comments)
                logger.info(f"第 {i+1} 个页面解析完成，获取 {len(comments)} 条评论")
            except (json.JSONDecodeError, TypeError):
                # 不是 JSON，当作普通 HTML 处理
                comments = self._parse_html_logic(html)
                all_comments.extend(comments)
                logger.info(f"第 {i+1} 个页面解析完成，获取 {len(comments)} 条评论")
            except Exception as e:
                logger.error(f"解析第 {i+1} 个页面时发生错误: {e}")
        
        logger.info(f"并发抓取完成，共获取 {len(all_comments)} 条评论")
        return all_comments

    @staticmethod
    def _parse_html_logic(html_content):
        """
        从 HTML 中解析评论节点，提取用户名、内容、星级

        Args:
            html_content: 网页 HTML 字符串

        Returns:
            list: 结构化评论数据列表
        """
        soup = BeautifulSoup(html_content, "html.parser")
        comment_nodes = soup.select(".comment-item")

        if not comment_nodes:
            logger.warning("在 HTML 中未找到 '.comment-item' 节点。")
            return []

        parsed_items = []

        for node in comment_nodes:
            # 定位豆瓣用户名
            user = node.select_one(".comment-info a")
            # 定位评论正文
            content = node.select_one(".short")
            # 豆瓣的星级写在 class="allstar40" 这样的属性里
            star_tag = node.select_one('span[class*="allstar"]')

            if not content:
                continue

            # 星级转换
            star_val = 0
            if star_tag:
                # 获取标签的class属性（可能是字符串）
                classes = star_tag.get('class', '')
                for c in classes:
                    if 'allstar' in c:
                        try:
                            star_val = int(re.search(r'\d+', c).group()) // 10
                        except (ValueError, AttributeError):
                            star_val = 0

            # --- 封装数据 ---
            parsed_items.append({
                "user_name": user.get_text(strip=True) if user else "匿名",
                "content": content.get_text(strip=True),
                "star": star_val
            })

        logger.info(f"解析成功！本次共提取到 {len(parsed_items)} 条评论数据。")
        return parsed_items