from app import app
from models import db
from sqlalchemy import text

def update_db():
    with app.app_context():
        try:
            # Add original_name column to works table
            db.session.execute(text("ALTER TABLE works ADD COLUMN original_name VARCHAR(500)"))
            db.session.commit()
            print("Successfully added original_name column to works table.")
        except Exception as e:
            print(f"Error adding column: {e}")
            db.session.rollback()

if __name__ == "__main__":
    update_db()
