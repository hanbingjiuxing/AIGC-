# AIGC 社团信息系统 - 环境与依赖说明

## 系统要求

| 项目 | 最低版本 | 推荐版本 |
|------|---------|---------|
| **Node.js** | 18.x | 20.x+ |
| **Python** | 3.10+ | 3.12+ |
| **npm** | 9.x | 10.x+ |

---

## 后端依赖 (Python)

安装命令:
```bash
cd backend
pip install -r requirements.txt
```

| 包名 | 版本 | 用途 |
|------|------|------|
| `flask` | ≥2.3.0 | Web 框架 |
| `flask-cors` | ≥4.0.0 | 跨域支持 |
| `flask-sqlalchemy` | ≥3.1.0 | ORM 数据库 |
| `PyJWT` | ≥2.8.0 | JWT 认证 |
| `Werkzeug` | ≥2.3.0 | 密码哈希 |

> 数据库: SQLite (内置，无需额外安装)

---

## 前端依赖 (Node.js)

安装命令:
```bash
cd frontend
npm install
```

### 生产依赖
| 包名 | 版本 | 用途 |
|------|------|------|
| `react` | ^19.2.0 | UI 框架 |
| `react-dom` | ^19.2.0 | DOM 渲染 |
| `react-router-dom` | ^7.10.1 | 路由管理 |
| `axios` | ^1.13.2 | HTTP 请求 |
| `lucide-react` | ^0.561.0 | 图标库 |

### 开发依赖
| 包名 | 用途 |
|------|------|
| `vite` ^7.2.4 | 开发服务器 & 构建 |
| `@vitejs/plugin-react` | React 支持 |
| `eslint` | 代码检查 |
| `tailwindcss` | CSS 框架 |
| `autoprefixer` / `postcss` | CSS 处理 |

---

## 快速安装

```bash
# 1. 安装后端依赖
cd backend
pip install -r requirements.txt

# 2. 安装前端依赖
cd ../frontend
npm install

# 3. 初始化数据库 (可选)
cd ../backend
python seed.py
```

---

## 启动方式

### 方式一：一键启动 (推荐)
```bash
双击运行 run_system.bat
```

### 方式二：手动启动
```bash
# 终端1 - 后端
cd backend
flask run --host=0.0.0.0

# 终端2 - 前端
cd frontend
npm run dev:lan
```

---

## 端口说明

| 服务 | 端口 | 地址 |
|------|------|------|
| 后端 API | 5000 | http://localhost:5000/api |
| 前端页面 | 5173 | http://localhost:5173 |

---

## 目录结构

```
AIGC社信息系统/
├── backend/                 # 后端代码
│   ├── app.py              # Flask 入口
│   ├── models.py           # 数据库模型
│   ├── config.py           # 配置文件
│   ├── routes/             # API 路由
│   ├── utils/              # 工具函数
│   ├── uploads/            # 文件上传目录
│   ├── requirements.txt    # Python 依赖
│   ├── seed.py             # 初始化数据
│   ├── admin_tool.py       # CLI 管理工具
│   └── admin_gui.py        # GUI 管理工具
├── frontend/                # 前端代码
│   ├── src/                # 源代码
│   ├── package.json        # Node 依赖
│   └── vite.config.js      # Vite 配置
├── run_system.bat          # 一键启动脚本
└── DEPLOY_LAN.md           # 局域网部署指南
```
