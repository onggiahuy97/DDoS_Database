"""Database connection and operations"""
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager 
from app.models.security import CREATE_TABLES_SQL
from app.models.client_profiles import CLIENT_PROFILES_TABLE_SQL
from config import config 

# Create a connection pool 
db_pool = SimpleConnectionPool(
    1, 20,
    dbname=config.DB_NAME,
    user=config.DB_USER,
    password=config.DB_PASSWORD,
    host=config.DB_HOST,
    port=config.DB_PORT,
)

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = db_pool.getconn()
    try: 
        yield conn
    finally:
        db_pool.putconn(conn)

@contextmanager 
def get_db_cursor():
    """Context manager for database cursors""" 
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try: 
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise 
        finally:
            cursor.close()

def setup_pg_stat_statements():
    """
    Try to enable pg_stat_statements if it's installed but not enabled.
    Returns True if successful, False otherwise.
    """
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

def setup_database():
    """Initialize the database and create tables if they don't exist"""
    with get_db_cursor() as cursor:
        # Create security tables
        cursor.execute(CREATE_TABLES_SQL)
        
        # Create client profile tables
        cursor.execute(CLIENT_PROFILES_TABLE_SQL)
    
    # Try to enable pg_stat_statements
    setup_pg_stat_statements()
