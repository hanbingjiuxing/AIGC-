from models import db, Work, User
from config import Config
import os
from datetime import datetime
from werkzeug.utils import secure_filename


def get_works(user_id: int = None, role: str = 'student', current_user_id: int = None):
    if role == 'student':
        return Work.query.filter_by(user_id=current_user_id).order_by(Work.created_at.desc()).all()
    else:
        if user_id:
            return Work.query.filter_by(user_id=user_id).order_by(Work.created_at.desc()).all()
        return Work.query.order_by(Work.created_at.desc()).all()


def get_member_works(user_id: int):
    user = User.query.get_or_404(user_id)
    works = Work.query.filter_by(user_id=user_id).order_by(Work.created_at.desc()).all()
    return user, works


def upload_work(user_id: int, file, title: str = '', description: str = '') -> Work:
    if not file or file.filename == '':
        raise ValueError('未选择文件')
    
    if not title:
        title = file.filename
    
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
    filename = timestamp + filename
    
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
    file.save(file_path)
    
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
    
    work = Work(
        user_id=user_id,
        title=title,
        description=description,
        file_path=filename,
        original_name=file.filename,
        file_type=file_type,
        status='success'
    )
    
    db.session.add(work)
    db.session.commit()
    
    return work


def get_work_file_path(work_id: int) -> str:
    work = Work.query.get_or_404(work_id)
    file_path = os.path.join(Config.UPLOAD_FOLDER, work.file_path)
    if not os.path.exists(file_path):
        raise FileNotFoundError('文件不存在')
    return file_path, work.original_name or work.file_path


def get_work_stats(role: str, user_id: int):
    if role == 'student':
        total = Work.query.filter_by(user_id=user_id).count()
        success = Work.query.filter_by(user_id=user_id, status='success').count()
        failed = Work.query.filter_by(user_id=user_id, status='failed').count()
    else:
        total = Work.query.count()
        success = Work.query.filter_by(status='success').count()
        failed = Work.query.filter_by(status='failed').count()
    
    return {'total': total, 'success': success, 'failed': failed}