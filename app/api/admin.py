# app/api/admin.py
"""Admin endpoints for monitoring and management"""
from flask import Blueprint, jsonify
from app.services.protection import get_protection_stats
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

        # Get statistics by IP
        cursor.execute("""
            SELECT 
                ip_address, 
                COUNT(*) as query_count,
                AVG(estimated_cost) as avg_cost,
                AVG(risk_score) as avg_risk,
                MAX(estimated_cost) as max_cost,
                MAX(risk_score) as max_risk
            FROM query_cost_log
            WHERE timestamp > NOW() - INTERVAL '1 hour'
            GROUP BY ip_address
            ORDER BY query_count DESC
            LIMIT 10
        """)
        ip_stats = [
            {
                "ip": row[0],
                "query_count": row[1],
                "avg_cost": row[2],
                "avg_risk": row[3],
                "max_cost": row[4],
                "max_risk": row[5]
            }
            for row in cursor.fetchall()
        ]

        return jsonify({
            "high_cost_queries": high_cost_queries,
            "high_risk_queries": high_risk_queries,
            "ip_stats": ip_stats
        }), 200
