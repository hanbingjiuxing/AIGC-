from models import db, Attendance, User
from datetime import datetime


def get_attendance(user_id: int = None, role: str = 'student', current_user_id: int = None):
    if role == 'student':
        return Attendance.query.filter_by(user_id=current_user_id).order_by(Attendance.date.desc(), Attendance.time.desc()).all()
    else:
        if user_id:
            return Attendance.query.filter_by(user_id=user_id).order_by(Attendance.date.desc(), Attendance.time.desc()).all()
        return Attendance.query.order_by(Attendance.date.desc(), Attendance.time.desc()).all()


def record_attendance(user_id: int, semester_term: str = '') -> Attendance:
    now = datetime.now()
    date = now.date()
    time = now.time()
    
    attendance = Attendance(
        user_id=user_id,
        date=date,
        time=time,
        semester_term=semester_term
    )
    
    db.session.add(attendance)
    db.session.commit()
    
    return attendance


def get_attendance_stats(user_id: int = None, role: str = 'student', current_user_id: int = None):
    if role == 'student':
        total = Attendance.query.filter_by(user_id=current_user_id).count()
        monthly_counts = {}
        for attendance in Attendance.query.filter_by(user_id=current_user_id):
            key = attendance.date.strftime('%Y-%m')
            monthly_counts[key] = monthly_counts.get(key, 0) + 1
    else:
        total = Attendance.query.count()
        monthly_counts = {}
        for attendance in Attendance.query.all():
            key = attendance.date.strftime('%Y-%m')
            monthly_counts[key] = monthly_counts.get(key, 0) + 1
    
    return {'total': total, 'monthly': monthly_counts}