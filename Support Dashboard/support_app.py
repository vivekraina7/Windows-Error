# support_app.py - Support Dashboard Application (Phase 2)
from flask import Flask, render_template, request, jsonify, session, flash, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import logging
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SUPPORT_SECRET_KEY', 'support-secret-key')

# Construct path to shared database (for local fallback)
shared_db_path = os.path.join(os.path.dirname(__file__), '..', 'Client_App', 'instance', 'dump_analyzer.db')
shared_db_path = os.path.abspath(shared_db_path)

# Normalize DATABASE_URL for Render Postgres + SQLite fallback
database_url = os.getenv('SUPPORT_DATABASE_URL', f'sqlite:///{shared_db_path}')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['CLIENT_API_URL'] = os.getenv('CLIENT_API_URL', 'http://localhost:5000/api')

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# Support Staff Model
class SupportStaff(db.Model):
    __tablename__ = 'support_staff'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='agent')  # agent, manager
    is_available = db.Column(db.Boolean, default=True)
    last_assigned = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_authenticated(self):
        return True
    
    def is_active(self):
        return True
    
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)

# Create a local Ticket model that mirrors the client app's structure
class SupportTicket(db.Model):
    __tablename__ = 'tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, nullable=False)
    
    # Ticket details
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    error_code = db.Column(db.String(20), nullable=True)
    priority = db.Column(db.String(20), default='medium')
    status = db.Column(db.String(20), default='open')
    
    # Assignment and resolution
    assigned_to = db.Column(db.Integer, db.ForeignKey('support_staff.id'), nullable=True)
    assigned_at = db.Column(db.DateTime, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    solution = db.Column(db.Text, nullable=True)
    
    # Metadata
    conversation_id = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    assigned_staff = db.relationship('SupportStaff', backref='assigned_tickets')
    
    @property
    def user(self):
        """Get user info for this ticket"""
        return ClientUser.query.get(self.user_id)
    
    @property
    def username(self):
        """Get username for template compatibility"""
        user = self.user
        return user.username if user else "Unknown"
    
    @property
    def email(self):
        """Get email for template compatibility"""  
        user = self.user
        return user.email if user else "Unknown"

# User model for accessing user info
class ClientUser(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    system_config = db.Column(db.Text, nullable=True)
    
    def get_system_config_dict(self):
        if self.system_config:
            try:
                import json
                return json.loads(self.system_config)
            except:
                return {}
        return {}

@login_manager.user_loader
def load_user(user_id):
    return SupportStaff.query.get(int(user_id))

# Round-robin assignment logic
def get_next_available_agent():
    """Get next available agent using round-robin"""
    available_agents = SupportStaff.query.filter_by(
        role='agent', 
        is_available=True
    ).order_by(SupportStaff.last_assigned.asc().nullsfirst()).all()
    
    if available_agents:
        return available_agents[0]
    return None

def assign_ticket_round_robin(ticket):
    """Assign ticket using round-robin algorithm"""
    agent = get_next_available_agent()
    if agent:
        ticket.assigned_to = agent.id
        ticket.assigned_at = datetime.utcnow()
        ticket.status = 'in_progress'
        agent.last_assigned = datetime.utcnow()
        
        db.session.commit()
        
        logging.info(f"Ticket {ticket.ticket_id} assigned to {agent.username}")
        return agent
    return None

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        staff = SupportStaff.query.filter_by(username=username).first()
        
        if staff and staff.check_password(password):
            login_user(staff)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Dashboard Routes
@app.route('/')
@login_required
def dashboard():
    try:
        # Get ticket statistics
        total_tickets = SupportTicket.query.count()
        open_tickets = SupportTicket.query.filter_by(status='open').count()
        assigned_tickets = SupportTicket.query.filter_by(assigned_to=current_user.id).count()
        resolved_tickets = SupportTicket.query.filter_by(status='resolved').count()
        
        # Get recent tickets for current user
        my_tickets = SupportTicket.query.filter_by(assigned_to=current_user.id)\
                                       .order_by(SupportTicket.updated_at.desc()).limit(5).all()
        
        # Get unassigned tickets (for managers)
        unassigned_tickets = SupportTicket.query.filter_by(assigned_to=None)\
                                               .order_by(SupportTicket.created_at.asc()).limit(10).all()
        
        return render_template('dashboard.html',
                             total_tickets=total_tickets,
                             open_tickets=open_tickets,
                             assigned_tickets=assigned_tickets,
                             resolved_tickets=resolved_tickets,
                             my_tickets=my_tickets,
                             unassigned_tickets=unassigned_tickets)
    except Exception as e:
        logging.error(f"Dashboard error: {str(e)}")
        flash('Error loading dashboard', 'error')
        return render_template('dashboard.html',
                             total_tickets=0,
                             open_tickets=0,
                             assigned_tickets=0,
                             resolved_tickets=0,
                             my_tickets=[],
                             unassigned_tickets=[])

@app.route('/tickets')
@login_required
def tickets():
    status_filter = request.args.get('status', '')
    assigned_filter = request.args.get('assigned', '')
    
    query = SupportTicket.query
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    if assigned_filter == 'me':
        query = query.filter_by(assigned_to=current_user.id)
    elif assigned_filter == 'unassigned':
        query = query.filter_by(assigned_to=None)
    
    tickets = query.order_by(SupportTicket.created_at.desc()).all()
    
    return render_template('tickets.html', tickets=tickets, 
                         status_filter=status_filter, assigned_filter=assigned_filter)

@app.route('/ticket/<ticket_id>')
@login_required
def view_ticket(ticket_id):
    try:
        ticket = SupportTicket.query.filter_by(ticket_id=ticket_id).first_or_404()
        
        # Get user info
        user = ClientUser.query.get(ticket.user_id)
        
        return render_template('view_ticket.html', ticket=ticket, user=user)
    except Exception as e:
        logging.error(f"Error viewing ticket {ticket_id}: {str(e)}")
        flash('Error loading ticket details', 'error')
        return redirect(url_for('tickets'))

@app.route('/ticket/<ticket_id>/assign', methods=['POST'])
@login_required
def assign_ticket(ticket_id):
    ticket = SupportTicket.query.filter_by(ticket_id=ticket_id).first_or_404()
    
    if current_user.role == 'manager':
        # Manager can assign to specific agent
        agent_id = request.form.get('agent_id')
        if agent_id:
            agent = SupportStaff.query.get(agent_id)
            if agent:
                ticket.assigned_to = agent.id
                ticket.assigned_at = datetime.utcnow()
                ticket.status = 'in_progress'
                agent.last_assigned = datetime.utcnow()
                
                db.session.commit()
                flash(f'Ticket assigned to {agent.username}', 'success')
    else:
        # Regular assignment (round-robin or self-assign)
        if not ticket.assigned_to:
            ticket.assigned_to = current_user.id
            ticket.assigned_at = datetime.utcnow()
            ticket.status = 'in_progress'
            current_user.last_assigned = datetime.utcnow()
            
            db.session.commit()
            flash('Ticket assigned to you', 'success')
    
    return redirect(url_for('view_ticket', ticket_id=ticket_id))

@app.route('/ticket/<ticket_id>/update_status', methods=['POST'])
@login_required
def update_ticket_status(ticket_id):
    ticket = SupportTicket.query.filter_by(ticket_id=ticket_id).first_or_404()
    
    new_status = request.form.get('status')
    solution = request.form.get('solution', '')
    
    if new_status in ['open', 'in_progress', 'pending_user', 'resolved', 'closed']:
        ticket.status = new_status
        ticket.updated_at = datetime.utcnow()
        
        if new_status == 'resolved' and solution:
            ticket.solution = solution
            ticket.resolved_at = datetime.utcnow()
            
            # Update knowledge base if solution provided
            update_knowledge_base(ticket.error_code, solution)
        
        db.session.commit()
        
        # Notify client app
        notify_client_app(ticket)
        
        flash(f'Ticket status updated to {new_status}', 'success')
    
    return redirect(url_for('view_ticket', ticket_id=ticket_id))

def update_knowledge_base(error_code, solution):
    """Update knowledge base with new solution"""
    if not error_code or not solution:
        return
    
    try:
        # Call client app API to update knowledge base
        requests.post(f"{app.config['CLIENT_API_URL']}/knowledge_base/update", 
                     json={
                         'error_code': error_code,
                         'solution': solution,
                         'source': 'support_dashboard'
                     }, timeout=5)
    except Exception as e:
        logging.error(f"Failed to update knowledge base: {e}")

def notify_client_app(ticket):
    """Notify client app of ticket updates"""
    try:
        requests.put(f"{app.config['CLIENT_API_URL']}/tickets/{ticket.ticket_id}/status",
                    json={
                        'status': ticket.status,
                        'solution': ticket.solution,
                        'updated_at': ticket.updated_at.isoformat()
                    }, timeout=5)
    except Exception as e:
        logging.error(f"Failed to notify client app: {e}")

# API Routes (for client app communication)
@app.route('/api/tickets', methods=['POST'])
def receive_ticket():
    """Receive new ticket from client app - tickets are already in shared database"""
    data = request.get_json()
    
    try:
        # Find the existing ticket that was just created in the client app
        ticket = SupportTicket.query.filter_by(ticket_id=data['ticket_id']).first()
        
        if ticket:
            # Auto-assign using round-robin
            assign_ticket_round_robin(ticket)
            
            logging.info(f"Ticket found and assigned: {ticket.ticket_id}")
            return jsonify({"status": "success", "ticket_id": ticket.ticket_id}), 201
        else:
            logging.error(f"Ticket not found in database: {data['ticket_id']}")
            return jsonify({"status": "error", "message": "Ticket not found"}), 404
        
    except Exception as e:
        logging.error(f"Error processing ticket: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/tickets/<ticket_id>/user_update', methods=['PUT'])
def handle_user_update(ticket_id):
    """Handle updates from client app when user adds messages"""
    ticket = SupportTicket.query.filter_by(ticket_id=ticket_id).first()
    
    if ticket:
        data = request.get_json()
        ticket.status = data.get('status', ticket.status)
        ticket.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({"status": "success"})
    
    return jsonify({"status": "error", "message": "Ticket not found"}), 404

@app.route('/api/stats')
def api_stats():
    """API endpoint for dashboard statistics"""
    stats = {
        'total_tickets': SupportTicket.query.count(),
        'open_tickets': SupportTicket.query.filter_by(status='open').count(),
        'in_progress': SupportTicket.query.filter_by(status='in_progress').count(),
        'resolved_tickets': SupportTicket.query.filter_by(status='resolved').count(),
        'available_agents': SupportStaff.query.filter_by(role='agent', is_available=True).count()
    }
    
    return jsonify(stats)
    
# Function removed - not needed in support dashboard
# Initialize database
# @app.before_first_request
def create_tables():
    db.create_all()
    
    # Create default admin user if not exists
    if not SupportStaff.query.filter_by(username='admin').first():
        admin = SupportStaff(
            username='admin',
            email='admin@support.com',
            role='manager'
        )
        admin.set_password('admin123')
        
        agent1 = SupportStaff(
            username='agent1',
            email='agent1@support.com',
            role='agent'
        )
        agent1.set_password('agent123')
        
        agent2 = SupportStaff(
            username='agent2',
            email='agent2@support.com',
            role='agent'
        )
        agent2.set_password('agent123')
        
        db.session.add_all([admin, agent1, agent2])
        db.session.commit()
        
        logging.info("Default support staff created")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # Create tables and initialize database
    with app.app_context():
        create_tables()
    
    print("=" * 50)
    print("Support Dashboard Starting")
    print("=" * 50)
    print(f"Using database: {shared_db_path}")
    print("Default accounts:")
    print("  Manager: admin / admin123")
    print("  Agent: agent1 / agent123")
    print("  Agent: agent2 / agent123")
    print("=" * 50)
    
    app.run(debug=True, host='127.0.0.1', port=8001)

