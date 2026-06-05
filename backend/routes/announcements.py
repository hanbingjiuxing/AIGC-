from flask import Blueprint, request, jsonify, g
from models import db, Announcement
from utils.decorators import token_required, privileged_required

announcements_bp = Blueprint('announcements', __name__, url_prefix='/api/announcements')

@announcements_bp.route('', methods=['GET'])
@token_required
def get_announcements():
    """Get all announcements (accessible to all authenticated users)"""
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return jsonify({
        'announcements': [a.to_dict() for a in announcements]
    })

@announcements_bp.route('', methods=['POST'])
@privileged_required
def create_announcement():
    """Create a new announcement (teacher/president only)"""
    data = request.get_json()
    
    if not data.get('title'):
        return jsonify({'error': '标题不能为空'}), 400
    
    announcement = Announcement(
        title=data['title'],
        content=data.get('content', ''),
        tag=data.get('tag', '通知'),
        created_by=g.current_user.id
    )
    
    db.session.add(announcement)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '公告发布成功',
        'announcement': announcement.to_dict()
    }), 201

@announcements_bp.route('/<int:id>', methods=['PUT'])
@privileged_required
def update_announcement(id):
    """Update an announcement (teacher/president only)"""
    announcement = Announcement.query.get_or_404(id)
    data = request.get_json()
    
    if data.get('title'):
        announcement.title = data['title']
    if 'content' in data:
        announcement.content = data['content']
    if data.get('tag'):
        announcement.tag = data['tag']
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '公告更新成功',
        'announcement': announcement.to_dict()
    })

@announcements_bp.route('/<int:id>', methods=['DELETE'])
@privileged_required
def delete_announcement(id):
    """Delete an announcement (teacher/president only)"""
    announcement = Announcement.query.get_or_404(id)
    
    db.session.delete(announcement)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '公告删除成功'
    })
