#!/usr/bin/env python3
"""
Initialize Support Dashboard Database
Creates support_staff table in the shared database
"""

import os
import sys
import sqlite3
import hashlib
from datetime import datetime

def simple_hash(password):
    """Simple password hashing for initialization"""
    return hashlib.sha256(password.encode()).hexdigest()

# Get the absolute path to the shared database
shared_db_path = os.path.join(os.path.dirname(__file__), '..', 'Client_App', 'instance', 'dump_analyzer.db')
shared_db_path = os.path.abspath(shared_db_path)

def create_support_tables():
    """Create support tables if they don't exist"""
    
    print(f"Connecting to database: {shared_db_path}")
    
    if not os.path.exists(shared_db_path):
        print("ERROR: Client app database not found. Please run the client app first.")
        return False
    
    try:
        conn = sqlite3.connect(shared_db_path)
        cursor = conn.cursor()
        
        # Create support_staff table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS support_staff (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(80) UNIQUE NOT NULL,
                email VARCHAR(120) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) DEFAULT 'agent',
                is_available BOOLEAN DEFAULT 1,
                last_assigned DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Check if default users exist
        cursor.execute("SELECT COUNT(*) FROM support_staff")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("Creating default support staff...")
            
            # Create default support staff
            admin_hash = simple_hash('admin123')
            agent1_hash = simple_hash('agent123')
            agent2_hash = simple_hash('agent123')
            
            staff_data = [
                ('admin', 'admin@support.com', admin_hash, 'manager'),
                ('agent1', 'agent1@support.com', agent1_hash, 'agent'),
                ('agent2', 'agent2@support.com', agent2_hash, 'agent')
            ]
            
            cursor.executemany(
                "INSERT INTO support_staff (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
                staff_data
            )
            
            print("Default support staff created:")
            print("  Manager: admin / admin123")
            print("  Agent: agent1 / agent123")
            print("  Agent: agent2 / agent123")
        else:
            print(f"Support staff table already has {count} users")
        
        conn.commit()
        conn.close()
        
        print("Support database initialization completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error initializing support database: {str(e)}")
        return False

if __name__ == '__main__':
    success = create_support_tables()
    if success:
        print("\nYou can now start the support dashboard!")
    else:
        print("\nFailed to initialize support database.")
        sys.exit(1)