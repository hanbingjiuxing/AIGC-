from flask import Flask
from flask_cors import CORS
from config import Config
from models import db
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Enable CORS for frontend (Allow all origins for LAN dev)
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Initialize database
    db.init_app(app)
    
    # Ensure upload folder exists
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.members import members_bp
    from routes.works import works_bp
    from routes.attendance import attendance_bp
    from routes.announcements import announcements_bp
    from routes.update import update_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(members_bp)
    app.register_blueprint(works_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(announcements_bp)
    app.register_blueprint(update_bp)
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    # Health check endpoint
    @app.route('/api/health')
    def health():
        return {'status': 'ok', 'message': 'AIGC Society Backend is running'}
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
