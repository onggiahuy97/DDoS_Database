"""
Run this script to fix the pg_stat_statements error
"""
import os

# Paths to modify
services_dir = os.path.join('app', 'services')
resource_monitor_path = os.path.join(services_dir, 'resource_monitor.py')

# Read the current file
with open(resource_monitor_path, 'r') as file:
    content = file.read()

# Modified get_database_stats method that works without pg_stat_statements
modified_method = """
    @staticmethod
    def get_database_stats():
        \"\"\"
        Query database statistics without requiring pg_stat_statements.
        \"\"\"
        try:
            with get_db_cursor() as cursor:
                # Get active connections
                cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
                active_connections = cursor.fetchone()[0]
                
                # Get information about currently running queries
                cursor.execute(\"\"\"
                    SELECT COUNT(*), 
                           AVG(EXTRACT(EPOCH FROM (now() - query_start))),
                           MAX(EXTRACT(EPOCH FROM (now() - query_start)))
                    FROM pg_stat_activity 
                    WHERE state = 'active' 
                      AND query NOT ILIKE '%pg_stat_activity%'
                \"\"\")
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
"""

# Replace the get_database_stats method
import re
pattern = r"@staticmethod\s+def get_database_stats\(\)[\s\S]+?return {[\s\S]+?}"
fixed_content = re.sub(pattern, modified_method, content)

# Write the fixed content back
with open(resource_monitor_path, 'w') as file:
    file.write(fixed_content)

print("ResourceMonitor.get_database_stats() has been fixed to work without pg_stat_statements.")
print("Now run your application with: python run.py")
