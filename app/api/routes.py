"""Main API endpoint for the application."""
from flask import Blueprint, jsonify, request 
from app.database.db import get_db_cursor 
from app.api.middleware import ddos_protection_middleware
from app.services.protection import log_connection
from app.services.protection import is_ip_blocked, log_connection
from app.api.quiplet import is_intrusion

def score_request(client_ip, username, query):
    is_blocked = is_ip_blocked(client_ip)
    log_req = log_connection(client_ip, username, query)
    intrusion_status = is_intrusion(query, username)

    score = 0
    if is_blocked or not log_req:
        score += 1
    if intrusion_status:
        score += 1
    
    block = score >= 2

    return {
        "block" : block,
        "score" : score,
        "metadata":{
            "ip_blocked" : is_blocked,
            "rate_limit": not log_req,
            "intrusion": intrusion_status
        }
    }


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
    user_id = request.args.get('username')
    client_ip = request.remote_addr
    print(f"Received query from user {user_id}: {query}")
    log_connection(client_ip, user_id, query)

    is_threat = score_request(client_ip, user_id, query)
    print(f"Score: {is_threat['score']}, Block: {is_threat['block']}, Metadata: {is_threat['metadata']}")
    if is_threat["block"]:
        return jsonify(
            {
                "error": "Your IP is blocked due to sus. activity.",
                "details" : is_threat["metadata"],
                "score": is_threat["score"]
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
                return jsonify({"status": "Query executed successfully",
                                "details" : is_threat["metadata"],
                                "score": is_threat["score"]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



