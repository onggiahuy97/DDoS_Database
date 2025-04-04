"""Database connection and operations"""
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager 
from app.models.security import CREATE_TABLES_SQL
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

def setup_database():
    """Initialize the database and create tables if they don't exist"""
    with get_db_cursor() as cursor:
        cursor.execute(CREATE_TABLES_SQL)
