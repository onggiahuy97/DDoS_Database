"""Middleware for handling requests and responses."""
from functools import wraps
from flask import request, jsonify 
from app.services.protection import is_ip_blocked, log_connection 

def ddos_protection_middleware(f):
    """Middleware to check for DDoS attacks and log connections."""
    @wraps(f) 
    def decorated_function(*args, **kwargs):
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        # client_ip = request.remote_addr 
        username = request.args.get('username', 'anonymous')

        # Check if IP is blocked 
        if is_ip_blocked(client_ip):
            return jsonify({"error": "Your IP is blocked due to suspicious activity."}), 403

        # Log the connection
        if not log_connection(client_ip, username):
            return jsonify({"error": "Your IP has been temporarily blocked due to too many requests."}), 429

        return f(*args, **kwargs)
    
    return decorated_function
