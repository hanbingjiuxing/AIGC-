#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AIGC Society Database Admin Tool - GUI Version
===============================================
图形化数据库管理工具，无需登录账号直接操作数据库。

使用方法:
    python admin_gui.py
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, User, Work, Attendance, Announcement, SystemConfig

app = create_app()


class AdminGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AIGC 社团信息系统 - 数据库管理工具")
        self.root.geometry("900x600")
        self.root.configure(bg="#1e1e2e")
        
        # Style configuration
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TNotebook", background="#1e1e2e", borderwidth=0)
        self.style.configure("TNotebook.Tab", background="#313244", foreground="#cdd6f4", padding=[15, 8], font=('Microsoft YaHei UI', 10))
        self.style.map("TNotebook.Tab", background=[("selected", "#89b4fa")], foreground=[("selected", "#1e1e2e")])
        self.style.configure("Treeview", background="#313244", foreground="#cdd6f4", fieldbackground="#313244", rowheight=28, font=('Microsoft YaHei UI', 9))
        self.style.configure("Treeview.Heading", background="#45475a", foreground="#cdd6f4", font=('Microsoft YaHei UI', 10, 'bold'))
        self.style.map("Treeview", background=[("selected", "#89b4fa")], foreground=[("selected", "#1e1e2e")])
        
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_users_tab()
        self.create_announcements_tab()
        self.create_works_tab()
        self.create_attendance_tab()
        
    def create_button(self, parent, text, command, color="#89b4fa"):
        btn = tk.Button(parent, text=text, command=command, 
                       bg=color, fg="#1e1e2e", font=('Microsoft YaHei UI', 9, 'bold'),
                       relief=tk.FLAT, padx=15, pady=5, cursor="hand2")
        btn.bind("<Enter>", lambda e: btn.configure(bg="#b4befe"))
        btn.bind("<Leave>", lambda e: btn.configure(bg=color))
        return btn

    # ==================== Users Tab ====================
    def create_users_tab(self):
        frame = tk.Frame(self.notebook, bg="#1e1e2e")
        self.notebook.add(frame, text="👤 用户管理")
        
        # Toolbar
        toolbar = tk.Frame(frame, bg="#1e1e2e")
        toolbar.pack(fill=tk.X, pady=10, padx=10)
        
        self.create_button(toolbar, "🔄 刷新", self.refresh_users).pack(side=tk.LEFT, padx=5)
        self.create_button(toolbar, "➕ 添加用户", self.add_user, "#a6e3a1").pack(side=tk.LEFT, padx=5)
        self.create_button(toolbar, "🔑 重置密码", self.reset_password, "#f9e2af").pack(side=tk.LEFT, padx=5)
        self.create_button(toolbar, "👑 修改角色", self.change_role, "#cba6f7").pack(side=tk.LEFT, padx=5)
        self.create_button(toolbar, "🗑️ 删除", self.delete_user, "#f38ba8").pack(side=tk.LEFT, padx=5)
        
        # Treeview
        columns = ("ID", "用户名", "角色", "学号", "班级", "状态")
        self.users_tree = ttk.Treeview(frame, columns=columns, show="headings", height=20)
        
        for col in columns:
            self.users_tree.heading(col, text=col)
            self.users_tree.column(col, width=120 if col != "班级" else 200)
        
        self.users_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.users_tree.yview)
        self.users_tree.configure(yscrollcommand=scrollbar.set)
        
        self.refresh_users()
    
    def refresh_users(self):
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
        
        with app.app_context():
            users = User.query.all()
            for u in users:
                status = "活跃" if u.is_active else "停用"
                self.users_tree.insert("", tk.END, values=(u.id, u.username, u.role, u.student_id or "-", u.class_name or "-", status))
    
    def add_user(self):
        dialog = UserDialog(self.root, "添加用户")
        if dialog.result:
            with app.app_context():
                if User.query.filter_by(username=dialog.result['username']).first():
                    messagebox.showerror("错误", "用户名已存在")
                    return
                user = User(
                    username=dialog.result['username'],
                    role=dialog.result['role'],
                    student_id=dialog.result['student_id'] or None,
                    class_name=dialog.result['class_name'] or None
                )
                user.set_password(dialog.result['password'])
                db.session.add(user)
                db.session.commit()
                messagebox.showinfo("成功", f"用户 {dialog.result['username']} 创建成功")
                self.refresh_users()
    
    def reset_password(self):
        selected = self.users_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择一个用户")
            return
        
        item = self.users_tree.item(selected[0])
        user_id = item['values'][0]
        username = item['values'][1]
        
        new_pwd = simpledialog.askstring("重置密码", f"请输入 {username} 的新密码：", show='*')
        if new_pwd:
            with app.app_context():
                user = User.query.get(user_id)
                if user:
                    user.set_password(new_pwd)
                    db.session.commit()
                    messagebox.showinfo("成功", f"密码已重置")
    
    def change_role(self):
        selected = self.users_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择一个用户")
            return
        
        item = self.users_tree.item(selected[0])
        user_id = item['values'][0]
        
        role = simpledialog.askstring("修改角色", "请输入新角色 (student/teacher/president)：")
        if role and role in ['student', 'teacher', 'president']:
            with app.app_context():
                user = User.query.get(user_id)
                if user:
                    user.role = role
                    db.session.commit()
                    messagebox.showinfo("成功", f"角色已更新为 {role}")
                    self.refresh_users()
    
    def delete_user(self):
        selected = self.users_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择一个用户")
            return
        
        item = self.users_tree.item(selected[0])
        user_id = item['values'][0]
        username = item['values'][1]
        
        if messagebox.askyesno("确认删除", f"确定要删除用户 {username} 吗？\n（该用户的所有作品、考勤记录、公告也将被删除）"):
            with app.app_context():
                user = db.session.get(User, user_id)
                if user:
                    # Delete related records first
                    Work.query.filter_by(user_id=user_id).delete()
                    Attendance.query.filter_by(user_id=user_id).delete()
                    Announcement.query.filter_by(created_by=user_id).delete()
                    # Now delete the user
                    db.session.delete(user)
                    db.session.commit()
                    messagebox.showinfo("成功", "用户已删除")
                    self.refresh_users()

    # ==================== Announcements Tab ====================
    def create_announcements_tab(self):
        frame = tk.Frame(self.notebook, bg="#1e1e2e")
        self.notebook.add(frame, text="📢 公告管理")
        
        # Toolbar
        toolbar = tk.Frame(frame, bg="#1e1e2e")
        toolbar.pack(fill=tk.X, pady=10, padx=10)
        
        self.create_button(toolbar, "🔄 刷新", self.refresh_announcements).pack(side=tk.LEFT, padx=5)
        self.create_button(toolbar, "➕ 添加公告", self.add_announcement, "#a6e3a1").pack(side=tk.LEFT, padx=5)
        self.create_button(toolbar, "✏️ 编辑", self.edit_announcement, "#f9e2af").pack(side=tk.LEFT, padx=5)
        self.create_button(toolbar, "🗑️ 删除", self.delete_announcement, "#f38ba8").pack(side=tk.LEFT, padx=5)
        self.create_button(toolbar, "🧹 清空全部", self.clear_announcements, "#eba0ac").pack(side=tk.LEFT, padx=5)
        
        # Treeview
        columns = ("ID", "标签", "标题", "发布者", "日期")
        self.ann_tree = ttk.Treeview(frame, columns=columns, show="headings", height=20)
        
        self.ann_tree.heading("ID", text="ID")
        self.ann_tree.heading("标签", text="标签")
        self.ann_tree.heading("标题", text="标题")
        self.ann_tree.heading("发布者", text="发布者")
        self.ann_tree.heading("日期", text="日期")
        
        self.ann_tree.column("ID", width=50)
        self.ann_tree.column("标签", width=80)
        self.ann_tree.column("标题", width=400)
        self.ann_tree.column("发布者", width=100)
        self.ann_tree.column("日期", width=100)
        
        self.ann_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.refresh_announcements()
    
    def refresh_announcements(self):
        for item in self.ann_tree.get_children():
            self.ann_tree.delete(item)
        
        with app.app_context():
            announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
            for a in announcements:
                author = User.query.get(a.created_by)
                self.ann_tree.insert("", tk.END, values=(a.id, a.tag, a.title, author.username if author else "-", a.created_at.strftime('%Y-%m-%d')))
    
    def add_announcement(self):
        dialog = AnnouncementDialog(self.root, "添加公告")
        if dialog.result:
            with app.app_context():
                admin = User.query.filter(User.role.in_(['teacher', 'president'])).first()
                ann = Announcement(
                    title=dialog.result['title'],
                    content=dialog.result['content'],
                    tag=dialog.result['tag'],
                    created_by=admin.id if admin else 1
                )
                db.session.add(ann)
                db.session.commit()
                messagebox.showinfo("成功", "公告已添加")
                self.refresh_announcements()
    
    def edit_announcement(self):
        selected = self.ann_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择一条公告")
            return
        
        item = self.ann_tree.item(selected[0])
        ann_id = item['values'][0]
        
        with app.app_context():
            ann = Announcement.query.get(ann_id)
            if ann:
                dialog = AnnouncementDialog(self.root, "编辑公告", ann)
                if dialog.result:
                    ann.title = dialog.result['title']
                    ann.content = dialog.result['content']
                    ann.tag = dialog.result['tag']
                    db.session.commit()
                    messagebox.showinfo("成功", "公告已更新")
                    self.refresh_announcements()
    
    def delete_announcement(self):
        selected = self.ann_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择一条公告")
            return
        
        item = self.ann_tree.item(selected[0])
        ann_id = item['values'][0]
        
        if messagebox.askyesno("确认删除", "确定要删除这条公告吗？"):
            with app.app_context():
                ann = Announcement.query.get(ann_id)
                if ann:
                    db.session.delete(ann)
                    db.session.commit()
                    messagebox.showinfo("成功", "公告已删除")
                    self.refresh_announcements()
    
    def clear_announcements(self):
        if messagebox.askyesno("确认清空", "确定要删除所有公告吗？此操作不可恢复！"):
            with app.app_context():
                Announcement.query.delete()
                db.session.commit()
                messagebox.showinfo("成功", "所有公告已清空")
                self.refresh_announcements()

    # ==================== Works Tab ====================
    def create_works_tab(self):
        frame = tk.Frame(self.notebook, bg="#1e1e2e")
        self.notebook.add(frame, text="🎨 作品管理")
        
        # Toolbar
        toolbar = tk.Frame(frame, bg="#1e1e2e")
        toolbar.pack(fill=tk.X, pady=10, padx=10)
        
        self.create_button(toolbar, "🔄 刷新", self.refresh_works).pack(side=tk.LEFT, padx=5)
        self.create_button(toolbar, "🗑️ 删除", self.delete_work, "#f38ba8").pack(side=tk.LEFT, padx=5)
        self.create_button(toolbar, "🧹 清空全部", self.clear_works, "#eba0ac").pack(side=tk.LEFT, padx=5)
        
        # Treeview
        columns = ("ID", "标题", "作者", "类型", "状态", "日期")
        self.works_tree = ttk.Treeview(frame, columns=columns, show="headings", height=20)
        
        for col in columns:
            self.works_tree.heading(col, text=col)
        
        self.works_tree.column("ID", width=50)
        self.works_tree.column("标题", width=300)
        self.works_tree.column("作者", width=100)
        self.works_tree.column("类型", width=80)
        self.works_tree.column("状态", width=80)
        self.works_tree.column("日期", width=100)
        
        self.works_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.refresh_works()
    
    def refresh_works(self):
        for item in self.works_tree.get_children():
            self.works_tree.delete(item)
        
        with app.app_context():
            works = Work.query.order_by(Work.created_at.desc()).all()
            for w in works:
                author = User.query.get(w.user_id)
                self.works_tree.insert("", tk.END, values=(w.id, w.title, author.username if author else "-", w.file_type or "-", w.status, w.created_at.strftime('%Y-%m-%d')))
    
    def delete_work(self):
        selected = self.works_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择一个作品")
            return
        
        item = self.works_tree.item(selected[0])
        work_id = item['values'][0]
        
        if messagebox.askyesno("确认删除", "确定要删除这个作品吗？"):
            with app.app_context():
                work = Work.query.get(work_id)
                if work:
                    db.session.delete(work)
                    db.session.commit()
                    messagebox.showinfo("成功", "作品已删除")
                    self.refresh_works()
    
    def clear_works(self):
        if messagebox.askyesno("确认清空", "确定要删除所有作品吗？此操作不可恢复！"):
            with app.app_context():
                Work.query.delete()
                db.session.commit()
                messagebox.showinfo("成功", "所有作品已清空")
                self.refresh_works()

    # ==================== Attendance Tab ====================
    def create_attendance_tab(self):
        frame = tk.Frame(self.notebook, bg="#1e1e2e")
        self.notebook.add(frame, text="📅 考勤管理")
        
        # Stats
        stats_frame = tk.Frame(frame, bg="#313244", padx=20, pady=20)
        stats_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.att_stats_label = tk.Label(stats_frame, text="加载中...", bg="#313244", fg="#cdd6f4", font=('Microsoft YaHei UI', 12))
        self.att_stats_label.pack()
        
        # Toolbar
        toolbar = tk.Frame(frame, bg="#1e1e2e")
        toolbar.pack(fill=tk.X, pady=10, padx=10)
        
        self.create_button(toolbar, "🔄 刷新", self.refresh_attendance).pack(side=tk.LEFT, padx=5)
        self.create_button(toolbar, "🧹 清空全部", self.clear_attendance, "#eba0ac").pack(side=tk.LEFT, padx=5)
        
        self.refresh_attendance()
    
    def refresh_attendance(self):
        with app.app_context():
            total = Attendance.query.count()
            self.att_stats_label.config(text=f"共 {total} 条考勤记录")
    
    def clear_attendance(self):
        if messagebox.askyesno("确认清空", "确定要删除所有考勤记录吗？此操作不可恢复！"):
            with app.app_context():
                Attendance.query.delete()
                db.session.commit()
                messagebox.showinfo("成功", "所有考勤记录已清空")
                self.refresh_attendance()


class UserDialog(tk.Toplevel):
    def __init__(self, parent, title):
        super().__init__(parent)
        self.title(title)
        self.geometry("450x420")
        self.configure(bg="#1e1e2e")
        self.resizable(False, False)
        self.result = None
        
        # Center the dialog
        self.transient(parent)
        self.grab_set()
        
        # Main container with padding
        container = tk.Frame(self, bg="#1e1e2e", padx=20, pady=15)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Form fields using grid for better layout
        fields = [
            ("用户名:", "username", False),
            ("密码:", "password", True),
            ("角色:", "role", False),
            ("学号:", "student_id", False),
            ("班级:", "class_name", False),
        ]
        
        self.entries = {}
        for i, (label, key, is_password) in enumerate(fields):
            lbl = tk.Label(container, text=label, bg="#1e1e2e", fg="#cdd6f4", font=('Microsoft YaHei UI', 10), anchor='w')
            lbl.grid(row=i, column=0, sticky='w', pady=8)
            
            entry = tk.Entry(container, bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4", font=('Microsoft YaHei UI', 10), relief=tk.FLAT, width=35)
            entry.grid(row=i, column=1, sticky='ew', pady=8, padx=(10, 0), ipady=5)
            
            if is_password:
                entry.config(show="*")
            if key == "role":
                entry.insert(0, "student")
            self.entries[key] = entry
        
        # Role hint
        hint = tk.Label(container, text="角色可选: student / teacher / president", bg="#1e1e2e", fg="#6c7086", font=('Microsoft YaHei UI', 8))
        hint.grid(row=len(fields), column=0, columnspan=2, sticky='w', pady=(0, 10))
        
        # Buttons
        btn_frame = tk.Frame(container, bg="#1e1e2e")
        btn_frame.grid(row=len(fields)+1, column=0, columnspan=2, pady=15)
        
        tk.Button(btn_frame, text="取消", command=self.destroy, bg="#45475a", fg="#cdd6f4", relief=tk.FLAT, padx=25, pady=8, font=('Microsoft YaHei UI', 10)).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="确定", command=self.submit, bg="#89b4fa", fg="#1e1e2e", relief=tk.FLAT, padx=25, pady=8, font=('Microsoft YaHei UI', 10, 'bold')).pack(side=tk.LEFT, padx=10)
        
        container.columnconfigure(1, weight=1)
        
        self.wait_window()
    
    def submit(self):
        self.result = {key: entry.get() for key, entry in self.entries.items()}
        if not self.result['username'] or not self.result['password']:
            messagebox.showerror("错误", "用户名和密码不能为空")
            return
        self.destroy()


class AnnouncementDialog(tk.Toplevel):
    def __init__(self, parent, title, announcement=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("500x400")
        self.configure(bg="#1e1e2e")
        self.resizable(False, False)
        self.result = None
        
        self.transient(parent)
        self.grab_set()
        
        # Title
        tk.Label(self, text="标题:", bg="#1e1e2e", fg="#cdd6f4", font=('Microsoft YaHei UI', 10)).pack(anchor=tk.W, padx=20, pady=(20, 0))
        self.title_entry = tk.Entry(self, bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4", font=('Microsoft YaHei UI', 10), relief=tk.FLAT)
        self.title_entry.pack(fill=tk.X, padx=20, pady=5, ipady=5)
        
        # Content
        tk.Label(self, text="内容:", bg="#1e1e2e", fg="#cdd6f4", font=('Microsoft YaHei UI', 10)).pack(anchor=tk.W, padx=20, pady=(10, 0))
        self.content_text = tk.Text(self, bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4", font=('Microsoft YaHei UI', 10), relief=tk.FLAT, height=8)
        self.content_text.pack(fill=tk.X, padx=20, pady=5)
        
        # Tag
        tk.Label(self, text="标签:", bg="#1e1e2e", fg="#cdd6f4", font=('Microsoft YaHei UI', 10)).pack(anchor=tk.W, padx=20, pady=(10, 0))
        self.tag_var = tk.StringVar(value="通知")
        tag_frame = tk.Frame(self, bg="#1e1e2e")
        tag_frame.pack(anchor=tk.W, padx=20, pady=5)
        for tag in ["通知", "活动", "必读"]:
            tk.Radiobutton(tag_frame, text=tag, variable=self.tag_var, value=tag, bg="#1e1e2e", fg="#cdd6f4", selectcolor="#313244", activebackground="#1e1e2e", activeforeground="#89b4fa").pack(side=tk.LEFT, padx=10)
        
        # Pre-fill if editing
        if announcement:
            self.title_entry.insert(0, announcement.title)
            self.content_text.insert("1.0", announcement.content or "")
            self.tag_var.set(announcement.tag)
        
        # Buttons
        btn_frame = tk.Frame(self, bg="#1e1e2e")
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="取消", command=self.destroy, bg="#45475a", fg="#cdd6f4", relief=tk.FLAT, padx=20, pady=5).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="保存", command=self.submit, bg="#89b4fa", fg="#1e1e2e", relief=tk.FLAT, padx=20, pady=5).pack(side=tk.LEFT, padx=10)
        
        self.wait_window()
    
    def submit(self):
        title = self.title_entry.get()
        if not title:
            messagebox.showerror("错误", "标题不能为空")
            return
        self.result = {
            'title': title,
            'content': self.content_text.get("1.0", tk.END).strip(),
            'tag': self.tag_var.get()
        }
        self.destroy()


def main():
    root = tk.Tk()
    app_gui = AdminGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
