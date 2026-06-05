from flask import Blueprint, jsonify, send_from_directory, request, abort
import os
import hashlib
from datetime import datetime

update_bp = Blueprint('update', __name__, url_prefix='/api/update')

MOCK_VERSION_INFO = {
    'version': '1.1.0',
    'download_url': 'http://localhost:5000/api/update/download',
    'checksum': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    'checksum_type': 'sha256',
    'size': 0,
    'release_notes': '1.1.0 更新说明:\n\n新增功能:\n- 新增自动更新功能\n- 优化签到系统\n- 改进作品管理界面\n\n修复问题:\n- 修复成员列表搜索bug\n- 修复文件下载异常',
    'min_required_version': '1.0.0'
}


@update_bp.route('/check', methods=['GET'])
def check_update():
    """检查版本更新"""
    return jsonify(MOCK_VERSION_INFO)


@update_bp.route('/download', methods=['GET'])
def download_update():
    """下载更新包（支持断点续传）"""
    update_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'updates')
    version = MOCK_VERSION_INFO['version']
    filename = f'update_{version}.zip'
    file_path = os.path.join(update_dir, filename)

    if not os.path.exists(file_path):
        create_mock_update_package(update_dir, filename)

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get('Range', None)

    if range_header:
        start, end = parse_range_header(range_header, file_size)
        if start >= file_size:
            abort(416)

        chunk_size = end - start + 1
        with open(file_path, 'rb') as f:
            f.seek(start)
            data = f.read(chunk_size)

        response = jsonify({'status': 'partial', 'data': data.decode('latin-1')})
        response.headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        response.headers['Content-Length'] = str(chunk_size)
        response.headers['Content-Type'] = 'application/octet-stream'
        response.status_code = 206
        return response
    else:
        return send_from_directory(update_dir, filename, as_attachment=True)


def parse_range_header(range_header: str, file_size: int):
    """解析Range请求头"""
    range_header = range_header.strip()
    if range_header.startswith('bytes='):
        range_header = range_header[6:]

    if '-' in range_header:
        start_str, end_str = range_header.split('-', 1)
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1
        return start, min(end, file_size - 1)
    return 0, file_size - 1


def create_mock_update_package(update_dir: str, filename: str):
    """创建模拟更新包"""
    os.makedirs(update_dir, exist_ok=True)

    import zipfile
    file_path = os.path.join(update_dir, filename)

    with zipfile.ZipFile(file_path, 'w') as zip_ref:
        zip_ref.writestr('version.json', jsonify({
            'version': MOCK_VERSION_INFO['version'],
            'installed_at': datetime.now().isoformat(),
            'release_notes': MOCK_VERSION_INFO['release_notes']
        }).get_data())
        zip_ref.writestr('README.md', f'# AIGC社信息系统 v{MOCK_VERSION_INFO["version"]}\n\n更新说明:\n{MOCK_VERSION_INFO["release_notes"]}')
        zip_ref.writestr('app.py', '# Mock updated app\nprint("Updated version!")')

    with open(file_path, 'rb') as f:
        checksum = hashlib.sha256(f.read()).hexdigest()

    MOCK_VERSION_INFO['size'] = os.path.getsize(file_path)
    MOCK_VERSION_INFO['checksum'] = checksum


@update_bp.route('/info', methods=['GET'])
def get_update_info():
    """获取完整更新信息"""
    return jsonify(MOCK_VERSION_INFO)