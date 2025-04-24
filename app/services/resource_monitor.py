# app/services/resource_monitor.py
"""Service for monitoring database resources and client behavior"""
import time
from datetime import datetime
from app.database.db import get_db_cursor
from app.models.client_profiles import ClientRiskProfile, DatabaseLoadHistory
from config import config

class ResourceMonitor:
    """Monitor database resources and update client risk profiles"""
    
    
    @staticmethod
    def get_database_stats():
        """
        Query database statistics without requiring pg_stat_statements.
        """
        try:
            with get_db_cursor() as cursor:
                # Get active connections
                cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
                active_connections = cursor.fetchone()[0]
                
                # Get information about currently running queries
                cursor.execute("""
                    SELECT COUNT(*), 
                           AVG(EXTRACT(EPOCH FROM (now() - query_start))),
                           MAX(EXTRACT(EPOCH FROM (now() - query_start)))
                    FROM pg_stat_activity 
                    WHERE state = 'active' 
                      AND query NOT ILIKE '%pg_stat_activity%'
                """)
                row = cursor.fetchone()
                running_queries = row[0]
                avg_query_time = row[1] if row[1] is not None else 0
                max_query_time = row[2] if row[2] is not None else 0
                
                # Calculate a simple load factor without pg_stat_statements
                load_factor = active_connections / max(1, config.MAX_CONNECTIONS)
                
                # Record load history
                cursor.execute(
                    DatabaseLoadHistory.insert_load_history(),
                    (active_connections, running_queries, avg_query_time, max_query_time, load_factor)
                )
                
                return {
                    'active_connections': active_connections,
                    'running_queries': running_queries,
                    'avg_query_time': avg_query_time,
                    'max_query_time': max_query_time,
                    'total_calls': 0,  # No data without pg_stat_statements
                    'overall_avg_time': 0,  # No data without pg_stat_statements
                    'load_factor': load_factor
                }
        except Exception as e:
            print(f"Error getting database stats: {e}")
            # Return default values
            return {
                'error': str(e),
                'active_connections': 0,
                'running_queries': 0,
                'avg_query_time': 0,
                'max_query_time': 0,
                'load_factor': 1.0
            }

        
        with get_db_cursor() as cursor:
            # Get active connections
            cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
            active_connections = cursor.fetchone()[0]
            
            # Get information about currently running queries
            cursor.execute("""
                SELECT COUNT(*), 
                       AVG(EXTRACT(EPOCH FROM (now() - query_start))),
                       MAX(EXTRACT(EPOCH FROM (now() - query_start)))
                FROM pg_stat_activity 
                WHERE state = 'active' 
                  AND query NOT ILIKE '%pg_stat_activity%'
            """)
            row = cursor.fetchone()
            running_queries = row[0]
            avg_query_time = row[1] if row[1] is not None else 0
            max_query_time = row[2] if row[2] is not None else 0
            
            # Query pg_stat_statements for overall statistics
            if is_enabled:
                cursor.execute("""
                    SELECT SUM(calls), 
                           SUM(total_exec_time)/SUM(calls) as avg_time
                    FROM pg_stat_statements
                """)
                row = cursor.fetchone()
                total_calls = row[0] if row[0] is not None else 0
                overall_avg_time = row[1] if row[1] is not None else 0
            else:
                total_calls = 0
                overall_avg_time = 0
            
            # Calculate a load factor (higher means more load)
            # This is a simple formula that can be adjusted based on specific needs
            load_factor = (active_connections / max(1, config.MAX_CONNECTIONS)) * 0.5 + \
                          (avg_query_time / max(0.1, config.TARGET_QUERY_TIME)) * 0.5
            
            # Record load history
            cursor.execute(
                DatabaseLoadHistory.insert_load_history(),
                (active_connections, running_queries, avg_query_time, max_query_time, load_factor)
            )
            
            return {
                'active_connections': active_connections,
                'running_queries': running_queries,
                'avg_query_time': avg_query_time,
                'max_query_time': max_query_time,
                'total_calls': total_calls,
                'overall_avg_time': overall_avg_time,
                'load_factor': load_factor
            }
    
    @staticmethod
    def get_client_resource_usage(ip_address):
        """
        Get resource usage statistics for a specific client.
        Requires pg_stat_statements.
        """
        # _, is_enabled = check_pg_stat_statements()

        with get_db_cursor() as cursor:
             # Check if extension is installed
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_available_extensions 
                    WHERE name = 'pg_stat_statements'
                )
            """)
            is_installed = cursor.fetchone()[0]
            
            # Check if extension is enabled
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension 
                    WHERE extname = 'pg_stat_statements'
                )
            """)
            is_enabled = cursor.fetchone()[0]

            
        if not is_enabled:
            return None
        
        with get_db_cursor() as cursor:
            # Since pg_stat_statements doesn't track client IPs, we need to use our own logs
            cursor.execute("""
                SELECT COUNT(*) as query_count,
                       AVG(estimated_cost) as avg_cost,
                       MAX(estimated_cost) as max_cost,
                       COUNT(CASE WHEN risk_score > 0.7 THEN 1 END) as high_risk_count
                FROM query_cost_log
                WHERE ip_address = %s
                  AND timestamp > NOW() - INTERVAL '1 hour'
            """, (ip_address,))
            
            result = cursor.fetchone()
            if not result:
                return None
                
            return {
                'query_count': result[0],
                'avg_query_cost': result[1] or 0.0,
                'max_query_cost': result[2] or 0.0,
                'high_risk_queries': result[3] or 0
            }
    
    @staticmethod
    def calculate_client_risk_score(ip_address, query_stats):
        """
        Calculate a risk score for a client based on their query patterns.
        """
        if not query_stats or query_stats['query_count'] == 0:
            return 0.0
            
        # Base risk factors
        query_volume_risk = min(1.0, query_stats['query_count'] / config.QUERY_VOLUME_THRESHOLD)
        high_cost_risk = min(1.0, query_stats['max_query_cost'] / 1000.0)
        high_risk_query_ratio = query_stats['high_risk_queries'] / query_stats['query_count']
        
        # Calculate overall risk (weighted sum)
        risk_score = (query_volume_risk * 0.4) + \
                     (high_cost_risk * 0.3) + \
                     (high_risk_query_ratio * 0.3)
                     
        return min(1.0, risk_score)
    
    @staticmethod
    def calculate_timeout_multiplier(risk_score, db_load_factor):
        """
        Calculate a timeout multiplier based on risk score and DB load.
        
        Lower values mean more restrictive timeouts.
        1.0 is the baseline (normal timeout).
        """
        # Base multiplier is inversely proportional to risk score
        # Higher risk = lower multiplier = shorter timeout
        base_multiplier = 1.0 - (risk_score * 0.8)  # 0.2 to 1.0
        
        # Further reduce multiplier under high load
        load_adjustment = 1.0 / max(1.0, db_load_factor)  # Reduces as load increases
        
        # Combine factors but ensure minimum value
        return max(0.1, base_multiplier * load_adjustment)
    
    @staticmethod
    def update_client_profile(ip_address, query_cost=None, query_risk=None):
        """
        Update a client's risk profile based on their latest query and overall patterns.
        
        Args:
            ip_address: Client IP address
            query_cost: Cost of the latest query (optional)
            query_risk: Risk score of the latest query (optional)
            
        Returns:
            dict: Updated client profile
        """
        # Get current DB load factor
        with get_db_cursor() as cursor:
            cursor.execute(DatabaseLoadHistory.get_current_load_factor())
            result = cursor.fetchone()
            db_load_factor = result[0] if result and result[0] is not None else 1.0
        
        # Get client's resource usage statistics
        query_stats = ResourceMonitor.get_client_resource_usage(ip_address)
        
        # Calculate new risk score
        if query_stats:
            risk_score = ResourceMonitor.calculate_client_risk_score(ip_address, query_stats)
            
            # Calculate timeout multiplier
            timeout_multiplier = ResourceMonitor.calculate_timeout_multiplier(risk_score, db_load_factor)
            
            # Update client profile in database
            with get_db_cursor() as cursor:
                # Check if profile exists
                cursor.execute(ClientRiskProfile.get_profile_query(), (ip_address,))
                profile_exists = cursor.fetchone() is not None
                
                # Update values in the profile
                cursor.execute(
                    ClientRiskProfile.update_profile_query(),
                    (
                        # VALUES for INSERT
                        ip_address, risk_score, 1, 
                        query_stats['avg_query_cost'], query_stats['max_query_cost'], 
                        query_stats['high_risk_queries'], timeout_multiplier,
                        # VALUES for UPDATE (after ON CONFLICT)
                        risk_score, 1, 
                        query_cost or 0, 1, 
                        query_cost or 0, 
                        1 if query_risk and query_risk > 0.7 else 0,
                        timeout_multiplier
                    )
                )
                
                # Get updated profile
                cursor.execute(ClientRiskProfile.get_profile_query(), (ip_address,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'ip_address': ip_address,
                        'risk_score': row[0],
                        'total_queries': row[1],
                        'avg_query_cost': row[2],
                        'max_query_cost': row[3],
                        'high_risk_queries': row[4], 
                        'timeout_multiplier': row[5],
                        'last_updated': row[6],
                        'notes': row[7]
                    }
        
        return None

    @staticmethod
    def get_client_profile(ip_address):
        """
        Get a client's current risk profile.
        
        Returns:
            dict: Client profile or None if not found
        """
        with get_db_cursor() as cursor:
            cursor.execute(ClientRiskProfile.get_profile_query(), (ip_address,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'ip_address': ip_address,
                    'risk_score': row[0],
                    'total_queries': row[1],
                    'avg_query_cost': row[2],
                    'max_query_cost': row[3],
                    'high_risk_queries': row[4],
                    'timeout_multiplier': row[5],
                    'last_updated': row[6],
                    'notes': row[7]
                }
        
        return None

    @staticmethod
    def get_statement_timeout(ip_address):
        """
        Calculate the appropriate statement timeout for a client based on their risk profile
        and current database load.
        
        Returns:
            int: Statement timeout in milliseconds
        """
        # Get client profile to determine timeout multiplier
        profile = ResourceMonitor.get_client_profile(ip_address)
        
        # Default timeout
        base_timeout = config.DEFAULT_STATEMENT_TIMEOUT
        
        # Apply multiplier from profile if available
        if profile:
            multiplier = profile['timeout_multiplier']
        else:
            # No profile means new client - use default multiplier
            multiplier = 1.0
            
        # Get current DB load factor
        with get_db_cursor() as cursor:
            cursor.execute(DatabaseLoadHistory.get_current_load_factor())
            result = cursor.fetchone()
            db_load_factor = result[0] if result and result[0] is not None else 1.0
            
        # Under high load, reduce timeout based on load factor
        if db_load_factor > 2.0:
            # Further reduce timeout for high load scenarios
            load_adjustment = 1.0 / db_load_factor
            multiplier *= load_adjustment
        
        # Calculate final timeout
        timeout_ms = int(base_timeout * multiplier)
        
        # Ensure minimum timeout
        return max(config.MIN_STATEMENT_TIMEOUT, timeout_ms)
