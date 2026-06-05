from flask import Blueprint, request, jsonify, g, send_from_directory, current_app
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from models import db, Work
from config import Config
from utils.decorators import token_required, privileged_required

works_bp = Blueprint('works', __name__, url_prefix='/api/works')

@works_bp.route('', methods=['GET'])
@token_required
def get_works():
    user_id = request.args.get('user_id', type=int)
    
    # Students can only see their own works
    if g.current_user.role == 'student':
        works = Work.query.filter_by(user_id=g.current_user.id).order_by(Work.created_at.desc()).all()
    else:
        # Teachers and presidents can see all or filter by user
        if user_id:
            works = Work.query.filter_by(user_id=user_id).order_by(Work.created_at.desc()).all()
        else:
            works = Work.query.order_by(Work.created_at.desc()).all()
    
    return jsonify({
        'works': [w.to_dict() for w in works]
    })

@works_bp.route('/upload', methods=['POST'])
@token_required
def upload_work():
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    
    file = request.files['file']
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    
    if not title:
        title = file.filename
    
    # Allow all files
    filename = secure_filename(file.filename)
    # Add timestamp to avoid conflicts
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
    filename = timestamp + filename
    
    # Ensure upload directory exists
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    
    file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
    file.save(file_path)
    
    # Determine file type
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext in ['png', 'jpg', 'jpeg', 'gif']:
        file_type = 'image'
    elif ext in ['mp4']:
        file_type = 'video'
    elif ext in ['mp3']:
        file_type = 'audio'
    elif ext in ['py', 'cpp', 'c']:
        file_type = 'code'
    elif ext in ['pdf', 'doc', 'docx']:
        file_type = 'document'
    else:
        file_type = ext if ext else 'other'
    
    # Create work record
    work = Work(
        user_id=g.current_user.id,
        title=title,
        description=description,
        file_path=filename,
        original_name=file.filename,
        file_type=file_type,
        status='success'
    )
    
    db.session.add(work)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '作品上传成功',
        'work': work.to_dict()
    }), 201

@works_bp.route('/<int:id>/file', methods=['GET'])
@token_required
def download_work(id):
    from flask import send_file
    work = Work.query.get_or_404(id)
    
    # Check permission
    if g.current_user.role == 'student' and work.user_id != g.current_user.id:
        return jsonify({'error': '无权访问此文件'}), 403
    
    file_path = os.path.join(Config.UPLOAD_FOLDER, work.file_path)
    if not os.path.exists(file_path):
        return jsonify({'error': '文件不存在'}), 404
        
    return send_file(
        file_path,
        as_attachment=True,
        download_name=work.original_name or work.file_path,
        mimetype='application/octet-stream'
    )

@works_bp.route('/stats', methods=['GET'])
@token_required
def get_stats():
    if g.current_user.role == 'student':
        # Student sees only their own stats
        total = Work.query.filter_by(user_id=g.current_user.id).count()
        success = Work.query.filter_by(user_id=g.current_user.id, status='success').count()
        failed = Work.query.filter_by(user_id=g.current_user.id, status='failed').count()
    else:
        # Teachers/presidents see all stats
        total = Work.query.count()
        success = Work.query.filter_by(status='success').count()
        failed = Work.query.filter_by(status='failed').count()
    
    return jsonify({
        'total': total,
        'success': success,
        'failed': failed
    })
