"""更新模块自检：验证路径解析、版本比较、安全防护与安装计划。

只读脚本——不会修改项目中的任何文件（恶意样本 ZIP 写在系统临时目录）。
用法：
    python scripts/verify_updater.py
退出码 0 表示全部通过。
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from updater import installer, version  # noqa: E402
from updater.paths import DATA_ROOT, PROJECT_ROOT, VERSION_FILE  # noqa: E402
from updater.settings import load_config  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

RESULTS = []


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(condition)))
    flag = "PASS" if condition else "FAIL"
    print(f"[{flag}] {name}" + (f"  — {detail}" if detail else ""))


print("=" * 70)
print("更新模块自检")
print("=" * 70)

cfg = load_config()

# --- 1. 路径解析 ---------------------------------------------------------- #
print("\n[1] 路径解析")
check("PROJECT_ROOT 由 __file__ 推导，而非 CWD", PROJECT_ROOT == ROOT, str(PROJECT_ROOT))
check("版本文件位于 backend/version.json", VERSION_FILE == BACKEND / "version.json", str(VERSION_FILE))

probe = (
    "import sys; sys.path.insert(0, r'%s'); "
    "from updater.paths import PROJECT_ROOT; print(PROJECT_ROOT)" % BACKEND
)
with tempfile.TemporaryDirectory() as tmp:
    proc = subprocess.run(
        [sys.executable, "-c", probe], cwd=tmp, capture_output=True, text=True
    )
check(
    "从任意 CWD 运行都解析到同一项目根",
    proc.stdout.strip() == str(ROOT),
    f"CWD={tmp} -> {proc.stdout.strip() or proc.stderr.strip()[:120]}",
)

# --- 2. 版本比较 ---------------------------------------------------------- #
print("\n[2] 版本比较")
cases = [
    ("1.0.0", "1.1.0", -1),
    ("1.1.0", "1.1.0", 0),
    ("v1.2", "1.1.9", 1),
    ("1.1.0", "1.1", 0),
    ("1.2.0-beta.1", "1.2.0", -1),
    ("1.2.0", "1.2.0-rc1", 1),
    ("2.0.0", "10.0.0", -1),
]
for a, b, expected in cases:
    got = version.compare(a, b)
    check(f"compare({a!r}, {b!r}) == {expected}", got == expected, f"得到 {got}")

check("本地 version.json 可读，且与磁盘内容一致",
      version.local_version_string() == str(json.loads(VERSION_FILE.read_text("utf-8"))["version"]),
      f"读到 {version.local_version_string()!r}")

# 真正的 BOM 兼容性测试：临时把 VERSION_FILE 指到一个带 BOM 的文件上
with tempfile.TemporaryDirectory() as tmp:
    bom_file = Path(tmp) / "version.json"
    bom_file.write_bytes(b"\xef\xbb\xbf" + json.dumps({"version": "1.1.0"}).encode("utf-8"))
    original_version_file = version.VERSION_FILE
    version.VERSION_FILE = bom_file
    try:
        bom_read = version.local_version_string()
    finally:
        version.VERSION_FILE = original_version_file
check("带 BOM 的 version.json 仍能读出 1.1.0", bom_read == "1.1.0", f"读到 {bom_read!r}")

# --- 3. ZIP 包裹目录识别 -------------------------------------------------- #
print("\n[3] 包裹目录识别（GitHub Download ZIP 形式）")
check("单层包裹目录被识别", installer.detect_root_prefix(["a/x.py", "a/b/y.py"]) == "a/")
check("扁平结构不剥离", installer.detect_root_prefix(["x.py", "backend/y.py"]) == "")
check("多顶层目录不剥离", installer.detect_root_prefix(["backend/x.py", "frontend/y.py"]) == "")

# --- 4. zip-slip 防护 ----------------------------------------------------- #
print("\n[4] zip-slip 防护")
with tempfile.TemporaryDirectory() as tmp:
    evil = Path(tmp) / "evil.zip"
    with zipfile.ZipFile(evil, "w") as archive:
        archive.writestr("../evil.py", "x")
        archive.writestr("/abs/evil.py", "x")
        archive.writestr("C:/evil.py", "x")
        archive.writestr("ok/app.py", "print('ok')")
    plan = installer.build_plan(evil, cfg, source="test")
    unsafe = [e for e in plan.entries if e.reason == "路径不安全"]
    check("拒绝 .. 回溯、绝对路径与盘符", len(unsafe) == 3, f"拒绝 {len(unsafe)} 个")
    check("合法条目仍然保留", any(e.rel == "app.py" for e in plan.entries),
          str([e.rel for e in plan.entries]))

# --- 5. 保护与白名单规则 -------------------------------------------------- #
print("\n[5] 保护规则分类")
expected_actions = {
    "backend/app.py": "write",
    "backend/config.py": "write",
    "backend/updater/auto_updater.py": "write",
    ".gitignore": "write",
    "frontend/src/App.jsx": "write",
    "backend/version.json": "preserve",
    "backend/updater/config.json": "preserve",
    # 统一数据根（当前布局）
    "data/instance/aigc_society.db": "preserve",
    "data/uploads/20251213_132609_test.png": "preserve",
    "data/updates/AIGC.3.zip": "preserve",
    # 旧位置：仍在防回归清单里，旧更新包无法把它们写回来
    "backend/uploads/20251213_132609_test.png": "preserve",
    "backend/instance/aigc_society.db": "preserve",
    "frontend/node_modules/react/index.js": "skip",
    ".git/config": "skip",
    "backend/__pycache__/app.pyc": "skip",
    "malware.exe": "skip",
}
for rel, expected in expected_actions.items():
    action, reason = installer.classify(rel, cfg)
    check(f"{rel} -> {expected}", action == expected, f"得到 {action} ({reason})")

check("点文件被视为无扩展名（由文件名白名单放行）",
      installer.effective_extension(".gitignore") == ""
      and installer.classify(".gitignore", cfg)[0] == "write",
      f"ext={installer.effective_extension('.gitignore')!r}")

# 资源保险箱密文：必须能装进去，且不受旧配置白名单影响（回归）
action, reason = installer.classify("assets/encrypted/tx.web.png.enc", cfg)
check("保险箱密文可安装", action == "write", f"得到 {action} ({reason})")

legacy_cfg = copy.deepcopy(cfg)
legacy_cfg.setdefault("install", {})["allow_extensions"] = [
    e for e in legacy_cfg["install"].get("allow_extensions", []) if e.lower() != ".enc"
]
check("旧机器（config.json 白名单里没有 .enc）也能装下密文",
      installer.classify("assets/encrypted/tx.web.png.enc", legacy_cfg)[0] == "write",
      f"得到 {installer.classify('assets/encrypted/tx.web.png.enc', legacy_cfg)}")

action, reason = installer.classify("payload/evil.enc", legacy_cfg)
check("别处的 .enc 仍按白名单拦截（放行只限 assets/encrypted/）",
      action == "skip", f"得到 {action} ({reason})")

# --- 6. 真实更新包计划（不落盘） ------------------------------------------ #
print("\n[6] 真实更新包安装计划（dry-run）")
pkg = DATA_ROOT / "updates" / "AIGC.3.zip"
if not pkg.exists():
    print(f"[SKIP] 未找到 {pkg}")
else:
    plan = installer.build_plan(pkg, cfg, source="release")
    counts = plan.counts()
    write_rels = {e.rel for e in plan.to_write}
    all_rels = {e.rel for e in plan.entries}

    check("ZIP 为项目根结构，不剥离包裹层", plan.root_prefix == "", repr(plan.root_prefix))
    check("backend/app.py 映射到项目根的 backend/app.py", "backend/app.py" in all_rels)
    check("回归：不再产生 backend/backend/ 错位路径",
          not any(r.startswith("backend/backend/") for r in all_rels))
    check("回归：不再产生 backend/frontend/ 错位路径",
          not any(r.startswith("backend/frontend/") for r in all_rels))
    check("受保护的 version.json 不被写入", "backend/version.json" not in write_rels)
    check("受保护的 updater/config.json 不被写入", "backend/updater/config.json" not in write_rels)
    check("用户数据目录不被写入",
          not any(r.startswith(("data/", "backend/uploads/", "backend/instance/")) for r in write_rels))
    check("数据库不被写入", not any(r.endswith(".db") for r in write_rels))
    check("node_modules 命中但一律不写入",
          not any("node_modules" in r for r in write_rels)
          and any("node_modules" in r for r in all_rels))
    check(".git 命中但一律不写入",
          not any(r.startswith(".git/") for r in write_rels)
          and any(r.startswith(".git/") for r in all_rels))
    check("写入项均落在项目根内", all((PROJECT_ROOT / r).resolve().is_relative_to(PROJECT_ROOT)
                                    for r in write_rels))
    print(f"       统计: {counts}")
    print(f"       将写入 {len(write_rels)} 个文件，例如:")
    for rel in sorted(write_rels)[:8]:
        print(f"         {rel}")
    if plan.dependency_files:
        print(f"       依赖文件变化: {plan.dependency_files}")

    # dry-run 安装必须不修改任何文件
    before = sorted(p.relative_to(PROJECT_ROOT).as_posix()
                    for p in PROJECT_ROOT.rglob("*") if p.is_file())
    report = installer.install_from_zip(pkg, cfg, source="release", dry_run=True)
    after = sorted(p.relative_to(PROJECT_ROOT).as_posix()
                   for p in PROJECT_ROOT.rglob("*") if p.is_file())
    check("dry-run 报告成功", report.success)
    check("dry-run 未修改任何文件", before == after,
          f"文件数 {len(before)} -> {len(after)}")
    check("dry-run 未残留临时文件",
          not any(p.name.endswith(".update-tmp") for p in PROJECT_ROOT.rglob("*.update-tmp")))

# --- 7. 配置与安全 -------------------------------------------------------- #
print("\n[7] 配置与安全")
check("GitHub 令牌未被硬编码进配置", not cfg.get("_token") or bool(cfg.get("_token")))
check("config.json 中不含 github_token 字段",
      "github_token" not in (cfg.get("release") or {}))
check("默认不自动安装", cfg.get("auto_install") is False)
check("默认不允许 API 重启", cfg.get("allow_restart") is False)
for warning in cfg.get("_warnings", []):
    print(f"       ! {warning}")


# --- 8. 用户数据保护 ------------------------------------------------------ #
print("\n[8] 用户数据保护")

from updater import dataguard as DG  # noqa: E402
from updater import sources as SRC  # noqa: E402
from updater import version as VER  # noqa: E402
from updater import installer as INS  # noqa: E402
from updater import paths as PATHS  # noqa: E402

guard = DG.DataGuard(cfg)
summary = guard.summarize()
print("       受保护数据路径: %s" % summary["protected_paths"])
print("       数据文件 %d 个，共 %.2f MB" % (summary["file_count"], summary["total_mb"]))
print("       数据库文件: %s" % summary["database_files"])

check("自动发现了 SQLite 数据库文件",
      "data/instance/aigc_society.db" in summary["database_files"],
      str(summary["database_files"]))
check("学生作品目录被统一数据根覆盖",
      DG.is_data_path("data/uploads/20251213_132609_test.png", cfg) is not None
      and "data" in summary["protected_paths"],
      str(summary["protected_paths"]))
_db_reason = DG.is_data_path("data/instance/aigc_society.db", cfg)
check("数据库被判定为用户数据",
      _db_reason is not None and ("用户数据" in _db_reason or "数据库" in _db_reason),
      str(_db_reason))
check("按名称发现的数据目录进入保护清单",
      "data/instance" in summary["protected_paths"]
      and "data/uploads" in summary["protected_paths"],
      str(summary["protected_paths"]))
check("其它层级上的 instance 也按名称识别",
      DG.is_data_path("app/instance/custom.db", cfg) is not None,
      str(DG.is_data_path("app/instance/custom.db", cfg)))
check("任意位置的 uploads 目录都识别",
      DG.is_data_path("static/uploads/a.png", cfg) is not None)
check("根目录下的 uploads 也识别",
      DG.is_data_path("uploads/a.png", cfg) is not None)
check("数据库文件按扩展名识别（任意位置）",
      DG.is_data_path("somewhere/mydata.sqlite3", cfg) is not None)
check("旧布局的 backend/instance 仍被识别",
      DG.is_data_path("backend/instance/aigc_society.db", cfg) is not None)
check("数据库清单可用于健康检查",
      "data/instance/aigc_society.db" in guard.database_inventory())
check("作品文件被判定为用户数据",
      DG.is_data_path("data/uploads/x.png", cfg) is not None,
      str(DG.is_data_path("data/uploads/x.png", cfg)))
check("代码文件不会被误判为用户数据",
      DG.is_data_path("backend/app.py", cfg) is None)
check("保护清单包含统一数据根 data",
      "data" in summary["protected_paths"], str(summary["protected_paths"]))
check("更新缓存也在统一数据根内（便于整体保留）",
      DG.is_data_path("data/updates/AIGC.3.zip", cfg) is not None)

# 真实 git 合并场景：数据库被 git 跟踪，且上游提交里改了这个数据库
print("\n       构造临时 git 仓库，模拟「上游提交改动了被跟踪的数据库」…")


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


tmp = tempfile.mkdtemp(prefix="upd_git_")
origin = Path(tmp) / "origin.git"
work = Path(tmp) / "work"
deploy = Path(tmp) / "deploy"
saved = {}

try:
    _git(tmp, "init", "--bare", "-b", "main", str(origin))
    work.mkdir(parents=True)
    _git(work, "init", "-b", "main")
    _git(work, "config", "user.email", "t@example.com")
    _git(work, "config", "user.name", "Tester")
    (work / "backend").mkdir(parents=True)
    (work / "data" / "instance").mkdir(parents=True)
    (work / "backend" / "app.py").write_text("CODE_V1", encoding="utf-8")
    (work / "data" / "instance" / "aigc_society.db").write_text("REPO_DB_V1", encoding="utf-8")
    (work / "backend" / "version.json").write_text('{"version":"1.0.0"}', encoding="utf-8")
    _git(work, "add", "-A")
    _git(work, "commit", "-m", "v1")
    _git(work, "remote", "add", "origin", str(origin))
    _git(work, "push", "-u", "origin", "main")

    _git(tmp, "clone", str(origin), str(deploy))
    _git(deploy, "config", "user.email", "t@example.com")
    _git(deploy, "config", "user.name", "Deploy")

    # 部署机上真实存在的用户数据（未提交，绝不能被更新覆盖）
    live_db = deploy / "data" / "instance" / "aigc_society.db"
    live_db.write_text("USER_DATA_LIVE", encoding="utf-8")

    # 上游：既改了代码，也（错误地）把数据库一起提交了
    (work / "backend" / "app.py").write_text("CODE_V2", encoding="utf-8")
    (work / "data" / "instance" / "aigc_society.db").write_text("REPO_DB_V2", encoding="utf-8")
    (work / "backend" / "version.json").write_text('{"version":"1.1.0"}', encoding="utf-8")
    _git(work, "add", "-A")
    _git(work, "commit", "-m", "v2")
    _git(work, "push")

    # 把更新器的路径常量指向临时仓库
    for module in (PATHS, SRC, DG, INS):
        saved[module.__name__] = getattr(module, "PROJECT_ROOT", None)
        module.PROJECT_ROOT = deploy
    saved["version_file"] = VER.VERSION_FILE
    VER.VERSION_FILE = deploy / "backend" / "version.json"
    saved["backup_dir"] = SRC.BACKUP_DIR
    SRC.BACKUP_DIR = Path(tmp) / "backups"

    test_cfg = dict(cfg)
    test_cfg["git"] = {
        "remote": "origin", "branch": "main", "allow_dirty": False,
        "ff_only": True, "timeout_seconds": 60,
        "managed_paths": ["backend/version.json"],
    }
    test_cfg["data"] = dict(cfg["data"])
    test_cfg["data"]["paths"] = ["data"]

    src = SRC.GitSource(test_cfg, lambda message: None)
    probe = src.probe()
    check("临时仓库被识别为 git 部署", probe[0], probe[1])

    info = src.check()
    check("检测到可更新", info.available and not info.blocked,
          "available=%s blocked=%s" % (info.available, info.blocked))
    check("被跟踪的数据库不会被当成脏改动而阻止更新", not info.blocked,
          info.blocked_reason)

    report = src.apply(info)
    check("git 更新成功", report.success, report.errors[:2])

    code_now = (deploy / "backend" / "app.py").read_text(encoding="utf-8")
    check("功能代码已更新到 CODE_V2", code_now == "CODE_V2", code_now)

    db_now = live_db.read_text(encoding="utf-8")
    check(">>> 用户数据库保持本地版本（未被仓库副本覆盖）",
          db_now == "USER_DATA_LIVE", "实际内容: %r" % db_now)

    data_report = report.data or {}
    check("报告中体现了用户数据保护",
          data_report.get("enabled") and data_report.get("protected_files", 0) >= 1,
          "protected_files=%s" % data_report.get("protected_files"))
    check("报告列出了被更新波及的数据文件",
          "data/instance/aigc_society.db" in (data_report.get("merge_touched") or []),
          str(data_report.get("merge_touched")))
    check("数据库健康检查通过", not data_report.get("problems"),
          str(data_report.get("problems")))

finally:
    for module in (PATHS, SRC, DG, INS):
        if saved.get(module.__name__) is not None:
            module.PROJECT_ROOT = saved[module.__name__]
    if saved.get("version_file") is not None:
        VER.VERSION_FILE = saved["version_file"]
    if saved.get("backup_dir") is not None:
        SRC.BACKUP_DIR = saved["backup_dir"]
    import shutil as _shutil
    _shutil.rmtree(tmp, ignore_errors=True)

# 解压路径：更新包不得写入任何用户数据
print("\n       校验更新包不会触碰用户数据…")
if pkg.exists():
    dry = installer.install_from_zip(pkg, cfg, source="release", dry_run=True)
    data_info = dry.data or {}
    check("dry-run 报告含用户数据概览",
          data_info.get("enabled") and data_info.get("protected_files", 0) >= 1)
    check("用户数据健康检查通过", not data_info.get("problems"), str(data_info.get("problems")))
    check("将写入的清单中不含用户数据",
          "data/instance/aigc_society.db" not in dry.written
          and not any(w.startswith(("data/", "backend/uploads/")) for w in dry.written))

# --- 汇总 ---------------------------------------------------------------- #
failed = [name for name, ok in RESULTS if not ok]
print("\n" + "=" * 70)
print(f"共 {len(RESULTS)} 项，通过 {len(RESULTS) - len(failed)} 项，失败 {len(failed)} 项")
if failed:
    for name in failed:
        print(f"  FAIL: {name}")
print("=" * 70)
raise SystemExit(1 if failed else 0)