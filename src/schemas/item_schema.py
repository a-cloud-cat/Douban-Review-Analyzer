from pydantic import BaseModel
from typing import Optional

class ReviewItem(BaseModel):
    user_name: str
    star: int
    content: str
    douban_id: Optional[str] = None