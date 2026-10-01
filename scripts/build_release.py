"""打包发布压缩包（干净包）。

用法：
    python scripts/build_release.py                # 用已提交内容（HEAD）打包 —— 发布用
    python scripts/build_release.py --worktree     # 用当前工作区打包（含未提交改动，仅供本地测试）
    python scripts/build_release.py --out DIR      # 指定输出目录（默认 build/releases）

产物：<out>/AIGC_v<版本>.zip，并打印体积、条目数与 SHA-256。

打包规则（见 docs/UPDATE_GUIDE.md 第 7 节）：
  * 顶层是项目结构（backend/、frontend/ ...），外面套一层包裹目录，更新程序会自动剥离；
  * **不含** frontend/node_modules、data/、.git/、build/、__pycache__ ——
    这几项要么会被更新程序跳过，要么会被数据保护挡住，打进包里只会让体积从
    几百 KB 膨胀到几十 MB（旧包 48 MB，其中 45 MB 是 node_modules）；
  * tools/ 不属于仓库，天然不会被打进去。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WRAPPER = "AIGC社信息系统"

# 即使被 git 跟踪，也不允许出现在发布包里的路径片段
FORBIDDEN_PARTS = ("node_modules", "__pycache__", ".git", ".venv", "venv", "build", "dist")
FORBIDDEN_TOP = ("data",)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass


def git(*args: str) -> str:
    """跑一条 git 命令，按 UTF-8 解码（Windows 上 locale 是 GBK，不能靠默认解码）。"""
    out = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True
    ).stdout
    return out.decode("utf-8", "surrogateescape")


def read_version(rev: str | None) -> str:
    """从指定版本（rev=None 表示工作区）读取 backend/version.json 里的版本号。"""
    if rev:
        raw = git("show", f"{rev}:backend/version.json")
    else:
        raw = (ROOT / "backend" / "version.json").read_text("utf-8")
    return json.loads(raw)["version"]


def build_from_head(rev: str, dest: Path) -> None:
    git("archive", "--format=zip", f"--prefix={WRAPPER}/", "-o", str(dest), rev)


def build_from_worktree(dest: Path) -> None:
    listing = git("ls-files", "-z", "--cached", "--others", "--exclude-standard")
    names = [n for n in listing.split("\0") if n]
    if not names:
        raise SystemExit("git ls-files 没返回任何文件，检查是否在仓库里运行")
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name in names:
            src = ROOT / name
            if not src.is_file():
                continue
            zf.write(src, f"{WRAPPER}/{name}")


def verify(dest: Path, expected_version: str) -> dict:
    problems: list[str] = []
    with zipfile.ZipFile(dest) as zf:
        infos = zf.infolist()
        names = [i.filename for i in infos]

        bad_crc = zf.testzip()
        if bad_crc:
            problems.append(f"CRC 校验失败：{bad_crc}")

        for n in names:
            if not n.startswith(WRAPPER + "/"):
                problems.append(f"条目不在包裹目录内：{n}")
                break
        for n in names:
            parts = n[len(WRAPPER) + 1 :].split("/")
            top = parts[0]
            if top in FORBIDDEN_TOP or any(p in FORBIDDEN_PARTS for p in parts):
                problems.append(f"包含应当排除的路径：{n}")
                break

        try:
            packed_version = json.loads(zf.read(f"{WRAPPER}/backend/version.json"))["version"]
        except KeyError:
            packed_version = None
            problems.append("包内缺少 backend/version.json")
        if packed_version and packed_version != expected_version:
            problems.append(f"包内版本号 {packed_version} != 期望 {expected_version}")

        unpacked = sum(i.file_size for i in infos)

    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    return {
        "entries": len(names),
        "unpacked": unpacked,
        "version": packed_version,
        "sha256": digest,
        "problems": problems,
        "names": names,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="打包 AIGC 社信息系统发布压缩包（干净包）")
    ap.add_argument("--out", default=str(ROOT / "build" / "releases"), help="输出目录")
    ap.add_argument("--rev", default="HEAD", help="打包的 git 版本（默认 HEAD）")
    ap.add_argument("--worktree", action="store_true", help="用当前工作区打包（含未提交改动）")
    ap.add_argument("--list", action="store_true", help="打印包内文件清单")
    args = ap.parse_args()

    if args.worktree:
        version = read_version(None)
        dirty = git("status", "--porcelain").strip()
        if dirty:
            print("[!] 工作区有未提交改动，本次打包包含这些改动（仅供本地测试）：")
            for line in dirty.splitlines():
                print("      " + line)
    else:
        version = read_version(args.rev)
        dirty = git("status", "--porcelain").strip()
        if dirty:
            print("[i] 工作区有未提交改动，本次只打包已提交内容（HEAD）。")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"AIGC_v{version}.zip"
    if dest.exists():
        dest.unlink()

    if args.worktree:
        build_from_worktree(dest)
    else:
        build_from_head(args.rev, dest)

    info = verify(dest, version)
    size = dest.stat().st_size
    print()
    print("=" * 64)
    print(f"发布包   : {dest}")
    print(f"版本     : {info['version']}")
    print(f"体积     : {size:,} 字节 ({size / 1024:.1f} KB)   解压后 {info['unpacked'] / 1024:.1f} KB")
    print(f"条目数   : {info['entries']}")
    print(f"SHA-256  : {info['sha256']}")
    print("=" * 64)

    if args.list:
        for n in info["names"]:
            print("  " + n)

    if info["problems"]:
        print()
        for p in info["problems"]:
            print(f"[FAIL] {p}")
        return 1

    print("[OK] 包结构与版本号校验通过（无 node_modules / data / .git）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
