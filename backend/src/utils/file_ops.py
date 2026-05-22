from pathlib import Path
from uuid import uuid4


def ensure_parent_dir(file_path: str):
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)


def ensure_dir(dir_path: str):
    Path(dir_path).mkdir(parents=True, exist_ok=True)


def unique_file_path(dir_path: str, suffix: str = ".tmp") -> str:
    ensure_dir(dir_path)
    return str(Path(dir_path) / f"{uuid4().hex}{suffix}")


def cleanup_file(file_path: str):
    path = Path(file_path)
    if path.exists():
        path.unlink()
