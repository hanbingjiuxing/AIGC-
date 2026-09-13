from models import db, User


def get_all_active_users(search: str = ''):
    query = User.query.filter(User.is_active == True)
    
    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) | 
            (User.student_id.ilike(f'%{search}%'))
        )
    
    return query.all()


def create_user(username: str, student_id: str, class_name: str = '', role: str = 'student') -> User:
    existing = User.query.filter(
        (User.username == username) | (User.student_id == student_id)
    ).first()
    
    if existing:
        raise ValueError('用户名或学号已存在')
    
    user = User(
        username=username,
        student_id=student_id,
        class_name=class_name,
        role=role
    )
    user.set_password(student_id)
    
    db.session.add(user)
    db.session.commit()
    
    return user


def update_user(user_id: int, **kwargs) -> User:
    user = User.query.get_or_404(user_id)
    
    if 'username' in kwargs:
        user.username = kwargs['username']
    if 'student_id' in kwargs:
        user.student_id = kwargs['student_id']
    if 'class_name' in kwargs:
        user.class_name = kwargs['class_name']
    if 'role' in kwargs:
        user.role = kwargs['role']
    if 'is_active' in kwargs:
        user.is_active = kwargs['is_active']
    
    db.session.commit()
    return user


def reset_password(user_id: int) -> str:
    user = User.query.get_or_404(user_id)
    new_password = user.student_id or '123456'
    user.set_password(new_password)
    db.session.commit()
    return new_password


def deactivate_user(user_id: int) -> None:
    user = User.query.get_or_404(user_id)
    user.is_active = False
    db.session.commit()