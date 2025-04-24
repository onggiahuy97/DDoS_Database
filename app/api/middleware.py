# app/api/middleware.py
"""Middleware for handling requests and responses."""
from functools import wraps
from flask import request, jsonify 
from app.services.protection import is_ip_blocked, log_connection
from app.services.resource_monitor import ResourceMonitor
from app.services.query_analysis import log_query_analysis
from app.database.db import get_db_cursor

def ddos_protection_middleware(f):
    """Middleware to check for DDoS attacks and log connections."""
    @wraps(f) 
    def decorated_function(*args, **kwargs):
        client_ip = request.remote_addr 
        username = request.args.get('username', 'anonymous')

        # Check if IP is blocked 
        if is_ip_blocked(client_ip):
            return jsonify({"error": "Your IP is blocked due to suspicious activity."}), 403

        # Log the connection
        if not log_connection(client_ip, username):
            return jsonify({"error": "Your IP has been temporarily blocked due to too many requests."}), 429

        # Update client profile with this new connection
        ResourceMonitor.update_client_profile(client_ip)

        return f(*args, **kwargs)
    
    return decorated_function

def query_control_middleware(f):
    """Middleware to apply dynamic statement timeouts and resource controls."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.remote_addr
        
        # Get the appropriate statement timeout for this client
        timeout_ms = ResourceMonitor.get_statement_timeout(client_ip)
        
        # Execute the query with the dynamic timeout
        with get_db_cursor() as cursor:
            # Set statement timeout for this session
            cursor.execute(f"SET statement_timeout = {timeout_ms}")
            
            # Now execute the controller function
            return f(*args, **kwargs)
    
    return decorated_function
