from datetime import datetime, date
from models import db, Attendance, User, SystemConfig
from typing import List, Dict


class AttendanceStatsService:

    @staticmethod
    def get_semester_config() -> tuple[date, date]:
        semester_start = SystemConfig.get_value('semester_start', '2023-09-01')
        semester_end = SystemConfig.get_value('semester_end', '2024-01-31')

        start_date = datetime.strptime(semester_start, '%Y-%m-%d').date()
        end_date = datetime.strptime(semester_end, '%Y-%m-%d').date()

        return start_date, end_date

    @staticmethod
    def calculate_total_days(start_date: date, end_date: date) -> int:
        today = date.today()
        total_days = (min(today, end_date) - start_date).days + 1
        return max(total_days, 0)

    @staticmethod
    def calculate_attendance_rate(attendance_count: int, total_days: int) -> float:
        if total_days == 0:
            return 0.0
        return round((attendance_count / total_days) * 100, 1)

    @staticmethod
    def get_student_attendance_count(user_id: int, start_date: date, end_date: date) -> int:
        return Attendance.query.filter(
            Attendance.user_id == user_id,
            Attendance.date >= start_date,
            Attendance.date <= end_date
        ).count()

    @staticmethod
    def is_signed_today(user_id: int) -> bool:
        today = date.today()
        return Attendance.query.filter_by(
            user_id=user_id,
            date=today
        ).first() is not None

    @staticmethod
    def get_student_stats(user_id: int, start_date: date, end_date: date, total_days: int) -> Dict:
        attendance_count = AttendanceStatsService.get_student_attendance_count(user_id, start_date, end_date)
        rate = AttendanceStatsService.calculate_attendance_rate(attendance_count, total_days)
        signed_today = AttendanceStatsService.is_signed_today(user_id)

        return {
            'total': attendance_count,
            'rate': rate,
            'todaySigned': signed_today
        }

    @staticmethod
    def get_all_students_stats(start_date: date, end_date: date, total_days: int) -> Dict:
        today = date.today()

        students = User.query.filter(
            User.is_active == True,
            User.role == 'student'
        ).all()

        if not students:
            return {
                'students': [],
                'totalStudents': 0,
                'signedToday': 0,
                'totalDays': total_days
            }

        student_ids = [student.id for student in students]

        semester_attendances = db.session.query(
            Attendance.user_id,
            db.func.count(Attendance.id).label('count')
        ).filter(
            Attendance.user_id.in_(student_ids),
            Attendance.date >= start_date,
            Attendance.date <= end_date
        ).group_by(Attendance.user_id).all()

        attendance_count_map = {user_id: count for user_id, count in semester_attendances}

        today_attendances = Attendance.query.filter(
            Attendance.user_id.in_(student_ids),
            Attendance.date == today
        ).all()

        signed_today_set = {att.user_id for att in today_attendances}

        student_stats = []
        total_signed_today = 0

        for student in students:
            attendance_count = attendance_count_map.get(student.id, 0)
            rate = AttendanceStatsService.calculate_attendance_rate(attendance_count, total_days)
            signed_today = student.id in signed_today_set

            if signed_today:
                total_signed_today += 1

            student_stats.append({
                'id': student.id,
                'name': student.username,
                'total': attendance_count,
                'rate': rate,
                'signedToday': signed_today
            })

        return {
            'students': student_stats,
            'totalStudents': len(students),
            'signedToday': total_signed_today,
            'totalDays': total_days
        }