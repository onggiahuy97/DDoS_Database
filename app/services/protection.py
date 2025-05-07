from datetime import datetime 
from config import config
from app.database.db import get_db_cursor
from app.models.security import ConnectionLog, BlockedIP, UserLog

def is_ip_blocked(ip_address):
    """Check if an IP is currently blocked"""
    with get_db_cursor() as cursor:
        cursor.execute(BlockedIP.is_blocked_query(), (ip_address,))
        return cursor.fetchone() is not None 

def log_connection(ip_address, username):
    """Log a connection attempt and check for suspicious activity"""
    with get_db_cursor() as cursor:
        # Record connection
        cursor.execute(ConnectionLog.insert_query(), (ip_address, username))

        # Check connection frequency 
        cursor.execute(ConnectionLog.count_recent_query(), (ip_address,))
        connection_count = cursor.fetchone()[0]

        if connection_count > config.MAX_CONNECTION_PER_MINUTE:
            # Block IP for syspicious activity 
            block_expires = datetime.now() + config.BLOCK_DURATION
            reason = f"Too many connections: {connection_count}/min"

            cursor.execute(
                BlockedIP.block_ip_query(),
                (ip_address, block_expires, reason, block_expires, reason)
            )
            return False 
    
        return True 

def get_protection_stats():
    """Get current DDoS protection statistics"""
    with get_db_cursor() as cursor:
        # Get connection counts by IP in the last hour 
        cursor.execute("""
            SELECT ip_address, COUNT(*)
            FROM connection_log 
            WHERE timestamp > NOW() - INTERVAL '1 hour'
            GROUP BY ip_address
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        active_ips = [{"ip": row[0], "count": row[1]} for row in cursor.fetchall()]

        # Get currently blocked IPs 
        cursor.execute("""
            SELECT ip_address, blocked_at, block_expires, reason
            FROM blocked_ips 
            WHERE block_expires > NOW()
        """)

        blocked = [
            {
                "ip": row[0],
                "blocked_at": row[1],
                "expires": row[2],
                "reason": row[3]
            }
            for row in cursor.fetchall()
        ]

        return {
            "most_active_ips": active_ips,
            "blocked_ips": blocked
        }

def log_query(ip_address, username, query, executed):
    """Log a user query when executed"""
    with get_db_cursor() as cursor:
        # Record query
        cursor.execute(UserLog.insert_query(), (ip_address, username, query, executed))

        return True 
