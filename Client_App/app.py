# app.py - Updated Flask application with user authentication and ticket system
from flask import Flask, render_template, request, jsonify, session, flash, redirect, url_for, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from werkzeug.security import check_password_hash
import os
import json
import logging
from datetime import datetime
import uuid
import requests

# Load environment variables FIRST
from dotenv import load_dotenv
load_dotenv()

# Import models and forms
from models import db, User, Ticket, TicketMessage, Conversation, ConversationMessage, DumpAnalysis, KnowledgeBaseSolution, SolutionFeedback
from forms import RegistrationForm, LoginForm, SupportTicketForm, UserProfileForm, ChangePasswordForm, TicketMessageForm, FeedbackForm

# Import utility modules
try:
    from utils.dump_analyzer import DumpAnalyzer
    from utils.file_scanner import FileScanner
    from utils.knowledge_base import KnowledgeBase
    from utils.gemini_assistant import GeminiAssistant
except ImportError as e:
    print(f"Warning: Could not import some modules: {e}")
    DumpAnalyzer = None
    FileScanner = None
    KnowledgeBase = None
    GeminiAssistant = None

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key-change-this')
database_url = os.getenv('DATABASE_URL', 'sqlite:///instance/dump_analyzer.db')

# Fix postgres:// -> postgresql:// for SQLAlchemy compatibility
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['DEBUG'] = os.getenv('FLASK_ENV') == 'development'

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize logging
logging.basicConfig(
    filename='logs/app.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)

if app.config['DEBUG']:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    console_handler.setFormatter(formatter)
    logging.getLogger().addHandler(console_handler)

# Initialize components safely
def safe_init(component_class, name):
    """Safely initialize components with error handling"""
    try:
        if component_class:
            instance = component_class()
            logging.info(f"{name} initialized successfully")
            return instance
        else:
            logging.warning(f"{name} class not available")
            return None
    except Exception as e:
        logging.error(f"Error initializing {name}: {str(e)}")
        return None

dump_analyzer = safe_init(DumpAnalyzer, "DumpAnalyzer")
file_scanner = safe_init(FileScanner, "FileScanner")
knowledge_base = safe_init(KnowledgeBase, "KnowledgeBase")
gemini_assistant = safe_init(GeminiAssistant, "GeminiAssistant")

# Authentication Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            # Create system config dictionary
            system_config = {
                'os_version': form.os_version.data,
                'processor': form.processor.data,
                'ram_size': form.ram_size.data,
                'storage_type': form.storage_type.data,
                'graphics_card': form.graphics_card.data or 'Not specified',
                'motherboard': form.motherboard.data or 'Not specified',
                'additional_info': form.additional_info.data or '',
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Create user
            user = User(
                username=form.username.data,
                email=form.email.data.lower()
            )
            user.set_password(form.password.data)
            user.set_system_config(system_config)
            
            db.session.add(user)
            db.session.commit()
            
            logging.info(f"New user registered: {user.username}")
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Registration error: {str(e)}")
            flash('An error occurred during registration. Please try again.', 'error')
    
    return render_template('auth/register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # Try to find user by username or email
        user = User.query.filter(
            (User.username == form.username.data) | 
            (User.email == form.username.data.lower())
        ).first()
        
        if user and user.check_password(form.password.data):
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            login_user(user, remember=form.remember_me.data)
            logging.info(f"User logged in: {user.username}")
            
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('auth/login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    username = current_user.username
    logout_user()
    logging.info(f"User logged out: {username}")
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

# Profile Management Routes
@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('auth/profile.html', user=current_user)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile"""
    form = UserProfileForm(
        original_username=current_user.username,
        original_email=current_user.email
    )
    
    if request.method == 'GET':
        # Pre-populate form with current user data
        form.username.data = current_user.username
        form.email.data = current_user.email
        
        # Pre-populate system config
        config = current_user.get_system_config_dict()
        if config:
            form.os_version.data = config.get('os_version', '')
            form.processor.data = config.get('processor', '')
            form.ram_size.data = config.get('ram_size', '')
            form.storage_type.data = config.get('storage_type', 'ssd')
            form.graphics_card.data = config.get('graphics_card', '')
            form.motherboard.data = config.get('motherboard', '')
            form.additional_info.data = config.get('additional_info', '')
    
    if form.validate_on_submit():
        try:
            # Update user data
            current_user.username = form.username.data
            current_user.email = form.email.data.lower()
            
            # Update system config
            system_config = {
                'os_version': form.os_version.data,
                'processor': form.processor.data,
                'ram_size': form.ram_size.data,
                'storage_type': form.storage_type.data,
                'graphics_card': form.graphics_card.data or 'Not specified',
                'motherboard': form.motherboard.data or 'Not specified',
                'additional_info': form.additional_info.data or '',
                'updated_at': datetime.utcnow().isoformat()
            }
            current_user.set_system_config(system_config)
            
            db.session.commit()
            
            logging.info(f"Profile updated for user: {current_user.username}")
            flash('Your profile has been updated successfully.', 'success')
            return redirect(url_for('profile'))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Profile update error: {str(e)}")
            flash('An error occurred while updating your profile.', 'error')
    
    return render_template('auth/edit_profile.html', form=form)

@app.route('/profile/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password"""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            
            logging.info(f"Password changed for user: {current_user.username}")
            flash('Your password has been changed successfully.', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Current password is incorrect.', 'error')
    
    return render_template('auth/change_password.html', form=form)

# Main Application Routes
@app.route('/')
@login_required
def index():
    """Main dashboard page"""
    try:
        # Get user's recent activity
        recent_analyses = DumpAnalysis.query.filter_by(user_id=current_user.id)\
                                           .order_by(DumpAnalysis.created_at.desc())\
                                           .limit(5).all()
        
        # Get recent tickets
        recent_tickets = Ticket.query.filter_by(user_id=current_user.id)\
                                   .order_by(Ticket.created_at.desc())\
                                   .limit(3).all()
        
        # Get system stats
        total_analyses = DumpAnalysis.query.filter_by(user_id=current_user.id).count()
        total_tickets = Ticket.query.filter_by(user_id=current_user.id).count()
        
        return render_template('dashboard/index.html', 
                             recent_analyses=recent_analyses,
                             recent_tickets=recent_tickets,
                             total_analyses=total_analyses,
                             total_tickets=total_tickets)
    except Exception as e:
        logging.error(f"Error loading dashboard: {str(e)}")
        flash("Error loading dashboard", "error")
        return render_template('dashboard/index.html', 
                             recent_analyses=[],
                             recent_tickets=[],
                             total_analyses=0,
                             total_tickets=0)

@app.route('/scan', methods=['POST'])
@login_required
def scan_dumps():
    """Initiate dump file scan"""
    try:
        logging.info(f"Starting dump file scan for user: {current_user.username}")
        
        if not file_scanner:
            logging.error("File scanner not available")
            return jsonify({"status": "error", "message": "File scanner not available"}), 500
        
        # Scan for dump files
        scan_results = file_scanner.scan_directories()
        logging.info(f"Scan found {len(scan_results) if scan_results else 0} files")
        
        if not scan_results:
            return jsonify({"status": "no_files", "message": "No dump files found"})
        
        # Analyze found dump files
        analysis_results = []
        for i, dump_file in enumerate(scan_results):
            try:
                logging.info(f"Processing file {i+1}/{len(scan_results)}: {dump_file.get('filename', 'unknown')}")
                
                # Check if this file was already analyzed
                existing_analysis = DumpAnalysis.query.filter_by(
                    user_id=current_user.id,
                    file_path=dump_file['path']
                ).first()
                
                if existing_analysis:
                    # Use existing analysis
                    analysis = {
                        'file_info': dump_file,
                        'error_code': existing_analysis.error_code,
                        'error_name': existing_analysis.error_name,
                        'category': existing_analysis.category,
                        'confidence': existing_analysis.confidence,
                        'analyzer_method': existing_analysis.analyzer_method,
                        'faulting_module': existing_analysis.faulting_module,
                        'process_name': existing_analysis.process_name,
                        'analysis_time': existing_analysis.created_at.isoformat()
                    }
                else:
                    # Perform new analysis
                    if dump_analyzer:
                        analysis = dump_analyzer.analyze_dump(dump_file)
                    else:
                        analysis = {
                            'file_info': dump_file,
                            'error_code': 'Unknown',
                            'error_name': 'Analysis unavailable',
                            'analysis_time': datetime.now().isoformat(),
                            'analyzer_method': 'none',
                            'confidence': 'low'
                        }
                    
                    # Save analysis to database
                    if analysis and analysis.get('error_code') != 'Unknown':
                        dump_analysis = DumpAnalysis(
                            user_id=current_user.id,
                            file_path=dump_file['path'],
                            filename=dump_file['filename'],
                            file_size=dump_file['size'],
                            error_code=analysis.get('error_code'),
                            error_name=analysis.get('error_name'),
                            category=analysis.get('category'),
                            confidence=analysis.get('confidence'),
                            analyzer_method=analysis.get('analyzer_method'),
                            faulting_module=analysis.get('faulting_module'),
                            process_name=analysis.get('process_name')
                        )
                        dump_analysis.set_analysis_data(analysis)
                        db.session.add(dump_analysis)
                
                if analysis:
                    # Search knowledge base for solutions
                    if knowledge_base and analysis.get('error_code') != 'Unknown':
                        try:
                            solutions = knowledge_base.search_solutions(analysis['error_code'])
                            analysis['solutions'] = solutions
                        except Exception as e:
                            logging.error(f"Error searching knowledge base: {str(e)}")
                            analysis['solutions'] = None
                    else:
                        analysis['solutions'] = None
                    
                    analysis_results.append(analysis)
                    
            except Exception as e:
                logging.error(f"Error analyzing {dump_file}: {str(e)}")
                analysis_results.append({
                    'file_info': dump_file,
                    'error_code': 'Error',
                    'error_name': f'Analysis failed: {str(e)}',
                    'analysis_time': datetime.now().isoformat(),
                    'analyzer_method': 'failed',
                    'confidence': 'none',
                    'solutions': None
                })
        
        # Commit any new analyses
        try:
            db.session.commit()
        except Exception as e:
            logging.error(f"Error saving analyses: {str(e)}")
            db.session.rollback()
        
        logging.info(f"Scan completed. Analyzed {len(analysis_results)} dumps")
        
        return jsonify({
            "status": "success",
            "results": analysis_results,
            "count": len(analysis_results)
        })
        
    except Exception as e:
        logging.error(f"Error during scan: {str(e)}")
        return jsonify({"status": "error", "message": f"Scan failed: {str(e)}"}), 500

@app.route('/scan_results')
@login_required
def scan_results():
    """Display scan results page"""
    results = request.args.get('results', '[]')
    try:    
        results_data = json.loads(results) if results != '[]' else []
        return render_template('scan_results.html', results=results_data)
    except Exception as e:
        logging.error(f"Error loading scan results: {str(e)}")
        flash("Error loading scan results", "error")
        return redirect(url_for('index'))

# Ticket Management Routes
@app.route('/support')
@login_required
def support():
    """Support contact form - FIXED VERSION"""
    form = SupportTicketForm()
    conversation_id = request.args.get('conversation_id', '')
    error_code = request.args.get('error_code', '')
    
    # Pre-populate form if error code is provided
    if error_code:
        form.error_code.data = error_code
        form.title.data = f"Issue with error code {error_code}"
    
    # Debug CSRF
    print(f"CSRF token: {form.csrf_token.current_token}")
    
    return render_template('support/support.html', form=form, conversation_id=conversation_id)

@app.route('/submit_support', methods=['POST'])
@login_required
def submit_support():
    """Submit support request - FIXED VERSION"""
    form = SupportTicketForm()
    
    if form.validate_on_submit():
        try:
            # Create support ticket
            ticket = Ticket(
                user_id=current_user.id,
                title=form.title.data,
                description=form.description.data,
                error_code=form.error_code.data or None,
                priority=form.priority.data,
                conversation_id=request.form.get('conversation_id') or None
            )
            
            db.session.add(ticket)
            db.session.flush()  # Get the ticket ID
            
            # Add initial system message (your existing code)
            system_message = f"Ticket created by {current_user.username}\n"
            if hasattr(form, 'steps_tried') and form.steps_tried.data:
                system_message += f"\nSteps already tried:\n{form.steps_tried.data}"
            
            # Add system configuration
            config = current_user.get_system_config_dict()
            if config:
                system_message += f"\n\nSystem Configuration:\n"
                system_message += f"OS: {config.get('os_version', 'Not specified')}\n"
                system_message += f"Processor: {config.get('processor', 'Not specified')}\n"
                system_message += f"RAM: {config.get('ram_size', 'Not specified')}\n"
                system_message += f"Storage: {config.get('storage_type', 'Not specified')}\n"
                if config.get('graphics_card') and config.get('graphics_card') != 'Not specified':
                    system_message += f"Graphics: {config.get('graphics_card')}\n"
                if config.get('additional_info'):
                    system_message += f"Additional Info: {config.get('additional_info')}\n"
            
            initial_message = TicketMessage(
                ticket_id=ticket.id,
                sender_id=current_user.id,
                sender_type=TicketMessage.TYPE_SYSTEM,
                message=system_message,
                is_internal=False
            )
            db.session.add(initial_message)
            
            db.session.commit()
            
            # Send ticket to support dashboard - FIXED
            success = send_ticket_to_support_api(ticket)
            if not success:
                logging.warning(f"Failed to send ticket {ticket.ticket_id} to support dashboard")
            
            logging.info(f"Support ticket created: {ticket.ticket_id} by {current_user.username}")
            flash(f'Support ticket {ticket.ticket_id} created successfully!', 'success')
            return redirect(url_for('view_ticket', ticket_id=ticket.ticket_id))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error submitting support request: {str(e)}")
            flash("Error submitting support request. Please try again.", "error")
    else:
        # Form validation failed
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", "error")
    
    return render_template('support/support.html', form=form)
# @app.route('/submit_support', methods=['POST'])
# @login_required
# def submit_support():
#     """Submit support request - FIXED VERSION"""
#     form = SupportTicketForm()
    
#     # Add debugging
#     print("Form validation:", form.validate_on_submit())
#     print("Form errors:", form.errors)
#     print("Form data:", request.form)
    
#     if form.validate_on_submit():
#         try:
#             # Create support ticket
#             ticket = Ticket(
#                 user_id=current_user.id,
#                 title=form.title.data,
#                 description=form.description.data,
#                 error_code=form.error_code.data or None,
#                 priority=form.priority.data,
#                 conversation_id=request.form.get('conversation_id') or None
#             )
            
#             db.session.add(ticket)
#             db.session.flush()  # Get the ticket ID
            
#             # Add initial system message
#             system_message = f"Ticket created by {current_user.username}\n"
#             if hasattr(form, 'steps_tried') and form.steps_tried.data:
#                 system_message += f"\nSteps already tried:\n{form.steps_tried.data}"
            
#             # Add system configuration
#             config = current_user.get_system_config_dict()
#             if config:
#                 system_message += f"\n\nSystem Configuration:\n"
#                 system_message += f"OS: {config.get('os_version', 'Not specified')}\n"
#                 system_message += f"Processor: {config.get('processor', 'Not specified')}\n"
#                 system_message += f"RAM: {config.get('ram_size', 'Not specified')}\n"
#                 system_message += f"Storage: {config.get('storage_type', 'Not specified')}\n"
#                 if config.get('graphics_card') and config.get('graphics_card') != 'Not specified':
#                     system_message += f"Graphics: {config.get('graphics_card')}\n"
#                 if config.get('additional_info'):
#                     system_message += f"Additional Info: {config.get('additional_info')}\n"
            
#             initial_message = TicketMessage(
#                 ticket_id=ticket.id,
#                 sender_id=current_user.id,
#                 sender_type=TicketMessage.TYPE_SYSTEM,
#                 message=system_message,
#                 is_internal=False
#             )
#             db.session.add(initial_message)
            
#             db.session.commit()
            
#             logging.info(f"Support ticket created: {ticket.ticket_id} by {current_user.username}")
#             flash(f'Support ticket {ticket.ticket_id} created successfully!', 'success')
#             return redirect(url_for('view_ticket', ticket_id=ticket.ticket_id))
            
#         except Exception as e:
#             db.session.rollback()
#             logging.error(f"Error submitting support request: {str(e)}")
#             print(f"Database error: {str(e)}")  # Debug print
#             flash("Error submitting support request. Please try again.", "error")
#     else:
#         # Form validation failed
#         print("Form validation failed!")
#         for field, errors in form.errors.items():
#             print(f"Field {field}: {errors}")
#             for error in errors:
#                 flash(f"{field}: {error}", "error")
    
#     return render_template('support/support.html', form=form)


# @app.route('/submit_support', methods=['POST'])
# @login_required
# def submit_support():
#     """Submit support request"""
#     form = SupportTicketForm()
    
#     # Debug: Print form data
#     logging.info(f"Form validation: {form.validate_on_submit()}")
#     logging.info(f"Form errors: {form.errors}")
#     logging.info(f"Form data: {request.form}")
    
#     if form.validate_on_submit():
#         try:
#             # Create support ticket
#             ticket = Ticket(
#                 user_id=current_user.id,
#                 title=form.title.data,
#                 description=form.description.data,
#                 error_code=form.error_code.data or None,
#                 priority=form.priority.data,
#                 conversation_id=request.form.get('conversation_id') or None
#             )
            
#             logging.info(f"Created ticket object: {ticket}")
            
#             db.session.add(ticket)
#             db.session.flush()  # Get the ticket ID
            
#             logging.info(f"Ticket ID after flush: {ticket.id}")
            
#             # Add initial system message
#             system_message = f"Ticket created by {current_user.username}\n"
#             if form.steps_tried.data:
#                 system_message += f"\nSteps already tried:\n{form.steps_tried.data}"
            
#             # Add system configuration
#             config = current_user.get_system_config_dict()
#             if config:
#                 system_message += f"\n\nSystem Configuration:\n"
#                 system_message += f"OS: {config.get('os_version', 'Not specified')}\n"
#                 system_message += f"Processor: {config.get('processor', 'Not specified')}\n"
#                 system_message += f"RAM: {config.get('ram_size', 'Not specified')}\n"
#                 system_message += f"Storage: {config.get('storage_type', 'Not specified')}\n"
#                 if config.get('graphics_card') and config.get('graphics_card') != 'Not specified':
#                     system_message += f"Graphics: {config.get('graphics_card')}\n"
#                 if config.get('additional_info'):
#                     system_message += f"Additional Info: {config.get('additional_info')}\n"
            
#             initial_message = TicketMessage(
#                 ticket_id=ticket.id,
#                 sender_id=current_user.id,
#                 sender_type=TicketMessage.TYPE_SYSTEM,
#                 message=system_message,
#                 is_internal=False
#             )
#             db.session.add(initial_message)
            
#             # Add conversation history if requested
#             if form.attach_conversation.data and ticket.conversation_id:
#                 try:
#                     conversation = Conversation.query.filter_by(
#                         conversation_id=ticket.conversation_id,
#                         user_id=current_user.id
#                     ).first()
                    
#                     if conversation:
#                         conv_messages = ConversationMessage.query.filter_by(
#                             conversation_id=conversation.id
#                         ).order_by(ConversationMessage.created_at).all()
                        
#                         if conv_messages:
#                             conv_history = "AI Conversation History:\n" + "="*50 + "\n"
#                             for msg in conv_messages:
#                                 role = "User" if msg.role == "user" else "AI Assistant"
#                                 conv_history += f"{role}: {msg.content}\n\n"
                            
#                             conv_message = TicketMessage(
#                                 ticket_id=ticket.id,
#                                 sender_id=current_user.id,
#                                 sender_type=TicketMessage.TYPE_SYSTEM,
#                                 message=conv_history,
#                                 is_internal=False
#                             )
#                             db.session.add(conv_message)
#                 except Exception as e:
#                     logging.error(f"Error attaching conversation: {str(e)}")
            
#             db.session.commit()
            
#             # Send ticket to support dashboard API
#             send_ticket_to_support_api(ticket)
            
#             logging.info(f"Support ticket created: {ticket.ticket_id} by {current_user.username}")
#             flash(f'Support ticket {ticket.ticket_id} created successfully. You will receive updates via email.', 'success')
#             return redirect(url_for('view_ticket', ticket_id=ticket.ticket_id))
            
#         except Exception as e:
#             db.session.rollback()
#             logging.error(f"Error submitting support request: {str(e)}")
#             logging.error(f"Exception type: {type(e)}")
#             import traceback
#             logging.error(f"Traceback: {traceback.format_exc()}")
#             flash(f"Error submitting support request: {str(e)}", "error")
#     else:
#         # Form validation failed
#         logging.error(f"Form validation failed. Errors: {form.errors}")
#         for field, errors in form.errors.items():
#             for error in errors:
#                 flash(f"{field}: {error}", "error")
    
#     return render_template('support/support.html', form=form)
def check_database_tables():
    """Check if all required tables exist"""
    from sqlalchemy import inspect
    
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    
    required_tables = ['users', 'tickets', 'ticket_messages']
    missing_tables = [table for table in required_tables if table not in tables]
    
    if missing_tables:
        print(f"Missing tables: {missing_tables}")
        print("Run: python init_db.py init")
    else:
        print("All required tables exist")
    
    return len(missing_tables) == 0

# 4. Test the form creation
def test_form_creation():
    """Test if the form can be created without errors"""
    try:
        form = SupportTicketForm()
        print("Form created successfully")
        print("Form fields:", [field.name for field in form])
        return True
    except Exception as e:
        print(f"Form creation error: {e}")
        return False

def send_ticket_to_support_api(ticket):
    """Send ticket to support dashboard API - FIXED"""
    try:
        support_api_url = 'http://localhost:8001/api/tickets'  # Direct URL to ensure it works
        print(f"DEBUG: Using API URL: {support_api_url}")  # Debug print to verify correct URL
        
        ticket_data = {
            'ticket_id': ticket.ticket_id,
            'user_id': ticket.user_id,
            'username': ticket.user.username,
            'email': ticket.user.email,
            'title': ticket.title,
            'description': ticket.description,
            'error_code': ticket.error_code,
            'priority': ticket.priority,
            'status': ticket.status,
            'created_at': ticket.created_at.isoformat(),
            'system_config': ticket.user.get_system_config_dict()
        }
        
        logging.info(f"Sending ticket to support API: {support_api_url}")
        logging.info(f"Ticket data: {ticket_data}")
        
        response = requests.post(
            support_api_url,
            json=ticket_data,
            timeout=10,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 201:
            logging.info(f"Ticket {ticket.ticket_id} sent to support dashboard successfully")
            return True
        else:
            logging.error(f"Failed to send ticket to support dashboard: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error sending ticket to support API: {str(e)}")
        return False
    except Exception as e:
        logging.error(f"Error sending ticket to support API: {str(e)}")
        return False
# def send_ticket_to_support_api(ticket):
#     """Send ticket to support dashboard API"""
#     try:
#         support_api_url = os.getenv('SUPPORT_API_URL', 'http://localhost:5001/api/tickets')
        
#         ticket_data = {
#             'ticket_id': ticket.ticket_id,
#             'user_id': ticket.user_id,
#             'username': ticket.user.username,
#             'email': ticket.user.email,
#             'title': ticket.title,
#             'description': ticket.description,
#             'error_code': ticket.error_code,
#             'priority': ticket.priority,
#             'status': ticket.status,
#             'created_at': ticket.created_at.isoformat(),
#             'system_config': ticket.user.get_system_config_dict()
#         }
        
#         response = requests.post(
#             support_api_url,
#             json=ticket_data,
#             timeout=10,
#             headers={'Content-Type': 'application/json'}
#         )
        
#         if response.status_code == 201:
#             logging.info(f"Ticket {ticket.ticket_id} sent to support dashboard successfully")
#         else:
#             logging.warning(f"Failed to send ticket to support dashboard: {response.status_code}")
            
#     except Exception as e:
#         logging.error(f"Error sending ticket to support API: {str(e)}")

@app.route('/tickets')
@login_required
def my_tickets():
    """View user's tickets"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    query = Ticket.query.filter_by(user_id=current_user.id)
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    tickets = query.order_by(Ticket.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('support/my_tickets.html', tickets=tickets, status_filter=status_filter)

@app.route('/ticket/<ticket_id>')
@login_required
def view_ticket(ticket_id):
    """View specific ticket"""
    ticket = Ticket.query.filter_by(
        ticket_id=ticket_id,
        user_id=current_user.id
    ).first_or_404()
    
    messages = TicketMessage.query.filter_by(ticket_id=ticket.id)\
                                 .filter_by(is_internal=False)\
                                 .order_by(TicketMessage.created_at).all()
    
    form = TicketMessageForm()
    
    return render_template('support/view_ticket.html', 
                         ticket=ticket, 
                         messages=messages, 
                         form=form)

@app.route('/ticket/<ticket_id>/add_message', methods=['POST'])
@login_required
def add_ticket_message(ticket_id):
    """Add message to ticket"""
    ticket = Ticket.query.filter_by(
        ticket_id=ticket_id,
        user_id=current_user.id
    ).first_or_404()
    
    if not ticket.can_be_updated_by_user():
        flash('This ticket cannot be updated anymore.', 'error')
        return redirect(url_for('view_ticket', ticket_id=ticket_id))
    
    form = TicketMessageForm()
    if form.validate_on_submit():
        try:
            message = TicketMessage(
                ticket_id=ticket.id,
                sender_id=current_user.id,
                sender_type=TicketMessage.TYPE_USER,
                message=form.message.data
            )
            
            # Update ticket status if it was resolved
            if ticket.status == Ticket.STATUS_RESOLVED:
                ticket.status = Ticket.STATUS_IN_PROGRESS
            
            db.session.add(message)
            db.session.commit()
            
            # Notify support dashboard
            notify_support_of_update(ticket)
            
            flash('Your message has been added to the ticket.', 'success')
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error adding message to ticket: {str(e)}")
            flash('Error adding message to ticket.', 'error')
    
    return redirect(url_for('view_ticket', ticket_id=ticket_id))

def notify_support_of_update(ticket):
    """Notify support dashboard of ticket update"""
    try:
        support_api_url = os.getenv('SUPPORT_API_URL', 'http://localhost:5001/api/tickets')
        
        response = requests.put(
            f"{support_api_url}/{ticket.ticket_id}/user_update",
            json={
                'updated_at': datetime.utcnow().isoformat(),
                'status': ticket.status
            },
            timeout=5
        )
        
        if response.status_code == 200:
            logging.info(f"Support dashboard notified of ticket {ticket.ticket_id} update")
        
    except Exception as e:
        logging.error(f"Error notifying support of update: {str(e)}")

# Chatbot Routes
@app.route('/chatbot')
@login_required
def chatbot():
    """Gemini AI chatbot interface"""
    error_code = request.args.get('error_code', '')
    solution_id = request.args.get('solution_id', '')
    
    # Create new conversation
    conversation_id = str(uuid.uuid4())
    try:
        conversation = Conversation(
            conversation_id=conversation_id,
            user_id=current_user.id,
            error_code=error_code
        )
        db.session.add(conversation)
        db.session.commit()
        
    except Exception as e:
        logging.error(f"Error creating conversation: {str(e)}")
        db.session.rollback()
    
    return render_template('chatbot/chatbot.html', 
                         conversation_id=conversation_id,
                         error_code=error_code)

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    """Handle chat messages with Gemini AI"""
    try:
        data = request.get_json()
        conversation_id = data.get('conversation_id')
        user_message = data.get('message')
        
        if not conversation_id or not user_message:
            return jsonify({"error": "Missing required data"}), 400
        
        # Get conversation from database
        conversation = Conversation.query.filter_by(
            conversation_id=conversation_id,
            user_id=current_user.id
        ).first()
        
        if not conversation:
            return jsonify({"error": "Conversation not found"}), 404
        
        # Add user message to database
        user_msg = ConversationMessage(
            conversation_id=conversation.id,
            role='user',
            content=user_message
        )
        db.session.add(user_msg)
        
        # Get conversation history
        messages = ConversationMessage.query.filter_by(conversation_id=conversation.id)\
                                          .order_by(ConversationMessage.created_at).all()
        
        message_history = [{'role': msg.role, 'content': msg.content} for msg in messages]
        
        # Get AI response
        if gemini_assistant and gemini_assistant.initialized:
            ai_response = gemini_assistant.get_response(
                user_message, 
                conversation.error_code or '',
                message_history
            )
        else:
            ai_response = {
                'content': "I apologize, but the AI assistant is currently unavailable. Please contact support for assistance with your issue.",
                'escalate': True,
                'escalation_reason': 'ai_unavailable'
            }
        
        # Add AI response to database
        ai_msg = ConversationMessage(
            conversation_id=conversation.id,
            role='assistant',
            content=ai_response['content']
        )
        db.session.add(ai_msg)
        
        # Update conversation status if escalated
        if ai_response.get('escalate', False):
            conversation.status = 'escalated'
            conversation.escalated = True
            conversation.escalation_reason = ai_response.get('escalation_reason', 'user_request')
        
        db.session.commit()
        
        return jsonify({
            "response": ai_response['content'],
            "escalate": ai_response.get('escalate', False),
            "escalation_reason": ai_response.get('escalation_reason', '')
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error in chat: {str(e)}")
        return jsonify({"error": f"Chat error occurred: {str(e)}"}), 500

# Feedback and API Routes
@app.route('/api/feedback', methods=['POST'])
@login_required
def feedback():
    """API endpoint for user feedback"""
    try:
        data = request.get_json()
        error_code = data.get('error_code')
        feedback_type = data.get('feedback')
        timestamp = data.get('timestamp')
        notes = data.get('notes', '')
        
        # Save feedback to database
        feedback_record = SolutionFeedback(
            user_id=current_user.id,
            error_code=error_code,
            feedback_type=feedback_type,
            notes=notes
        )
        db.session.add(feedback_record)
        
        # Update knowledge base solution stats
        kb_solution = KnowledgeBaseSolution.query.filter_by(error_code=error_code).first()
        if kb_solution:
            if feedback_type == 'solved':
                kb_solution.success_count += 1
            elif feedback_type == 'failed':
                kb_solution.failure_count += 1
        
        db.session.commit()
        
        logging.info(f"Feedback received: {feedback_type} for {error_code} from {current_user.username}")
        return jsonify({"status": "success", "message": "Feedback recorded"})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error recording feedback: {str(e)}")
        return jsonify({"status": "error", "message": "Failed to record feedback"}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": db.engine.url.database is not None,
            "file_scanner": file_scanner is not None,
            "dump_analyzer": dump_analyzer is not None,
            "knowledge_base": knowledge_base is not None,
            "gemini_assistant": gemini_assistant is not None and getattr(gemini_assistant, 'initialized', False)
        }
    })

# Error Handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

# Initialize database
# @app.before_first_request
def create_tables():
    """Create database tables on first request"""
    try:
        db.create_all()
        logging.info("Database tables created successfully")
    except Exception as e:
        logging.error(f"Error creating database tables: {str(e)}")

if __name__ == '__main__':
    # Ensure directories exist
    os.makedirs('logs', exist_ok=True)
    os.makedirs('knowledge_base', exist_ok=True)
    
    # Initialize database tables
    create_tables()
    
    # Print startup information
    print("=" * 60)
    print("Windows Dump Analyzer Starting Up")
    print("=" * 60)
    print(f"Debug mode: {app.config['DEBUG']}")
    print(f"Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"Components status:")
    print(f"  - File Scanner: {'✓' if file_scanner else '✗'}")
    print(f"  - Dump Analyzer: {'✓' if dump_analyzer else '✗'}")
    print(f"  - Knowledge Base: {'✓' if knowledge_base else '✗'}")
    print(f"  - Gemini AI: {'✓' if gemini_assistant and getattr(gemini_assistant, 'initialized', False) else '✗'}")
    print("=" * 60)
    print("Flask server will start on: http://127.0.0.1:8000")
    print("=" * 60)
    
    # Run the app
    app.run(
        debug=app.config['DEBUG'], 
        host='127.0.0.1', 
        port=8000,
        use_reloader=False

    )

