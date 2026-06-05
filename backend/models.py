from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # student, teacher, president
    student_id = db.Column(db.String(20), unique=True)
    class_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    works = db.relationship('Work', backref='author', lazy='dynamic')
    attendances = db.relationship('Attendance', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.username,
            'username': self.username,
            'role': self.role,
            'studentId': self.student_id,
            'class': self.class_name,
            'lastLogin': self.last_login.isoformat() if self.last_login else None,
            'createdAt': self.created_at.strftime('%Y-%m-%d') if self.created_at else None,
            'status': 'online' if self.last_login and (datetime.utcnow() - self.last_login).seconds < 3600 else 'offline',
            'isActive': self.is_active
        }

class Work(db.Model):
    __tablename__ = 'works'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(500))
    original_name = db.Column(db.String(500))
    file_type = db.Column(db.String(50))
    status = db.Column(db.String(20), default='success')  # pending, processing, success, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'date': self.created_at.strftime('%Y-%m-%d'),
            'status': self.status,
            'type': self.file_type,
            'userId': self.user_id,
            'fileName': self.file_path,
            'originalName': self.original_name or self.file_path
        }

class Attendance(db.Model):
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    semester_term = db.Column(db.String(50))
    
    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'time': self.time.strftime('%H:%M:%S'),
            'semester': self.semester_term
        }

class SystemConfig(db.Model):
    __tablename__ = 'system_config'
    
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.String(500))
    
    @staticmethod
    def get_value(key, default=None):
        config = SystemConfig.query.get(key)
        return config.value if config else default
    
    @staticmethod
    def set_value(key, value):
        config = SystemConfig.query.get(key)
        if config:
            config.value = value
        else:
            config = SystemConfig(key=key, value=value)
            db.session.add(config)
        db.session.commit()

class Announcement(db.Model):
    __tablename__ = 'announcements'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    tag = db.Column(db.String(50), default='通知')  # 活动, 通知, 必读
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    author = db.relationship('User', backref='announcements')
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'tag': self.tag,
            'date': self.created_at.strftime('%Y-%m-%d'),
            'createdBy': self.created_by,
            'authorName': self.author.username if self.author else None
        }

