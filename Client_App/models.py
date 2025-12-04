# models.py - Database Models for User Authentication and Ticket System
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication and profile management"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    system_config = db.Column(db.Text, nullable=True)  # JSON string with system specs
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    tickets = db.relationship('Ticket', backref='user', lazy=True, cascade='all, delete-orphan')
    conversations = db.relationship('Conversation', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def get_system_config_dict(self):
        """Parse system config JSON string to dict"""
        if self.system_config:
            try:
                import json
                return json.loads(self.system_config)
            except:
                return {}
        return {}
    
    def set_system_config(self, config_dict):
        """Set system config from dict"""
        import json
        self.system_config = json.dumps(config_dict)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Ticket(db.Model):
    """Support ticket model"""
    __tablename__ = 'tickets'
    
    # Status choices
    STATUS_OPEN = 'open'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_PENDING_USER = 'pending_user'
    STATUS_RESOLVED = 'resolved'
    STATUS_CLOSED = 'closed'
    
    # Priority choices
    PRIORITY_LOW = 'low'
    PRIORITY_MEDIUM = 'medium'
    PRIORITY_HIGH = 'high'
    PRIORITY_CRITICAL = 'critical'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Ticket details
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    error_code = db.Column(db.String(20), nullable=True)
    priority = db.Column(db.String(20), default=PRIORITY_MEDIUM)
    status = db.Column(db.String(20), default=STATUS_OPEN)
    
    # Assignment and resolution
    assigned_to = db.Column(db.Integer, nullable=True)  # Will link to support_staff in support app
    assigned_at = db.Column(db.DateTime, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    solution = db.Column(db.Text, nullable=True)
    
    # Metadata
    conversation_id = db.Column(db.String(50), nullable=True)  # Link to AI conversation
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = db.relationship('TicketMessage', backref='ticket', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        super(Ticket, self).__init__(**kwargs)
        if not self.ticket_id:
            self.ticket_id = self.generate_ticket_id()
    
    @staticmethod
    def generate_ticket_id():
        """Generate unique ticket ID"""
        timestamp = datetime.now().strftime('%Y%m%d')
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"DUMP-{timestamp}-{unique_id}"
    
    def get_status_display(self):
        """Get human-readable status"""
        status_map = {
            self.STATUS_OPEN: 'Open',
            self.STATUS_IN_PROGRESS: 'In Progress',
            self.STATUS_PENDING_USER: 'Pending User Response',
            self.STATUS_RESOLVED: 'Resolved',
            self.STATUS_CLOSED: 'Closed'
        }
        return status_map.get(self.status, self.status.title())
    
    def get_priority_display(self):
        """Get human-readable priority"""
        priority_map = {
            self.PRIORITY_LOW: 'Low',
            self.PRIORITY_MEDIUM: 'Medium',
            self.PRIORITY_HIGH: 'High',
            self.PRIORITY_CRITICAL: 'Critical'
        }
        return priority_map.get(self.priority, self.priority.title())
    
    def can_be_updated_by_user(self):
        """Check if user can still update this ticket"""
        return self.status in [self.STATUS_OPEN, self.STATUS_IN_PROGRESS, self.STATUS_PENDING_USER]
    
    def __repr__(self):
        return f'<Ticket {self.ticket_id}>'

class TicketMessage(db.Model):
    """Messages within a support ticket"""
    __tablename__ = 'ticket_messages'
    
    # Message types
    TYPE_USER = 'user'
    TYPE_SUPPORT = 'support'
    TYPE_SYSTEM = 'system'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    sender_id = db.Column(db.Integer, nullable=True)  # User ID or Support Staff ID
    sender_type = db.Column(db.String(20), nullable=False)  # user, support, system
    message = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, default=False)  # Internal notes not visible to user
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<TicketMessage {self.id} for Ticket {self.ticket_id}>'

class Conversation(db.Model):
    """AI conversation tracking"""
    __tablename__ = 'conversations'
    
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    error_code = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(20), default='in_progress')
    escalated = db.Column(db.Boolean, default=False)
    escalation_reason = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = db.relationship('ConversationMessage', backref='conversation', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Conversation {self.conversation_id}>'

class ConversationMessage(db.Model):
    """Messages within AI conversations"""
    __tablename__ = 'conversation_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # user, assistant
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ConversationMessage {self.id}>'

class DumpAnalysis(db.Model):
    """Store dump file analysis results"""
    __tablename__ = 'dump_analyses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)
    error_code = db.Column(db.String(20), nullable=True)
    error_name = db.Column(db.String(200), nullable=True)
    category = db.Column(db.String(50), nullable=True)
    confidence = db.Column(db.String(20), nullable=True)
    analyzer_method = db.Column(db.String(50), nullable=True)
    faulting_module = db.Column(db.String(200), nullable=True)
    process_name = db.Column(db.String(200), nullable=True)
    analysis_data = db.Column(db.Text, nullable=True)  # JSON string with full analysis
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='dump_analyses')
    
    def get_analysis_dict(self):
        """Parse analysis data JSON string to dict"""
        if self.analysis_data:
            try:
                import json
                return json.loads(self.analysis_data)
            except:
                return {}
        return {}
    
    def set_analysis_data(self, data_dict):
        """Set analysis data from dict"""
        import json
        self.analysis_data = json.dumps(data_dict)
    
    def __repr__(self):
        return f'<DumpAnalysis {self.filename} for User {self.user_id}>'

# Knowledge Base Enhancement (extend existing)
class KnowledgeBaseSolution(db.Model):
    """Enhanced knowledge base with user feedback"""
    __tablename__ = 'kb_solutions'
    
    id = db.Column(db.Integer, primary_key=True)
    error_code = db.Column(db.String(20), nullable=False, index=True)
    error_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.String(20), default='medium')
    solutions = db.Column(db.Text, nullable=False)  # JSON string
    additional_info = db.Column(db.Text, nullable=True)
    gemini_context = db.Column(db.Text, nullable=True)
    success_count = db.Column(db.Integer, default=0)
    failure_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_solutions_list(self):
        """Parse solutions JSON string to list"""
        try:
            import json
            return json.loads(self.solutions)
        except:
            return []
    
    def set_solutions(self, solutions_list):
        """Set solutions from list"""
        import json
        self.solutions = json.dumps(solutions_list)
    
    def get_success_rate(self):
        """Calculate success rate percentage"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0
        return round((self.success_count / total) * 100, 1)
    
    def __repr__(self):
        return f'<KBSolution {self.error_code}>'

class SolutionFeedback(db.Model):
    """Track user feedback on solutions"""
    __tablename__ = 'solution_feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    error_code = db.Column(db.String(20), nullable=False)
    feedback_type = db.Column(db.String(20), nullable=False)  # solved, partial, failed
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationship
    user = db.relationship('User', backref='solution_feedbacks')
    
    def __repr__(self):
        return f'<SolutionFeedback {self.feedback_type} for {self.error_code}>'