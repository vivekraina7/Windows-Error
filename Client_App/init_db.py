# init_db.py - Database Initialization Script
"""
Database initialization script for Windows Dump Analyzer
Run this script to set up the database tables and create sample data
"""

import os
import sys
from datetime import datetime
from flask import Flask
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import models and app configuration
from models import db, User, KnowledgeBaseSolution
from utils.knowledge_base import create_knowledge_base_file

def create_app():
    """Create Flask app for database initialization"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///dump_analyzer.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    db.init_app(app)
    
    return app

def init_database():
    """Initialize database with tables and sample data"""
    app = create_app()
    
    with app.app_context():
        print("Creating database tables...")
        
        # Drop all tables if they exist (for clean setup)
        db.drop_all()
        print("Dropped existing tables")
        
        # Create all tables
        db.create_all()
        print("Created new tables")
        
        # Create knowledge base file
        create_knowledge_base_file()
        print("Created knowledge base file")
        
        # Load knowledge base solutions into database
        load_knowledge_base_solutions()
        
        # Create sample admin user
        create_sample_users()
        
        print("Database initialization completed successfully!")

def load_knowledge_base_solutions():
    """Load knowledge base solutions from JSON into database"""
    import json
    
    kb_file = 'knowledge_base/errors.json'
    if not os.path.exists(kb_file):
        print(f"Knowledge base file not found: {kb_file}")
        return
    
    try:
        with open(kb_file, 'r', encoding='utf-8') as f:
            kb_data = json.load(f)
        
        solutions_added = 0
        for error_data in kb_data.get('errors', []):
            # Check if solution already exists
            existing = KnowledgeBaseSolution.query.filter_by(
                error_code=error_data['error_code']
            ).first()
            
            if not existing:
                solution = KnowledgeBaseSolution(
                    error_code=error_data['error_code'],
                    error_name=error_data['error_name'],
                    description=error_data['description'],
                    category=error_data['category'],
                    confidence=error_data['confidence'],
                    additional_info=error_data.get('additional_info', ''),
                    gemini_context=error_data.get('gemini_context', '')
                )
                solution.set_solutions(error_data['solutions'])
                
                db.session.add(solution)
                solutions_added += 1
        
        db.session.commit()
        print(f"Loaded {solutions_added} knowledge base solutions")
        
    except Exception as e:
        print(f"Error loading knowledge base solutions: {str(e)}")
        db.session.rollback()

def create_sample_users():
    """Create sample users for testing"""
    try:
        # Create admin user
        admin_user = User(
            username='admin',
            email='admin@dumpanalyzer.com'
        )
        admin_user.set_password('admin123')
        admin_user.set_system_config({
            'os_version': 'Windows 11 Pro',
            'processor': 'Intel Core i7-12700K',
            'ram_size': '32GB',
            'storage_type': 'nvme',
            'graphics_card': 'NVIDIA RTX 4070',
            'motherboard': 'ASUS ROG STRIX Z690-E',
            'additional_info': 'Development system for testing',
            'updated_at': datetime.utcnow().isoformat()
        })
        
        db.session.add(admin_user)
        
        # Create test user
        test_user = User(
            username='testuser',
            email='test@example.com'
        )
        test_user.set_password('test123')
        test_user.set_system_config({
            'os_version': 'Windows 11 Home',
            'processor': 'AMD Ryzen 5 5600X',
            'ram_size': '16GB',
            'storage_type': 'ssd',
            'graphics_card': 'AMD RX 6700 XT',
            'motherboard': 'MSI B550 Gaming Plus',
            'additional_info': 'Gaming setup',
            'updated_at': datetime.utcnow().isoformat()
        })
        
        db.session.add(test_user)
        
        db.session.commit()
        print("Created sample users:")
        print("  - admin / admin123 (admin@dumpanalyzer.com)")
        print("  - testuser / test123 (test@example.com)")
        
    except Exception as e:
        print(f"Error creating sample users: {str(e)}")
        db.session.rollback()

def reset_database():
    """Reset database by dropping and recreating all tables"""
    app = create_app()
    
    with app.app_context():
        print("Resetting database...")
        
        # Drop all tables
        db.drop_all()
        print("Dropped all tables")
        
        # Recreate tables
        db.create_all()
        print("Recreated tables")
        
        print("Database reset completed!")

def backup_database():
    """Create a backup of the current database"""
    import shutil
    from datetime import datetime
    
    db_file = 'dump_analyzer.db'
    if os.path.exists(db_file):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'dump_analyzer_backup_{timestamp}.db'
        
        shutil.copy2(db_file, backup_file)
        print(f"Database backed up to: {backup_file}")
    else:
        print("No database file found to backup")

def check_database():
    """Check database status and show statistics"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if tables exist
            users_count = User.query.count()
            kb_solutions_count = KnowledgeBaseSolution.query.count()
            
            print("Database Status:")
            print(f"  - Users: {users_count}")
            print(f"  - Knowledge Base Solutions: {kb_solutions_count}")
            
            # Show sample data
            if users_count > 0:
                print("\nSample Users:")
                for user in User.query.limit(5).all():
                    print(f"  - {user.username} ({user.email}) - Created: {user.created_at}")
            
            if kb_solutions_count > 0:
                print("\nSample Knowledge Base Entries:")
                for solution in KnowledgeBaseSolution.query.limit(5).all():
                    print(f"  - {solution.error_code}: {solution.error_name}")
            
        except Exception as e:
            print(f"Error checking database: {str(e)}")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Database management for Windows Dump Analyzer')
    parser.add_argument('action', choices=['init', 'reset', 'backup', 'check'], 
                       help='Action to perform')
    
    args = parser.parse_args()
    
    if args.action == 'init':
        init_database()
    elif args.action == 'reset':
        confirm = input("Are you sure you want to reset the database? This will delete all data! (y/N): ")
        if confirm.lower() == 'y':
            reset_database()
        else:
            print("Database reset cancelled")
    elif args.action == 'backup':
        backup_database()
    elif args.action == 'check':
        check_database()