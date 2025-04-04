import os 
from datetime import timedelta 

# Load environment variables or use defaults 
class Config:
    DB_NAME = os.environ.get('DB_NAME', 'testdb')
    DB_USER = os.environ.get('DB_USER', 'huyong97')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'password')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')

    MAX_CONNECTION_PER_MINUTE = int(os.environ.get('MAX_CONNECTION_PER_MINUTE', 10))
    MAX_QUERIES_PER_MINUTE = int(os.environ.get('MAX_QUERIES_PER_MINUTE', 10))
    BLOCK_DURATION = timedelta(minutes=int(os.environ.get('BLOCK_DURATION_MINUTES', 5)))  # in minutes

    API_PORT = int(os.environ.get('API_PORT', 5002))
    DEBUG_MODE = os.environ.get('DEBUG_MODE', 'False').lower() == 'true'

config = Config()
