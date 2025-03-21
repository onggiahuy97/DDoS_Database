# main.py
import os
import sys
import logging
from src.monitor.server import DBMonitorServer

def setup_environment():
    """Set up necessary directories and files"""
    directories = ['logs', 'config', 'src']
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
    
    # Create empty log files if they don't exist
    log_files = ['logs/system.log', 'logs/queries.log', 'logs/alerts.log']
    for log_file in log_files:
        if not os.path.exists(log_file):
            with open(log_file, 'w') as f:
                pass  # Create empty file

if __name__ == "__main__":
    # Set up environment
    setup_environment()
    
    # Configure logging for the main script
    logging.basicConfig(
        filename='logs/system.log',
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger('main')
    
    try:
        logger.info("Starting DB Monitor")
        server = DBMonitorServer()
        server.start()
    except Exception as e:
        logger.critical(f"Fatal error in main: {str(e)}")
        sys.exit(1)
