"""安全安装器：把更新包内容落盘到项目根，并保护用户数据。

相对旧实现修复的关键点：
  1. 安装根固定为 PROJECT_ROOT（由 __file__ 推导），与 CWD 无关；
  2. 识别并剥离 ZIP 的单层包裹目录（GitHub "Download ZIP" 的 AIGC--main/ 形式）；
  3. zip-slip 防护：拒绝绝对路径、.. 回溯、盘符与反斜杠；
  4. preserve 白名单按"项目根相对路径"匹配，因此真正生效
     （旧版因路径错位导致数据库/上传目录/version.json 全部失去保护）；
  5. 写入前后端做备份，失败自动回滚；逐文件原子替换，避免半截文件。
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import shutil
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .dataguard import DataGuard, is_data_path
from .paths import BACKUP_DIR, PROJECT_ROOT, relative_to_root

# 无扩展名但需要放行的常见文件名
ALLOW_FILENAMES = {
    ".gitignore", ".gitattributes", ".editorconfig", ".npmrc", ".nvmrc",
    ".env.example", ".dockerignore", "license", "licence", "makefile",
    "dockerfile", "procfile", "readme", "changelog",
}

#: 资源保险箱目录：里面的密文属于站点数据（不是可执行内容），
#: 不受 install.allow_extensions 限制 —— 详见 classify()
VAULT_CIPHER_DIR = "assets/encrypted"

CHUNK = 1024 * 1024


class InstallError(Exception):
    """安装阶段失败。"""


@dataclass
class PlanEntry:
    rel: str                    # 项目根相对 POSIX 路径
    action: str                 # write | unchanged | preserve | skip
    reason: str = ""
    size: int = 0


@dataclass
class InstallPlan:
    source: str
    root_prefix: str = ""
    entries: List[PlanEntry] = field(default_factory=list)
    dependency_files: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    @property
    def to_write(self) -> List[PlanEntry]:
        return [e for e in self.entries if e.action == "write"]

    def counts(self) -> Dict[str, int]:
        result: Dict[str, int] = {}
        for entry in self.entries:
            result[entry.action] = result.get(entry.action, 0) + 1
        return result

    def summary(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "root_prefix": self.root_prefix,
            "counts": self.counts(),
            "total": len(self.entries),
            "dependency_files": list(self.dependency_files),
            "notes": list(self.notes),
            "files_to_write": [e.rel for e in self.to_write][:500],
        }


@dataclass
class InstallReport:
    success: bool
    dry_run: bool = False
    source: str = ""
    root_prefix: str = ""
    written: List[str] = field(default_factory=list)
    unchanged: List[str] = field(default_factory=list)
    preserved: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    backup_dir: Optional[str] = None
    rolled_back: bool = False
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "dry_run": self.dry_run,
            "source": self.source,
            "root_prefix": self.root_prefix,
            "written_count": len(self.written),
            "unchanged_count": len(self.unchanged),
            "preserved_count": len(self.preserved),
            "skipped_count": len(self.skipped),
            "written": self.written[:500],
            "preserved": self.preserved[:200],
            "skipped": self.skipped[:200],
            "errors": self.errors,
            "notes": self.notes,
            "backup_dir": self.backup_dir,
            "rolled_back": self.rolled_back,
            "data": self.data,
        }


# --------------------------------------------------------------------------- #
# 路径与分类工具
# --------------------------------------------------------------------------- #

def effective_extension(name: str) -> str:
    """取文件名最后一个点之后的部分；无点则为空串。

    不用 Path.suffix，因为 .gitignore 这类点文件会被它判成没有后缀。
    """
    base = name.rsplit("/", 1)[-1]
    idx = base.rfind(".")
    return base[idx:].lower() if idx > 0 else ""


def is_unsafe_member(name: str) -> Optional[str]:
    """返回不安全原因；None 表示安全。"""
    if not name or name in (".", "./"):
        return "空路径"
    raw = name.replace("\\", "/")
    if raw.startswith("/") or raw.startswith("//"):
        return "绝对路径"
    if len(raw) > 1 and raw[1] == ":":
        return "包含盘符"
    parts = [p for p in raw.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        return "包含 .. 回溯"
    return None


def detect_root_prefix(names: Sequence[str]) -> str:
    """若所有条目都在同一个顶层目录下，返回该目录（用于剥离 GitHub Download ZIP 的包裹层）。"""
    candidates = {n.split("/", 1)[0] for n in names if n and not n.startswith("/")}
    if len(candidates) != 1:
        return ""
    only = candidates.pop()
    # 只有当这个顶层项确实是"目录"（存在该前缀下的条目）时才剥离
    if any(n.startswith(only + "/") for n in names):
        return only + "/"
    return ""


def resolve_within_root(rel: str) -> Optional[Path]:
    """把项目根相对路径解析为绝对路径；越界返回 None。

    绝不使用 str.startswith 比较路径：短名、长名、符号链接与大小写差异
    都会让朴素的前缀比较失效（旧实现的 preserve 白名单正是栽在这里）。
    """
    candidate = PROJECT_ROOT / rel
    if relative_to_root(candidate) is None:
        return None
    return candidate


def _matches_any(rel: str, patterns: Iterable[str]) -> bool:
    name = rel.rsplit("/", 1)[-1]
    for pattern in patterns:
        if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(name, pattern):
            return True
    return False


def classify(rel: str, cfg: Dict[str, Any]) -> Tuple[str, str]:
    """把项目根相对路径分类为 write / preserve / skip。"""
    install_cfg = cfg.get("install", {}) or {}
    parts = rel.split("/")

    for skip_dir in install_cfg.get("skip_dirs", []) or []:
        if skip_dir in parts:
            return "skip", f"忽略目录 {skip_dir}"

    # 用户数据优先判定：数据库与学生作品在报告中应显示为"受保护"而非"忽略"
    data_reason = is_data_path(rel, cfg)
    if data_reason:
        return "preserve", data_reason

    if _matches_any(rel, install_cfg.get("skip_globs", []) or []):
        return "skip", "忽略文件类型"

    for keep in install_cfg.get("preserve_files", []) or []:
        if rel == keep.replace("\\", "/"):
            return "preserve", f"受保护文件 {keep}"

    for keep_dir in install_cfg.get("preserve_dirs", []) or []:
        keep_norm = keep_dir.replace("\\", "/").strip("/")
        if rel == keep_norm or rel.startswith(keep_norm + "/"):
            return "preserve", f"受保护目录 {keep_dir}"

    # 资源保险箱的密文无条件放行。原因：backend/updater/config.json 是受保护文件
    # （更新永远不覆盖它），旧机器上的 allow_extensions 里没有 ".enc"，
    # 从 Release 包升级时密文会被整批跳过 —— 结果就是 About 页头像退回社徽。
    # 只放行这一个目录下的密文，别处的 .enc 仍然按白名单处理。
    if rel == VAULT_CIPHER_DIR or rel.startswith(VAULT_CIPHER_DIR + "/"):
        return "write", "资源保险箱密文"

    ext = effective_extension(rel)
    allowed = {e.lower() for e in (install_cfg.get("allow_extensions") or [])}
    base = parts[-1].lower()
    if ext not in allowed and base not in ALLOW_FILENAMES:
        return "skip", f"扩展名不在白名单: {ext or '(无)'}"

    return "write", ""


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    try:
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(CHUNK), b""):
                hasher.update(chunk)
    except OSError:
        return ""
    return hasher.hexdigest()


# --------------------------------------------------------------------------- #
# 计划构建
# --------------------------------------------------------------------------- #

def build_plan(zip_path: Path, cfg: Dict[str, Any], source: str = "release") -> InstallPlan:
    """解析更新包并生成安装计划（不修改任何文件）。"""
    if not Path(zip_path).exists():
        raise InstallError(f"更新包不存在: {zip_path}")
    if not zipfile.is_zipfile(zip_path):
        raise InstallError(f"更新包不是有效的 ZIP 文件: {zip_path}")

    plan = InstallPlan(source=source)

    with zipfile.ZipFile(zip_path) as archive:
        infos = [i for i in archive.infolist() if not i.is_dir()]
        safe_names: List[str] = []
        rejected: List[str] = []

        for info in infos:
            reason = is_unsafe_member(info.filename)
            if reason:
                rejected.append(f"{info.filename} ({reason})")
            else:
                safe_names.append(info.filename)

        if rejected:
            plan.notes.append(f"已拒绝 {len(rejected)} 个不安全条目（zip-slip 防护）")
            plan.entries.extend(
                PlanEntry(rel=name, action="skip", reason="路径不安全") for name in rejected
            )

        prefix = detect_root_prefix(safe_names)
        plan.root_prefix = prefix
        if prefix:
            plan.notes.append(f"已识别并剥离包裹目录: {prefix}")

        for info in infos:
            if is_unsafe_member(info.filename):
                continue
            rel = info.filename[len(prefix):] if prefix and info.filename.startswith(prefix) else info.filename
            rel = rel.replace("\\", "/").strip("/")
            if not rel:
                continue

            action, reason = classify(rel, cfg)
            if action == "write" and resolve_within_root(rel) is None:
                action, reason = "skip", "路径越界（不在项目根内）"
            if action == "write":
                target = PROJECT_ROOT / rel
                if target.exists():
                    try:
                        if target.stat().st_size == info.file_size and _sha256_file(target) == hashlib.sha256(
                            archive.read(info)
                        ).hexdigest():
                            action, reason = "unchanged", "内容一致"
                    except (OSError, zipfile.BadZipFile, KeyError):
                        pass

            plan.entries.append(
                PlanEntry(rel=rel, action=action, reason=reason, size=info.file_size)
            )

    for rel in ("backend/requirements.txt", "frontend/package.json", "frontend/package-lock.json"):
        entry = next((e for e in plan.entries if e.rel == rel), None)
        if entry is not None and entry.action == "write":
            plan.dependency_files.append(rel)

    if plan.dependency_files:
        if "backend/requirements.txt" in plan.dependency_files:
            plan.notes.append("backend/requirements.txt 有变化，更新后可能需要重新安装 Python 依赖")
        if any(p.startswith("frontend/") for p in plan.dependency_files):
            plan.notes.append("frontend/package.json 有变化，更新后需要在 frontend/ 执行 npm install")

    return plan


# --------------------------------------------------------------------------- #
# 计划执行
# --------------------------------------------------------------------------- #

def _data_report(guard: "DataGuard", db_before: Dict[str, Any], data_written: List[str]) -> Dict[str, Any]:
    """汇总用户数据保护结果。data_written 必须为空，否则说明保护规则有漏洞。"""
    summary = guard.summarize()
    problems = guard.health_check(db_before)
    if data_written:
        problems.append("更新包试图写入用户数据文件（已阻止）: " + ", ".join(data_written[:5]))
    return {
        "enabled": True,
        "protected_paths": summary["protected_paths"],
        "protected_files": summary["file_count"],
        "total_mb": summary["total_mb"],
        "database_files": summary["database_files"],
        "merge_touched": [],
        "data_written": data_written,
        "problems": problems,
    }


def _prune_backups(keep: int) -> None:
    if keep <= 0 or not BACKUP_DIR.exists():
        return
    backups = sorted(
        (d for d in BACKUP_DIR.iterdir() if d.is_dir() and d.name.startswith("backup_")),
        key=lambda d: d.name,
    )
    for stale in backups[:-keep]:
        shutil.rmtree(stale, ignore_errors=True)


def extract_version_json(zip_path: Path) -> Optional[Dict[str, Any]]:
    """从更新包中取出 backend/version.json 的内容（用于安装后写入权威版本号）。"""
    try:
        with zipfile.ZipFile(zip_path) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                name = info.filename.replace("\\", "/")
                if name.endswith("backend/version.json"):
                    try:
                        data = json.loads(archive.read(info).decode("utf-8-sig"))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        return None
                    return data if isinstance(data, dict) else None
    except (OSError, zipfile.BadZipFile):
        return None
    return None


def install_from_zip(
    zip_path: Path,
    cfg: Dict[str, Any],
    source: str = "release",
    dry_run: bool = False,
    progress: Optional[Any] = None,
) -> InstallReport:
    """按计划把更新包落盘。dry_run=True 时只生成报告，不修改任何文件。"""
    plan = build_plan(zip_path, cfg, source=source)
    report = InstallReport(
        success=True,
        dry_run=dry_run,
        source=source,
        root_prefix=plan.root_prefix,
        notes=list(plan.notes),
    )

    report.preserved = [e.rel for e in plan.entries if e.action == "preserve"]
    report.skipped = [e.rel for e in plan.entries if e.action == "skip"]
    report.unchanged = [e.rel for e in plan.entries if e.action == "unchanged"]

    data_cfg = cfg.get("data", {}) or {}
    data_enabled = bool(data_cfg.get("enabled", True))
    guard = DataGuard(cfg) if data_enabled else None
    db_before = guard.database_inventory() if guard else {}

    if dry_run:
        report.written = [e.rel for e in plan.to_write]
        if guard:
            report.data = _data_report(guard, db_before, [])
        return report

    install_cfg = cfg.get("install", {}) or {}
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"backup_{timestamp}"
    do_backup = bool(install_cfg.get("backup_before_update", True))

    created: List[str] = []
    overwritten: List[str] = []

    with zipfile.ZipFile(zip_path) as archive:
        prefix = plan.root_prefix
        total = max(len(plan.to_write), 1)
        done = 0

        try:
            for entry in plan.to_write:
                member = prefix + entry.rel if prefix else entry.rel
                target = resolve_within_root(entry.rel)
                if target is None:
                    report.errors.append(f"拒绝越界写入: {entry.rel}")
                    report.success = False
                    continue

                target.parent.mkdir(parents=True, exist_ok=True)

                if target.exists():
                    if do_backup:
                        dest = backup_path / entry.rel
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(target, dest)
                    overwritten.append(entry.rel)
                else:
                    created.append(entry.rel)

                # 原子替换：先写临时文件再 rename
                tmp = target.with_name(target.name + ".update-tmp")
                with archive.open(member) as src, tmp.open("wb") as dst:
                    shutil.copyfileobj(src, dst, CHUNK)
                os.replace(tmp, target)

                report.written.append(entry.rel)
                done += 1
                if progress:
                    progress(int(done / total * 100), 100, f"写入 {done}/{total}")

            if do_backup and (overwritten or created):
                report.backup_dir = str(backup_path)
                _prune_backups(int(install_cfg.get("max_backups", 5)))

        except Exception as exc:  # noqa: BLE001 - 需要兜住任何失败并回滚
            report.errors.append(f"安装中断: {exc}")
            report.success = False
            report.rolled_back = _rollback(backup_path, created, overwritten, report)

    if guard:
        data_written = [rel for rel in report.written if is_data_path(rel, cfg)]
        report.data = _data_report(guard, db_before, data_written)
        if report.data["problems"]:
            for problem in report.data["problems"]:
                report.errors.append(problem)
            report.success = False

    return report


def _rollback(backup_path: Path, created: List[str], overwritten: List[str], report: InstallReport) -> bool:
    """回滚：删除新建文件，从备份恢复被覆盖的文件。"""
    ok = True
    for rel in created:
        try:
            target = PROJECT_ROOT / rel
            if target.exists():
                target.unlink()
        except OSError as exc:
            ok = False
            report.errors.append(f"回滚删除失败 {rel}: {exc}")

    for rel in overwritten:
        source = backup_path / rel
        try:
            if source.exists():
                shutil.copy2(source, PROJECT_ROOT / rel)
            else:
                ok = False
                report.errors.append(f"回滚缺少备份: {rel}")
        except OSError as exc:
            ok = False
            report.errors.append(f"回滚恢复失败 {rel}: {exc}")

    if ok:
        report.notes.append("已回滚到更新前的状态")
    else:
        report.notes.append(f"回滚不完整，请手动检查备份目录: {backup_path}")
    return ok
