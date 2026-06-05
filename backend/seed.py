"""
初始化数据脚本 - 创建测试用户
运行方式: python seed.py
"""
from app import create_app
from models import db, User, SystemConfig

def seed_database():
    app = create_app()
    
    with app.app_context():
        # 清空现有数据 (可选)
        # db.drop_all()
        # db.create_all()
        
        # 检查是否已有用户
        if User.query.first():
            print("数据库已有数据，跳过初始化")
            return
        
        # 创建测试用户
        users = [
            {
                'username': 'teacher',
                'password': '123456',
                'role': 'teacher',
                'student_id': 'T001',
                'class_name': '指导老师'
            },
            {
                'username': 'president',
                'password': '123456',
                'role': 'president',
                'student_id': '20220001',
                'class_name': '2022级 科技班'
            },
            {
                'username': 'student',
                'password': '123456',
                'role': 'student',
                'student_id': '20230101',
                'class_name': '2023级 计算机一班'
            },
            {
                'username': '李文',
                'password': '123456',
                'role': 'student',
                'student_id': '20230102',
                'class_name': '2023级 计算机一班'
            },
            {
                'username': '张伟',
                'password': '123456',
                'role': 'student',
                'student_id': '20230103',
                'class_name': '2023级 美术二班'
            }
        ]
        
        for user_data in users:
            user = User(
                username=user_data['username'],
                role=user_data['role'],
                student_id=user_data['student_id'],
                class_name=user_data['class_name']
            )
            user.set_password(user_data['password'])
            db.session.add(user)
            print(f"创建用户: {user_data['username']} (角色: {user_data['role']})")
        
        # 创建系统配置
        configs = [
            ('semester_start', '2023-09-01'),
            ('semester_end', '2024-01-31')
        ]
        
        for key, value in configs:
            config = SystemConfig(key=key, value=value)
            db.session.add(config)
            print(f"设置配置: {key} = {value}")
        
        db.session.commit()
        print("\n初始化完成！")
        print("\n测试账号:")
        print("  老师: teacher / 123456")
        print("  社长: president / 123456")
        print("  学生: student / 123456")

if __name__ == '__main__':
    seed_database()
