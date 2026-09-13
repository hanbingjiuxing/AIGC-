"""路径解析：全部锚定到代码真实位置，绝不依赖进程当前工作目录（CWD）。

这是对旧实现最关键的修复。旧版把 install_dir 设为 '.' 并拼接相对路径，
一旦 CWD 不是预期目录，更新包就会被解压到 backend/backend/ 之类的错误位置，
同时 preserve 保护白名单会整体失效（数据库、上传目录失去保护）。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

#: <项目根>/backend/updater
PACKAGE_DIR: Path = Path(__file__).resolve().parent
#: <项目根>/backend
BACKEND_DIR: Path = PACKAGE_DIR.parent
#: <项目根> —— 更新包安装根目录，与 GitHub Release ZIP 的目录结构一致
PROJECT_ROOT: Path = BACKEND_DIR.parent

#: 版本记录文件
VERSION_FILE: Path = BACKEND_DIR / "version.json"
#: 更新器配置文件
CONFIG_FILE: Path = PACKAGE_DIR / "config.json"

# --------------------------------------------------------------------------- #
# 统一的运行期数据根目录
# --------------------------------------------------------------------------- #
#: 唯一的用户数据 / 运行期数据根目录。
#: 升级维护时只需要保留这一个目录，项目里的其余内容都是可以整体覆盖的代码。
DATA_ROOT: Path = PROJECT_ROOT / "data"
#: SQLite 数据库（用户、考勤、公告等）
DATA_INSTANCE_DIR: Path = DATA_ROOT / "instance"
#: 学生作品与上传文件
DATA_UPLOADS_DIR: Path = DATA_ROOT / "uploads"
#: 更新包下载缓存
STATE_DIR: Path = DATA_ROOT / "updates"
#: 更新前备份（含用户数据快照）
BACKUP_DIR: Path = DATA_ROOT / "backups"

#: 需要在启动时确保存在的数据子目录
DATA_SUBDIRS = (DATA_INSTANCE_DIR, DATA_UPLOADS_DIR, STATE_DIR, BACKUP_DIR)

# 旧版数据位置（backend/instance、backend/uploads、根目录 instance/uploads 等）
# 不再写死在这里：由 dataguard.find_data_dirs() 按**文件夹名称**扫描识别，
# 这样将来再调整目录结构也不会漏掉用户数据。


def relpath_of(path) -> str:
    """返回相对项目根的 POSIX 风格路径；不在项目根内则返回绝对路径。"""
    rel = relative_to_root(path)
    if rel is None:
        return Path(path).as_posix()
    return rel or "."


def norm_path(path: Any) -> Path:
    """规范化路径用于比较：解析符号链接与 Windows 8.3 短名，并统一大小写。

    必须成对使用：Path.resolve() 会把 8.3 短名展开成长名，
    拿它去和未规范化的路径做 relative_to / 前缀比较会直接抛错或误判。
    """
    return Path(os.path.normcase(os.path.realpath(str(path))))


def relative_to_root(path: Any, root: Optional[Any] = None) -> Optional[str]:
    """把路径表示为相对项目根的 POSIX 路径；不在项目根内时返回 None。

    **保留原始大小写**：规范化只用于"是否在根内"的判断。若把 normcase 的结果
    当作返回值，Windows 上会得到全小写路径，导致与 git 输出的真实文件名
    （例如学生上传的 MyPhoto.PNG）对不上，保护规则会静默失效。
    """
    base = norm_path(root if root is not None else PROJECT_ROOT)
    try:
        resolved = Path(os.path.realpath(str(path)))
    except OSError:
        return None
    normalized = Path(os.path.normcase(str(resolved)))
    if normalized == base:
        return ""
    if base not in normalized.parents:
        return None
    return Path(*resolved.parts[len(base.parts):]).as_posix()


def is_within_project(path) -> bool:
    """判断路径是否位于项目根之内（含项目根本身）。"""
    return relative_to_root(path) is not None
