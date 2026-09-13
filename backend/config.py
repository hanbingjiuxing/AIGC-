import os

from updater.paths import DATA_INSTANCE_DIR, DATA_UPLOADS_DIR


def _sqlite_uri(path) -> str:
    """把绝对路径转成 SQLAlchemy 的 sqlite:/// URL（Windows 需要正斜杠）。"""
    return 'sqlite:///' + path.as_posix()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'aigc-society-secret-key-2024'

    # 用户数据库统一放在 <项目根>/data/instance/ 下：
    # 升级维护时只需保留 data/ 目录，其余都是可整体覆盖的代码。
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DATABASE_URL')
        or _sqlite_uri(DATA_INSTANCE_DIR / 'aigc_society.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_EXPIRATION_HOURS = 24

    # 学生作品与上传文件统一放在 <项目根>/data/uploads/ 下
    UPLOAD_FOLDER = str(DATA_UPLOADS_DIR)

    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'py', 'cpp', 'c', 'mp4', 'mp3', 'zip', 'rar', '7z'}
