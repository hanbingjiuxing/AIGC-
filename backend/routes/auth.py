from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
import jwt
from models import db, User
from config import Config
from utils.decorators import token_required

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '请求数据为空'}), 400
    
    account = data.get('account', '').strip()
    password = data.get('password', '')
    
    if not account or not password:
        return jsonify({'error': '账号或密码不能为空'}), 400
    
    # Find user by username or student_id
    user = User.query.filter(
        (User.username == account) | (User.student_id == account)
    ).first()
    
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    
    if not user.is_active:
        return jsonify({'error': '账号异常，请联系管理员'}), 403
    
    if not user.check_password(password):
        return jsonify({'error': '密码错误'}), 401
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    # Generate JWT token
    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(hours=Config.JWT_EXPIRATION_HOURS)
    }, Config.SECRET_KEY, algorithm='HS256')
    
    return jsonify({
        'token': token,
        'user': user.to_dict()
    })

@auth_bp.route('/change_password', methods=['POST'])
@token_required
def change_password():
    data = request.get_json()
    
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    
    if not current_password or not new_password:
        return jsonify({'error': '请填写所有字段'}), 400
    
    if not g.current_user.check_password(current_password):
        return jsonify({'error': '当前密码错误'}), 401
    
    if len(new_password) < 6:
        return jsonify({'error': '新密码长度至少6位'}), 400
    
    g.current_user.set_password(new_password)
    db.session.commit()
    
    return jsonify({'success': True, 'message': '密码修改成功'})

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user():
    return jsonify({'user': g.current_user.to_dict()})
