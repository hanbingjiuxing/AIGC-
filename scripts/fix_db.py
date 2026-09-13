from app import app
from models import db
from sqlalchemy import text

def fix_schema():
    with app.app_context():
        # Check if description column exists in works table
        try:
            db.session.execute(text("SELECT description FROM works LIMIT 1"))
            print("Column 'description' already exists in 'works' table.")
        except Exception:
            print("Adding 'description' column to 'works' table...")
            db.session.execute(text("ALTER TABLE works ADD COLUMN description TEXT"))
            db.session.commit()
            print("Done.")

if __name__ == "__main__":
    fix_schema()
