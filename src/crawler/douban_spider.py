import json
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from src.crawler.base_spider import BaseSpider
from src.utils.logger import get_logger

# 获取日志器
logger = get_logger("douban_spider")


class DoubanSpider(BaseSpider):
    """
    豆瓣电影评论爬虫，继承自 BaseSpider，支持解析 HTML / JSON 异步接口
    自动提取用户名、评论内容、评分星级
    """

    def fetch_data(self, raw_curl: str):
        """
        根据 curl 命令抓取豆瓣评论数据，自动识别 JSON 接口 / 普通 HTML 页面

        Args:
            raw_curl: 浏览器复制的完整 curl 请求字符串

        Returns:
            list: 解析后的评论数据列表，每条为字典格式

        Raises:
            无异常抛出，内部已捕获处理
        """
        raw_response = self.get_html_by_curl(raw_curl)

        if not raw_response:
            logger.error("未能获取到任何响应内容。 怀疑：网络链接失败等")
            return []

        try:
            # strip剥夺：去除字符串最前面和最后面的空格、换行、空字符
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
    
    def fetch_data_concurrent(self, raw_curls: List[str]) -> List[Dict[str, Any]]:
        """
        并发抓取多个页面的评论数据

        Args:
            raw_curls: 浏览器复制的完整 curl 请求字符串列表

        Returns:
            list: 解析后的评论数据列表，每条为字典格式

        Raises:
            无异常抛出，内部已捕获处理
        """
        all_comments = []
        
        # 并发获取所有页面的 HTML
        htmls = self.get_htmls_by_curls(raw_curls)
        
        # 解析每个页面的评论
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