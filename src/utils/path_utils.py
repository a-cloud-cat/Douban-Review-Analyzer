from pathlib import Path
from typing import Optional, Union

def get_project_root() -> Path:
    """获取项目根目录"""
    return Path(__file__).resolve().parent.parent.parent

def get_data_dir(subdir: Optional[str] = None) -> Path:
    """获取数据目录"""
    path = get_project_root() / "data"
    if subdir:
        path = path / subdir
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_config_dir() -> Path:
    """获取配置目录"""
    path = get_project_root() / "config"
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_logs_dir() -> Path:
    """获取日志目录"""
    path = get_project_root() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path

def ensure_dir(path: Union[str, Path]) -> Path:
    """确保目录存在，不存在则创建"""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_relative_path(from_path: Path, to_path: Path) -> Path:
    """获取相对路径"""
    return Path(to_path).relative_to(from_path)