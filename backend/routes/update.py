"""更新 API。

这是**真实实现**，替换了原先返回硬编码 MOCK_VERSION_INFO 的桩代码。
所有接口都需要老师/社长权限，且只操作后台更新服务，不做同步阻塞。

状态机取值：
    idle / checking / up_to_date / update_available / blocked
    downloading / installing / installed / error
"""

from flask import Blueprint, jsonify, request

from updater import get_service
from utils.decorators import privileged_required

update_bp = Blueprint('update', __name__, url_prefix='/api/update')

VALID_SOURCES = (None, 'auto', 'git', 'release')


@update_bp.route('/status', methods=['GET'])
@privileged_required
def get_status():
    """当前更新状态、进度、最近日志（前端轮询此接口）。"""
    return jsonify(get_service().status())


@update_bp.route('/check', methods=['POST'])
@privileged_required
def check_update():
    """在后台检查更新（立即返回，结果通过 /status 轮询）。"""
    payload = request.get_json(silent=True) or {}
    source = payload.get('source')
    if source not in VALID_SOURCES:
        return jsonify({'error': 'source 只能是 auto、git 或 release'}), 400

    service = get_service()
    accepted = service.start_check(source)
    return jsonify({
        'accepted': accepted,
        'reason': '' if accepted else '已有更新任务正在进行',
        'status': service.status(),
    })


@update_bp.route('/preview', methods=['GET'])
@privileged_required
def preview_update():
    """预览将要变更的文件列表，不修改任何文件。"""
    return jsonify(get_service().preview())


@update_bp.route('/install', methods=['POST'])
@privileged_required
def install_update():
    """安装更新。body: {"dry_run": false} —— dry_run 只预演不落盘。"""
    payload = request.get_json(silent=True) or {}
    dry_run = bool(payload.get('dry_run', False))

    service = get_service()
    accepted = service.start_install(dry_run=dry_run)
    status = service.status()
    return jsonify({
        'accepted': accepted,
        'dry_run': dry_run,
        'reason': '' if accepted else (status.get('error') or '当前没有可安装的更新'),
        'status': status,
    })


@update_bp.route('/restart', methods=['POST'])
@privileged_required
def restart_service():
    """按配置重启后端进程（默认关闭 allow_restart）。"""
    return jsonify(get_service().restart())


@update_bp.route('/log', methods=['GET'])
@privileged_required
def get_log():
    """最近的后台日志行。"""
    service = get_service()
    try:
        limit = max(1, min(300, int(request.args.get('limit', 80))))
    except (TypeError, ValueError):
        limit = 80
    with service._lock:  # noqa: SLF001 - 只读快照
        logs = list(service.logs)[-limit:]
    return jsonify({'state': service.state, 'logs': logs})
