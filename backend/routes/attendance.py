from flask import Blueprint, request, jsonify, g
from datetime import datetime, date
from models import db, Attendance, User, SystemConfig
from utils.decorators import token_required, teacher_required, privileged_required
from services.attendance_stats_service import AttendanceStatsService

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
    start_date, end_date = AttendanceStatsService.get_semester_config()
    total_days = AttendanceStatsService.calculate_total_days(start_date, end_date)
    
    if g.current_user.role == 'student':
        stats = AttendanceStatsService.get_student_stats(
            g.current_user.id,
            start_date,
            end_date,
            total_days
        )
        stats['totalDays'] = total_days
        return jsonify(stats)
    else:
        return jsonify(AttendanceStatsService.get_all_students_stats(
            start_date,
            end_date,
            total_days
        ))

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
