"""Application factory module"""
from flask import Flask 
from app.database.db import setup_database
from app.api.routes import api_bp 
from app.api.admin import admin_bp

def create_app(config_object):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_object)

    # Init database 
    setup_database()

    # Register blueprints
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)

    return app

