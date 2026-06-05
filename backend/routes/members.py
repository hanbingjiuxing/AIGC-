from flask import Blueprint, request, jsonify, g
from models import db, User
from utils.decorators import token_required, teacher_required, privileged_required

members_bp = Blueprint('members', __name__, url_prefix='/api/members')

@members_bp.route('', methods=['GET'])
@token_required
@privileged_required
def get_members():
    search = request.args.get('search', '')
    
    query = User.query.filter(User.is_active == True)
    
    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) | 
            (User.student_id.ilike(f'%{search}%'))
        )
    
    members = query.all()
    return jsonify({
        'members': [m.to_dict() for m in members],
        'total': len(members)
    })

@members_bp.route('', methods=['POST'])
@token_required
@teacher_required
def create_member():
    data = request.get_json()
    
    username = data.get('name', '').strip()
    student_id = data.get('studentId', '').strip()
    class_name = data.get('class', '').strip()
    role = data.get('role', 'student')
    
    if not username or not student_id:
        return jsonify({'error': '姓名和学号不能为空'}), 400
    
    # Check if user already exists
    existing = User.query.filter(
        (User.username == username) | (User.student_id == student_id)
    ).first()
    
    if existing:
        return jsonify({'error': '用户名或学号已存在'}), 409
    
    # Create new user with default password (student_id)
    user = User(
        username=username,
        student_id=student_id,
        class_name=class_name,
        role=role
    )
    user.set_password(student_id)  # Default password is student ID
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '成员创建成功',
        'member': user.to_dict()
    }), 201

@members_bp.route('/<int:id>', methods=['PUT'])
@token_required
@teacher_required
def update_member(id):
    user = User.query.get_or_404(id)
    data = request.get_json()
    
    if 'name' in data:
        user.username = data['name'].strip()
    if 'studentId' in data:
        user.student_id = data['studentId'].strip()
    if 'class' in data:
        user.class_name = data['class'].strip()
    if 'role' in data:
        user.role = data['role']
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '成员信息已更新',
        'member': user.to_dict()
    })

@members_bp.route('/<int:id>/reset_password', methods=['POST'])
@token_required
@teacher_required
def reset_password(id):
    user = User.query.get_or_404(id)
    
    # Reset to student ID as default password
    new_password = user.student_id or '123456'
    user.set_password(new_password)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'密码已重置为: {new_password}'
    })

@members_bp.route('/<int:id>', methods=['DELETE'])
@token_required
@teacher_required
def delete_member(id):
    user = User.query.get_or_404(id)
    
    # Soft delete - just deactivate
    user.is_active = False
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '成员已注销'
    })

@members_bp.route('/<int:id>/works', methods=['GET'])
@token_required
@privileged_required
def get_member_works(id):
    from models import Work
    
    user = User.query.get_or_404(id)
    works = Work.query.filter_by(user_id=id).order_by(Work.created_at.desc()).all()
    
    return jsonify({
        'member': user.to_dict(),
        'works': [w.to_dict() for w in works]
    })
