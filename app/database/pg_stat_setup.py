# app/database/pg_stat_setup.py
"""Utilities for setting up and checking PostgreSQL extensions"""
from app.database.db import get_db_cursor

def check_pg_stat_statements():
    """
    Check if pg_stat_statements extension is installed and active.
    Returns a tuple (is_installed, is_enabled)
    """
    # Check if extension is installed
    with get_db_cursor() as cursor:
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

def setup_pg_stat_statements():
    """
    Try to enable pg_stat_statements if it's installed but not enabled.
    Returns True if successful, False otherwise.
    """
    is_installed, is_enabled = check_pg_stat_statements()
    
    if is_enabled:
        return True  # Already enabled
    
    if not is_installed:
        return False  # Not installed, can't enable
    
    try:
        with get_db_cursor() as cursor:
            cursor.execute("CREATE EXTENSION pg_stat_statements")
        return True
    except Exception as e:
        print(f"Failed to enable pg_stat_statements: {e}")
        return False
