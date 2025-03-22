# main.py
import socket
import threading
import time
import logging
import yaml
import os
import sys
import psycopg2
from colorama import Fore, Style, init

# Import components from src/monitor
from src.monitor.query_analyzer import QueryAnalyzer
from src.monitor.rate_limiter import RateLimiter

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
        
        # Initialize components
        self.query_analyzer = QueryAnalyzer(self.db_type)
        self.rate_limiter = RateLimiter(config_path)
        
        # Stats tracking
        self.connection_count = 0
        self.active_connections = 0
        self.start_time = time.time()
        
        print(f"{Fore.GREEN}Initialized DB Monitor for {self.db_type}{Style.RESET_ALL}")
        logger.info(f"Server initialized for {self.db_type} database")
    
    def start(self):
        """Start the monitoring server"""
        # Set up server socket
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Allow port reuse
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server.bind(('0.0.0.0', self.listen_port))
            server.listen(100)  # Connection backlog
            
            print(f"{Fore.GREEN}DB Monitor listening on port {self.listen_port}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Press Ctrl+C to stop{Style.RESET_ALL}")
            logger.info(f"Server listening on port {self.listen_port}")
            
            # Start stats display thread
            stats_thread = threading.Thread(target=self.display_stats)
            stats_thread.daemon = True
            stats_thread.start()
            
            while True:
                client, address = server.accept()
                logger.info(f"New connection from {address[0]}:{address[1]}")
                
                self.connection_count += 1
                self.active_connections += 1
                
                # Check rate limit
                if not self.rate_limiter.check_rate_limit(address[0]):
                    print(f"{Fore.RED}Rate limit exceeded for {address[0]} - Closing connection{Style.RESET_ALL}")
                    client.send(b"ERROR: Rate limit exceeded\n")
                    client.close()
                    self.active_connections -= 1
                    continue
                
                # Handle each client in a separate thread
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
        """Handle a client connection"""
        client_ip = address[0]
        
        try:
            # Receive the query
            data = client_socket.recv(4096)
            if not data:
                logger.info(f"Empty connection from {client_ip}")
                client_socket.close()
                self.active_connections -= 1
                return
            
            # Analyze the query
            query_info = self.query_analyzer.parse_query(data)
            logger.info(f"Query from {client_ip}: Type={query_info['query_type']}, Complexity={query_info['complexity']}")
            
            # Check rate limit after analyzing the query
            if not self.rate_limiter.check_rate_limit(client_ip, query_info):
                print(f"{Fore.RED}Rate limit exceeded for {client_ip} - Rejecting query{Style.RESET_ALL}")
                client_socket.send(b"ERROR: Rate limit exceeded\n")
                client_socket.close()
                self.active_connections -= 1
                return
            
            # Connect to the database and execute the query
            try:
                # Establish database connection
                if self.db_type.lower() == 'postgresql':
                    db_conn = psycopg2.connect(
                        host=self.db_host,
                        port=self.db_port,
                        dbname=self.db_name,
                        user=self.db_user,
                        password=self.db_password
                    )
                    
                    # Create a cursor
                    cursor = db_conn.cursor()
                    
                    # Execute the query
                    query_str = data.decode('utf-8')
                    print(f"{Fore.CYAN}Executing query: {query_str}{Style.RESET_ALL}")
                    
                    # Record start time for query execution
                    query_start_time = time.time()
                    cursor.execute(query_str)
                    query_duration = time.time() - query_start_time
                    
                    # Log query execution time
                    logger.info(f"Query executed in {query_duration:.4f} seconds")
                    
                    # Fetch results
                    try:
                        results = cursor.fetchall()
                        
                        # Get column names
                        column_names = [desc[0] for desc in cursor.description]
                        
                        # Format results
                        response = f"Query executed successfully in {query_duration:.4f} seconds.\n\n"
                        response += " | ".join(column_names) + "\n"
                        response += "-" * (sum(len(name) for name in column_names) + (3 * (len(column_names) - 1))) + "\n"
                        
                        for row in results:
                            response += " | ".join(str(val) for val in row) + "\n"
                        
                        # Send response back to client
                        client_socket.send(response.encode())
                        
                    except psycopg2.ProgrammingError:
                        # Command executed successfully but no rows to fetch (e.g., INSERT)
                        response = f"Command executed successfully in {query_duration:.4f} seconds. Rows affected: {cursor.rowcount}\n"
                        client_socket.send(response.encode())
                    
                    # Commit the transaction
                    db_conn.commit()
                    
                    # Close cursor and connection
                    cursor.close()
                    db_conn.close()
                    
                elif self.db_type.lower() == 'mysql':
                    # Add MySQL implementation here
                    pass
                    
                else:
                    error_msg = f"Unsupported database type: {self.db_type}"
                    print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
                    client_socket.send(f"ERROR: {error_msg}\n".encode())
                    
            except Exception as db_error:
                error_msg = f"Database error: {str(db_error)}"
                print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
                client_socket.send(f"ERROR: {error_msg}\n".encode())
                logger.error(error_msg)
                
                # Record failed query
                self.rate_limiter.record_failed_query(client_ip)
                
        except Exception as e:
            print(f"{Fore.RED}Error handling client {client_ip}: {str(e)}{Style.RESET_ALL}")
            logger.error(f"Error handling client {client_ip}: {str(e)}")
        finally:
            # Clean up
            client_socket.close()
            self.active_connections -= 1
            logger.info(f"Connection from {client_ip} closed")
    
    def display_stats(self):
        """Display server statistics periodically"""
        while True:
            time.sleep(2)  # Update every 2 seconds
            
            # Calculate uptime
            uptime = time.time() - self.start_time
            uptime_str = f"{int(uptime // 3600):02d}:{int((uptime % 3600) // 60):02d}:{int(uptime % 60):02d}"
            
            # Clear screen (cross-platform)
            os.system('cls' if os.name == 'nt' else 'clear')
            
            # Display stats
            print(f"{Fore.GREEN}===== DB Monitor Statistics ====={Style.RESET_ALL}")
            print(f"Uptime: {uptime_str}")
            print(f"Total connections: {self.connection_count}")
            print(f"Active connections: {self.active_connections}")
            print(f"Database: {self.db_type} on {self.db_host}:{self.db_port}")
            print(f"Listening on port: {self.listen_port}")
            print(f"\n{Fore.CYAN}===== Client Activity ====={Style.RESET_ALL}")
            
            # Display client stats from rate limiter
            client_stats = self.rate_limiter.get_client_stats()
            
            if not client_stats:
                print("No client activity yet")
            else:
                print(f"{'IP Address':<15} {'Queries':<8} {'Queries/min':<12} {'Status':<10}")
                print("-" * 50)
                
                for ip, stats in client_stats.items():
                    status = f"{Fore.RED}WARNING{Style.RESET_ALL}" if stats['rate'] > self.rate_limiter.query_threshold else f"{Fore.GREEN}OK{Style.RESET_ALL}"
                    print(f"{ip:<15} {stats['count']:<8} {stats['rate']:<12.2f} {status}")
            
            print(f"\n{Fore.YELLOW}Press Ctrl+C to stop server{Style.RESET_ALL}")

def setup_environment():
    """Set up necessary directories and files"""
    directories = ['logs', 'config', 'src/monitor', 'src/detection', 'src/alerts']
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
    
    # Create empty log files if they don't exist
    log_files = ['logs/monitor.log', 'logs/queries.log', 'logs/alerts.log']
    for log_file in log_files:
        if not os.path.exists(log_file):
            with open(log_file, 'w') as f:
                pass  # Create empty file

if __name__ == "__main__":
    try:
        # Set up environment
        setup_environment()
        
        # Start the monitor
        monitor = DBMonitor()
        monitor.start()
    except Exception as e:
        print(f"{Fore.RED}Fatal error: {str(e)}{Style.RESET_ALL}")
        logger.critical(f"Fatal error: {str(e)}")
        sys.exit(1)
