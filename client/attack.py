import socket
import sys
import time
import argparse
from colorama import Fore, Style, init
import threading
import random
import ipaddress

# Initialize colorama for cross-platform colored terminal output
init()

class DBClient:
    def __init__(self, host='localhost', port=8080, client_id=None):
        self.host = host
        self.port = port
        self.socket = None
        self.client_id = client_id or f"Client-{random.randint(1000, 9999)}"
        # Generate a random IP for identification purposes
        self.fake_ip = str(ipaddress.IPv4Address(random.randint(1, 2**32-1)))
        while ipaddress.IPv4Address(self.fake_ip).is_private:
            self.fake_ip = str(ipaddress.IPv4Address(random.randint(1, 2**32-1)))
    
    def connect(self):
        """Connect to the monitoring server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print(f"{Fore.GREEN}{self.client_id} ({self.fake_ip}) connected to server at {self.host}:{self.port}{Style.RESET_ALL}")
            
            # Send an initial header with the fake IP
            header = f"X-Client-IP: {self.fake_ip}\r\n\r\n"
            self.socket.send(header.encode())
            
            return True
        except ConnectionRefusedError:
            print(f"{Fore.RED}{self.client_id} ({self.fake_ip}) Error: Connection refused. Is the server running?{Style.RESET_ALL}")
            return False
        except Exception as e:
            print(f"{Fore.RED}{self.client_id} ({self.fake_ip}) Error connecting: {str(e)}{Style.RESET_ALL}")
            return False
    
    def disconnect(self):
        """Disconnect from the server"""
        if self.socket:
            self.socket.close()
            print(f"{Fore.YELLOW}{self.client_id} ({self.fake_ip}) Disconnected from server{Style.RESET_ALL}")
    
    def send_query(self, query):
        """Send a query to the server with a header containing the fake IP"""
        if not self.socket:
            print(f"{Fore.RED}{self.client_id} ({self.fake_ip}) Not connected to server{Style.RESET_ALL}")
            return None
        
        try:
            # Prepare the query with a header
            full_query = f"X-Client-IP: {self.fake_ip}\r\n\r\n{query}"
            
            # Send the query
            print(f"{Fore.YELLOW}{self.client_id} ({self.fake_ip}) Sending: {query}{Style.RESET_ALL}")
            self.socket.send(full_query.encode())
            
            # Wait for response with timeout
            self.socket.settimeout(10.0)  # 10 second timeout
            
            # Receive response data
            chunks = []
            while True:
                try:
                    chunk = self.socket.recv(4096)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    
                    # If we have a small chunk, we might be done
                    if len(chunk) < 4096:
                        # Try to get more data, but with a short timeout
                        self.socket.settimeout(0.5)
                        continue
                except socket.timeout:
                    # No more data
                    break
            
            self.socket.settimeout(None)  # Reset timeout
            
            if not chunks:
                print(f"{Fore.RED}{self.client_id} ({self.fake_ip}) No data received{Style.RESET_ALL}")
                return None
            
            # Combine all chunks
            response = b''.join(chunks)
            
            # Process the response
            try:
                # Try to decode as UTF-8
                return response.decode('utf-8')
            except UnicodeDecodeError:
                # If it's binary data (e.g., from PostgreSQL)
                return f"Binary response received ({len(response)} bytes)"
            
        except socket.timeout:
            print(f"{Fore.RED}{self.client_id} ({self.fake_ip}) Timeout waiting for response{Style.RESET_ALL}")
            return None
        except Exception as e:
            print(f"{Fore.RED}{self.client_id} ({self.fake_ip}) Error sending query: {str(e)}{Style.RESET_ALL}")
            # Only close the socket if there's an error
            if self.socket:
                self.socket.close()
                self.socket = None
            return None

def client_thread_function(host, port, client_id, query, count, delay, interval, continuous=False):
    """Function to run in each client thread"""
    client = DBClient(host, port, client_id)
    
    if not client.connect():
        return
    
    try:
        iteration = 0
        while continuous or iteration < count:
            iteration += 1
            # Send the query
            response = client.send_query(query)
            if not response and client.socket is None:
                # Try to reconnect if connection was lost
                if not client.connect():
                    print(f"{Fore.RED}{client.client_id} ({client.fake_ip}) Failed to reconnect. Thread exiting.{Style.RESET_ALL}")
                    break
            
            # Wait for the specified delay
            time.sleep(delay)
            
            # If we're in continuous mode, check if we need to wait for the interval
            if continuous and iteration % 10 == 0:  # Every 10 queries, wait for the interval
                time.sleep(interval)
    
    except KeyboardInterrupt:
        print(f"{Fore.YELLOW}Interrupted. Stopping client {client.client_id}{Style.RESET_ALL}")
    finally:
        client.disconnect()

def multi_client_attack(host, port, num_clients, query, count, delay, interval, continuous=False):
    """Launch multiple clients with different IDs"""
    print(f"{Fore.CYAN}=== Starting Multi-Client Attack ==={Style.RESET_ALL}")
    print(f"Launching {num_clients} clients with query: {query}")
    print(f"Each client will send {count} queries with {delay}s delay between queries")
    print(f"Client operation mode: {'Continuous' if continuous else f'{count} queries per client'}")
    
    threads = []
    try:
        for i in range(num_clients):
            client_id = f"Client-{i+1}"
            print(f"{Fore.GREEN}Launching {client_id}{Style.RESET_ALL}")
            
            # Create and start thread
            thread = threading.Thread(
                target=client_thread_function,
                args=(host, port, client_id, query, count, delay, interval, continuous)
            )
            thread.daemon = True  # Allow the program to exit even if threads are running
            thread.start()
            threads.append(thread)
            
            # Small delay between starting clients
            time.sleep(0.5)
        
        print(f"{Fore.CYAN}All clients launched. Press Ctrl+C to stop the attack.{Style.RESET_ALL}")
        
        # Wait until interrupted
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"{Fore.YELLOW}Attack interrupted by user. Shutting down...{Style.RESET_ALL}")
            
    except KeyboardInterrupt:
        print(f"{Fore.YELLOW}Attack interrupted by user during setup. Shutting down...{Style.RESET_ALL}")
        
    print(f"{Fore.CYAN}=== Attack Completed ==={Style.RESET_ALL}")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Database Client for Testing DDoS Protection')
    parser.add_argument('--host', default='localhost', help='Server host (default: localhost)')
    parser.add_argument('--port', type=int, default=8080, help='Server port (default: 8080)')
    parser.add_argument('--query', default='SELECT * FROM users;', help='Query to use for testing')
    parser.add_argument('--count', type=int, default=10, help='Number of queries per client')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between queries (seconds)')
    
    # Add new arguments for multi-client attack
    parser.add_argument('--attack', action='store_true', help='Run multi-client attack')
    parser.add_argument('--clients', type=int, default=3, help='Number of simultaneous clients')
    parser.add_argument('--interval', type=int, default=5, help='Seconds between query batches')
    parser.add_argument('--continuous', action='store_true', help='Run in continuous mode')
    
    args = parser.parse_args()
    
    if args.attack:
        multi_client_attack(
            args.host, 
            args.port,
            args.clients,
            args.query,
            args.count,
            args.delay,
            args.interval,
            args.continuous
        )
    else:
        # Single client mode
        client = DBClient(args.host, args.port)
        if not client.connect():
            sys.exit(1)
        
        try:
            # Just send the query once
            response = client.send_query(args.query)
            if response:
                print(f"{Fore.CYAN}=== Response ==={Style.RESET_ALL}")
                print(response)
        finally:
            client.disconnect()

if __name__ == "__main__":
    main()
