import json
import re
from bs4 import BeautifulSoup
from src.crawler.base_spider import BaseSpider
from src.utils.logger import get_logger

# 获取日志器
logger = get_logger("douban_spider")


class DoubanSpider(BaseSpider):
    def fetch_data(self, raw_curl: str):
        raw_response = self.get_html_by_curl(raw_curl)

        if not raw_response:
            logger.error("未能获取到任何响应内容。 怀疑：网络链接失败等")
            return []

        try:
            clean_content = raw_response.strip() # strip剥夺：去除字符串最前面和最后面的空格、换行、空字符
            data = json.loads(clean_content) # json.loads 把字符串转成 Python 的字典

            # 豆瓣的异步接口会把 HTML 塞在一个叫 "html" 的字段里
            if isinstance(data, dict) and "html" in data:
                logger.info("成功识别：这是一个 JSON 异步接口，正在解析内部 HTML 片段...")
                # 递归：把 JSON 里的那部分 HTML 提取出来再解析
                return self._parse_html_logic(data["html"])
        except (json.JSONDecodeError, TypeError):
            # 如果报错，说明抓回来的不是 JSON（是普通网页），直接跳过异常处理
            pass

        # 3. 默认处理：如果不是 JSON，就当作普通 HTML 页面处理
        logger.info("成功识别：这是一个常规 HTML 页面...")
        return self._parse_html_logic(raw_response)

    @staticmethod
    def _parse_html_logic(html_content):

        soup = BeautifulSoup(html_content, "html.parser")
        comment_nodes = soup.select(".comment-item")

        if not comment_nodes:
            logger.warning("在 HTML 中未找到 '.comment-item' 节点。")
            return []

        parsed_items = []

        for node in comment_nodes:
            user = node.select_one(".comment-info a") # 定位豆瓣用户名
            content = node.select_one(".short") # 定位评论正文
            star_tag = node.select_one('span[class*="allstar"]')# 豆瓣的星级写在 class="allstar40" 这样的属性里

            if not content:
                continue

            # 星级转换
            star_val = 0
            if star_tag:
                classes = star_tag.get('class', '') # 获取标签的class属性（可能是字符串）
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