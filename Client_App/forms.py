# forms.py - Clean WTForms without placeholder issues
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, PasswordField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional

# Import User model (will be available after models.py is loaded)
try:
    from models import User
except ImportError:
    # Handle case where models aren't loaded yet
    User = None

class RegistrationForm(FlaskForm):
    """User registration form"""
    username = StringField('Username', validators=[
        DataRequired(message='Username is required'),
        Length(min=3, max=20, message='Username must be between 3 and 20 characters')
    ])
    
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address')
    ])
    
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=6, message='Password must be at least 6 characters long')
    ])
    
    password_confirm = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password'),
        EqualTo('password', message='Passwords must match')
    ])
    
    # System Configuration Fields
    os_version = StringField('Operating System', validators=[
        DataRequired(message='OS version is required')
    ], default='Windows 11')
    
    processor = StringField('Processor', validators=[
        DataRequired(message='Processor information is required')
    ])
    
    ram_size = StringField('RAM', validators=[
        DataRequired(message='RAM size is required')
    ])
    
    storage_type = SelectField('Primary Storage', choices=[
        ('ssd', 'SSD'),
        ('hdd', 'HDD'),
        ('nvme', 'NVMe SSD'),
        ('hybrid', 'Hybrid (SSD + HDD)')
    ], validators=[DataRequired()])
    
    graphics_card = StringField('Graphics Card', validators=[Optional()])
    
    motherboard = StringField('Motherboard', validators=[Optional()])
    
    additional_info = TextAreaField('Additional System Information', validators=[Optional()])
    
    def validate_username(self, username):
        """Check if username already exists"""
        if User:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Username already exists. Please choose a different one.')
    
    def validate_email(self, email):
        """Check if email already exists"""
        if User:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Email already registered. Please use a different email or login.')

class LoginForm(FlaskForm):
    """User login form"""
    username = StringField('Username or Email', validators=[
        DataRequired(message='Please enter your username or email')
    ])
    
    password = PasswordField('Password', validators=[
        DataRequired(message='Please enter your password')
    ])
    
    remember_me = BooleanField('Remember Me')

class SupportTicketForm(FlaskForm):
    """Support ticket creation form"""
    title = StringField('Issue Title', validators=[
        DataRequired(message='Please provide a title for your issue'),
        Length(min=5, max=200, message='Title must be between 5 and 200 characters')
    ])
    
    description = TextAreaField('Issue Description', validators=[
        DataRequired(message='Please describe your issue'),
        Length(min=20, max=2000, message='Description must be between 20 and 2000 characters')
    ])
    
    error_code = StringField('Error Code (if any)', validators=[Optional()])
    
    priority = SelectField('Priority Level', choices=[
        ('low', 'Low - General questions, feature requests'),
        ('medium', 'Medium - System issues affecting functionality'),
        ('high', 'High - Critical system problems, frequent crashes'),
        ('critical', 'Critical - System completely unusable')
    ], default='medium', validators=[DataRequired()])
    
    steps_tried = TextAreaField('Steps Already Tried', validators=[Optional()])
    
    attach_conversation = BooleanField('Include AI conversation history', default=True)
    email_updates = BooleanField('Send me email updates', default=True)
    submit = SubmitField('Submit Request')
    class Meta:
        csrf = True

class UserProfileForm(FlaskForm):
    """User profile update form"""
    username = StringField('Username', validators=[
        DataRequired(message='Username is required'),
        Length(min=3, max=20, message='Username must be between 3 and 20 characters')
    ])
    
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address')
    ])
    
    # System Configuration Fields
    os_version = StringField('Operating System', validators=[DataRequired()])
    processor = StringField('Processor', validators=[DataRequired()])
    ram_size = StringField('RAM', validators=[DataRequired()])
    storage_type = SelectField('Primary Storage', choices=[
        ('ssd', 'SSD'),
        ('hdd', 'HDD'),
        ('nvme', 'NVMe SSD'),
        ('hybrid', 'Hybrid (SSD + HDD)')
    ], validators=[DataRequired()])
    
    graphics_card = StringField('Graphics Card', validators=[Optional()])
    motherboard = StringField('Motherboard', validators=[Optional()])
    additional_info = TextAreaField('Additional System Information', validators=[Optional()])
    
    def __init__(self, original_username, original_email, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email
    
    def validate_username(self, username):
        """Check if username already exists (excluding current user)"""
        if User and username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Username already exists. Please choose a different one.')
    
    def validate_email(self, email):
        """Check if email already exists (excluding current user)"""
        if User and email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Email already registered. Please use a different email.')

class ChangePasswordForm(FlaskForm):
    """Change password form"""
    current_password = PasswordField('Current Password', validators=[
        DataRequired(message='Please enter your current password')
    ])
    
    new_password = PasswordField('New Password', validators=[
        DataRequired(message='Please enter a new password'),
        Length(min=6, message='Password must be at least 6 characters long')
    ])
    
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message='Please confirm your new password'),
        EqualTo('new_password', message='Passwords must match')
    ])

class TicketMessageForm(FlaskForm):
    """Form for adding messages to existing tickets"""
    message = TextAreaField('Your Message', validators=[
        DataRequired(message='Please enter your message'),
        Length(min=5, max=1000, message='Message must be between 5 and 1000 characters')
    ])

class FeedbackForm(FlaskForm):
    """Form for solution feedback"""
    feedback_type = SelectField('Did this solution help?', choices=[
        ('solved', 'Yes, it solved my problem completely'),
        ('partial', 'It helped partially, but I still have issues'),
        ('failed', 'No, it didn\'t help at all')
    ], validators=[DataRequired()])
    
    notes = TextAreaField('Additional Comments', validators=[Optional()])