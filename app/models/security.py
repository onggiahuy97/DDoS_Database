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

CREATE TABLE IF NOT EXISTS query_cost_log (
    id SERIAL PRIMARY KEY,
    ip_address VARCHAR(45),
    query_hash TEXT,
    normalized_query TEXT,
    estimated_cost FLOAT,
    risk_score FLOAT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS user_logs (
    id SERIAL PRIMARY KEY,
    ip_address VARCHAR(45),
    username VARCHAR(100),
    query_text TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    query_count INTEGER DEFAULT 1,
    executed BOOLEAN
);
CREATE TABLE IF NOT EXISTS blocked_users (
    user_id VARCHAR PRIMARY KEY,
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

class QueryCostLog:
    """Model for query cost log entries"""
    table_name = "query_cost_log"
    
    @staticmethod
    def insert_query():
        return f"""
            INSERT INTO {QueryCostLog.table_name} 
            (ip_address, query_hash, normalized_query, estimated_cost, risk_score) 
            VALUES (%s, %s, %s, %s, %s)
        """
    
    @staticmethod
    def get_recent_query_costs(ip_address, minutes=5):
        return f"""
            SELECT AVG(estimated_cost), AVG(risk_score) 
            FROM {QueryCostLog.table_name} 
            WHERE ip_address = %s AND timestamp > NOW() - INTERVAL '{minutes} minute'
        """

class UserLog:
    """Model for connection log entries"""
    table_name = "user_logs"

    @staticmethod
    def insert_query():
        return f"""
            INSERT INTO {UserLog.table_name} (ip_address, username, query_text, executed) 
            VALUES (%s, %s, %s, %s)
        """

    @staticmethod
    def count_recent_query(minutes=1):
        return f"""
            SELECT COUNT(*) FROM {ConnectionLog.table_name} 
            WHERE ip_address = %s AND timestamp > NOW() - INTERVAL '{minutes} minute'
        """

class BlockedUser:
    """Model for blocked User addresses"""
    table_name = "blocked_users"

    @staticmethod
    def is_blocked_user():
        return f"""
            SELECT 1 FROM {BlockedUser.table_name} 
            WHERE user_id = %s AND block_expires > NOW()
        """

    @staticmethod
    def block_user():
        return f"""
            INSERT INTO {BlockedUser.table_name} (user_id, block_expires, reason) 
            VALUES (%s, %s, %s) 
            ON CONFLICT (user_id) DO UPDATE 
            SET block_expires = %s, reason = %s
        """

