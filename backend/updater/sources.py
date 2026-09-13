"""更新来源：GitSource（git pull 优先）与 ReleaseSource（GitHub Release ZIP 回退）。

GitSource 的安全前提：工作区必须干净（无未提交改动），否则拒绝更新并列出文件，
避免 git pull 覆盖或丢失本地改动。可用 git.allow_dirty 显式放开（不建议）。
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import installer
from .dataguard import DataGuard, is_data_path
from .installer import InstallError, InstallReport
from .paths import BACKUP_DIR, PROJECT_ROOT, STATE_DIR
from .version import is_newer, local_version_string, normalize

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

ProgressFn = Optional[Callable[[int, int, str], None]]
LogFn = Callable[[str], None]

# 版本管理之外、由更新器自身或运行期产生的路径，不应算作"本地改动"
DEFAULT_DIRTY_IGNORES = [
    "backend/version.json",
    # 统一数据根：全部运行期与用户数据
    "data/*",
    # 旧版位置（迁移完成前的残留，保留以防误判）
    "backend/instance/*",
    "backend/uploads/*",
    "backend/updates/*",
    "backend/backup/*",
    "frontend/node_modules/*",
    "frontend/dist/*",
    "*.pyc",
    "*.pyo",
    "__pycache__/*",
    "*/__pycache__/*",
]

# 由更新器运行期写入、以仓库内容为准的文件（合并前会被还原）
DEFAULT_MANAGED_PATHS = ["backend/version.json"]

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


class SourceUnavailable(Exception):
    """该更新来源在当前环境下不可用。"""


@dataclass
class UpdateInfo:
    source: str
    current_version: str
    remote_version: str
    available: bool = False
    blocked: bool = False
    blocked_reason: str = ""
    notes: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "current_version": self.current_version,
            "remote_version": self.remote_version,
            "available": self.available,
            "blocked": self.blocked,
            "blocked_reason": self.blocked_reason,
            "notes": self.notes,
            "details": self.details,
        }


# --------------------------------------------------------------------------- #
# Git 后端
# --------------------------------------------------------------------------- #

class GitSource:
    name = "git"
    label = "git pull"

    def __init__(self, cfg: Dict[str, Any], log: LogFn):
        self.cfg = cfg
        self.log = log
        self.git_cfg = cfg.get("git", {}) or {}
        self.remote = self.git_cfg.get("remote", "origin")
        self.branch = self.git_cfg.get("branch", "main")
        self.timeout = int(self.git_cfg.get("timeout_seconds", 180))

    # -- 基础设施 ----------------------------------------------------------- #

    def probe(self) -> Tuple[bool, str]:
        if not shutil.which("git"):
            return False, "未安装 git"
        if not (PROJECT_ROOT / ".git").exists():
            return False, "项目目录不是 git 仓库（缺少 .git）"
        return True, ""

    def _run(self, args: List[str], timeout: Optional[int] = None) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        env.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")
        env["LC_ALL"] = "C"
        try:
            return subprocess.run(
                ["git", "-C", str(PROJECT_ROOT), *args],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout or self.timeout,
                env=env,
                creationflags=_NO_WINDOW,
            )
        except FileNotFoundError as exc:
            raise SourceUnavailable("未安装 git") from exc
        except subprocess.TimeoutExpired as exc:
            raise SourceUnavailable(f"git 命令超时（{timeout or self.timeout}s）: git {' '.join(args)}") from exc

    def _run_ok(self, args: List[str], timeout: Optional[int] = None) -> str:
        proc = self._run(args, timeout=timeout)
        if proc.returncode != 0:
            raise SourceUnavailable(
                f"git {' '.join(args)} 失败: {(proc.stderr or proc.stdout or '').strip()[:400]}"
            )
        return (proc.stdout or "").strip()

    # -- 脏工作区检测 ------------------------------------------------------- #

    @staticmethod
    def _parse_porcelain_z(raw: str) -> List[str]:
        paths: List[str] = []
        entries = raw.split("\0")
        idx = 0
        while idx < len(entries):
            entry = entries[idx]
            if not entry:
                idx += 1
                continue
            if len(entry) < 4:
                idx += 1
                continue
            status = entry[:2]
            paths.append(entry[3:])
            idx += 2 if ("R" in status or "C" in status) else 1
        return paths

    def _dirty_files(self) -> List[str]:
        # 注意：绝不能对 -z 输出做 strip()。porcelain 的第一条记录形如
        # " M path\0"，开头的空格是状态位的一部分；strip 会把它吃掉，
        # 导致 entry[3:] 少切一个字符、路径被破坏、保护规则匹配失败。
        proc = self._run(["status", "--porcelain", "-z"])
        if proc.returncode != 0:
            raise SourceUnavailable(
                f"git status 失败: {(proc.stderr or '').strip()[:200]}"
            )
        raw = proc.stdout or ""
        if not raw:
            return []
        ignores = list(DEFAULT_DIRTY_IGNORES) + list(self.git_cfg.get("ignore_dirty_paths", []) or [])
        dirty = []
        for path in self._parse_porcelain_z(raw):
            posix = path.replace("\\", "/")
            if any(fnmatch.fnmatch(posix, pat) for pat in ignores):
                continue
            # 按名称识别：任何位置的 instance/uploads/*.db 都算用户数据，
            # 不应因为"看起来是本地改动"而阻止更新
            if is_data_path(posix, self.cfg):
                continue
            dirty.append(posix)
        return sorted(set(dirty))

    # -- 检查 --------------------------------------------------------------- #

    def check(self) -> UpdateInfo:
        ok, reason = self.probe()
        if not ok:
            raise SourceUnavailable(reason)

        current = local_version_string()
        remote_version = current
        details: Dict[str, Any] = {"remote": self.remote, "branch": self.branch}

        self.log(f"正在从 {self.remote}/{self.branch} 获取远端信息…")
        remote_url = self._run_ok(["remote", "get-url", self.remote])
        details["remote_url"] = remote_url

        local_head = self._run_ok(["rev-parse", "HEAD"])
        details["local_head"] = local_head[:12]

        self._run_ok(["fetch", "--prune", self.remote, self.branch])
        remote_head = self._run_ok(["rev-parse", f"{self.remote}/{self.branch}"])
        details["remote_head"] = remote_head[:12]

        # 远端声明的版本号（仓库内 backend/version.json）
        proc = self._run(["show", f"{self.remote}/{self.branch}:backend/version.json"])
        if proc.returncode == 0 and proc.stdout.strip():
            try:
                remote_version = normalize(json.loads(proc.stdout.lstrip("\ufeff")).get("version", current))
            except (json.JSONDecodeError, AttributeError):
                pass
        details["remote_version"] = remote_version

        # 注意顺序：git rev-list --left-right --count A...B 输出 "<A 独有> <B 独有>"，
        # 即 ahead 在前、behind 在后。写反会导致"远端有新提交"被误判为"本地领先远端"，
        # 从而永远不会更新。
        counts = self._run_ok(["rev-list", "--left-right", "--count", f"HEAD...{self.remote}/{self.branch}"])
        try:
            ahead, behind = (int(x) for x in counts.split())
        except ValueError:
            ahead = behind = 0
        details["commits_behind"] = behind
        details["commits_ahead"] = ahead

        commits_text = ""
        if behind:
            commits_text = self._run_ok(["log", "--oneline", "--no-decorate", "-n", "20", f"HEAD..{self.remote}/{self.branch}"])

        info = UpdateInfo(
            source=self.name,
            current_version=current,
            remote_version=remote_version,
            details=details,
        )

        if local_head == remote_head:
            info.available = False
            info.notes = "本地与远端代码完全一致"
            return info

        if behind == 0 and ahead > 0:
            info.available = False
            info.notes = f"本地领先远端 {ahead} 个提交，无需更新"
            return info

        dirty = self._dirty_files()
        details["dirty_files"] = dirty[:100]
        if dirty and not self.git_cfg.get("allow_dirty", False):
            info.available = True
            info.blocked = True
            info.blocked_reason = (
                f"检测到 {len(dirty)} 个未提交的本地改动，为避免丢失代码已拒绝自动更新。"
                "请先提交或暂存（git stash）后再更新。"
            )
            info.notes = commits_text
            return info

        info.available = True
        info.notes = commits_text or f"远端有 {behind} 个新提交"
        return info

    # -- 应用 --------------------------------------------------------------- #

    def apply(self, info: UpdateInfo, progress: ProgressFn = None) -> InstallReport:
        report = InstallReport(success=False, source=self.name)
        if info.blocked:
            report.errors.append(info.blocked_reason)
            return report

        old_head = self._run_ok(["rev-parse", "HEAD"])
        previous_version = local_version_string()

        data_cfg = self.cfg.get("data", {}) or {}
        guard = DataGuard(self.cfg, self.log)
        data_enabled = bool(data_cfg.get("enabled", True))
        db_before = guard.database_inventory() if data_enabled else {}

        # ---- 用户数据保护：只处理"本次合并真的会碰到"的数据文件 ---------- #
        # 本项目的 backend/instance/aigc_society.db 与 backend/uploads/* 是被 git
        # 跟踪的，直接合并会用仓库里的旧副本覆盖学生作品与用户数据。做法：
        #   1. 算出本次合并会改动的文件，挑出其中属于用户数据的部分；
        #   2. 快照这些文件的**当前本地内容**；
        #   3. 其中有本地改动的，临时换成仓库版本好让合并能进行；
        #   4. 合并后（成败都算）把本地内容放回去。
        # 未被本次合并触及的数据文件完全不会被读写，也就没有数据空窗期。
        remote_ref = f"{self.remote}/{self.branch}"
        data_touched: List[str] = []
        snapshot_dir: Optional[Path] = None

        if data_enabled:
            changed = [
                line.strip() for line in
                self._run(["diff", "--name-only", old_head, remote_ref]).stdout.splitlines()
                if line.strip()
            ]
            data_touched = guard.at_risk(changed)
            if data_touched:
                report.notes.append(
                    f"本次更新包含 {len(data_touched)} 个用户数据文件，将一律保持本地版本"
                )
                if data_cfg.get("snapshot_at_risk_files", True):
                    snapshot_dir = BACKUP_DIR / f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    copied = guard.snapshot(data_touched, snapshot_dir)
                    self.log(f"已快照 {len(copied)} 个用户数据文件 -> {snapshot_dir}")
                blocked = [p for p in data_touched if p in self._locally_modified()]
                if blocked and snapshot_dir:
                    self._run(["checkout", "--", *blocked])
                    self.log(f"临时还原 {len(blocked)} 个有本地改动的数据文件，以便合并能够进行")

        def _restore_local_data() -> None:
            """把用户数据恢复为更新前的内容（必须有快照）。"""
            if not (data_enabled and data_touched and snapshot_dir):
                return
            restored = guard.restore(snapshot_dir, data_touched)
            if restored:
                self.log(f"已还原 {len(restored)} 个用户数据文件到更新前的内容")
                report.notes.append(
                    f"已还原 {len(restored)} 个用户数据文件，本地数据未被仓库副本覆盖"
                )

        # version.json 等由更新器自身写入的文件可能带本地改动，
        # git 会因此拒绝合并；这些文件以仓库内容为准，先还原再合并。
        managed = list(self.git_cfg.get("managed_paths", DEFAULT_MANAGED_PATHS) or [])
        if managed:
            self._run(["checkout", "--", *managed])

        if progress:
            progress(10, 100, "正在合并远端改动…")

        if self.git_cfg.get("ff_only", True):
            merge_args = ["merge", "--ff-only", f"{self.remote}/{self.branch}"]
        else:
            merge_args = ["merge", "--no-edit", f"{self.remote}/{self.branch}"]

        proc = self._run(merge_args)
        if proc.returncode != 0:
            message = (proc.stderr or proc.stdout or "").strip()[:400]
            report.errors.append(f"git 合并失败: {message}")
            # 注意：这里绝不能用 git reset --hard —— 它会连同被跟踪的
            # 数据库与学生作品一起回退，反而造成数据丢失。改用 merge --abort。
            abort = self._run(["merge", "--abort"])
            if abort.returncode == 0:
                report.rolled_back = True
                report.notes.append("已中止合并，工作区保持更新前状态")
            else:
                report.notes.append("合并未产生改动，工作区保持原样")
            _restore_local_data()
            report.data = self._data_report(guard, db_before, data_touched, data_enabled)
            return report

        new_head = self._run_ok(["rev-parse", "HEAD"])
        if progress:
            progress(90, 100, "更新完成")

        report.success = True
        report.written = [
            line for line in
            self._run(["diff", "--name-only", old_head, new_head]).stdout.splitlines()
            if line.strip()
        ]
        report.notes.append(f"{old_head[:12]} -> {new_head[:12]}（共 {len(report.written)} 个文件变化）")

        if info.details.get("commits_behind"):
            report.notes.append(f"合并了 {info.details['commits_behind']} 个远端提交")

        # ---- 用户数据保护：把本地版本放回去 -------------------------------- #
        _restore_local_data()
        report.data = self._data_report(guard, db_before, data_touched, data_enabled)

        self._record_state(
            source=self.name,
            previous_version=previous_version,
            new_version=local_version_string(),
            local_head=new_head,
            previous_head=old_head,
            report=report,
        )
        return report

    def _locally_modified(self) -> set:
        """全部有本地改动的路径（不做忽略过滤）。"""
        proc = self._run(["status", "--porcelain", "-z"])
        if proc.returncode != 0:
            return set()
        return {p.replace("\\", "/") for p in self._parse_porcelain_z(proc.stdout or "")}

    @staticmethod
    def _data_report(
        guard: "DataGuard",
        db_before: Dict[str, Any],
        merged_touched: List[str],
        data_enabled: bool,
    ) -> Dict[str, Any]:
        """汇总用户数据保护结果，供界面与日志展示。"""
        if not data_enabled:
            return {"enabled": False}
        summary = guard.summarize()
        problems = guard.health_check(db_before)
        return {
            "enabled": True,
            "protected_paths": summary["protected_paths"],
            "protected_files": summary["file_count"],
            "total_mb": summary["total_mb"],
            "database_files": summary["database_files"],
            "merge_touched": merged_touched,
            "problems": problems,
        }

    @staticmethod
    def _record_state(**payload: Any) -> None:
        record_runtime_state(payload)


# --------------------------------------------------------------------------- #
# GitHub Release 后端
# --------------------------------------------------------------------------- #

class ReleaseSource:
    name = "release"
    label = "GitHub Release"

    def __init__(self, cfg: Dict[str, Any], log: LogFn):
        self.cfg = cfg
        self.log = log
        self.rel_cfg = cfg.get("release", {}) or {}
        self.repo = self.rel_cfg.get("repo", "")
        self.api_base = (self.rel_cfg.get("api_base") or "https://api.github.com").rstrip("/")
        self.timeout = int(self.rel_cfg.get("timeout_seconds", 60))
        self.retries = int(self.rel_cfg.get("max_retries", 3))
        self.retry_delay = float(self.rel_cfg.get("retry_delay_seconds", 5))
        self.chunk = int(self.rel_cfg.get("chunk_size_bytes", 1024 * 1024))
        self.verify_ssl = bool(self.rel_cfg.get("verify_ssl", True))

    # -- 基础设施 ----------------------------------------------------------- #

    def probe(self) -> Tuple[bool, str]:
        if requests is None:
            return False, "未安装 requests 库"
        if not self.repo or "/" not in self.repo:
            return False, "未配置 release.repo"
        return True, ""

    def _proxies(self) -> Dict[str, str]:
        prox_cfg = self.cfg.get("proxy", {}) or {}
        if not prox_cfg.get("enabled"):
            return {}
        url = prox_cfg.get("url") or ""
        if not url:
            return {}
        return {"http": url, "https": url}

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "AIGC-Society-Updater",
        }
        token = self.cfg.get("_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    # -- 检查 --------------------------------------------------------------- #

    def check(self) -> UpdateInfo:
        ok, reason = self.probe()
        if not ok:
            raise SourceUnavailable(reason)

        url = f"{self.api_base}/repos/{self.repo}/releases/latest"
        current = local_version_string()
        proxies = self._proxies()
        if proxies:
            self.log(f"使用代理: {proxies['https']}")

        last_error = ""
        for attempt in range(1, self.retries + 1):
            self.log(f"正在检查 GitHub Release… ({attempt}/{self.retries})")
            try:
                response = requests.get(
                    url, headers=self._headers(), timeout=self.timeout,
                    verify=self.verify_ssl, proxies=proxies,
                )
                if response.status_code == 404:
                    raise SourceUnavailable(f"仓库 {self.repo} 没有已发布的 Release")
                response.raise_for_status()
                data = response.json()
                return self._build_info(data, current)
            except SourceUnavailable:
                raise
            except requests.exceptions.RequestException as exc:
                last_error = str(exc)
                self.log(f"请求失败: {last_error}")
                if attempt < self.retries:
                    time.sleep(self.retry_delay)
            except (json.JSONDecodeError, ValueError) as exc:
                raise SourceUnavailable(f"GitHub 返回内容无法解析: {exc}") from exc

        raise SourceUnavailable(f"无法连接 GitHub API: {last_error}")

    def _build_info(self, data: Dict[str, Any], current: str) -> UpdateInfo:
        import re

        tag = normalize(data.get("tag_name") or data.get("name") or "")
        notes = (data.get("body") or "").strip()
        pattern = self.rel_cfg.get("asset_pattern") or r"\.zip$"

        asset = None
        for candidate in data.get("assets") or []:
            if re.search(pattern, candidate.get("name", "")):
                asset = candidate
                break

        details: Dict[str, Any] = {
            "tag": data.get("tag_name"),
            "html_url": data.get("html_url"),
            "published_at": data.get("published_at"),
            "asset_name": (asset or {}).get("name"),
            "asset_size": (asset or {}).get("size", 0),
        }

        payload: Dict[str, Any] = {}
        if asset:
            digest = (asset.get("digest") or "").strip()
            checksum = ""
            if digest.startswith("sha256:"):
                checksum = digest.split(":", 1)[1]
            payload = {
                "name": asset.get("name"),
                "url": asset.get("browser_download_url"),
                "size": int(asset.get("size") or 0),
                "checksum": checksum,
                "checksum_type": "sha256",
            }
            details["checksum_available"] = bool(checksum)

        return UpdateInfo(
            source=self.name,
            current_version=current,
            remote_version=tag,
            available=is_newer(tag, current) and bool(asset),
            blocked=not asset,
            blocked_reason="" if asset else f"Release {tag} 中没有匹配 {pattern} 的资产",
            notes=notes,
            details=details,
            payload=payload,
        )

    # -- 下载 --------------------------------------------------------------- #

    def download(self, info: UpdateInfo, progress: ProgressFn = None) -> Path:
        payload = info.payload or {}
        url = payload.get("url")
        if not url:
            raise InstallError("Release 缺少可下载的资产地址")

        STATE_DIR.mkdir(parents=True, exist_ok=True)
        name = payload.get("name") or Path(url).name or f"update_{info.remote_version}.zip"
        final = STATE_DIR / name
        part = final.with_name(final.name + ".part")
        expected_size = int(payload.get("size") or 0)
        checksum = (payload.get("checksum") or "").lower()
        proxies = self._proxies()

        if final.exists() and expected_size and final.stat().st_size == expected_size:
            if not checksum or installer._sha256_file(final) == checksum:
                self.log(f"已存在完整的更新包，跳过下载: {name}")
                return final
            self.log("已存在的更新包校验不通过，将重新下载")
            final.unlink(missing_ok=True)

        downloaded = part.stat().st_size if part.exists() else 0
        headers = {}
        if downloaded:
            headers["Range"] = f"bytes={downloaded}-"
            self.log(f"检测到已下载 {downloaded} 字节，尝试断点续传")

        last_error = ""
        for attempt in range(1, self.retries + 1):
            try:
                self.log(f"开始下载 {name}… ({attempt}/{self.retries})")
                response = requests.get(
                    url, headers=headers, stream=True, timeout=self.timeout,
                    verify=self.verify_ssl, proxies=proxies, allow_redirects=True,
                )
                response.raise_for_status()

                total = int(response.headers.get("content-length") or 0)
                if total and headers.get("Range"):
                    total += downloaded
                if not total:
                    total = expected_size

                mode = "ab" if downloaded and response.status_code == 206 else "wb"
                if mode == "wb":
                    downloaded = 0

                with part.open(mode) as fh:
                    started = time.time()
                    for chunk in response.iter_content(chunk_size=self.chunk):
                        if not chunk:
                            continue
                        fh.write(chunk)
                        downloaded += len(chunk)
                        elapsed = max(time.time() - started, 1e-6)
                        speed = downloaded / elapsed / 1024 / 1024
                        text = f"下载中 {downloaded / 1048576:.1f}MB / {total / 1048576:.1f}MB ({speed:.1f}MB/s)"
                        if progress:
                            progress(int(downloaded / total * 100) if total else 0, 100, text)
                        self.log(text)

                if expected_size and part.stat().st_size != expected_size:
                    raise InstallError(
                        f"下载大小不符: 期望 {expected_size} 字节，实际 {part.stat().st_size} 字节"
                    )
                if checksum:
                    actual = installer._sha256_file(part)
                    if actual != checksum:
                        raise InstallError(f"校验失败: 期望 {checksum[:16]}…，实际 {actual[:16]}…")

                os.replace(part, final)
                self.log("更新包下载完成并通过校验")
                return final
            except (requests.exceptions.RequestException, InstallError) as exc:
                last_error = str(exc)
                self.log(f"下载失败: {last_error}")
                if attempt < self.retries:
                    time.sleep(self.retry_delay)

        raise InstallError(f"下载更新包失败: {last_error}")

    # -- 应用 --------------------------------------------------------------- #

    def apply(
        self,
        info: UpdateInfo,
        progress: ProgressFn = None,
        dry_run: bool = False,
        zip_path: Optional[Path] = None,
    ) -> InstallReport:
        artifact = Path(zip_path) if zip_path else self.download(info, progress)
        previous_version = local_version_string()
        report = installer.install_from_zip(
            artifact, self.cfg, source=self.name, dry_run=dry_run, progress=progress
        )
        if report.success and not dry_run:
            # version.json 在安装阶段受保护，安装成功后由更新器写入权威版本号，
            # 否则本地版本会一直停留在旧值，界面会反复提示"有新版本"。
            from .version import write_local_version

            payload = installer.extract_version_json(artifact) or {}
            payload["version"] = normalize(info.remote_version) or payload.get("version", "")
            payload["installed_at"] = datetime.now().isoformat(timespec="seconds")
            payload["installed_by"] = "release"
            payload["previous_version"] = previous_version
            if info.details.get("tag"):
                payload["tag"] = info.details["tag"]
            try:
                write_local_version(payload)
                report.notes.append(f"已更新版本记录为 {payload['version']}")
            except OSError as exc:
                report.errors.append(f"写入 version.json 失败: {exc}")

            self._record_state(
                source=self.name,
                previous_version=previous_version,
                new_version=payload["version"],
                artifact=str(artifact),
                report=report,
            )
        return report

    @staticmethod
    def _record_state(**payload: Any) -> None:
        record_runtime_state(payload)


# --------------------------------------------------------------------------- #
# 运行期状态记录（不写入任何 git 跟踪的文件）
# --------------------------------------------------------------------------- #

def record_runtime_state(payload: Dict[str, Any]) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        target = STATE_DIR / "last_update.json"
        data = dict(payload)
        report = data.pop("report", None)
        if isinstance(report, InstallReport):
            data["report"] = report.to_dict()
        target.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def build_sources(cfg: Dict[str, Any], log: LogFn) -> Tuple[List[Any], List[str]]:
    """按配置构造候选来源列表，返回 (sources, 跳过原因)。"""
    mode = cfg.get("source", "auto")
    git_source = GitSource(cfg, log)
    release_source = ReleaseSource(cfg, log)
    notes: List[str] = []

    if mode == "git":
        candidates = [git_source]
    elif mode == "release":
        candidates = [release_source]
    else:
        candidates = [git_source, release_source]

    usable = []
    for source in candidates:
        ok, reason = source.probe()
        if ok:
            usable.append(source)
        else:
            notes.append(f"{source.label} 不可用: {reason}")
    return usable, notes
