import socket
import threading
import time
import logging
import yaml
import os
import sys
import psycopg2
from collections import defaultdict
from colorama import Fore, Style, init

# Initialize colorama for cross-platform colored terminal output
init()

# Ensure logs directory exists
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configure logging
logging.basicConfig(
    filename='logs/monitor.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('db_monitor')

class DBMonitor:
    def __init__(self, config_path='config/server.yml'):
        # Load configuration
        with open(config_path, 'r') as config_file:
            config = yaml.safe_load(config_file)
        
        self.listen_port = config['server']['listen_port']
        self.db_host = config['database']['host']
        self.db_port = config['database']['port']
        self.db_type = config['database']['type']
        self.db_name = config['database']['db_name']
        self.db_user = config['database']['user']
        self.db_password = config['database']['password']
        
        # Stats tracking
        self.query_counts = defaultdict(int)  # IP -> total query count
        self.connection_count = 0
        self.active_connections = 0
        self.start_time = time.time()
        
        print(f"{Fore.GREEN}Initialized DB Monitor for {self.db_type}{Style.RESET_ALL}")
        logger.info(f"Server initialized for {self.db_type} database")
    
    def start(self):
        """Start the monitoring server"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server.bind(('0.0.0.0', self.listen_port))
            server.listen(100)
            print(f"{Fore.GREEN}DB Monitor listening on port {self.listen_port}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Press Ctrl+C to stop{Style.RESET_ALL}")
            logger.info(f"Server listening on port {self.listen_port}")
            
            # Start the statistics display thread
            stats_thread = threading.Thread(target=self.display_stats)
            stats_thread.daemon = True
            stats_thread.start()
            
            while True:
                client, address = server.accept()
                logger.info(f"New connection from {address[0]}:{address[1]}")
                self.connection_count += 1
                self.active_connections += 1
                
                # Handle client connection in a separate thread
                client_handler = threading.Thread(
                    target=self.handle_client,
                    args=(client, address)
                )
                client_handler.daemon = True
                client_handler.start()
                
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Server shutdown initiated{Style.RESET_ALL}")
            logger.info("Server shutdown initiated")
        except Exception as e:
            print(f"{Fore.RED}Server error: {str(e)}{Style.RESET_ALL}")
            logger.error(f"Server error: {str(e)}")
        finally:
            server.close()
    
    def handle_client(self, client_socket, address):
        client_ip = address[0]
        client_socket.settimeout(60)  # Set client connection timeout to 1 minute
        try:
            while True:
                data = client_socket.recv(4096)
                if not data:
                    break
                self.log_query(client_ip, data)
                # Connect to the database and execute the query as before
                if self.db_type.lower() == 'postgresql':
                    db_conn = psycopg2.connect(
                        host=self.db_host,
                        port=self.db_port,
                        dbname=self.db_name,
                        user=self.db_user,
                        password=self.db_password
                    )
                    cursor = db_conn.cursor()
                    query_str = data.decode('utf-8')
                    print(f"{Fore.CYAN}Executing query: {query_str}{Style.RESET_ALL}")
                    cursor.execute(query_str)
                    try:
                        results = cursor.fetchall()
                        column_names = [desc[0] for desc in cursor.description]
                        response = "Query executed successfully.\n\n"
                        response += " | ".join(column_names) + "\n"
                        response += "-" * (sum(len(name) for name in column_names) + (3 * (len(column_names) - 1))) + "\n"
                        for row in results:
                            response += " | ".join(str(val) for val in row) + "\n"
                        client_socket.send(response.encode())
                    except psycopg2.ProgrammingError:
                        response = f"Command executed successfully. Rows affected: {cursor.rowcount}\n"
                        client_socket.send(response.encode())
                    db_conn.commit()
                    cursor.close()
                    db_conn.close()
                elif self.db_type.lower() == 'mysql':
                    # Add MySQL implementation here if needed
                    pass
                else:
                    error_msg = f"Unsupported database type: {self.db_type}"
                    print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
                    client_socket.send(f"ERROR: {error_msg}\n".encode())
        except socket.timeout:
            logger.info(f"Connection from {client_ip} timed out.")
        except Exception as e:
            print(f"{Fore.RED}Error handling client {client_ip}: {str(e)}{Style.RESET_ALL}")
            logger.error(f"Error handling client {client_ip}: {str(e)}")
        finally:
            client_socket.close()
            logger.info(f"Connection from {client_ip} closed")
            self.active_connections -= 1
    
    def log_query(self, client_ip, data):
        """Log a query"""
        now = time.time()
        with open('logs/queries.log', 'a') as log_file:
            log_entry = f"{now},{client_ip},{data[:100]}\n"
            log_file.write(log_entry)
        self.query_counts[client_ip] += 1
    
    def display_stats(self):
        """Display server statistics periodically"""
        while True:
            time.sleep(2)
            
            uptime = time.time() - self.start_time
            uptime_str = f"{int(uptime // 3600):02d}:{int((uptime % 3600) // 60):02d}:{int(uptime % 60):02d}"
            
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"{Fore.GREEN}===== DB Monitor Statistics ====={Style.RESET_ALL}")
            print(f"Uptime: {uptime_str}")
            print(f"Total connections: {self.connection_count}")
            print(f"Active connections: {self.active_connections}")
            print(f"Database: {self.db_type} on {self.db_host}:{self.db_port}")
            print(f"Listening on port: {self.listen_port}")
            print(f"\n{Fore.CYAN}===== Client Activity ====={Style.RESET_ALL}")
            
            if not self.query_counts:
                print("No client activity yet")
            else:
                print(f"{'IP Address':<15} {'Queries':<8}")
                print("-" * 25)
                for ip, count in self.query_counts.items():
                    print(f"{ip:<15} {count:<8}")
                    
            print(f"\n{Fore.YELLOW}Press Ctrl+C to stop server{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        monitor = DBMonitor()
        monitor.start()
    except Exception as e:
        print(f"{Fore.RED}Fatal error: {str(e)}{Style.RESET_ALL}")
        logger.critical(f"Fatal error: {str(e)}")
        sys.exit(1)
