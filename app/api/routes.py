"""Main API endpoint for the application."""
from flask import Blueprint, jsonify, request 
from app.database.db import get_db_cursor 
from app.api.middleware import ddos_protection_middleware
from app.services.intrusion.classify import is_intrusion

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
    query = request.json.get('query_text')
    user = request.json.get("username")

    result = is_intrusion(query, user)
    print(result)
    
    if result["verdict"] == "Blocked":
        return jsonify({"error" : f"User is blocked due to suspicious activity. Please contact an administrator."}, 403)
    elif result["verdict"] == "Intrusion":
        return jsonify({
            "status" : "Action Blocked",
            "reason" : "System flagged due to odd query behavior."
        }, 403)
    elif result["verdict"] == "Allowed":
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



