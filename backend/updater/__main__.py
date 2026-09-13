"""更新器命令行入口。

用法（在 backend 目录下执行）：
    python -m updater status            # 查看配置、路径、当前版本与来源可用性
    python -m updater layout            # 查看/迁移统一数据目录（data/）
    python -m updater check             # 同步检查更新
    python -m updater preview           # 预览将要变更的文件（不修改任何文件）
    python -m updater update --dry-run  # 预演一次完整更新流程（不修改任何文件）
    python -m updater update            # 实际安装更新（需要 --yes 或交互确认）
"""

from __future__ import annotations

import argparse
import sys
import time

try:  # Windows 控制台默认可能是 GBK
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

from .paths import BACKEND_DIR, PROJECT_ROOT, VERSION_FILE
from .service import BUSY_STATES, get_service
from .settings import load_config
from .version import local_version_string


def _wait(service, timeout: float = 900.0) -> None:
    started = time.time()
    while service.status()["busy"]:
        if time.time() - started > timeout:
            print("等待超时", file=sys.stderr)
            return
        time.sleep(0.3)


def cmd_status(_args) -> int:
    cfg = load_config()
    print("=" * 66)
    print("AIGC 社信息系统 · 更新模块状态")
    print("=" * 66)
    print(f"项目根目录      : {PROJECT_ROOT}")
    print(f"后端目录        : {BACKEND_DIR}")
    print(f"版本文件        : {VERSION_FILE}  (存在: {VERSION_FILE.exists()})")
    print(f"本地版本        : {local_version_string()}")
    print(f"当前工作目录    : {__import__('os').getcwd()}")
    print()
    print(f"启用更新        : {cfg['enabled']}")
    print(f"启动时检查      : {cfg['check_on_startup']}（延迟 {cfg['startup_delay_seconds']}s，异步）")
    print(f"自动安装        : {cfg['auto_install']}")
    print(f"周期检查        : {cfg['check_interval_hours']} 小时")
    print(f"来源模式        : {cfg['source']}（git 优先，失败回退 Release）")
    print(f"GitHub 仓库     : {cfg['release']['repo']}")
    print(f"GitHub 令牌     : {'已通过环境变量配置' if cfg.get('_token') else '未配置（公开仓库无需令牌）'}")
    print(f"代理            : {cfg['proxy']['enabled']} {cfg['proxy']['url'] or ''}")
    print(f"允许 API 重启   : {cfg['allow_restart']}")
    print()

    from .sources import build_sources

    sources, notes = build_sources(cfg, lambda m: None)
    print("可用更新来源:")
    for source in sources:
        print(f"  - {source.label}")
    for note in notes:
        print(f"  ! {note}")
    for warning in cfg.get("_warnings", []):
        print(f"  ! {warning}")
    return 0


def cmd_layout(_args) -> int:
    """创建统一数据目录，并把旧位置的数据迁移过来（幂等，绝不覆盖）。"""
    from .datalayout import ensure_layout, format_report

    print("=" * 66)
    print("统一数据目录布局")
    print("=" * 66)
    print(format_report(ensure_layout()))
    print()
    print("升级维护时只需保留 data/ 目录，其余内容均可整体覆盖。")
    return 0


def cmd_check(_args) -> int:
    service = get_service()
    service.start_check()
    _wait(service)
    status = service.status()
    info = status.get("update") or {}
    print()
    print(f"状态          : {status['state']}")
    print(f"说明          : {status['message']}")
    if info:
        print(f"当前版本      : {info.get('current_version')}")
        print(f"远端版本      : {info.get('remote_version')}")
        print(f"来源          : {info.get('source')}")
        if info.get("blocked"):
            print(f"被阻止        : {info.get('blocked_reason')}")
        dirty = (info.get("details") or {}).get("dirty_files") or []
        if dirty:
            print(f"本地未提交改动({len(dirty)}):")
            for path in dirty[:20]:
                print(f"    {path}")
        for key in ("remote_url", "local_head", "remote_head", "commits_behind", "commits_ahead"):
            value = (info.get("details") or {}).get(key)
            if value is not None:
                print(f"{key:<14}: {value}")
    if info.get("notes"):
        print("-" * 66)
        print(info["notes"][:2000])
    return 0 if status["state"] != "error" else 1


def cmd_preview(_args) -> int:
    service = get_service()
    service.start_check()
    _wait(service)
    preview = service.preview()
    print()
    print(preview.get("message"))
    for path in (preview.get("files") or [])[:200]:
        print(f"  {path}")
    return 0


def cmd_update(args) -> int:
    service = get_service()
    service.start_check()
    _wait(service)
    status = service.status()
    if not (status.get("update") or {}).get("available"):
        print(f"无需更新：{status['message']}")
        return 0

    if not args.dry_run and not args.yes:
        print(f"即将安装更新 {status['remote_version']}（来源 {status['update']['source']}）")
        answer = input("确认继续？输入 yes 回车：").strip().lower()
        if answer not in ("yes", "y"):
            print("已取消")
            return 1

    service.start_install(dry_run=args.dry_run)
    _wait(service)
    status = service.status()
    report = status.get("report") or {}
    print()
    print(f"结果          : {status['state']}")
    print(f"说明          : {status['message']}")
    if report:
        print(f"写入文件      : {report.get('written_count')}")
        print(f"未变化        : {report.get('unchanged_count')}")
        print(f"受保护保留    : {report.get('preserved_count')}")
        print(f"跳过          : {report.get('skipped_count')}")
        print(f"备份目录      : {report.get('backup_dir')}")
        print(f"已回滚        : {report.get('rolled_back')}")
        for note in report.get("notes") or []:
            print(f"  * {note}")
        for err in report.get("errors") or []:
            print(f"  ! {err}")
    return 0 if status["state"] == "installed" else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m updater", description="AIGC 社信息系统更新工具")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="显示配置、路径与来源可用性").set_defaults(func=cmd_status)
    sub.add_parser("layout", help="创建/迁移统一数据目录 data/").set_defaults(func=cmd_layout)
    sub.add_parser("check", help="同步检查更新").set_defaults(func=cmd_check)
    sub.add_parser("preview", help="预览将要变更的文件（不修改任何文件）").set_defaults(func=cmd_preview)

    update = sub.add_parser("update", help="安装更新")
    update.add_argument("--dry-run", action="store_true", help="只预演，不修改任何文件")
    update.add_argument("--yes", action="store_true", help="跳过交互确认")
    update.set_defaults(func=cmd_update)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
