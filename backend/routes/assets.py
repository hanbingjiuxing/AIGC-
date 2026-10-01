"""站点运行期资源：用到时才从保险箱解密，明文不落盘。

`frontend/public/` 里不再放这类图片。仓库与发布包里只有 `assets/encrypted/`
下的密文；浏览器请求这个接口时才解密到**内存**并直接返回，进程退出即消失——
磁盘上任何时候都不会留下明文，所以也不需要"关闭后清理"。

新增一个站点资源：
    1. python scripts/asset_vault.py encrypt <明文> --out assets/encrypted/<名字>.enc
    2. 在 SITE_ASSETS 里加一条即可

密钥缺失（例如换了一台机器部署、没把 data/secrets/asset-vault.key 带过来）时
返回 404 而不是 500，前端 <img onError> 会退回到社徽，不会出现裂图。
"""

from io import BytesIO

from flask import Blueprint, current_app, jsonify, send_file

from utils.asset_vault import DEFAULT_KEY_FILE, PROJECT_ROOT, VaultError, decrypt_plaintext

assets_bp = Blueprint('assets', __name__, url_prefix='/api/assets')

#: 资源名 -> (密文路径[相对项目根], MIME 类型)
SITE_ASSETS = {
    'avatar': ('assets/encrypted/tx.web.png.enc', 'image/png'),
}

#: 进程内缓存：资源名 -> (明文, etag)。每个进程只解密一次。
_cache = {}


def load_asset(name):
    """解密并缓存，返回 (明文 bytes, etag)。解密失败抛 VaultError。"""
    cached = _cache.get(name)
    if cached is not None:
        return cached
    rel, _mimetype = SITE_ASSETS[name]
    data, header = decrypt_plaintext(PROJECT_ROOT / rel, DEFAULT_KEY_FILE, False)
    # 明文摘要稳定不变，直接拿来做 ETag，重复访问走 304，不必再解密
    etag = header['source_sha256']
    _cache[name] = (data, etag)
    return data, etag


@assets_bp.route('/<name>', methods=['GET'])
def get_asset(name):
    entry = SITE_ASSETS.get(name)
    if entry is None:
        return jsonify({'error': f'未知资源: {name}'}), 404

    try:
        data, etag = load_asset(name)
    except VaultError as exc:
        current_app.logger.warning('[资源] %s 解密失败: %s', name, exc)
        return jsonify({'error': '资源暂不可用', 'detail': str(exc)}), 404

    return send_file(BytesIO(data), mimetype=entry[1], max_age=86400, etag=etag)
