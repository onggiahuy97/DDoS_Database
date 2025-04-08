# app/api/routes.py
"""Main API endpoint for the application."""
from flask import Blueprint, jsonify, request 
from app.database.db import get_db_cursor 
from app.api.middleware import ddos_protection_middleware
from app.services.query_analysis import is_query_suspicious

api_bp = Blueprint('api', __name__)

@api_bp.route('/customers', methods=['GET'])
@ddos_protection_middleware
def get_customers():
    """Get all customers - a simple endpoint to test the protection."""
    try: 
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM customers")
            columns = [desc[0] for desc in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            return jsonify({"customers": results}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/query', methods=['POST'])
@ddos_protection_middleware
def handle_query():
    """Handle database queries with DDoS Protection"""
    query = request.json.get('query')
    if not query:
        return jsonify({"error": "No query provided"}), 400

    # Get client IP
    client_ip = request.remote_addr

    # Analyze the query for suspicious patterns
    is_suspicious, risk_score, reason = is_query_suspicious(client_ip, query)
    
    if is_suspicious:
        return jsonify({
            "error": "Query rejected", 
            "reason": reason,
            "risk_score": risk_score
        }), 403

    try: 
        with get_db_cursor() as cursor:
            cursor.execute(query)

            if query.strip().upper().startswith('SELECT'):
                columns = [desc[0] for desc in cursor.description]
                results = []
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                return jsonify({"results": results}), 200
            else:
                return jsonify({"status": "Query executed successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
