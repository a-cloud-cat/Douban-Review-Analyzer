import sys
from pathlib import Path

from src.utils.path_utils import get_project_root
root_path = get_project_root()

if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from src.db.base import engine, Base

def reset_database():
    print("正在连接数据库进行重置操作")

    try:
        Base.metadata.drop_all(bind=engine)
        print("旧数据与物理表已成功删除。")

        Base.metadata.create_all(bind=engine)
        print("数据库结构已重新初始化（当前为空表状态）。")

    except Exception as e:
        print(f"重置失败，请检查数据库连接或是否被占用: {e}")