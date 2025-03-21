import socket
import threading
import time
import logging
import yaml
import os
import sys
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
        
        # Rate limiting
        self.window_size = config['detection']['window_size']
        self.query_threshold = config['detection']['threshold']['queries_per_minute']
        
        # Stats tracking
        self.query_counts = defaultdict(list)  # IP -> [(timestamp, 1)]
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
                if not self.check_rate_limit(address[0]):
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
            # Connect to the actual database
            db_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            db_socket.connect((self.db_host, self.db_port))
            
            print(f"{Fore.CYAN}Client {client_ip} connected to database{Style.RESET_ALL}")
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
            
        except ConnectionRefusedError:
            error_msg = f"Error: Could not connect to database at {self.db_host}:{self.db_port}"
            print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
            client_socket.send(f"{error_msg}\n".encode())
            logger.error(error_msg)
        except Exception as e:
            print(f"{Fore.RED}Error handling client {client_ip}: {str(e)}{Style.RESET_ALL}")
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
                
                # Log received data
                if direction == "client-to-db":
                    # This is a query from client to DB - log it
                    self.log_query(client_ip, data)
                
                # Forward data
                destination.send(data)
        except Exception as e:
            logger.error(f"Error in {direction} forwarding for {client_ip}: {str(e)}")
    
    def log_query(self, client_ip, data):
        """Log a query and check rate limits"""
        now = time.time()
        
        # Log the query
        with open('logs/queries.log', 'a') as log_file:
            log_entry = f"{now},{client_ip},{data[:100]}\n"
            log_file.write(log_entry)
        
        # Update query counts for rate limiting
        self.query_counts[client_ip].append((now, 1))
        
        # Clean old entries
        if client_ip in self.query_counts:
            self.query_counts[client_ip] = [
                (ts, count) for ts, count in self.query_counts[client_ip]
                if now - ts < self.window_size
            ]
    
    def check_rate_limit(self, client_ip):
        """Check if the client has exceeded rate limits"""
        now = time.time()
        
        # Clean old entries
        if client_ip in self.query_counts:
            self.query_counts[client_ip] = [
                (ts, count) for ts, count in self.query_counts[client_ip]
                if now - ts < self.window_size
            ]
            
            # Count queries in current window
            total_queries = sum(count for ts, count in self.query_counts[client_ip])
            
            # If we have enough history
            if self.query_counts[client_ip]:
                # Calculate the actual window size (might be less than self.window_size)
                earliest_ts = min(ts for ts, _ in self.query_counts[client_ip])
                actual_window = now - earliest_ts
                
                # Only apply rate limiting if we have some history
                if actual_window > 5:  # At least 5 seconds of history
                    # Normalize to per-minute rate
                    queries_per_minute = (total_queries / actual_window) * 60
                    
                    # Check if rate exceeds threshold
                    if queries_per_minute > self.query_threshold:
                        logger.warning(f"Rate limit exceeded for {client_ip}: {queries_per_minute:.2f} queries/min")
                        return False
        
        return True
    
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
            
            # Display client stats
            if not self.query_counts:
                print("No client activity yet")
            else:
                print(f"{'IP Address':<15} {'Queries':<8} {'Queries/min':<12} {'Status':<10}")
                print("-" * 50)
                
                now = time.time()
                for ip, queries in self.query_counts.items():
                    # Clean old entries first
                    valid_queries = [(ts, count) for ts, count in queries if now - ts < self.window_size]
                    
                    if valid_queries:
                        total = sum(count for _, count in valid_queries)
                        earliest_ts = min(ts for ts, _ in valid_queries)
                        window = now - earliest_ts
                        
                        if window > 0:
                            rate = (total / window) * 60
                            status = f"{Fore.RED}WARNING{Style.RESET_ALL}" if rate > self.query_threshold else f"{Fore.GREEN}OK{Style.RESET_ALL}"
                            print(f"{ip:<15} {total:<8} {rate:<12.2f} {status}")
            
            print(f"\n{Fore.YELLOW}Press Ctrl+C to stop server{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        monitor = DBMonitor()
        monitor.start()
    except Exception as e:
        print(f"{Fore.RED}Fatal error: {str(e)}{Style.RESET_ALL}")
        logger.critical(f"Fatal error: {str(e)}")
        sys.exit(1)
