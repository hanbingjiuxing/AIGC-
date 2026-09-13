"""统一的数据目录布局与自动迁移。

设计目标：**升级维护时只需要保留一个目录**。

    data/
    ├── instance/     SQLite 数据库（用户信息、考勤、公告）
    ├── uploads/      学生作品与上传文件
    ├── updates/      更新包下载缓存
    └── backups/      更新前备份（含用户数据快照）

历史版本把这些内容放在不同位置（backend/instance、backend/uploads、根目录
instance/、uploads/、app/instance ...），父级目录换过多次，但**文件夹名字
从来没有变过**。所以这里按名称扫描并归位，而不是写死路径：

  * 目标不存在      -> 直接搬过去；
  * 目标已存在同名项 -> 保留目标、跳过该项并记录，**绝不覆盖**；
  * 旧目录搬空后     -> 删除空目录。
整个过程可重复执行（幂等），不会丢数据。
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from .dataguard import find_data_dirs
from .paths import DATA_ROOT, DATA_SUBDIRS, PROJECT_ROOT


def describe_layout() -> Dict[str, Any]:
    """返回当前数据目录布局概览。"""
    return {
        "data_root": str(DATA_ROOT),
        "subdirs": [str(p) for p in DATA_SUBDIRS],
        "exists": DATA_ROOT.exists(),
    }


def _move_contents(source: Path, target: Path, report: Dict[str, List[str]]) -> None:
    """把 source 下的条目逐个搬到 target；已存在的目标项一律保留不覆盖。"""
    target.mkdir(parents=True, exist_ok=True)
    try:
        items = sorted(source.iterdir())
    except OSError as exc:
        report["errors"].append(f"读取目录失败 {source}: {exc}")
        return
    for item in items:
        destination = target / item.name
        if destination.exists():
            report["skipped"].append(f"{item} -> {destination}（目标已存在，保留目标）")
            continue
        try:
            shutil.move(str(item), str(destination))
            report["moved"].append(f"{item} -> {destination}")
        except (OSError, shutil.Error) as exc:
            report["errors"].append(f"迁移失败 {item} -> {destination}: {exc}")
            return


def ensure_layout(migrate: bool = True, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """创建统一数据目录，并把按名称扫描到的用户数据归位（幂等）。"""
    report: Dict[str, Any] = {
        "data_root": str(DATA_ROOT),
        "created": [],
        "moved": [],
        "skipped": [],
        "errors": [],
        "legacy_left": [],
    }

    try:
        DATA_ROOT.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        report["errors"].append(f"无法创建数据根目录 {DATA_ROOT}: {exc}")
        return report

    for subdir in DATA_SUBDIRS:
        if not subdir.exists():
            try:
                subdir.mkdir(parents=True, exist_ok=True)
                report["created"].append(str(subdir))
            except OSError as exc:
                report["errors"].append(f"无法创建目录 {subdir}: {exc}")

    if not migrate:
        return report

    for data_dir in find_data_dirs(cfg):
        legacy = PROJECT_ROOT / data_dir.rel
        target = PROJECT_ROOT / data_dir.dest_rel
        try:
            if not legacy.is_dir() or legacy.resolve() == target.resolve():
                continue
        except OSError:
            continue

        report["moved"].append(f"发现用户数据目录 {data_dir.rel}（按名称识别）")
        _move_contents(legacy, target, report)

        try:
            if legacy.is_dir() and not any(legacy.iterdir()):
                legacy.rmdir()
                report["moved"].append(f"已删除空的旧目录 {legacy}")
            elif legacy.is_dir():
                report["legacy_left"].append(
                    f"{legacy}（目标中已存在同名项，未覆盖）"
                )
        except OSError as exc:
            report["errors"].append(f"清理旧目录失败 {legacy}: {exc}")

    return report


def format_report(report: Dict[str, Any]) -> str:
    """把迁移报告整理成便于打印的文本。"""
    lines = [f"数据目录: {report['data_root']}"]
    for key, title in (
        ("created", "新建目录"),
        ("moved", "迁移"),
        ("skipped", "跳过（保留已有）"),
        ("errors", "错误"),
        ("legacy_left", "旧目录仍留有内容"),
    ):
        items = report.get(key) or []
        if items:
            lines.append(f"  {title} ({len(items)}):")
            lines.extend(f"    - {item}" for item in items[:20])
    if len(lines) == 1:
        lines.append("  无需迁移，布局已就绪")
    return "\n".join(lines)
