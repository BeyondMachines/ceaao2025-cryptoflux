"""
Configuration settings for the Banking Application
Supports SQLite3 (default) and PostgreSQL databases
"""
import os
from datetime import timedelta

class Config:
    """Base configuration class with default settings"""
    
    # Flask settings
    # SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32).hex()

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")

    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    
    DB_HOST = os.environ.get('DB_HOST')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    DB_NAME = os.environ.get('DB_NAME')
    DB_USER = os.environ.get('DB_USER')
    DB_PASS = os.environ.get('DB_PASS')
    SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    

    # SQLAlchemy settings
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Set to True for SQL debugging
    
    # Database engine optimizations
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_timeout': 20,
        'pool_recycle': 300,  # 5 minutes
        'pool_pre_ping': True,  # Verify connections before use
    }
