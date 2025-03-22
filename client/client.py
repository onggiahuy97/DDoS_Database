import socket
import sys
import time
import argparse
from colorama import Fore, Style, init

# Initialize colorama for cross-platform colored terminal output
init()

class DBClient:
    def __init__(self, host='localhost', port=8080):
        self.host = host
        self.port = port
        self.socket = None
    
    def connect(self):
        """Connect to the monitoring server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print(f"{Fore.GREEN}Connected to server at {self.host}:{self.port}{Style.RESET_ALL}")
            return True
        except ConnectionRefusedError:
            print(f"{Fore.RED}Error: Connection refused. Is the server running?{Style.RESET_ALL}")
            return False
        except Exception as e:
            print(f"{Fore.RED}Error connecting: {str(e)}{Style.RESET_ALL}")
            return False
    
    def disconnect(self):
        """Disconnect from the server"""
        if self.socket:
            self.socket.close()
            print(f"{Fore.YELLOW}Disconnected from server{Style.RESET_ALL}")
    
    def send_query(self, query):
        """Send a query to the server"""
        if not self.socket:
            print(f"{Fore.RED}Not connected to server{Style.RESET_ALL}")
            return None
        
        try:
            # Send the query
            print(f"{Fore.YELLOW}Sending: {query}{Style.RESET_ALL}")
            self.socket.send(query.encode())
            
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
                print(f"{Fore.RED}No data received{Style.RESET_ALL}")
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
            print(f"{Fore.RED}Timeout waiting for response{Style.RESET_ALL}")
            return None
        except Exception as e:
            print(f"{Fore.RED}Error sending query: {str(e)}{Style.RESET_ALL}")
            # Only close the socket if there's an error
            if self.socket:
                self.socket.close()
                self.socket = None
            return None
    
    def stress_test(self, query, count, delay=0.1):
        """Send multiple queries in rapid succession for stress testing"""
        print(f"{Fore.YELLOW}Starting stress test with {count} queries (delay: {delay}s){Style.RESET_ALL}")
        
        success_count = 0
        start_time = time.time()
        
        for i in range(count):
            sys.stdout.write(f"\rSending query {i+1}/{count}...")
            sys.stdout.flush()
            
            response = self.send_query(query)
            if response:
                success_count += 1
            
            # If the socket was closed due to an error, try to reconnect
            if self.socket is None:
                print(f"\n{Fore.YELLOW}Connection lost, attempting to reconnect...{Style.RESET_ALL}")
                if not self.connect():
                    print(f"{Fore.RED}Failed to reconnect. Aborting stress test.{Style.RESET_ALL}")
                    break
            
            # Add delay between queries
            if i < count - 1:  # Skip delay after the last query
                time.sleep(delay)
        
        duration = time.time() - start_time
        queries_per_sec = count / duration if duration > 0 else 0
        
        print(f"\n{Fore.GREEN}Stress test completed:{Style.RESET_ALL}")
        print(f"  Successful queries: {success_count}/{count}")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Rate: {queries_per_sec:.2f} queries/second")

def interactive_mode(client):
    """Interactive mode where user can type queries"""
    print(f"{Fore.CYAN}=== Interactive Mode ==={Style.RESET_ALL}")
    print("Type your SQL queries (type 'exit' to quit, 'stress' for stress test):")
    
    while True:
        print(f"{Fore.GREEN}SQL> {Style.RESET_ALL}", end='')
        user_input = input().strip()
        
        if user_input.lower() == 'exit':
            break
        elif user_input.lower() == 'stress':
            # Prompt for stress test parameters
            test_query = input("Enter query to use for stress test: ")
            try:
                count = int(input("Number of queries to send: "))
                delay = float(input("Delay between queries (seconds): "))
                client.stress_test(test_query, count, delay)
            except ValueError:
                print(f"{Fore.RED}Invalid number format{Style.RESET_ALL}")
        elif user_input:
            # Send the query
            print(f"{Fore.YELLOW}Sending query...{Style.RESET_ALL}")
            response = client.send_query(user_input)
            
            if response:
                print(f"{Fore.CYAN}=== Response ==={Style.RESET_ALL}")
                print(response)
            
            # Check if we need to reconnect
            if client.socket is None:
                print(f"{Fore.YELLOW}Connection lost, attempting to reconnect...{Style.RESET_ALL}")
                if not client.connect():
                    print(f"{Fore.RED}Failed to reconnect. Exiting interactive mode.{Style.RESET_ALL}")
                    break

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Database Client for Testing DDoS Protection')
    parser.add_argument('--host', default='localhost', help='Server host (default: localhost)')
    parser.add_argument('--port', type=int, default=8080, help='Server port (default: 8080)')
    parser.add_argument('--stress', action='store_true', help='Run stress test immediately')
    parser.add_argument('--query', help='Query to use for stress test')
    parser.add_argument('--count', type=int, default=100, help='Number of queries for stress test')
    parser.add_argument('--delay', type=float, default=0.1, help='Delay between queries (seconds)')
    
    args = parser.parse_args()
    
    # Create client and connect
    client = DBClient(args.host, args.port)
    if not client.connect():
        sys.exit(1)
    
    try:
        if args.stress and args.query:
            # Run stress test with provided parameters
            client.stress_test(args.query, args.count, args.delay)
        else:
            # Start interactive mode
            interactive_mode(client)
    finally:
        client.disconnect()

if __name__ == "__main__":
    main()
