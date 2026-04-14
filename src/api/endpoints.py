class DoubanEndpoints:
    """
    豆瓣 API 接口地址构造工具类，提供各接口 URL 的统一生成方法
    """

    @staticmethod
    def get_comment_url(movie_id, start=0):
        """
        构造豆瓣电影短评列表的请求 URL

        Args:
            movie_id: 豆瓣电影 ID
            start: 分页起始位置，默认为 0

        Returns:
            str: 完整的豆瓣短评接口 URL

        Raises:
            无异常抛出
        """
        # 豆瓣电影短评接口地址
        return f"https://movie.douban.com/subject/{movie_id}/comments?start={start}&limit=20&status=P&sort=new_score"

endpoints = DoubanEndpoints()