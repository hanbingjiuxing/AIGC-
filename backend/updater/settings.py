"""更新器配置：内置默认值 <- updater/config.json <- 环境变量覆盖。

安全约定：**GitHub 令牌只能来自环境变量** AIGC_UPDATE_GITHUB_TOKEN，
不会被写入配置文件、日志或 API 响应。旧版把 PAT 硬编码在源码和 config.json 里，
一旦提交就等同于公开泄露。
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .paths import BACKUP_DIR, CONFIG_FILE, PROJECT_ROOT, STATE_DIR

TOKEN_ENV = "AIGC_UPDATE_GITHUB_TOKEN"

DEFAULTS: Dict[str, Any] = {
    "enabled": True,
    # 启动时后台异步检查（不阻塞启动、不自动安装）
    "check_on_startup": True,
    "startup_delay_seconds": 8,
    # 仅提示，不自动安装；安装必须由管理员在界面确认
    "auto_install": False,
    # 0 表示不做周期性检查（只保留启动检查与手动检查）
    "check_interval_hours": 0,
    # auto | git | release
    "source": "auto",

    "git": {
        "remote": "origin",
        "branch": "main",
        "#allow_dirty": "工作区有未提交改动时是否仍允许更新（false = 拒绝并列出文件）",
        "allow_dirty": False,
        "ff_only": True,
        "timeout_seconds": 180,
    },

    "release": {
        "repo": "hanbingjiuxing/AIGC-",
        "api_base": "https://api.github.com",
        "asset_pattern": r"\.zip$",
        "verify_ssl": True,
        "timeout_seconds": 60,
        "max_retries": 3,
        "retry_delay_seconds": 5,
        "chunk_size_bytes": 1048576,
    },

    "proxy": {
        "enabled": False,
        "url": "",
    },

    # 用户数据（"非功能"信息）：数据库、学生作品等，更新时永不丢失
    "data": {
        "enabled": True,
        # 统一的数据根目录：数据库、学生作品、更新缓存与更新前备份都在这里。
        # 升级维护时只需要保留这一个目录，其余内容都是可整体覆盖的代码。
        "paths": [
            "data",
        ],
        # 需要保护的数据文件夹名 -> 新版统一位置（一般不需要修改）
        "dir_names": {},
        # 自动发现项目内任意位置的 SQLite 文件并纳入保护
        "auto_discover_databases": True,
        "database_globs": ["*.db", "*.sqlite", "*.sqlite3", "*.db3"],
        # 更新前快照被 git 跟踪的数据文件，万一被合并改写可立即还原
        "snapshot_at_risk_files": True,
        # 合并前对受跟踪的数据文件设置 skip-worktree，让 git 不去改它们
        "protect_tracked_git_paths": True,
        # 更新后校验数据库是否仍然存在且非空
        "verify_after_update": True,
    },

    "install": {
        "backup_before_update": True,
        "max_backups": 5,
        # 相对项目根；这些路径下的内容永远不会被更新包覆盖
        "preserve_dirs": [
            "data",
            # 旧版位置：保留在清单里，防止旧更新包把这两个目录重新写出来
            "backend/instance",
            "backend/uploads",
            "frontend/node_modules",
            "frontend/dist",
        ],
        "preserve_files": [
            "backend/version.json",
            "backend/updater/config.json",
            ".env",
        ],
        "skip_dirs": [
            ".git", ".github", "node_modules", "__pycache__",
            ".venv", "venv", "env", "dist", "build", ".pytest_cache", ".idea", ".vscode",
        ],
        "skip_globs": [
            "*.pyc", "*.pyo", "*.pyd", "*.db", "*.sqlite", "*.sqlite3", "*.log", "*.tmp",
        ],
        # 只允许这些后缀被写入（防止更新包夹带可执行文件）
        "allow_extensions": [
            ".py", ".json", ".md", ".txt", ".html", ".js", ".jsx", ".ts", ".tsx",
            ".css", ".scss", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".ico",
            ".bat", ".ps1", ".sh", ".yml", ".yaml", ".toml", ".cfg", ".ini",
            ".pdf", ".cjs", ".mjs", ".map", ".woff", ".woff2", ".ttf",
        ],
    },

    # 是否允许通过 API 触发进程自我重启（默认关闭；一般重启 run_system.bat 即可）
    "allow_restart": False,
}

_ENV_MAP = {
    "AIGC_UPDATE_ENABLED": ("enabled", bool),
    "AIGC_UPDATE_CHECK_ON_STARTUP": ("check_on_startup", bool),
    "AIGC_UPDATE_AUTO_INSTALL": ("auto_install", bool),
    "AIGC_UPDATE_SOURCE": ("source", str),
    "AIGC_UPDATE_CHECK_INTERVAL_HOURS": ("check_interval_hours", float),
    "AIGC_UPDATE_ALLOW_RESTART": ("allow_restart", bool),
    "AIGC_UPDATE_GITHUB_REPO": ("release.repo", str),
    "AIGC_UPDATE_PROXY": ("proxy.url", str),
}


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on", "y")


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in (override or {}).items():
        if key.startswith("#"):
            continue
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _set_path(cfg: Dict[str, Any], dotted: str, value: Any) -> None:
    node = cfg
    parts = dotted.split(".")
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


def _apply_env(cfg: Dict[str, Any], warnings: List[str]) -> None:
    for env_name, (dotted, caster) in _ENV_MAP.items():
        raw = os.environ.get(env_name)
        if raw is None or raw == "":
            continue
        try:
            if caster is bool:
                _set_path(cfg, dotted, _as_bool(raw))
            else:
                _set_path(cfg, dotted, caster(raw))
        except (TypeError, ValueError):
            warnings.append(f"环境变量 {env_name} 取值非法，已忽略: {raw!r}")

    # 代理也允许用标准的 HTTPS_PROXY/HTTP_PROXY
    if not cfg["proxy"].get("url"):
        for name in ("AIGC_UPDATE_PROXY", "HTTPS_PROXY", "https_proxy"):
            raw = os.environ.get(name)
            if raw:
                _set_path(cfg, "proxy.url", raw)
                _set_path(cfg, "proxy.enabled", True)
                break


def load_config(path: Optional[Path] = None) -> Dict[str, Any]:
    """加载并规范化配置。返回的 dict 额外含 _warnings 与 _token。"""
    cfg = copy.deepcopy(DEFAULTS)
    warnings: List[str] = []

    config_path = Path(path) if path else CONFIG_FILE
    if config_path.exists():
        try:
            raw = json.loads(config_path.read_text(encoding="utf-8-sig"))
            if isinstance(raw, dict):
                _deep_merge(cfg, raw)
                if "github_token" in raw:
                    warnings.append(
                        "config.json 中仍存在 github_token 字段，已忽略；"
                        f"请改用环境变量 {TOKEN_ENV}，并立即吊销该已泄露的令牌。"
                    )
            else:
                warnings.append(f"配置文件格式不是对象，已忽略: {config_path}")
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
            warnings.append(f"读取配置文件失败，使用默认配置: {exc}")
    else:
        warnings.append(f"未找到配置文件，使用默认配置: {config_path}")

    _apply_env(cfg, warnings)

    # 令牌只从环境变量读取
    cfg["_token"] = os.environ.get(TOKEN_ENV) or None

    # 解析派生路径
    cfg["_config_path"] = str(config_path)
    cfg["_state_dir"] = STATE_DIR
    cfg["_backup_dir"] = BACKUP_DIR
    cfg["_project_root"] = PROJECT_ROOT
    cfg["_warnings"] = warnings

    if cfg.get("source") not in ("auto", "git", "release"):
        warnings.append(f"source 取值非法（{cfg.get('source')!r}），已回退为 auto")
        cfg["source"] = "auto"

    return cfg


def public_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """可安全返回给前端的配置视图（剔除令牌与内部字段）。"""
    safe = {k: v for k, v in cfg.items() if not k.startswith("_")}
    safe["token_configured"] = bool(cfg.get("_token"))
    return safe
