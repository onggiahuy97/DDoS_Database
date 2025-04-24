# app/api/admin.py
"""Admin endpoints for monitoring and management"""
from flask import Blueprint, jsonify, request
from app.services.protection import get_protection_stats
from app.services.resource_monitor import ResourceMonitor
from app.models.client_profiles import ClientRiskProfile
from app.database.db import get_db_cursor

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/stats', methods=['GET'])
def admin_stats():
    """Show current DDoS protection statistics"""
    return jsonify(get_protection_stats()), 200

@admin_bp.route('/query-stats', methods=['GET'])
def query_stats():
    """Show query cost and risk statistics"""
    with get_db_cursor() as cursor:
        # Get highest cost queries
        cursor.execute("""
            SELECT ip_address, normalized_query, estimated_cost, risk_score, timestamp
            FROM query_cost_log
            ORDER BY estimated_cost DESC
            LIMIT 10
        """)
        high_cost_queries = [
            {
                "ip": row[0],
                "query": row[1],
                "cost": row[2],
                "risk": row[3],
                "timestamp": row[4]
            }
            for row in cursor.fetchall()
        ]

        # Get highest risk queries
        cursor.execute("""
            SELECT ip_address, normalized_query, estimated_cost, risk_score, timestamp
            FROM query_cost_log
            ORDER BY risk_score DESC
            LIMIT 10
        """)
        high_risk_queries = [
            {
                "ip": row[0],
                "query": row[1],
                "cost": row[2],
                "risk": row[3],
                "timestamp": row[4]
            }
            for row in cursor.fetchall()
        ]

        return jsonify({
            "high_cost_queries": high_cost_queries,
            "high_risk_queries": high_risk_queries
        }), 200

@admin_bp.route('/resource-stats', methods=['GET'])
def resource_stats():
    """Show database resource statistics"""
    # Get current database stats
    db_stats = ResourceMonitor.get_database_stats()
    
    # Get load history
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT timestamp, active_connections, running_queries, 
                   avg_query_time, max_query_time, load_factor
            FROM database_load_history
            ORDER BY timestamp DESC
            LIMIT 100
        """)
        
        load_history = [
            {
                "timestamp": row[0],
                "active_connections": row[1],
                "running_queries": row[2],
                "avg_query_time": row[3],
                "max_query_time": row[4],
                "load_factor": row[5]
            }
            for row in cursor.fetchall()
        ]
    
    # Get high risk clients
    with get_db_cursor() as cursor:
        cursor.execute(ClientRiskProfile.get_high_risk_clients_query())
        
        high_risk_clients = [
            {
                "ip": row[0],
                "risk_score": row[1],
                "total_queries": row[2],
                "avg_query_cost": row[3],
                "max_query_cost": row[4], 
                "high_risk_queries": row[5],
                "timeout_multiplier": row[6]
            }
            for row in cursor.fetchall()
        ]
    
    return jsonify({
        "current_stats": db_stats,
        "load_history": load_history,
        "high_risk_clients": high_risk_clients
    }), 200

@admin_bp.route('/client-profile/<ip_address>', methods=['GET'])
def get_client_profile(ip_address):
    """Get detailed profile for a specific client"""
    profile = ResourceMonitor.get_client_profile(ip_address)
    
    if profile:
        # Get recent queries from this client
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT normalized_query, estimated_cost, risk_score, timestamp
                FROM query_cost_log
                WHERE ip_address = %s
                ORDER BY timestamp DESC
                LIMIT 20
            """, (ip_address,))
            
            recent_queries = [
                {
                    "query": row[0],
                    "cost": row[1],
                    "risk": row[2],
                    "timestamp": row[3]
                }
                for row in cursor.fetchall()
            ]
            
            profile["recent_queries"] = recent_queries
            
        return jsonify(profile), 200
    else:
        return jsonify({"error": f"No profile found for IP {ip_address}"}), 404

@admin_bp.route('/client-profile/<ip_address>', methods=['PUT'])
def update_client_profile(ip_address):
    """Manually update a client's risk profile"""
    data = request.json
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Get allowed fields for manual update
    risk_score = data.get('risk_score')
    timeout_multiplier = data.get('timeout_multiplier')
    notes = data.get('notes')
    
    if risk_score is None and timeout_multiplier is None and notes is None:
        return jsonify({"error": "No valid fields provided for update"}), 400
    
    with get_db_cursor() as cursor:
        # Build dynamic update query based on provided fields
        update_fields = []
        params = []
        
        if risk_score is not None:
            update_fields.append("risk_score = %s")
            params.append(float(risk_score))
            
        if timeout_multiplier is not None:
            update_fields.append("timeout_multiplier = %s")
            params.append(float(timeout_multiplier))
            
        if notes is not None:
            update_fields.append("notes = %s")
            params.append(str(notes))
        
        # Add last updated timestamp and IP address
        update_fields.append("last_updated = NOW()")
        params.append(ip_address)  # For WHERE clause
        
        # Execute update
        query = f"""
            UPDATE client_risk_profiles
            SET {", ".join(update_fields)}
            WHERE ip_address = %s
        """
        
        cursor.execute(query, params)
        
        if cursor.rowcount == 0:
            # Profile doesn't exist, create it
            cursor.execute(
                """
                INSERT INTO client_risk_profiles 
                (ip_address, risk_score, timeout_multiplier, notes)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    ip_address,
                    risk_score if risk_score is not None else 0.0,
                    timeout_multiplier if timeout_multiplier is not None else 1.0,
                    notes if notes is not None else None
                )
            )
    
    # Get updated profile
    profile = ResourceMonitor.get_client_profile(ip_address)
    
    return jsonify(profile), 200
