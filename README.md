# AIGC社信息系统

厦门大学附属科技中学AIGC探索社信息管理系统

## 功能特性

- **成员管理**：社团成员信息管理、权限分配
- **作品管理**：AI作品上传、展示、分类管理
- **考勤管理**：社团活动考勤记录、统计分析
- **公告管理**：社团公告发布、查看
- **自动更新**：git 优先拉取 / GitHub Release 回退，异步检查、管理员确认安装、自动备份与回滚
- **用户数据保护**：数据库与学生作品在更新时永不覆盖、永不删除（含自动发现与快照还原）

## 技术栈

- **后端**: Python 3.x + Flask + SQLAlchemy + JWT
- **前端**: React + Vite + Axios
- **数据库**: SQLite

## 快速开始

### 环境要求

**无需预先安装任何开发环境。** 全新装好的 Windows 直接运行 `setup_env.bat`
即可，脚本会自己获取缺失的运行时：

- **Python 3.10+** — 本机已有则直接复用；没有则自动安装（优先 `winget`，
  其次从 python.org 下载官方安装包，按当前用户静默安装，不需要管理员权限）
- **Node.js 18+ / npm** — 同上自动安装；无法安装时改从 nodejs.org 下载官方
  便携版 zip，解压到 `runtime\node` 使用

> 完全离线的机器：先把一份已装好依赖的便携版 Python 放进 `runtime\python`，
> 脚本会优先使用它，全程不联网。

### 一键部署环境

运行 `setup_env.bat` 自动搭建开发环境：

```bash
setup_env.bat
```

该脚本会自动：
1. 检测并准备 Python（缺失则自动获取）
2. 在 `backend\venv` 创建虚拟环境并安装后端依赖
3. 检测并准备 Node.js / npm（缺失则自动获取）
4. 安装前端依赖

可以重复运行，已经就绪的部分会自动跳过。

### 一键启动系统

运行 `run_system.bat` 启动系统：

```bash
run_system.bat
```

该脚本会自动：
1. **检测更新**：如果项目里（或项目上一级的 `tools\` 目录里）放着
   `offline_updater.exe`，而旁边又有新版程序压缩包，脚本会先询问你是否更新；
   选「是」则更新完成后自动以新版本重新启动，选「否」直接启动当前版本
2. 启动后端服务器（端口 5000）
3. 启动前端开发服务器（端口 5173）
4. 自动打开浏览器

> 想跳过更新检测，可以运行 `run_system.bat --skip-update`。
> 没有放更新包时这一步会自动跳过，不会打扰你。

脚本启动后端与前端时会自动使用 `setup_env.bat` 准备好的运行时（依次查找
`backend\venv` → `runtime\` → 系统安装的解释器），因此不需要事先配置 PATH。

### 启动失败：离线版「关于这个系统」

启动脚本会等两个端口（5000 / 5173）真正就绪之后再打开浏览器。要是最后没起来
（没装 Python、后端依赖缺失、找不到 npm、端口一直没人监听……），它不会把你丢在
一个打不开的页面上，而是**自动打开离线版的「关于这个系统」页面**：

```
fallback\about.html
```

这一页是从系统内的 About 页复制出来的单文件 HTML：没有 React、没有后端、没有
任何外部请求，双击就能打开 —— 里面写着「遇到实在解决不了的 bug」该找谁。
内容与样式由 `scripts/build_about_fallback.py` 从 `frontend/src/pages/About.jsx`
和 `frontend/src/index.css` 生成（生成时逐句核对文案），改完 About 页记得重新跑一次：

```bash
python scripts/build_about_fallback.py          # 重新生成离线页
python scripts/build_about_fallback.py --check  # 只检查是否最新
```

详见 [fallback/README.md](fallback/README.md)。

### 脚本备份

`backup\` 文件夹里放着两份行为一致的备用脚本，供主脚本被删除时使用：

- `backup\run_system_backup.bat` — `run_system.bat` 的备份
- `backup\setup_env_backup.bat` — `setup_env.bat` 的备份

两份备份都会自行定位项目目录，放在别处也能运行（脚本会先看自己旁边有没有
`backend\`，没有就再往上一级找）。需要恢复主脚本时，复制回根目录的原名即可：

```bash
copy backup\setup_env_backup.bat setup_env.bat
copy backup\run_system_backup.bat run_system.bat
```

> 主脚本改动后请同步更新这两份备份，保持行为一致。

### 手动启动

**后端**：
```bash
cd backend
python app.py
```

> 也可以用 `flask run` 启动；两种方式都会在后台异步检查更新，互不影响。

**前端**：
```bash
cd frontend
npm run dev
```

### 数据库管理工具

运行 `admin_gui.py` 启动图形化数据库管理程序：

```bash
python admin_gui.py
```

该程序提供可视化界面，可直接操作数据库：
- 👤 用户管理：添加、删除、重置密码、修改角色
- 📢 公告管理：添加、编辑、删除公告
- 🎨 作品管理：查看、删除作品
- 📅 考勤管理：查看统计、清空记录

## 访问地址

- 前端地址：http://localhost:5173
- 后端 API：http://localhost:5000/api

## 默认账户

- **管理员账号**: admin
- **管理员密码**: admin

## 项目结构

```
AIGC社信息系统/
├── backend/        # 后端代码（Flask）
├── frontend/       # 前端代码（React + Vite）
├── data/           # 统一数据目录（数据库 / 学生作品 / 缓存 / 备份）
├── assets/         # 资源保险箱（加密归档的源文件母版）
├── docs/           # 项目文档
├── scripts/        # 辅助脚本
├── runtime/        # 自动获取的运行时（便携 Python / Node.js）
├── backup/         # 备用脚本（主脚本被删时使用）
├── fallback/       # 离线应急页（启动失败时自动打开的「关于这个系统」）
├── setup_env.bat   # 一键部署环境脚本
├── run_system.bat  # 一键启动系统脚本
├── admin_gui.py    # 数据库管理工具（GUI）
└── README.md       # 项目说明
```

## 目录说明

| 目录 | 说明 |
|------|------|
| `backend/` | Flask后端代码，包含API路由、业务逻辑、数据库模型 |
| `data/` | **统一数据目录**，含数据库、学生作品、更新缓存与备份。升级时只需保留此目录 |
| `frontend/` | React前端代码，包含页面组件、API服务封装 |
| `assets/` | 资源保险箱：站点图片等以密文归档，运行期由后端解密到内存、明文不落盘（见 `assets/README.md`） |
| `docs/` | 项目文档，包含系统说明书、部署指南、操作手册 |
| `scripts/` | 辅助脚本，包含数据库脚本、调试脚本等 |
| `runtime/` | 由 `setup_env.bat` 自动管理的运行时目录：`runtime\node` 为自动下载的便携 Node.js，`runtime\python` 可手动放入便携 Python 供离线使用。机器本地文件，不入版本库 |
| `backup/` | 备用脚本：`run_system_backup.bat` 与 `setup_env_backup.bat`，主脚本被删除时可直接双击使用。改动主脚本后请同步更新 |
| `fallback/` | 离线应急页：系统起不来时由 `run_system.bat` 自动打开的「关于这个系统」单文件 HTML，不需要框架与服务器。改完系统内 About 页后用 `scripts/build_about_fallback.py` 重新生成 |
## 更新说明

系统内置自动更新模块。以老师或社长账号登录后，在「系统设置 → 系统更新」中检查并安装：

- 优先通过 `git pull` 拉取（要求部署目录是 git 克隆且工作区干净）
- 不可用时自动回退到 GitHub Release 更新包
- 检查在后台异步进行，不会阻塞启动；安装必须由管理员确认
- 数据库、上传文件与更新器配置受保护，写入前自动备份，失败自动回滚

命令行方式：`cd backend && python -m updater check`

详细说明见 [docs/UPDATE_GUIDE.md](docs/UPDATE_GUIDE.md)。

## 文档

详细文档请查看 `docs/` 目录：

- `AIGC探索社信息系统说明书.pdf` - 系统完整说明书
- `SYSTEM_MANUAL.md` - 管理员操作手册
- `USER_MANUAL.md` - 用户操作手册
- `DEPLOY_LAN.md` - 局域网部署指南
- `ENVIRONMENT.md` - 环境配置说明
- `PROJECT_STRUCTURE.md` - 项目结构说明
- `UPDATE_GUIDE.md` - 系统更新指南（更新机制、配置、安全设计与故障排查）

## License

MIT License