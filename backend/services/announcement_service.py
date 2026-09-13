from models import db, Announcement


def get_announcements(tag: str = ''):
    query = Announcement.query.order_by(Announcement.created_at.desc())
    
    if tag:
        query = query.filter_by(tag=tag)
    
    return query.all()


def get_announcement(announcement_id: int) -> Announcement:
    return Announcement.query.get_or_404(announcement_id)


def create_announcement(title: str, content: str, tag: str = '通知', created_by: int = None) -> Announcement:
    announcement = Announcement(
        title=title,
        content=content,
        tag=tag,
        created_by=created_by or 1
    )
    
    db.session.add(announcement)
    db.session.commit()
    
    return announcement


def update_announcement(announcement_id: int, **kwargs) -> Announcement:
    announcement = Announcement.query.get_or_404(announcement_id)
    
    if 'title' in kwargs:
        announcement.title = kwargs['title']
    if 'content' in kwargs:
        announcement.content = kwargs['content']
    if 'tag' in kwargs:
        announcement.tag = kwargs['tag']
    
    db.session.commit()
    return announcement


def delete_announcement(announcement_id: int) -> None:
    announcement = Announcement.query.get_or_404(announcement_id)
    db.session.delete(announcement)
    db.session.commit()