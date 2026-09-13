from flask import Flask
from flask_cors import CORS
from config import Config
from models import db
import os
import threading

# 保证同一进程内只调度一次启动检查
_startup_check_lock = threading.Lock()
_startup_check_started = False


def start_updater():
    """在后台异步启动更新模块。

    刻意不做的事（这些正是旧实现的问题）：
      * 不在启动路径上同步检查/下载/安装——旧版会在 app.run() 之前
        同步下载整个更新包并覆盖源码，导致服务启动被阻塞甚至被改坏；
      * 不自动安装——安装必须由管理员在界面确认（除非显式打开 auto_install）。
    """
    global _startup_check_started
    with _startup_check_lock:
        if _startup_check_started:
            return
        _startup_check_started = True

    if os.environ.get('AIGC_UPDATE_SKIP_STARTUP'):
        print("[更新] 已通过 AIGC_UPDATE_SKIP_STARTUP 跳过启动检查")
        return

    try:
        from updater import get_service

        service = get_service()
        for warning in service.cfg.get('_warnings', []):
            print(f"[更新] 配置提示: {warning}")
        service.start_startup_check()
        service.start_periodic_check()
    except Exception as exc:  # noqa: BLE001 - 更新模块故障不应影响系统启动
        print(f"[更新] 更新模块初始化失败（不影响系统运行）: {exc}")


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 统一数据目录：创建 <项目根>/data/，并把旧位置的数据
    # （backend/instance、backend/uploads、backend/updates、backend/backup）
    # 自动迁移过来。必须在访问数据库之前执行。
    try:
        from updater.datalayout import ensure_layout, format_report

        layout = ensure_layout()
        for line in format_report(layout).splitlines():
            print(f"[数据] {line}")
        for error in layout.get("errors", []):
            print(f"[数据] !! {error}")
    except Exception as exc:  # noqa: BLE001 - 数据目录问题不应阻止启动
        print(f"[数据] 数据目录初始化失败（不影响启动）: {exc}")

    # Enable CORS for frontend (Allow all origins for LAN dev)
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    # Initialize database
    db.init_app(app)

    # Ensure upload folder exists
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    # Register blueprints
    from routes.auth import auth_bp
    from routes.members import members_bp
    from routes.works import works_bp
    from routes.attendance import attendance_bp
    from routes.announcements import announcements_bp
    from routes.update import update_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(members_bp)
    app.register_blueprint(works_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(announcements_bp)
    app.register_blueprint(update_bp)

    # Create tables
    with app.app_context():
        db.create_all()

    # Health check endpoint
    @app.route('/api/health')
    def health():
        return {'status': 'ok', 'message': 'AIGC Society Backend is running'}

    # 在应用创建后调度后台检查：这样无论是 python app.py 还是 flask run
    # 都能生效（旧实现只在 __main__ 里调用，用 flask run 启动时永远不会检查）。
    start_updater()

    return app


app = create_app()


if __name__ == '__main__':
    print("=" * 60)
    print("AIGC社信息系统启动中...")
    print("=" * 60)
    app.run(debug=False, port=5000)
