#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AIGC Society Database Admin Tool
================================
直接操作数据库的管理工具，无需登录账号。

使用方法:
    python admin_tool.py

警告: 此工具可直接修改数据库，请谨慎使用！
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, User, Work, Attendance, Announcement, SystemConfig
from werkzeug.security import generate_password_hash

app = create_app()

def print_menu():
    print("\n" + "=" * 50)
    print("       AIGC 社团信息系统 - 数据库管理工具")
    print("=" * 50)
    print("1. 用户管理")
    print("2. 公告管理")
    print("3. 作品管理")
    print("4. 考勤管理")
    print("5. 系统配置")
    print("0. 退出")
    print("-" * 50)

def user_menu():
    while True:
        print("\n--- 用户管理 ---")
        print("1. 列出所有用户")
        print("2. 重置用户密码")
        print("3. 修改用户角色")
        print("4. 删除用户")
        print("5. 添加新用户")
        print("0. 返回上级")
        
        choice = input("请选择: ").strip()
        
        with app.app_context():
            if choice == '1':
                users = User.query.all()
                print(f"\n共 {len(users)} 个用户:")
                print(f"{'ID':<5} {'用户名':<15} {'角色':<10} {'学号':<15} {'班级':<20}")
                print("-" * 65)
                for u in users:
                    print(f"{u.id:<5} {u.username:<15} {u.role:<10} {u.student_id or '-':<15} {u.class_name or '-':<20}")
            
            elif choice == '2':
                username = input("输入用户名: ").strip()
                user = User.query.filter_by(username=username).first()
                if user:
                    new_pwd = input("输入新密码 (留空=学号): ").strip()
                    if not new_pwd:
                        new_pwd = user.student_id or '123456'
                    user.set_password(new_pwd)
                    db.session.commit()
                    print(f"✓ 密码已重置为: {new_pwd}")
                else:
                    print("✗ 用户不存在")
            
            elif choice == '3':
                username = input("输入用户名: ").strip()
                user = User.query.filter_by(username=username).first()
                if user:
                    print(f"当前角色: {user.role}")
                    print("可选: student, teacher, president")
                    new_role = input("新角色: ").strip()
                    if new_role in ['student', 'teacher', 'president']:
                        user.role = new_role
                        db.session.commit()
                        print(f"✓ 角色已更新为: {new_role}")
                    else:
                        print("✗ 无效角色")
                else:
                    print("✗ 用户不存在")
            
            elif choice == '4':
                username = input("输入要删除的用户名: ").strip()
                user = User.query.filter_by(username=username).first()
                if user:
                    confirm = input(f"确认删除 {username}? (y/N): ").strip().lower()
                    if confirm == 'y':
                        db.session.delete(user)
                        db.session.commit()
                        print("✓ 用户已删除")
                else:
                    print("✗ 用户不存在")
            
            elif choice == '5':
                username = input("用户名: ").strip()
                password = input("密码: ").strip()
                role = input("角色 (student/teacher/president): ").strip() or 'student'
                student_id = input("学号 (可选): ").strip() or None
                class_name = input("班级 (可选): ").strip() or None
                
                if User.query.filter_by(username=username).first():
                    print("✗ 用户名已存在")
                else:
                    user = User(username=username, role=role, student_id=student_id, class_name=class_name)
                    user.set_password(password)
                    db.session.add(user)
                    db.session.commit()
                    print(f"✓ 用户 {username} 创建成功")
            
            elif choice == '0':
                break

def announcement_menu():
    while True:
        print("\n--- 公告管理 ---")
        print("1. 列出所有公告")
        print("2. 添加公告")
        print("3. 修改公告")
        print("4. 删除公告")
        print("5. 清空所有公告")
        print("0. 返回上级")
        
        choice = input("请选择: ").strip()
        
        with app.app_context():
            if choice == '1':
                announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
                print(f"\n共 {len(announcements)} 条公告:")
                for a in announcements:
                    print(f"[{a.id}] [{a.tag}] {a.title} - {a.created_at.strftime('%Y-%m-%d')}")
                    if a.content:
                        print(f"    内容: {a.content[:50]}{'...' if len(a.content) > 50 else ''}")
            
            elif choice == '2':
                title = input("标题: ").strip()
                content = input("内容: ").strip()
                tag = input("标签 (活动/通知/必读, 默认通知): ").strip() or '通知'
                
                # Use first admin user as creator
                admin = User.query.filter(User.role.in_(['teacher', 'president'])).first()
                if not admin:
                    admin = User.query.first()
                
                announcement = Announcement(
                    title=title,
                    content=content,
                    tag=tag,
                    created_by=admin.id if admin else 1
                )
                db.session.add(announcement)
                db.session.commit()
                print(f"✓ 公告已添加 (ID: {announcement.id})")
            
            elif choice == '3':
                ann_id = input("输入公告ID: ").strip()
                ann = Announcement.query.get(int(ann_id))
                if ann:
                    print(f"当前标题: {ann.title}")
                    new_title = input("新标题 (留空保持不变): ").strip()
                    new_content = input("新内容 (留空保持不变): ").strip()
                    new_tag = input("新标签 (留空保持不变): ").strip()
                    
                    if new_title:
                        ann.title = new_title
                    if new_content:
                        ann.content = new_content
                    if new_tag:
                        ann.tag = new_tag
                    
                    db.session.commit()
                    print("✓ 公告已更新")
                else:
                    print("✗ 公告不存在")
            
            elif choice == '4':
                ann_id = input("输入要删除的公告ID: ").strip()
                ann = Announcement.query.get(int(ann_id))
                if ann:
                    db.session.delete(ann)
                    db.session.commit()
                    print("✓ 公告已删除")
                else:
                    print("✗ 公告不存在")
            
            elif choice == '5':
                confirm = input("确认清空所有公告? (y/N): ").strip().lower()
                if confirm == 'y':
                    Announcement.query.delete()
                    db.session.commit()
                    print("✓ 所有公告已清空")
            
            elif choice == '0':
                break

def works_menu():
    while True:
        print("\n--- 作品管理 ---")
        print("1. 列出所有作品")
        print("2. 删除作品")
        print("3. 清空所有作品")
        print("0. 返回上级")
        
        choice = input("请选择: ").strip()
        
        with app.app_context():
            if choice == '1':
                works = Work.query.order_by(Work.created_at.desc()).all()
                print(f"\n共 {len(works)} 个作品:")
                for w in works:
                    author = User.query.get(w.user_id)
                    print(f"[{w.id}] {w.title} - {author.username if author else 'Unknown'} - {w.status}")
            
            elif choice == '2':
                work_id = input("输入作品ID: ").strip()
                work = Work.query.get(int(work_id))
                if work:
                    db.session.delete(work)
                    db.session.commit()
                    print("✓ 作品已删除")
                else:
                    print("✗ 作品不存在")
            
            elif choice == '3':
                confirm = input("确认清空所有作品? (y/N): ").strip().lower()
                if confirm == 'y':
                    Work.query.delete()
                    db.session.commit()
                    print("✓ 所有作品已清空")
            
            elif choice == '0':
                break

def attendance_menu():
    while True:
        print("\n--- 考勤管理 ---")
        print("1. 查看考勤统计")
        print("2. 清空考勤记录")
        print("0. 返回上级")
        
        choice = input("请选择: ").strip()
        
        with app.app_context():
            if choice == '1':
                total = Attendance.query.count()
                print(f"共 {total} 条考勤记录")
            
            elif choice == '2':
                confirm = input("确认清空所有考勤记录? (y/N): ").strip().lower()
                if confirm == 'y':
                    Attendance.query.delete()
                    db.session.commit()
                    print("✓ 所有考勤记录已清空")
            
            elif choice == '0':
                break

def config_menu():
    while True:
        print("\n--- 系统配置 ---")
        print("1. 查看所有配置")
        print("2. 设置配置项")
        print("0. 返回上级")
        
        choice = input("请选择: ").strip()
        
        with app.app_context():
            if choice == '1':
                configs = SystemConfig.query.all()
                print(f"\n共 {len(configs)} 条配置:")
                for c in configs:
                    print(f"  {c.key} = {c.value}")
            
            elif choice == '2':
                key = input("配置键: ").strip()
                value = input("配置值: ").strip()
                SystemConfig.set_value(key, value)
                print(f"✓ 配置已保存: {key} = {value}")
            
            elif choice == '0':
                break

def main():
    print("\n欢迎使用 AIGC 社团数据库管理工具!")
    print("警告: 此工具可直接修改数据库，请谨慎操作。\n")
    
    while True:
        print_menu()
        choice = input("请选择功能: ").strip()
        
        if choice == '1':
            user_menu()
        elif choice == '2':
            announcement_menu()
        elif choice == '3':
            works_menu()
        elif choice == '4':
            attendance_menu()
        elif choice == '5':
            config_menu()
        elif choice == '0':
            print("\n再见!")
            break
        else:
            print("无效选择，请重试")

if __name__ == '__main__':
    main()
