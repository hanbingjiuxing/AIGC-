"""AIGC 社信息系统 —— 更新模块。

对外入口：
    from updater import get_service
    service = get_service()
    service.start_check()      # 后台异步检查
    service.start_install()    # 后台异步安装

命令行：
    cd backend && python -m updater status|check|preview|update

本包采用惰性导入：`from updater.paths import ...` 这类轻量引用不会连带
加载 requests / 安装器等重型依赖（config.py 就依赖这一点）。
"""

from typing import Any

__all__ = [
    "get_service",
    "UpdateService",
    "load_config",
    "install_from_zip",
    "InstallError",
    "compare",
    "is_newer",
    "local_version_string",
    "read_local_version",
    "PROJECT_ROOT",
    "BACKEND_DIR",
    "VERSION_FILE",
    "DATA_ROOT",
    "ensure_layout",
]


def __getattr__(name: str) -> Any:  # PEP 562：按需导入
    if name in ("get_service", "UpdateService"):
        from . import service

        return {
            "get_service": service.get_service,
            "UpdateService": service.UpdateService,
        }[name]
    if name == "load_config":
        from .settings import load_config

        return load_config
    if name in ("install_from_zip", "InstallError"):
        from . import installer

        return getattr(installer, name)
    if name == "ensure_layout":
        from .datalayout import ensure_layout

        return ensure_layout
    if name in ("compare", "is_newer", "local_version_string", "read_local_version"):
        from . import version

        return getattr(version, name)
    if name in ("PROJECT_ROOT", "BACKEND_DIR", "VERSION_FILE", "DATA_ROOT"):
        from . import paths

        return getattr(paths, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
