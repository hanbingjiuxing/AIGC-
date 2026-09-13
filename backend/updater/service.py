"""更新服务编排层：状态机 + 后台线程。

设计目标（对应旧实现的问题）：
  * 启动时只在后台异步检查，绝不阻塞 app.run()，也绝不自动覆盖源码；
  * 安装必须由管理员显式确认（除非显式打开 auto_install）；
  * 所有耗时操作都在守护线程里跑，并通过 status() 暴露进度。
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import installer
from .paths import PROJECT_ROOT, STATE_DIR, VERSION_FILE
from .settings import load_config, public_config
from .sources import (
    GitSource,
    ReleaseSource,
    SourceUnavailable,
    UpdateInfo,
    build_sources,
)

# 状态取值
IDLE = "idle"
CHECKING = "checking"
UP_TO_DATE = "up_to_date"
UPDATE_AVAILABLE = "update_available"
BLOCKED = "blocked"
DOWNLOADING = "downloading"
INSTALLING = "installing"
INSTALLED = "installed"
ERROR = "error"

BUSY_STATES = {CHECKING, DOWNLOADING, INSTALLING}


class UpdateService:
    """单例更新服务。"""

    def __init__(self, cfg: Optional[Dict[str, Any]] = None):
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._loop_thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._last_log_at = 0.0

        self.cfg: Dict[str, Any] = cfg if cfg is not None else load_config()
        self.state: str = IDLE
        self.message: str = "尚未检查更新"
        self.progress: int = 0
        self.info: Optional[UpdateInfo] = None
        self.report: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.last_check_at: Optional[str] = None
        self.source_notes: List[str] = []
        self.restart_required: bool = False
        self.logs: deque = deque(maxlen=300)
        self._data_cache: Optional[Dict[str, Any]] = None
        self._data_cache_at: float = 0.0

    # -- 日志 --------------------------------------------------------------- #

    def log(self, message: str, throttle_seconds: float = 0.0) -> None:
        now = time.time()
        if throttle_seconds and now - self._last_log_at < throttle_seconds:
            return
        self._last_log_at = now
        stamp = datetime.now().strftime("%H:%M:%S")
        with self._lock:
            self.logs.append(f"[{stamp}] {message}")
        print(f"[更新] {message}", flush=True)

    # -- 只读视图 ----------------------------------------------------------- #

    def status(self) -> Dict[str, Any]:
        with self._lock:
            info = self.info.to_dict() if self.info else None
            return {
                "state": self.state,
                "busy": self.state in BUSY_STATES,
                "message": self.message,
                "progress": self.progress,
                "current_version": (info or {}).get("current_version", ""),
                "remote_version": (info or {}).get("remote_version", ""),
                "update": info,
                "report": self.report,
                "error": self.error,
                "last_check_at": self.last_check_at,
                "restart_required": self.restart_required,
                "source_notes": list(self.source_notes),
                "data": self.data_summary(),
                "config": public_config(self.cfg),
                "paths": {
                    "project_root": str(PROJECT_ROOT),
                    "version_file": str(VERSION_FILE),
                },
                "logs": list(self.logs)[-80:],
            }

    def data_summary(self, ttl_seconds: float = 30.0) -> Dict[str, Any]:
        """受保护的用户数据概览（数据库、学生作品），带短缓存避免频繁扫盘。"""
        now = time.time()
        if self._data_cache is not None and now - self._data_cache_at < ttl_seconds:
            return self._data_cache
        try:
            from .dataguard import DataGuard

            cache = DataGuard(self.cfg).summarize()
        except Exception as exc:  # noqa: BLE001
            cache = {"enabled": False, "error": str(exc)}
        with self._lock:
            self._data_cache = cache
            self._data_cache_at = now
        return cache

    # -- 检查 --------------------------------------------------------------- #

    def start_check(self, source_name: Optional[str] = None) -> bool:
        with self._lock:
            if self.state in BUSY_STATES:
                return False
            self.state = CHECKING
            self.message = "正在检查更新…"
            self.progress = 0
            self.error = None
            self.report = None
        self._spawn(self._check_worker, source_name)
        return True

    def _resolve_sources(self, source_name: Optional[str]) -> List[Any]:
        cfg = dict(self.cfg)
        if source_name:
            cfg["source"] = source_name
        sources, notes = build_sources(cfg, self.log)
        self.source_notes = notes
        return sources

    def _check_worker(self, source_name: Optional[str]) -> None:
        try:
            sources = self._resolve_sources(source_name)
            if not sources:
                raise SourceUnavailable("没有可用的更新来源；" + "；".join(self.source_notes))

            errors: List[str] = []
            info: Optional[UpdateInfo] = None
            for source in sources:
                try:
                    info = source.check()
                    break
                except SourceUnavailable as exc:
                    errors.append(f"{source.label}: {exc}")
                    self.log(f"{source.label} 检查失败：{exc}")
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{source.label}: {exc}")
                    self.log(f"{source.label} 检查异常：{exc}")

            if info is None:
                raise SourceUnavailable("；".join(errors) or "所有更新来源均不可用")

            with self._lock:
                self.info = info
                self.last_check_at = datetime.now().isoformat(timespec="seconds")

                if info.blocked:
                    self.state = BLOCKED
                    self.message = info.blocked_reason or "更新被阻止"
                elif info.available:
                    self.state = UPDATE_AVAILABLE
                    self.message = f"发现新版本 {info.remote_version}（当前 {info.current_version}）"
                else:
                    self.state = UP_TO_DATE
                    self.message = f"当前已是最新版本（{info.current_version}）"

                should_auto = (
                    self.cfg.get("auto_install")
                    and info.available
                    and not info.blocked
                )
            self.log(self.message)

            if should_auto:
                self.log("auto_install 已开启，开始自动安装")
                self.start_install()

        except Exception as exc:  # noqa: BLE001
            with self._lock:
                self.state = ERROR
                self.error = str(exc)
                self.message = f"检查更新失败：{exc}"
            self.log(self.message)

    # -- 安装 --------------------------------------------------------------- #

    def start_install(self, dry_run: bool = False) -> bool:
        with self._lock:
            if self.state in BUSY_STATES:
                return False
            if self.info is None or not self.info.available:
                self.state = ERROR
                self.error = "当前没有可安装的更新，请先检查更新"
                self.message = self.error
                return False
            if self.info.blocked and not dry_run:
                self.state = BLOCKED
                self.message = self.info.blocked_reason or "更新被阻止"
                return False
            self.state = INSTALLING if self.info.source == "git" else DOWNLOADING
            self.message = "正在准备更新…"
            self.progress = 0
            self.error = None
        self._spawn(self._install_worker, dry_run)
        return True

    def _progress(self, current: int, total: int, text: str) -> None:
        with self._lock:
            self.progress = max(0, min(100, int(current)))
            self.message = text
        self.log(text, throttle_seconds=1.5)

    def _install_worker(self, dry_run: bool) -> None:
        info = self.info
        try:
            if info is None:
                raise RuntimeError("没有可安装的更新信息")
            source = self._source_for(info)

            if info.source == "release":
                with self._lock:
                    self.state = DOWNLOADING
                    self.message = "正在下载更新包…"
            else:
                with self._lock:
                    self.state = INSTALLING
                    self.message = "正在应用 git 更新…"

            report = source.apply(info, progress=self._progress, dry_run=dry_run)
            payload = report.to_dict()

            with self._lock:
                self.report = payload
            for note in report.notes:
                self.log(note)

            if not report.success:
                raise RuntimeError("；".join(report.errors) or "安装失败")

            with self._lock:
                if dry_run:
                    self.state = UPDATE_AVAILABLE
                    self.message = f"预演完成：将写入 {len(report.written)} 个文件（未修改任何文件）"
                else:
                    self.state = INSTALLED
                    self.restart_required = True
                    self.message = (
                        f"更新完成：写入 {len(report.written)} 个文件，"
                        f"保留 {len(report.preserved)} 个受保护文件；请重启后端服务以生效"
                    )
            self.log(self.message)

        except Exception as exc:  # noqa: BLE001
            with self._lock:
                self.state = ERROR
                self.error = str(exc)
                self.message = f"更新失败：{exc}"
            self.log(self.message)

    def _source_for(self, info: UpdateInfo):
        if info.source == "git":
            return GitSource(self.cfg, self.log)
        return ReleaseSource(self.cfg, self.log)

    # -- 预览 --------------------------------------------------------------- #

    def preview(self) -> Dict[str, Any]:
        """预览将要变更的文件列表，绝不修改任何文件。"""
        info = self.info
        if info is None or not info.available:
            return {"available": False, "message": "请先检查更新"}

        try:
            if info.source == "git":
                source = GitSource(self.cfg, self.log)
                diff = source._run_ok([
                    "diff", "--name-only", "HEAD",
                    f"{source.remote}/{source.branch}",
                ])
                files = [line for line in diff.splitlines() if line.strip()]
                return {
                    "available": True,
                    "source": "git",
                    "file_count": len(files),
                    "files": files[:500],
                    "message": f"将有 {len(files)} 个文件变更（git 合并）",
                }

            source = ReleaseSource(self.cfg, self.log)
            name = (info.payload or {}).get("name")
            cached = STATE_DIR / name if name else None
            if cached is None or not cached.exists():
                return {
                    "available": True,
                    "source": "release",
                    "file_count": None,
                    "files": [],
                    "message": "更新包尚未下载，安装时将先下载再预览实际写入项",
                }

            plan = installer.build_plan(cached, self.cfg, source="release")
            summary = plan.summary()
            summary["available"] = True
            summary["message"] = f"将有 {summary['counts'].get('write', 0)} 个文件被写入"
            return summary

        except Exception as exc:  # noqa: BLE001
            return {"available": False, "message": f"预览失败：{exc}"}

    # -- 重启 --------------------------------------------------------------- #

    def restart(self) -> Dict[str, Any]:
        if not self.cfg.get("allow_restart"):
            return {"ok": False, "message": "配置未开启 allow_restart；请手动重启后端服务（如 run_system.bat）"}
        try:
            if hasattr(sys, "orig_argv") and sys.orig_argv:
                argv = list(sys.orig_argv)
            else:
                argv = [sys.executable] + list(sys.argv)
            flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0) if sys.platform == "win32" else 0
            subprocess.Popen(argv, cwd=str(PROJECT_ROOT), creationflags=flags)
            self.log(f"已启动新进程: {' '.join(argv)}")
            threading.Timer(1.0, lambda: __import__("os")._exit(0)).start()
            return {"ok": True, "message": "正在重启…"}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "message": f"重启失败：{exc}"}

    # -- 后台线程调度 ------------------------------------------------------- #

    def _spawn(self, target, *args) -> None:
        thread = threading.Thread(target=target, args=args, daemon=True, name=f"updater-{target.__name__}")
        with self._lock:
            self._thread = thread
        thread.start()

    def start_startup_check(self) -> bool:
        """启动时异步检查（不阻塞启动、不自动安装）。"""
        if not self.cfg.get("enabled") or not self.cfg.get("check_on_startup"):
            self.log("已跳过启动时检查（配置关闭）")
            return False
        delay = float(self.cfg.get("startup_delay_seconds", 8) or 0)

        def _runner() -> None:
            if self._stop.wait(delay):
                return
            self.start_check()

        self._spawn(_runner)
        self.log(f"已安排启动后台检查（{delay:.0f}s 后执行，不阻塞服务启动）")
        return True

    def start_periodic_check(self) -> bool:
        hours = float(self.cfg.get("check_interval_hours", 0) or 0)
        if hours <= 0 or not self.cfg.get("enabled"):
            return False

        def _loop() -> None:
            while not self._stop.wait(hours * 3600):
                self.start_check()

        self._loop_thread = threading.Thread(target=_loop, daemon=True, name="updater-periodic")
        self._loop_thread.start()
        self.log(f"已启动周期检查，每 {hours:g} 小时一次")
        return True

    def shutdown(self) -> None:
        self._stop.set()


_service: Optional[UpdateService] = None
_service_lock = threading.Lock()


def get_service() -> UpdateService:
    """获取（并惰性创建）全局更新服务单例。"""
    global _service
    with _service_lock:
        if _service is None:
            _service = UpdateService()
        return _service
