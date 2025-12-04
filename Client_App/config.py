# # config.py - Configuration Settings
# import os

# class Config:
#     SECRET_KEY = os.environ.get('SECRET_KEY') or '110011'
    
#     # Dump file locations
#     DUMP_LOCATIONS = [
#         r'C:\Windows\Minidump',
#         os.path.join(os.environ.get('LOCALAPPDATA', ''), 'CrashDumps')
#     ]
    
#     # WinDbg settings
#     WINDBG_PATH = os.environ.get('WINDBG_PATH') or r'C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\windbg.exe'
    
#     # Knowledge base settings
#     KNOWLEDGE_BASE_PATH = 'knowledge_base/errors.json'
    
#     # Email settings for support
#     SMTP_SERVER = 'smtp.gmail.com'
#     SMTP_PORT = 587
#     EMAIL_USERNAME = os.environ.get('EMAIL_USERNAME')
#     EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
    
#     # Gemini AI settings
#     GEMINI_API_KEY = "AIzaSyALQl3IlQPXT_dD8k5kvBA9j3aXenmfDAg"
#     GEMINI_MODEL = 'gemini-2.0-flash'
#     GEMINI_TEMPERATURE = 0.7
#     GEMINI_MAX_TOKENS = 1024
    
#     # Chatbot settings
#     CONVERSATION_TIMEOUT = 3600  # 1 hour
#     MAX_MESSAGE_HISTORY = 50
    
#     # Performance settings
#     MAX_DUMP_SIZE = 100 * 1024 * 1024  # 100MB
#     SCAN_TIMEOUT = 30  # seconds
    
#     # Logging
#     LOG_LEVEL = 'INFO'
#     LOG_FILE = 'logs/app.log'


# config.py - Enhanced Configuration Settings with Database Support
import os
from datetime import timedelta

class Config:
    """Base configuration class"""
    
    # Flask Settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database Settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///dump_analyzer.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Authentication Settings
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # File Upload Settings
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max file upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    
    # Dump file locations
    DUMP_LOCATIONS = [
        r'C:\Windows\Minidump',
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'CrashDumps')
    ]
    
    # WinDbg settings
    WINDBG_PATH = os.environ.get('WINDBG_PATH') or r'C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\windbg.exe'
    
    # Knowledge base settings
    KNOWLEDGE_BASE_PATH = 'knowledge_base/errors.json'
    
    # Email settings for notifications
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@dumpanalyzer.com'
    
    # Support Dashboard Integration
    SUPPORT_API_URL = os.environ.get('SUPPORT_API_URL') or 'http://localhost:5001/api'
    SUPPORT_API_KEY = os.environ.get('SUPPORT_API_KEY') or 'dev-support-api-key'
    
    # Gemini AI settings
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or "AIzaSyALQl3IlQPXT_dD8k5kvBA9j3aXenmfDAg"
    GEMINI_MODEL = 'gemini-2.0-flash'
    GEMINI_TEMPERATURE = 0.7
    GEMINI_MAX_TOKENS = 1024
    
    # Chatbot settings
    CONVERSATION_TIMEOUT = 3600  # 1 hour
    MAX_MESSAGE_HISTORY = 50
    
    # Performance settings
    MAX_DUMP_SIZE = 100 * 1024 * 1024  # 100MB
    SCAN_TIMEOUT = 30  # seconds
    
    # Pagination settings
    TICKETS_PER_PAGE = 10
    ANALYSES_PER_PAGE = 20
    
    # Security settings
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour CSRF token validity
    WTF_CSRF_SSL_STRICT = True
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = 'redis://localhost:6379' if os.environ.get('REDIS_URL') else 'memory://'
    RATELIMIT_DEFAULT = "100 per hour"
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = 'logs/app.log'
    
    # Backup settings
    BACKUP_DIRECTORY = 'backups'
    AUTO_BACKUP_ENABLED = os.environ.get('AUTO_BACKUP_ENABLED', 'false').lower() == 'true'
    BACKUP_RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', 30))
    
    @staticmethod
    def init_app(app):
        """Initialize application with this config"""
        # Create necessary directories
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        os.makedirs('knowledge_base', exist_ok=True)
        os.makedirs(app.config['BACKUP_DIRECTORY'], exist_ok=True)

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///dump_analyzer_dev.db'
    
    # Disable security features for development
    WTF_CSRF_ENABLED = False
    REMEMBER_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False
    
    # More verbose logging for development
    SQLALCHEMY_ECHO = True

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    
    # Disable external services for testing
    MAIL_SUPPRESS_SEND = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    
    # Use PostgreSQL in production
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://username:password@localhost/dump_analyzer'
    
    # Enhanced security for production
    PREFERRED_URL_SCHEME = 'https'
    
    # SSL redirect
    FORCE_HTTPS = True
    
    # Enhanced logging for production
    LOG_LEVEL = 'WARNING'
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Log to syslog in production
        import logging
        from logging.handlers import SysLogHandler
        
        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.WARNING)
        app.logger.addHandler(syslog_handler)

class DockerConfig(ProductionConfig):
    """Docker container configuration"""
    
    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)
        
        # Log to stdout in Docker
        import logging
        
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        app.logger.addHandler(stream_handler)

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'docker': DockerConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on environment"""
    return config[os.getenv('FLASK_CONFIG', 'default')]