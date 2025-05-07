# app/api/routes.py
"""Main API endpoint for the application."""
import sqlparse
from flask import Blueprint, jsonify, request 
from app.database.db import get_db_cursor 
from app.api.middleware import ddos_protection_middleware
from app.services.query_analysis import is_query_suspicious
from app.services.intrusion.classify import is_intrusion
from app.services.protection import log_query

api_bp = Blueprint('api', __name__)

role_permissions = {
    "admin" : ["SELECT", "INSERT", "UPDATE", "DELETE"],
    "staff" : ["SELECT", "INSERT", "UPDATE"],
    "analyst" : ["SELECT"]
}

def get_command(query):
    parser = sqlparse.parse(query)
    if not parser:
        return None

    if parser[0].tokens:
        for token in parser[0].tokens:
            if token.ttype in (sqlparse.tokens.DML, sqlparse.tokens.DDL):
                return token.value.upper()

    return None

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


@api_bp.route('/query-ids', methods=['POST'])
@ddos_protection_middleware
def handle_query_ids():
    """Handle database queries with IDS Protection"""
    query = request.json.get('query_text')
    user = request.json.get("username")
    client_ip = request.remote_addr
    command = get_command(query)

    if command is None:
        return jsonify({"Error" : "Could not parse the SQL operation"}), 400

    role = None
    if user.startswith("admin"):
        role = "admin"
    elif user.startswith("staff"):
        role = "staff"
    elif user.startswith("analyst"):
        role = "analyst"
    if role is None or command not in role_permissions[role]:
        log_query(username=user, query=query, executed=False, ip_address=client_ip)
        return jsonify({"error" : f"{user} cannot perform this operation"}), 400

    result = is_intrusion(query, user)
    print(result)

    if result["verdict"] == "Blocked":
        log_query(username=user, query=query, executed=False, ip_address=client_ip)
        return jsonify({"error" : f"User is blocked due to suspicious activity. Please contact an administrator."}, 403)
    elif result["verdict"] == "Intrusion":
        print(result)
        log_query(username=user, query=query, executed=False, ip_address=client_ip)
        return jsonify({
            "status" : "Action Blocked",
            "reason" : "System flagged due to odd query behavior.",
        }, 403)
    elif result["verdict"] == "Allowed":
        try: 
            log_query(username=user, query=query, executed=True, ip_address=client_ip)
            with get_db_cursor() as cursor:
                cursor.execute(query)
                if query.strip().upper().startswith('SELECT'):
                    columns = [desc[0] for desc in cursor.description]
                    results = []
                    for row in cursor.fetchall():
                        results.append(dict(zip(columns, row)))
                    return jsonify({"results": results}), 200
                else:
                    rows_affected = cursor.rowcount
                    return jsonify({"status": f"{command} was executed successfully",
                                    "rows_affected" : rows_affected}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
