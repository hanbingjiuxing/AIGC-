from functools import wraps
from flask import request, jsonify, g
import jwt
from config import Config
from models import User

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'error': '缺少认证令牌'}), 401
        
        try:
            data = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
            if not current_user or not current_user.is_active:
                return jsonify({'error': '用户不存在或已被禁用'}), 401
            g.current_user = current_user
        except jwt.ExpiredSignatureError:
            return jsonify({'error': '令牌已过期'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': '无效的令牌'}), 401
        
        return f(*args, **kwargs)
    return decorated

def teacher_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if g.current_user.role != 'teacher':
            return jsonify({'error': '需要老师权限'}), 403
        return f(*args, **kwargs)
    return decorated

def privileged_required(f):
    """Requires teacher or president role (includes token validation)"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # First, do token validation (same as token_required)
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'error': '缺少认证令牌'}), 401
        
        try:
            data = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
            if not current_user or not current_user.is_active:
                return jsonify({'error': '用户不存在或已被禁用'}), 401
            g.current_user = current_user
        except jwt.ExpiredSignatureError:
            return jsonify({'error': '令牌已过期'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': '无效的令牌'}), 401
        
        # Then check role
        if g.current_user.role not in ['teacher', 'president']:
            return jsonify({'error': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated

