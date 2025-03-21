# src/monitor/server.py
import socket
import threading
import logging
import yaml
import time

# Configure logging
logging.basicConfig(
    filename='logs/system.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('db_monitor')

class DBMonitorServer:
    def __init__(self, config_path='config/server.yml'):
        # Load configuration
        with open(config_path, 'r') as config_file:
            config = yaml.safe_load(config_file)
        
        self.listen_port = config['server']['listen_port']
        self.db_host = config['database']['host']
        self.db_port = config['database']['port']
        self.db_type = config['database']['type']  # 'mysql', 'postgresql', etc.
        
        # Stats tracking
        self.connection_count = 0
        self.active_connections = 0
        self.start_time = time.time()
        
        logger.info(f"Server initialized for {self.db_type} database")
        
    def start(self):
        """Start the monitoring server"""
        # Set up server socket
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Allow port reuse
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', self.listen_port))
        server.listen(100)  # Connection backlog
        
        logger.info(f"Server listening on port {self.listen_port}")
        print(f"DB Monitor Server listening on port {self.listen_port}")
        
        try:
            while True:
                client, address = server.accept()
                logger.info(f"New connection from {address[0]}:{address[1]}")
                
                self.connection_count += 1
                self.active_connections += 1
                
                # Handle each client in a separate thread
                client_handler = threading.Thread(
                    target=self.handle_client,
                    args=(client, address)
                )
                client_handler.daemon = True
                client_handler.start()
        except KeyboardInterrupt:
            logger.info("Server shutdown initiated")
            server.close()
        except Exception as e:
            logger.error(f"Server error: {str(e)}")
            server.close()
    
    def handle_client(self, client_socket, address):
        """Handle a client connection"""
        client_ip = address[0]
        
        try:
            # Connect to the actual database
            db_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            db_socket.connect((self.db_host, self.db_port))
            
            logger.info(f"Connected to database for client {client_ip}")
            
            # Set up for bidirectional communication
            client_to_db = threading.Thread(
                target=self.forward_data,
                args=(client_socket, db_socket, client_ip, "client-to-db")
            )
            db_to_client = threading.Thread(
                target=self.forward_data,
                args=(db_socket, client_socket, client_ip, "db-to-client")
            )
            
            client_to_db.daemon = True
            db_to_client.daemon = True
            
            client_to_db.start()
            db_to_client.start()
            
            # Wait for both directions to complete
            client_to_db.join()
            db_to_client.join()
            
        except Exception as e:
            logger.error(f"Error handling client {client_ip}: {str(e)}")
        finally:
            # Clean up
            self.active_connections -= 1
            client_socket.close()
            if 'db_socket' in locals():
                db_socket.close()
            logger.info(f"Connection from {client_ip} closed")
    
    def forward_data(self, source, destination, client_ip, direction):
        """Forward data between sockets and log the traffic"""
        try:
            while True:
                # Receive data
                data = source.recv(4096)
                if not data:
                    break
                
                # Log received data (in real implementation, you'd parse and analyze the query here)
                if direction == "client-to-db":
                    # This is a query from client to DB - log it
                    self.log_query(client_ip, data)
                
                # Forward data
                destination.send(data)
        except Exception as e:
            logger.error(f"Error in {direction} forwarding for {client_ip}: {str(e)}")
    
    def log_query(self, client_ip, data):
        """Log a query for analysis"""
        # Basic logging for now, will be expanded with query analysis later
        query_time = time.time()
        
        # In a real implementation, parse the query based on db_type
        # For now, just log the raw data
        with open('logs/queries.log', 'a') as log_file:
            log_entry = f"{query_time},{client_ip},{data[:100]}\n"
            log_file.write(log_entry)
            
        logger.debug(f"Logged query from {client_ip}")

if __name__ == "__main__":
    try:
        server = DBMonitorServer()
        server.start()
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}")
