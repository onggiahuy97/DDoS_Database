"""Database schema models for security features"""

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS connection_log (
    id SERIAL PRIMARY KEY,
    ip_address VARCHAR(45),
    username VARCHAR(100),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    query_count INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS blocked_ips (
    ip_address VARCHAR(45) PRIMARY KEY,
    blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    block_expires TIMESTAMP,
    reason TEXT
);
"""

class ConnectionLog:
    """Model for connection log entries"""
    table_name = "connection_log"
    
    @staticmethod
    def insert_query():
        return f"""
            INSERT INTO {ConnectionLog.table_name} (ip_address, username) 
            VALUES (%s, %s)
        """
    
    @staticmethod
    def count_recent_query(minutes=1):
        return f"""
            SELECT COUNT(*) FROM {ConnectionLog.table_name} 
            WHERE ip_address = %s AND timestamp > NOW() - INTERVAL '{minutes} minute'
        """

class BlockedIP:
    """Model for blocked IP addresses"""
    table_name = "blocked_ips"
    
    @staticmethod
    def is_blocked_query():
        return f"""
            SELECT 1 FROM {BlockedIP.table_name} 
            WHERE ip_address = %s AND block_expires > NOW()
        """
    
    @staticmethod
    def block_ip_query():
        return f"""
            INSERT INTO {BlockedIP.table_name} (ip_address, block_expires, reason) 
            VALUES (%s, %s, %s) 
            ON CONFLICT (ip_address) DO UPDATE 
            SET block_expires = %s, reason = %s
        """
