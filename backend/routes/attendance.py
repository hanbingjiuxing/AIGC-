from flask import Blueprint, request, jsonify, g
from datetime import datetime, date
from models import db, Attendance, User, SystemConfig
from utils.decorators import token_required, teacher_required, privileged_required

attendance_bp = Blueprint('attendance', __name__, url_prefix='/api/attendance')

@attendance_bp.route('/signin', methods=['POST'])
@token_required
def signin():
    today = date.today()
    now = datetime.now().time()
    
    # Check if already signed in today
    existing = Attendance.query.filter_by(
        user_id=g.current_user.id,
        date=today
    ).first()
    
    if existing:
        return jsonify({
            'success': False,
            'message': '今日已签到',
            'attendance': existing.to_dict()
        }), 409
    
    # Get current semester term
    semester_start = SystemConfig.get_value('semester_start', '2023-09-01')
    semester_end = SystemConfig.get_value('semester_end', '2024-01-31')
    semester_term = f"{semester_start[:4]}-{'春季' if int(semester_start[5:7]) < 7 else '秋季'}"
    
    # Create attendance record
    attendance = Attendance(
        user_id=g.current_user.id,
        date=today,
        time=now,
        semester_term=semester_term
    )
    
    db.session.add(attendance)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '签到成功',
        'attendance': attendance.to_dict()
    })

@attendance_bp.route('/history', methods=['GET'])
@token_required
def get_history():
    attendances = Attendance.query.filter_by(
        user_id=g.current_user.id
    ).order_by(Attendance.date.desc()).limit(30).all()
    
    return jsonify({
        'history': [a.to_dict() for a in attendances]
    })

@attendance_bp.route('/stats', methods=['GET'])
@token_required
def get_stats():
    semester_start = SystemConfig.get_value('semester_start', '2023-09-01')
    semester_end = SystemConfig.get_value('semester_end', '2024-01-31')
    
    start_date = datetime.strptime(semester_start, '%Y-%m-%d').date()
    end_date = datetime.strptime(semester_end, '%Y-%m-%d').date()
    today = date.today()
    
    # Calculate total possible days (weekdays only approximation)
    total_days = (min(today, end_date) - start_date).days + 1
    if total_days < 0:
        total_days = 0
    
    if g.current_user.role == 'student':
        # Student sees their own stats
        attendance_count = Attendance.query.filter(
            Attendance.user_id == g.current_user.id,
            Attendance.date >= start_date,
            Attendance.date <= end_date
        ).count()
        
        rate = round((attendance_count / total_days * 100) if total_days > 0 else 0, 1)
        
        # Check if signed in today
        today_signed = Attendance.query.filter_by(
            user_id=g.current_user.id,
            date=today
        ).first() is not None
        
        return jsonify({
            'total': attendance_count,
            'totalDays': total_days,
            'rate': rate,
            'todaySigned': today_signed
        })
    else:
        # Teacher/President sees all student stats
        students = User.query.filter(
            User.is_active == True,
            User.role == 'student'
        ).all()
        
        student_stats = []
        total_signed_today = 0
        
        for student in students:
            count = Attendance.query.filter(
                Attendance.user_id == student.id,
                Attendance.date >= start_date,
                Attendance.date <= end_date
            ).count()
            
            rate = round((count / total_days * 100) if total_days > 0 else 0, 1)
            
            # Check today
            signed_today = Attendance.query.filter_by(
                user_id=student.id,
                date=today
            ).first() is not None
            
            if signed_today:
                total_signed_today += 1
            
            student_stats.append({
                'id': student.id,
                'name': student.username,
                'total': count,
                'rate': rate,
                'signedToday': signed_today
            })
        
        return jsonify({
            'students': student_stats,
            'totalStudents': len(students),
            'signedToday': total_signed_today,
            'totalDays': total_days
        })

@attendance_bp.route('/config', methods=['GET'])
@token_required
def get_config():
    return jsonify({
        'semesterStart': SystemConfig.get_value('semester_start', '2023-09-01'),
        'semesterEnd': SystemConfig.get_value('semester_end', '2024-01-31')
    })

@attendance_bp.route('/config', methods=['POST'])
@token_required
@teacher_required
def set_config():
    data = request.get_json()
    
    if 'semesterStart' in data:
        SystemConfig.set_value('semester_start', data['semesterStart'])
    if 'semesterEnd' in data:
        SystemConfig.set_value('semester_end', data['semesterEnd'])
    
    return jsonify({
        'success': True,
        'message': '配置已更新'
    })
