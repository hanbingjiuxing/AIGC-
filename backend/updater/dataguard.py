"""用户数据保护：数据库、学生作品等"非功能"文件在更新过程中永不丢失。

识别方式是**按文件夹名称，与所在层级无关**：
  * 项目里任何深度上名为 instance 或 uploads 的文件夹，整体视为用户数据；
  * 任何位置的 *.db / *.sqlite / *.sqlite3 / *.db3 文件也一律保护；
  * data/ 统一数据根整体保护。

为什么不按路径：历史版本的父级目录换过多次（backend/instance、根目录
uploads/、app/instance ...），但这几个文件夹的名字从来没有变过。只认名字，
将来再调整目录结构也不会漏掉用户数据。

为什么还需要独立于 installer 的保护层：
  * installer 的保护白名单只管 ZIP 解压——它不碰 git；
  * 但 git 合并会操作**所有被 git 跟踪的文件**，而用户数据恰好可能被跟踪，
    一次 git pull 就可能用仓库里的旧副本覆盖学生的作品与用户数据。
"""

from __future__ import annotations

import fnmatch
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .paths import PROJECT_ROOT

#: 用户数据文件夹名 -> 新版统一位置（相对项目根）。
#: 只认名字、不认路径。
DATA_DIR_NAMES: Dict[str, str] = {
    "instance": "data/instance",
    "uploads": "data/uploads",
}

#: 统一数据根：整体受保护
DATA_ROOT_NAME = "data"

#: 数据库文件模式：任何位置的数据库都不覆盖
DEFAULT_DB_GLOBS: Tuple[str, ...] = ("*.db", "*.sqlite", "*.sqlite3", "*.db3")

#: 扫描用户数据目录时跳过的目录名
SCAN_SKIP_DIRS = {
    ".git", ".github", "node_modules", "__pycache__",
    ".venv", "venv", "env", "dist", "build", ".pytest_cache", ".idea", ".vscode",
    # 本项目自己的备份目录：里面含有数据副本，再扫一遍会被误判成待迁移的数据
    "backups",
}
#: 扫描时按前缀跳过的目录名（离线更新程序的备份目录）
SCAN_SKIP_PREFIXES = ("upgrade_backup",)
#: 扫描的最大深度
SCAN_MAX_DEPTH = 8


def _cfg_data(cfg: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return (cfg or {}).get("data", {}) or {}


def _norm_rel(value: Any) -> str:
    return str(value).replace("\\", "/").strip("/")


# --------------------------------------------------------------------------- #
# 名称规则
# --------------------------------------------------------------------------- #

def data_dir_names(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """数据文件夹名 -> 统一位置。可用 data.dir_names 扩展。"""
    names = {k.lower(): v for k, v in DATA_DIR_NAMES.items()}
    extra = _cfg_data(cfg).get("dir_names") or {}
    if isinstance(extra, dict):
        for key, value in extra.items():
            if str(key).strip() and str(value).strip():
                names[str(key).strip().lower()] = _norm_rel(value)
    return names


def dest_for_name(name: str, cfg: Optional[Dict[str, Any]] = None) -> Optional[str]:
    return data_dir_names(cfg).get(str(name).strip().lower())


def is_data_dir_name(name: str, cfg: Optional[Dict[str, Any]] = None) -> bool:
    return dest_for_name(name, cfg) is not None


def has_data_dir_component(rel: str, cfg: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """rel 中是否出现数据文件夹名；是则返回命中的名字。"""
    for part in _norm_rel(rel).split("/"):
        if is_data_dir_name(part, cfg):
            return part.lower()
    return None


def is_db_rel(rel: str, cfg: Optional[Dict[str, Any]] = None) -> bool:
    globs = tuple(_cfg_data(cfg).get("database_globs") or DEFAULT_DB_GLOBS)
    base = _norm_rel(rel).rsplit("/", 1)[-1]
    return any(fnmatch.fnmatch(base, g) for g in globs)


def explicit_data_paths(cfg: Optional[Dict[str, Any]]) -> Tuple[str, ...]:
    """配置里显式声明的数据路径（默认就是统一数据根 data）。"""
    if not _cfg_data(cfg).get("enabled", True):
        return ()
    return tuple(_norm_rel(p) for p in (_cfg_data(cfg).get("paths") or []) if str(p).strip())


def is_data_path(rel: str, cfg: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """判断项目根相对路径是否属于用户数据；是则返回命中的规则。"""
    if not _cfg_data(cfg).get("enabled", True):
        return None
    target = _norm_rel(rel)
    if not target:
        return None

    # 1) 任何层级上的 instance / uploads 文件夹（最先判定，报告更精确）
    hit = has_data_dir_component(target, cfg)
    if hit:
        return f"用户数据目录 {hit}"

    # 2) 统一数据根整体受保护
    for entry in explicit_data_paths(cfg):
        if target == entry or target.startswith(entry + "/"):
            return f"统一数据根 {entry}"

    # 3) 任何位置的数据库文件
    if is_db_rel(target, cfg):
        return "数据库文件"
    return None


# --------------------------------------------------------------------------- #
# 数据目录扫描
# --------------------------------------------------------------------------- #

@dataclass
class DataDir:
    rel: str        # 相对项目根，如 backend/instance
    name: str       # 命中的文件夹名
    dest_rel: str   # 新版统一位置，如 data/instance


def _scan_skip(name: str) -> bool:
    if name.lower() in SCAN_SKIP_DIRS:
        return True
    low = name.lower()
    return any(low.startswith(prefix) for prefix in SCAN_SKIP_PREFIXES)


def find_data_dirs(cfg: Optional[Dict[str, Any]] = None, root: Optional[Path] = None) -> List[DataDir]:
    """递归扫描项目，按**文件夹名称**找出所有用户数据目录（位置不限）。"""
    base = Path(root) if root is not None else PROJECT_ROOT
    found: List[DataDir] = []
    if not base.is_dir():
        return found

    def walk(directory: Path, rel_parts: Tuple[str, ...], depth: int) -> None:
        if depth > SCAN_MAX_DEPTH:
            return
        try:
            entries = sorted(directory.iterdir(), key=lambda p: p.name.lower())
        except OSError:
            return
        for entry in entries:
            try:
                if not entry.is_dir():
                    continue
            except OSError:
                continue
            if _scan_skip(entry.name):
                continue
            parts = rel_parts + (entry.name,)
            dest = dest_for_name(entry.name, cfg)
            if dest:
                # 命中数据文件夹：记录后不再深入（内部全是用户数据）
                try:
                    if any(entry.iterdir()):
                        found.append(DataDir(rel="/".join(parts), name=entry.name, dest_rel=dest))
                except OSError:
                    pass
                continue
            walk(entry, parts, depth + 1)

    walk(base, (), 0)
    found.sort(key=lambda d: d.rel)
    return found


def discover_database_files(cfg: Optional[Dict[str, Any]] = None,
                            root: Optional[Path] = None) -> Tuple[str, ...]:
    """按名称找出项目内所有数据库文件（相对项目根的 POSIX 路径）。"""
    base = Path(root) if root is not None else PROJECT_ROOT
    if not base.is_dir():
        return ()
    skip = set(SCAN_SKIP_DIRS)
    globs = tuple(_cfg_data(cfg).get("database_globs") or DEFAULT_DB_GLOBS)
    found: List[str] = []
    for current, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in skip and not _scan_skip(d)]
        for name in files:
            if any(fnmatch.fnmatch(name, g) for g in globs):
                try:
                    rel = Path(current, name).relative_to(base)
                except ValueError:
                    continue
                found.append(rel.as_posix())
    return tuple(sorted(found))


def data_paths(cfg: Optional[Dict[str, Any]] = None) -> Tuple[str, ...]:
    """受保护的数据路径：统一数据根 + 按名称扫描到的数据目录。"""
    entries: List[str] = list(explicit_data_paths(cfg))
    for data_dir in find_data_dirs(cfg):
        if data_dir.rel not in entries:
            entries.append(data_dir.rel)
    return tuple(entries)


# --------------------------------------------------------------------------- #
# 变更记录
# --------------------------------------------------------------------------- #

@dataclass
class DataChange:
    modified: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)
    added: List[str] = field(default_factory=list)

    @property
    def any(self) -> bool:
        return bool(self.modified or self.removed or self.added)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "modified": self.modified,
            "removed": self.removed,
            "added": self.added,
            "total": len(self.modified) + len(self.removed) + len(self.added),
        }

    def describe(self) -> str:
        parts = []
        if self.modified:
            parts.append(f"{len(self.modified)} 个被修改")
        if self.removed:
            parts.append(f"{len(self.removed)} 个被删除")
        if self.added:
            parts.append(f"{len(self.added)} 个新增")
        return "、".join(parts) if parts else "无变化"


class DataGuard:
    """用户数据的清单、快照、校验与还原。"""

    def __init__(self, cfg: Optional[Dict[str, Any]] = None,
                 log: Optional[Callable[[str], None]] = None):
        self.cfg = cfg or {}
        self.log = log or (lambda message: None)

    # -- 清单 --------------------------------------------------------------- #

    def data_dirs(self) -> List[DataDir]:
        return find_data_dirs(self.cfg)

    def _iter_files(self) -> Iterable[Tuple[str, Path]]:
        seen = set()
        for entry in data_paths(self.cfg):
            target = PROJECT_ROOT / entry
            if target.is_file():
                rel = entry
                if rel not in seen:
                    seen.add(rel)
                    yield rel, target
                continue
            if not target.is_dir():
                continue
            for current, dirs, files in os.walk(target):
                dirs[:] = [d for d in dirs if d not in ("__pycache__",) and not _scan_skip(d)]
                for name in files:
                    path = Path(current, name)
                    try:
                        rel = path.relative_to(PROJECT_ROOT).as_posix()
                    except ValueError:
                        continue
                    if rel in seen:
                        continue
                    seen.add(rel)
                    yield rel, path

    def inventory(self) -> Dict[str, Tuple[int, int]]:
        """数据清单：相对路径 -> (大小, mtime_ns)。"""
        result: Dict[str, Tuple[int, int]] = {}
        for rel, path in self._iter_files():
            try:
                stat = path.stat()
            except OSError:
                continue
            result[rel] = (stat.st_size, stat.st_mtime_ns)
        return result

    def summarize(self) -> Dict[str, Any]:
        inventory = self.inventory()
        total = sum(size for size, _ in inventory.values())
        databases = [rel for rel in inventory if is_db_rel(rel, self.cfg)]
        return {
            "enabled": bool(_cfg_data(self.cfg).get("enabled", True)),
            "protected_paths": list(data_paths(self.cfg)),
            "data_dirs": [{"rel": d.rel, "name": d.name, "dest_rel": d.dest_rel}
                          for d in self.data_dirs()],
            "file_count": len(inventory),
            "total_bytes": total,
            "total_mb": round(total / 1048576, 2),
            "database_files": databases,
            "sample": sorted(inventory)[:20],
        }

    # -- 风险与快照 --------------------------------------------------------- #

    def at_risk(self, changed_rels: Sequence[str]) -> List[str]:
        """在本次更新将改动的文件里，挑出属于用户数据的部分。"""
        risky = []
        for rel in changed_rels:
            if is_data_path(rel, self.cfg):
                risky.append(_norm_rel(rel))
        return sorted(set(risky))

    def tracked_data_files(self, git_runner: Callable[[List[str]], str]) -> List[str]:
        """返回被 git 跟踪的数据文件（只有这些才可能被合并覆盖或删除）。"""
        try:
            raw = git_runner(["ls-files"])
        except Exception:
            return []
        tracked = []
        for line in (raw or "").splitlines():
            rel = _norm_rel(line)
            if rel and is_data_path(rel, self.cfg):
                tracked.append(rel)
        return sorted(set(tracked))

    def snapshot(self, rels: Sequence[str], dest_dir: Path) -> List[str]:
        """把指定数据文件复制到 dest_dir（保持相对目录结构）。"""
        copied: List[str] = []
        for rel in rels:
            source = PROJECT_ROOT / rel
            if not source.is_file():
                continue
            dest = Path(dest_dir) / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            copied.append(rel)
        return copied

    # -- 校验与还原 --------------------------------------------------------- #

    def verify(self, before: Dict[str, Tuple[int, int]]) -> DataChange:
        """对比更新前后的数据清单。"""
        after = self.inventory()
        change = DataChange()
        for rel, meta in before.items():
            if rel not in after:
                change.removed.append(rel)
            elif after[rel] != meta:
                change.modified.append(rel)
        for rel in after:
            if rel not in before:
                change.added.append(rel)
        change.modified.sort()
        change.removed.sort()
        change.added.sort()
        return change

    def database_inventory(self) -> Dict[str, Tuple[int, int]]:
        """只取数据库文件，用于更新后的健康检查。"""
        return {
            rel: meta for rel, meta in self.inventory().items()
            if is_db_rel(rel, self.cfg)
        }

    def health_check(self, before_db: Dict[str, Tuple[int, int]]) -> List[str]:
        """确认更新前存在的数据库现在仍然存在且非空。"""
        problems: List[str] = []
        for rel, (size_before, _) in before_db.items():
            path = PROJECT_ROOT / rel
            if not path.exists():
                problems.append(f"数据库文件丢失: {rel}")
            elif path.stat().st_size == 0 and size_before > 0:
                problems.append(f"数据库文件被清空: {rel}")
        return problems

    def restore(self, snapshot_dir: Path, rels: Sequence[str]) -> List[str]:
        """从快照还原数据文件（含被删除的）。"""
        restored: List[str] = []
        for rel in rels:
            source = Path(snapshot_dir) / rel
            if not source.is_file():
                continue
            target = PROJECT_ROOT / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_name(target.name + ".restore-tmp")
            shutil.copy2(source, tmp)
            os.replace(tmp, target)
            restored.append(rel)
        return restored
