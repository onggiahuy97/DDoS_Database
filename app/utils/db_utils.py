# app/utils/db_utils.py
"""Utility functions for database operations"""

def check_pg_stat_statements(cursor):
    """
    Check if pg_stat_statements extension is installed and active.
    Returns a tuple (is_installed, is_enabled)
    """
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
    
    return is_installed, is_enabled
