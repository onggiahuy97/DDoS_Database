# app/models/client_profiles.py
"""Models for client risk profiles and resource controls"""

# Create table for client risk profiles
CLIENT_PROFILES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS client_risk_profiles (
    ip_address VARCHAR(45) PRIMARY KEY,
    risk_score FLOAT DEFAULT 0.0,
    total_queries INTEGER DEFAULT 0,
    avg_query_cost FLOAT DEFAULT 0.0,
    max_query_cost FLOAT DEFAULT 0.0,
    high_risk_queries INTEGER DEFAULT 0,
    timeout_multiplier FLOAT DEFAULT 1.0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS database_load_history (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    active_connections INTEGER,
    running_queries INTEGER,
    avg_query_time FLOAT,
    max_query_time FLOAT,
    load_factor FLOAT
);
"""

class ClientRiskProfile:
    """Model for client risk profiles"""
    table_name = "client_risk_profiles"
    
    @staticmethod
    def get_profile_query():
        return f"""
            SELECT risk_score, total_queries, avg_query_cost, 
                   max_query_cost, high_risk_queries, timeout_multiplier, 
                   last_updated, notes
            FROM {ClientRiskProfile.table_name}
            WHERE ip_address = %s
        """
    
    @staticmethod
    def update_profile_query():
        return f"""
            INSERT INTO {ClientRiskProfile.table_name}
            (ip_address, risk_score, total_queries, avg_query_cost, 
             max_query_cost, high_risk_queries, timeout_multiplier, last_updated)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (ip_address) DO UPDATE
            SET risk_score = %s,
                total_queries = {ClientRiskProfile.table_name}.total_queries + %s,
                avg_query_cost = 
                    (({ClientRiskProfile.table_name}.avg_query_cost * {ClientRiskProfile.table_name}.total_queries) + %s) / 
                    ({ClientRiskProfile.table_name}.total_queries + %s),
                max_query_cost = GREATEST({ClientRiskProfile.table_name}.max_query_cost, %s),
                high_risk_queries = {ClientRiskProfile.table_name}.high_risk_queries + %s,
                timeout_multiplier = %s,
                last_updated = NOW()
        """
    
    @staticmethod
    def get_high_risk_clients_query():
        return f"""
            SELECT ip_address, risk_score, total_queries, avg_query_cost, 
                   max_query_cost, high_risk_queries, timeout_multiplier
            FROM {ClientRiskProfile.table_name}
            WHERE risk_score > 0.5
            ORDER BY risk_score DESC
            LIMIT 20
        """

class DatabaseLoadHistory:
    """Model for database load history"""
    table_name = "database_load_history"
    
    @staticmethod
    def insert_load_history():
        return f"""
            INSERT INTO {DatabaseLoadHistory.table_name}
            (active_connections, running_queries, avg_query_time, max_query_time, load_factor)
            VALUES (%s, %s, %s, %s, %s)
        """
    
    @staticmethod
    def get_current_load_factor():
        return f"""
            SELECT load_factor
            FROM {DatabaseLoadHistory.table_name}
            ORDER BY timestamp DESC
            LIMIT 1
        """
