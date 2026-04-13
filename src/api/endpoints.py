class DoubanEndpoints:
    @staticmethod
    def get_comment_url(movie_id, start=0):
        # 豆瓣电影短评接口地址
        return f"https://movie.douban.com/subject/{movie_id}/comments?start={start}&limit=20&status=P&sort=new_score"

endpoints = DoubanEndpoints()