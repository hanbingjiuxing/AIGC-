# AIGC社信息系统 - 项目结构说明

## 项目概述

本项目是厦门大学附属科技中学AIGC探索社的信息管理系统，采用前后端分离架构，包含成员管理、作品管理、考勤管理和公告管理等核心功能。

## 目录结构

```
AIGC社信息系统/
├── backend/                    # 后端代码（Flask）
│   ├── app.py                  # Flask应用入口
│   ├── config.py               # 全局配置
│   ├── models.py               # 数据库模型
│   ├── requirements.txt        # Python依赖
│   ├── version.json            # 版本信息
│   ├── routes/                 # API路由层
│   │   ├── __init__.py
│   │   ├── auth.py             # 认证相关API
│   │   ├── members.py          # 成员管理API
│   │   ├── works.py            # 作品管理API
│   │   ├── attendance.py       # 考勤管理API
│   │   ├── announcements.py    # 公告管理API
│   │   ├── update.py           # 更新相关API
│   │   └── assets.py           # 站点资源API（按需解密，明文不落盘）
│   ├── services/               # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── user_service.py     # 用户业务逻辑
│   │   ├── work_service.py     # 作品业务逻辑
│   │   ├── attendance_service.py # 考勤业务逻辑
│   │   └── announcement_service.py # 公告业务逻辑
│   ├── utils/                  # 工具函数
│   │   ├── __init__.py
│   │   └── decorators.py       # 装饰器（权限验证等）
│   ├── updater/                # 自动更新模块
│   │   ├── __init__.py         # 对外入口（get_service）
│   │   ├── paths.py            # 路径解析（锚定 __file__，不依赖 CWD）
│   │   ├── version.py          # 版本号解析、比较与版本记录读写
│   │   ├── settings.py         # 配置加载（默认值 + config.json + 环境变量）
│   │   ├── sources.py          # 更新来源：git pull / GitHub Release
│   │   ├── installer.py        # 安全安装（zip-slip 防护、保护清单、备份回滚）
│   │   ├── service.py          # 状态机 + 后台线程编排
│   │   ├── __main__.py         # 命令行入口
│   │   └── config.json         # 更新配置
├── data/                       # 【统一数据目录】升级时唯一需要保留的目录
│   ├── instance/               #   SQLite 数据库
│   │   └── aigc_society.db     #     用户、考勤、公告
│   ├── uploads/                #   学生作品与上传文件
│   ├── updates/                #   更新包下载缓存
│   └── backups/                #   更新前备份（含用户数据快照）
├── assets/                     # 资源保险箱：不宜明文入库的源文件密文归档
│   ├── README.md               #   说明、密钥位置与还原步骤
│   └── encrypted/              #   密文（AES-256-GCM）
│       ├── tx.web.png.enc      #     网页版头像，/api/assets/avatar 运行期解密返回
│       └── tx.png.enc          #     母版原图（仅归档）
├── fallback/                   # 离线应急页（系统起不来时用）
│   ├── README.md               #   这一页是什么、怎么重新生成
│   └── about.html              #   单文件「关于这个系统」，无需框架/服务器，双击可开
├── frontend/                   # 前端代码（React + Vite）
│   ├── public/                 # 静态资源
│   ├── src/                    # 源代码
│   │   ├── components/         # 组件
│   │   │   └── dashboard/      # 仪表盘组件
│   │   ├── pages/              # 页面
│   │   ├── services/           # API服务层
│   │   ├── App.jsx             # 主应用组件
│   │   ├── main.jsx            # 入口文件
│   │   └── index.css           # 全局样式
│   ├── package.json            # Node.js依赖
│   └── vite.config.js          # Vite配置
├── docs/                       # 文档
│   ├── AIGC探索社信息系统说明书.pdf
│   ├── DEPLOY_LAN.md           # 局域网部署指南
│   ├── ENVIRONMENT.md          # 环境配置说明
│   ├── SYSTEM_MANUAL.md        # 系统管理员手册
│   ├── USER_MANUAL.md          # 用户操作手册
│   └── PROJECT_STRUCTURE.md    # 项目结构说明（本文件）
├── scripts/                    # 脚本文件
│   ├── run_system.bat          # 系统启动脚本
│   ├── setup_env.bat           # 环境搭建脚本
│   ├── seed.py                 # 数据库初始化脚本
│   ├── fix_db.py               # 数据库修复脚本
│   ├── update_db_v2.py         # 数据库升级脚本
│   ├── admin_gui.py            # 管理员图形界面
│   ├── admin_tool.py           # 管理员工具
│   ├── debug_*.py              # 调试脚本
│   ├── build_about_fallback.py # 生成离线版「关于这个系统」页（fallback/about.html）
│   └── generate_ssh_key.ps1    # SSH密钥生成脚本
└── README.md                   # 项目说明（待创建）
```

## 模块说明

### backend/

后端采用 Flask 框架，遵循分层架构设计：

| 目录/文件 | 职责 |
|-----------|------|
| `app.py` | 应用入口，初始化 Flask 应用，注册蓝图，后台异步调度更新检查（不阻塞启动） |
| `config.py` | 全局配置，包含数据库连接、JWT配置、文件上传限制等；数据统一放在 `data/` |
| `models.py` | 数据库模型定义，使用 SQLAlchemy ORM |
| `routes/` | API路由层，处理HTTP请求，调用服务层，返回响应 |
| `services/` | 业务逻辑层，封装核心业务逻辑，与数据库交互 |
| `utils/` | 工具函数，包含装饰器、通用工具等 |
| `updater/` | 更新模块：git pull 优先、GitHub Release 回退；异步检查、手动确认安装、数据保护与自动回滚 |
| `data/` | **统一数据目录**：数据库、学生作品、更新缓存与备份；升级时只需保留这一个目录 |

### frontend/

前端采用 React + Vite 框架：

| 目录/文件 | 职责 |
|-----------|------|
| `public/` | 静态资源文件 |
| `src/components/` | React组件，按功能模块组织 |
| `src/pages/` | 页面级组件 |
| `src/services/` | API服务封装 |
| `src/App.jsx` | 主应用组件，路由配置 |

### docs/

文档目录，存放项目相关文档：

| 文件 | 内容 |
|------|------|
| `AIGC探索社信息系统说明书.pdf` | 系统完整说明书 |
| `DEPLOY_LAN.md` | 局域网部署步骤 |
| `ENVIRONMENT.md` | 开发环境配置说明 |
| `SYSTEM_MANUAL.md` | 管理员操作手册 |
| `USER_MANUAL.md` | 用户操作手册 |
| `PROJECT_STRUCTURE.md` | 项目结构说明 |

### scripts/

脚本目录，存放辅助脚本：

| 文件 | 用途 |
|------|------|
| `run_system.bat` | Windows启动脚本 |
| `setup_env.bat` | 环境搭建脚本 |
| `seed.py` | 数据库初始化，创建管理员账户 |
| `fix_db.py` | 数据库修复工具 |
| `update_db_v2.py` | 数据库版本升级脚本 |
| `admin_gui.py` | 管理员图形界面工具 |
| `admin_tool.py` | 管理员命令行工具 |
| `asset_vault.py` | 资源保险箱命令行入口（实现见 `backend/utils/asset_vault.py`） |
| `debug_*.py` | 调试脚本 |
| `build_about_fallback.py` | 把系统内的「关于这个系统」页复制成单文件离线页 `fallback/about.html`（`--check` 只校验是否最新） |

## 技术栈

- **后端**: Python 3.x + Flask + SQLAlchemy + JWT
- **前端**: React + Vite + Axios
- **数据库**: SQLite
- **部署**: Flask开发服务器 / WSGI服务器

## 启动方式

### 开发环境

1. 安装后端依赖：
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. 初始化数据库：
   ```bash
   python scripts/seed.py
   ```

3. 启动后端：
   ```bash
   python app.py
   ```

4. 启动前端：
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

### 生产环境

参考 `docs/DEPLOY_LAN.md` 进行部署配置。

## 模块间依赖关系

```
routes/ (API路由)
    │
    ├──► services/ (业务逻辑)
    │       │
    │       ├──► models.py (数据库模型)
    │       │       └──► config.py (配置)
    │       │
    │       └──► config.py (配置)
    │
    ├──► utils/decorators.py (权限验证)
    │       ├──► config.py (配置)
    │       └──► models.py (用户模型)
    │
    └──► config.py (配置)

app.py (入口)
    ├──► routes/ (注册蓝图)
    ├──► config.py (加载配置)
    ├──► models.py (初始化数据库)
    └──► updater/ (后台异步检查更新，不阻塞启动)
```

## 编码规范

### 文件命名

- Python文件：小写蛇形命名（`user_service.py`）
- JavaScript/JSX文件：大驼峰命名（`MemberManagementView.jsx`）
- 配置文件：小写蛇形命名（`config.json`）

### 目录组织

- 按功能模块划分：`routes/`、`services/`、`utils/`
- 避免嵌套过深：最多3层目录结构

### 代码风格

- Python：遵循PEP 8规范
- JavaScript/JSX：使用ESLint检查

## 扩展建议

1. **新增功能模块**: 在 `routes/` 和 `services/` 中添加对应文件
2. **新增工具**: 在 `utils/` 中添加工具函数
3. **新增配置**: 在 `config.py` 中添加配置项
4. **新增文档**: 在 `docs/` 中添加说明文档

## 版本管理

版本信息存储在 `backend/version.json`。更新模块优先通过 `git pull` 获取更新，
不可用时回退到 GitHub Release 更新包；检查在后台异步进行，安装需管理员在
「系统设置 → 系统更新」中确认。详细说明见 [UPDATE_GUIDE.md](./UPDATE_GUIDE.md)。