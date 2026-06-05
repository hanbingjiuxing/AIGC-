#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Debug script to test announcement creation directly"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Announcement, User

app = create_app()

with app.app_context():
    print("=== Testing Announcement Creation ===")
    
    # Find a privileged user
    admin = User.query.filter(User.role.in_(['teacher', 'president'])).first()
    if not admin:
        print("ERROR: No teacher or president user found!")
        admin = User.query.first()
        print(f"Using first user: {admin.username if admin else 'None'}")
    else:
        print(f"Found admin user: {admin.username} (role: {admin.role})")
    
    if admin:
        try:
            # Try to create an announcement
            ann = Announcement(
                title="Test Announcement",
                content="This is a test",
                tag="通知",
                created_by=admin.id
            )
            db.session.add(ann)
            db.session.commit()
            print(f"SUCCESS! Created announcement with ID: {ann.id}")
            
            # Clean up
            db.session.delete(ann)
            db.session.commit()
            print("Cleaned up test announcement")
            
        except Exception as e:
            print(f"ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("No users in database!")
