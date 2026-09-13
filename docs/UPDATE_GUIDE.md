# 系统更新指南

> 适用于 AIGC 社信息系统 v1.1.0 及以后版本。
> 更新模块代码位于 `backend/updater/`。

## 1. 设计原则

| 原则 | 说明 |
|------|------|
| **不阻塞启动** | 检查更新在后台线程中进行，`app.run()` 不会等待网络请求 |
| **不自动覆盖** | 默认只检查、只提示；安装必须由管理员在界面点击确认 |
| **数据绝对安全** | 数据库、上传文件、版本记录、更新器配置**永不**被更新包覆盖 |
| **可回滚** | 写入前自动备份，写入失败自动回滚到更新前状态 |
| **路径不依赖 CWD** | 所有路径由 `updater/paths.py` 从 `__file__` 推导，与启动目录无关 |

## 2. 两种更新来源

系统采用 **git 优先、Release 回退** 的混合策略（`source: "auto"`）。

### 2.1 git 方式（优先）

**前提**：目标机安装了 `git`，且项目目录是完整的 git 克隆（存在 `.git/`）。

**流程**：`git fetch` → 比对 `HEAD` 与 `origin/<branch>` → `git merge --ff-only`

**拒绝更新的情况**（这是刻意的保护）：

- 工作区存在未提交改动 —— 界面会列出具体文件，请先提交或执行 `git stash`
- 本地分支领先远端（无需更新）
- 远端分支不存在或网络不可达 → 自动回退到 Release 方式

> `backend/version.json` 属于"更新器托管文件"，合并前会被还原为仓库版本，
> 因此它不会阻塞后续的 git 更新。

### 2.2 Release 方式（回退）

**前提**：能访问 GitHub API（公开仓库无需令牌）。

**流程**：读取 `releases/latest` → 下载匹配资产的 ZIP → 校验大小与 SHA256 →
解压覆盖（受保护路径除外）→ 写入 `backend/version.json`。

GitHub 新版 API 会在资产上返回 `digest` 字段（`sha256:...`），系统会用它做完整性校验；
若该字段缺失，则只比对文件大小并在日志中说明。

## 3. 配置

配置文件：`backend/updater/config.json`（**这是真正生效的配置**，旧版本中该文件从未被读取）。

关键配置项：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `enabled` | `true` | 是否启用更新模块 |
| `check_on_startup` | `true` | 启动后异步检查一次 |
| `startup_delay_seconds` | `8` | 启动后延迟多久开始检查 |
| `auto_install` | `false` | **是否自动安装（不建议开启）** |
| `check_interval_hours` | `0` | 周期性检查间隔，`0` 表示关闭 |
| `source` | `"auto"` | `auto` / `git` / `release` |
| `git.branch` | `"main"` | 跟踪的分支 |
| `git.allow_dirty` | `false` | 有本地改动时是否仍允许更新 |
| `release.repo` | `"hanbingjiuxing/AIGC-"` | GitHub 仓库 |
| `release.asset_pattern` | `\.zip$`（正则） | 匹配更新包的资产名 |
| `proxy.enabled` / `proxy.url` | `false` / `""` | 代理设置（默认关闭；旧版硬编码 127.0.0.1:7897，未启动时会拖慢检查） |
| `data.paths` | `["data"]` | 统一数据根目录，更新时永不覆盖 |
| `data.dir_names` | `{}` | 追加需要保护的文件夹名（默认已含 instance / uploads） |
| `data.auto_discover_databases` | `true` | 自动发现项目内所有 SQLite 文件并纳入保护 |
| `data.snapshot_at_risk_files` | `true` | git 更新前快照被波及的数据文件，用于还原 |
| `install.preserve_dirs` | 见配置文件 | 永不覆盖的目录（相对项目根） |
| `install.preserve_files` | 见配置文件 | 永不覆盖的文件 |
| `allow_restart` | `false` | 是否允许通过界面重启后端进程 |

### 环境变量

| 变量 | 说明 |
|------|------|
| `AIGC_UPDATE_GITHUB_TOKEN` | GitHub 令牌（**唯一**的令牌来源，公开仓库无需配置） |
| `AIGC_UPDATE_ENABLED` | 覆盖 `enabled` |
| `AIGC_UPDATE_SOURCE` | 覆盖 `source` |
| `AIGC_UPDATE_AUTO_INSTALL` | 覆盖 `auto_install` |
| `AIGC_UPDATE_PROXY` | 代理地址，如 `http://127.0.0.1:7897` |
| `AIGC_UPDATE_GITHUB_REPO` | 覆盖仓库名 |
| `AIGC_UPDATE_SKIP_STARTUP` | 设为任意值可跳过启动检查（调试用） |

> **安全提示**：令牌只从环境变量读取，不会写入配置文件、日志或 API 响应。
> 旧版本曾把 GitHub PAT 硬编码在 `app.py` 与 `config.json` 中，请确认该令牌已在 GitHub 上吊销。

## 4. 使用方式

### 4.1 图形界面

以**老师**或**社长**账号登录 → 侧边栏「系统设置」→「系统更新」卡片：

- **检查更新**：后台检查，不阻塞界面
- **预览变更**：列出将被修改的文件（不写盘）
- **预演**：完整走一遍安装流程但不写入任何文件
- **立即更新**：真正写入（会二次确认，并提示"数据库与上传文件会被保留"）
- **重启后端**：仅在 `allow_restart: true` 时出现

### 4.2 命令行

在 `backend` 目录下执行：

    python -m updater status            # 查看配置、路径、来源可用性
    python -m updater check             # 同步检查更新
    python -m updater preview           # 预览将变更的文件
    python -m updater update --dry-run  # 预演安装（不写入）
    python -m updater update            # 实际安装（需交互确认）

### 4.3 一键启动时自动检测（推荐用法）

把 `offline_updater.exe` 放到下列任一位置，**双击 `run_system.bat` 时就会自动检测更新**：

    <项目根>\tools\offline_updater.exe
    <项目根的上一级>\tools\offline_updater.exe
    <项目根>\offline_updater.exe

检测到更新包时会询问"是否现在更新"：

| 你的选择 | 结果 |
|---|---|
| **Y** | 先更新（备份 → 写代码 → 数据归位 → 校验），成功后**自动以新版本重新启动** |
| **直接回车 / 其他** | 跳过更新，立即启动当前版本 |
| 没有更新包 | 静默跳过，直接启动 |

> **为什么更新成功要重新拉起脚本？** 更新会覆盖 `run_system.bat` 自身，而
> cmd.exe 无法可靠地从一个已被替换的批处理里继续往下读（实测会静默中断），
> 所以更新程序会新开一个进程用新版本重启启动脚本。
>
> 想跳过检测：`run_system.bat --skip-update`

> **维护提醒**：`.bat` 文件里**不能出现中文等多字节字符** —— cmd.exe 按字节
> 推进文件位置，遇到多字节字符会错位，把后续命令读成乱码片段。所有面向用户的
> 中文提示都放在 `offline_updater.exe` 里（它用 WriteConsoleW 输出，不受影响）。

### 4.4 离线更新程序（与新版压缩包同目录）

适用于**不方便联网、也没有装 git** 的校园机器。工具位于 `tools/offline_updater.exe`，
**不属于应用本身，不需要打包进发布压缩包**。

它是用 C 写、已编译好的独立可执行文件（约 92 KB）：
**不需要 Python、不需要 git、不需要联网**，双击即可运行。

用法：把 `offline_updater.exe`（连同 `offline_updater.bat`）和「新版程序压缩包」
放进同一个目录（可以直接放进项目目录），双击 `offline_updater.bat`，
或在该目录打开命令行执行：

    offline_updater.exe              # 正常升级（会二次确认）
    offline_updater.exe --dry-run    # 只预演，不改动任何文件
    offline_updater.exe --yes        # 跳过确认

它做的事：

1. 找到同目录下的新版压缩包与项目目录；
2. **按文件夹名称识别用户数据**：项目里**任何层级**上名为 `instance`（数据库）
   或 `uploads`（学生作品）的文件夹，整体视为用户数据 —— 与它放在哪一层无关；
   此外任何位置的 `*.db` / `*.sqlite` / `*.sqlite3` 文件也一律保护；
3. 备份这些数据，再用压缩包里的新代码覆盖项目其余部分 ——
   **用户数据一律跳过，绝不覆盖**，即使压缩包里误带了同名文件夹也不会生效；
4. 把识别到的数据文件夹**归位到新版统一位置** `data/instance`、`data/uploads`
   —— 目标已存在同名项时保留目标，绝不覆盖；
5. 校验每个数据文件的 SHA-256，任何一步失败都会自动回滚。

> **为什么按名字、而不是按路径？**
> 服务器上实际部署的历史版本比当前仓库还要早，数据目录的父级位置换过多次
> （`backend/instance`、根目录 `uploads/`、`app/instance` …），但这两个
> 文件夹的**名字从来没有变过**。只认名字，就能兼容任意历史布局，
> 不会因为路径变了就漏掉用户数据。

其他参数：

| 参数 | 说明 |
|------|------|
| `--zip X.zip` | 同目录有多个压缩包时指定其一 |
| `--project DIR` | 指定项目目录（默认自动查找） |
| `--backup-dir DIR` | 备份存放位置（默认与本程序同目录的 `upgrade_backup_时间戳/`） |
| `--overwrite-config` | 用新版本的 `backend/updater/config.json` 覆盖本地配置（默认保留本地配置） |
| `--allow-any-extension` | 关闭扩展名白名单（默认只允许常见项目文件类型） |
| `--help` | 显示帮助 |
| `--restore 备份目录` | 用某个备份回滚代码（用户数据不动） |

> **发布提醒**：打包发布压缩包时请把 `tools/` 目录排除在外 —— 这个工具是给
> 部署者用的，不需要随应用分发。

源码 `tools/offline_updater.c` 也保留在仓库里，需要重新编译时用 MSVC 或 MinGW：

    gcc -O2 -municode -DUNICODE -D_UNICODE -o offline_updater.exe offline_updater.c

> 它内置了 ZIP 解析、DEFLATE 解压、CRC32 与 SHA-256，**不依赖任何第三方库**，
> 编译出的单个 exe 可以直接拷到任何 Windows 机器上运行。

### 4.5 自检

    python scripts/verify_updater.py

该脚本验证路径解析、版本比较、zip-slip 防护、保护规则与真实更新包的安装计划，
**不会修改项目文件**。

## 5. 用户数据保护（重点）

### 5.1 统一的数据目录

所有需要保留的内容都集中在项目根的一个目录里：

    data/
    ├── instance/     SQLite 数据库（用户账号、考勤、公告）
    ├── uploads/      学生作品与上传文件
    ├── updates/      更新包下载缓存
    └── backups/      更新前备份（含用户数据快照）

**升级维护只需要保留这一个目录**，项目里的其余内容都是可以整体覆盖的代码。

| 类别 | 内容 | 更新时的处理 |
|------|------|--------------|
| **功能代码** | `backend/*.py`、`frontend/src/`、路由、服务、界面 | 被更新覆盖 |
| **用户数据** | `data/instance/aigc_society.db`（用户、考勤、公告）、`data/uploads/`（学生作品） | **永不覆盖、永不删除** |

> 历史版本把数据放在不同位置（`backend/instance`、根目录 `uploads/`、
> `app/instance` …），父级目录换过多次。程序启动时会**按文件夹名称扫描**并
> 自动归位到 `data/`：目标已存在的文件一律保留不覆盖，搬空的旧目录会被删除。
> 迁移过程可重复执行（幂等），不会丢数据。
>
> 手动执行迁移：`cd backend && python -m updater layout`

### 5.2 保护机制（按文件夹名称识别）

数据保护独立于安装器，两条更新路径都覆盖。识别方式是
**按文件夹名称、与它放在哪一层无关**：

1. **文件夹名称**——项目里**任何深度**上名为 `instance`（数据库）或 `uploads`
   （学生作品）的文件夹，整体视为用户数据。历史版本的父级目录换过多次
   （`backend/instance`、根目录 `uploads/`、`app/instance` …），只认名字就不会漏。
   需要保护别的文件夹名时，用 `data.dir_names` 追加。
2. **数据库文件**——任何位置的 `*.db` / `*.sqlite` / `*.sqlite3` / `*.db3` 一并保护。
3. **统一数据根**——`data/` 整体保护（含更新缓存与备份）。
4. **ZIP 更新**：解压时数据路径一律判定为"受保护"而跳过；安装后再次校验，
   若发现确有数据文件被写入，则判定安装失败并回滚。
5. **git 更新（关键）**：本项目的数据库与学生作品**是被 git 跟踪的**，
   一次普通的 `git merge` 就会用仓库里的旧副本覆盖它们。因此 git 路径会：
   - 先算出本次合并会改动的文件，挑出其中属于用户数据的部分；
   - 快照这些文件的**当前本地内容**；
   - 其中有本地改动的，临时换成仓库版本好让合并能够进行；
   - 合并结束后（无论成败）把本地内容放回去。

   未被本次合并触及的数据文件完全不会被读写，因此不存在"数据空窗期"。
   按名称识别同样用在这里：任意布局下的 `instance`/`uploads`/`*.db`
   都不会被当成"本地改动"而阻止更新。
6. **健康检查**：更新后确认更新前存在的数据库仍然存在且非空，否则判定更新失败。
7. **界面可见**：更新卡片会列出受保护的数据路径、文件数量与体积，
   安装报告里也会写明本次更新是否触及过用户数据。

### 5.3 用户数据已从 git 中移除跟踪

数据文件被 git 跟踪是隐患：既让每次合并都有覆盖风险，也会把学生作品和
用户数据上传到公开仓库。本仓库已完成清理：

- 提交 `0e4863b` 把 `backend/instance`、`backend/uploads` 移出了版本库
  （`git rm --cached`，磁盘文件未删除，随后迁移到 `data/`）；
- 根目录 `.gitignore` 现已忽略 `data/` 与旧位置，今后不会再被跟踪。

> 自定义部署若发现数据仍被跟踪，可执行 `git rm -r --cached <数据路径>` 后提交。
> 更新器内置快照—还原保护，即使被跟踪也不会丢数据；但移除跟踪后
> git 就再也不会碰这些文件，风险更低。

## 6. 安全设计

| 防护 | 实现 |
|------|------|
| 路径越界（zip-slip） | 拒绝绝对路径、`..` 回溯、盘符；写入前再次校验目标必须在项目根内 |
| 路径比较 | 用规范化后的路径做包含判断（兼容 Windows 8.3 短名/长名/符号链接/大小写），**不做字符串前缀比较** |
| 覆盖白名单 | 只有扩展名在白名单内、且不在 `skip_dirs` / `skip_globs` 中的文件才会被写入 |
| 数据保护 | `data/` 下的用户数据永不覆盖、永不删除（两条更新路径都覆盖，见第 5 节） |
| 备份 / 回滚 | 覆盖前逐文件备份到 `backend/backup/backup_<时间戳>/`，任一步失败即自动回滚 |
| 原子写入 | 先写 `.update-tmp` 再 rename，避免中断产生半截文件 |
| 令牌 | 只从环境变量读取，不落盘、不回显 |

## 7. 维护者：发布新版本

1. 修改 `backend/version.json` 中的 `version`（如 `1.1.1`）
2. 提交并推送到 GitHub
3. 打标签：`git tag v1.1.1 && git push origin v1.1.1`
4. 打包 ZIP 并在 GitHub 创建同名 Release，把 ZIP 作为资产上传
5. 客户端即可通过「系统设置 → 系统更新」或启动检查获知新版本

**打包要求**：

- ZIP 必须是**项目根结构**（顶层包含 `backend/`、`frontend/` 等）
- 可以带一层包裹目录（如 GitHub 的 `AIGC--main/`），系统会自动剥离
- **不要**打包 `frontend/node_modules/`、`data/`、`.git/`
  —— 它们会被跳过或保护，但会让更新包从几百 KB 膨胀到几十 MB

## 8. 故障排查

| 现象 | 原因 | 处理 |
|------|------|------|
| 提示"检测到未提交的本地改动" | 走的是 git 方式且工作区不干净 | 提交或 `git stash` 后重试 |
| 提示"没有可用的更新来源" | 未装 git 且无法访问 GitHub API | 检查网络；如需代理请设置 `AIGC_UPDATE_PROXY` |
| 检查一直失败 | 代理不可达 | 默认 `proxy.enabled` 为 `false`；如需代理请填 `proxy.url` |
| 更新完成但页面没变化 | 后端仍运行旧代码 | 重启后端（重新运行 `run_system.bat`） |
| 前端报错找不到依赖 | `frontend/package.json` 有变化 | 在 `frontend/` 下执行 `npm install` |
| 后端导入失败 | `backend/requirements.txt` 有变化 | 执行 `pip install -r backend/requirements.txt` |
| 安装失败并回滚 | 文件被占用等 | 查看界面「后台日志」；备份保留在 `backend/backup/` |
| 报告提示"用户数据被更新波及" | 上游提交里错误地包含了数据库或作品 | 系统已自动还原为本地版本；建议按 5.2 停止跟踪数据文件 |

## 9. API 一览

所有接口都需要**老师或社长**权限（`Authorization: Bearer <token>`）。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/update/status` | 当前状态、进度、配置与最近日志 |
| POST | `/api/update/check` | 后台检查更新，body 可传 `{"source": "auto"}` |
| GET | `/api/update/preview` | 预览将要变更的文件 |
| POST | `/api/update/install` | 安装更新，body 可传 `{"dry_run": true}` 预演 |
| POST | `/api/update/restart` | 重启后端（受 `allow_restart` 控制） |
| GET | `/api/update/log` | 最近的后台日志 |

状态机取值：`idle` / `checking` / `up_to_date` / `update_available` / `blocked` /
`downloading` / `installing` / `installed` / `error`
