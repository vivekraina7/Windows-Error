# init_support_db.py - Updated for Postgres + SQLite support
"""
Database initialization script for Support Dashboard
Supports both local SQLite and Render Postgres
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

# Import your support models (same as support_app.py)
from support_app import db, SupportStaff  # Adjust import path as needed

def create_app():
    """Create Flask app for support database initialization"""
    app = Flask(__name__)
    
    # Use same config as support_app.py
    app.config['SECRET_KEY'] = os.getenv('SUPPORT_SECRET_KEY', 'support-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SUPPORT_DATABASE_URL', 
        'sqlite:///' + os.path.join(os.path.dirname(__file__), '..', 'Client_App', 'instance', 'dump_analyzer.db'))
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    return app

def init_support_database():
    """Initialize support tables and sample data"""
    app = create_app()
    
    with app.app_context():
        print(f"Using database: {app.config['SQLALCHEMY_DATABASE_URI']}")
        print("Creating support tables...")
        
        # Drop and recreate support_staff table (clean setup)
        if hasattr(db, 'drop_all'):
            db.drop_all()
            print("Dropped existing tables")
        
        db.create_all()
        print("Created support tables")
        
        # Check if default users exist
        count = SupportStaff.query.count()
        
        if count == 0:
            print("Creating default support staff...")
            
            # Create default staff (same credentials as before)
            staff_data = [
                ('admin', 'admin@support.com', 'admin123', 'manager'),
                ('agent1', 'agent1@support.com', 'agent123', 'agent'),
                ('agent2', 'agent2@support.com', 'agent123', 'agent')
            ]
            
            for username, email, password, role in staff_data:
                staff = SupportStaff(username=username, email=email, role=role)
                staff.set_password(password)  # Uses werkzeug hash like support_app.py
                db.session.add(staff)
            
            db.session.commit()
            print("Default support staff created:")
            print("  Manager: admin / admin123")
            print("  Agent: agent1 / agent123")
            print("  Agent: agent2 / agent123")
        else:
            print(f"Support staff table already has {count} users")
        
        print("Support database initialization completed!")

if __name__ == '__main__':
    init_support_database()
    print("\nYou can now start the support dashboard!")
