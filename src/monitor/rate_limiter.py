# src/monitor/rate_limiter.py
import time
import logging
from collections import defaultdict

logger = logging.getLogger('rate_limiter')

class RateLimiter:
    def __init__(self, config_path='config/detection.yml'):
        import yaml
        
        # Load configuration
        with open(config_path, 'r') as config_file:
            config = yaml.safe_load(config_file)
        
        self.window_size = config['detection']['window_size']  # seconds
        self.query_threshold = config['detection']['threshold']['queries_per_minute']
        self.failed_query_threshold = config['detection']['threshold']['failed_queries_per_minute']
        
        # Data structures for tracking
        self.query_counts = defaultdict(list)  # IP -> [(timestamp, count)]
        self.failed_query_counts = defaultdict(list)  # IP -> [(timestamp, count)]
        self.blacklist = set()  # Set of blacklisted IPs
        
        logger.info("Rate limiter initialized")
    
    def check_rate_limit(self, client_ip, query_info=None):
        """Check if the client has exceeded rate limits"""
        # Skip check for blacklisted IPs
        if client_ip in self.blacklist:
            logger.warning(f"Blocked request from blacklisted IP: {client_ip}")
            return False
        
        now = time.time()
        
        # Clean old entries
        self._clean_old_entries(client_ip, now)
        
        # Add current query
        self.query_counts[client_ip].append((now, 1))
        
        # Count queries in current window
        total_queries = sum(count for ts, count in self.query_counts[client_ip])
        
        # Normalize to per-minute rate for comparison with threshold
        current_window_size = min(self.window_size, now - min([ts for ts, _ in self.query_counts[client_ip]] or [now]))
        queries_per_minute = (total_queries / current_window_size) * 60
        
        # Log for monitoring
        logger.debug(f"Client {client_ip}: {queries_per_minute:.2f} queries/min (threshold: {self.query_threshold})")
        
        # Check if rate exceeds threshold
        if queries_per_minute > self.query_threshold:
            logger.warning(f"Rate limit exceeded for {client_ip}: {queries_per_minute:.2f} queries/min")
            return False
        
        return True
    
    def _clean_old_entries(self, client_ip, current_time):
        """Remove entries older than the window size"""
        if client_ip in self.query_counts:
            self.query_counts[client_ip] = [
                (ts, count) for ts, count in self.query_counts[client_ip]
                if current_time - ts < self.window_size
            ]
        
        if client_ip in self.failed_query_counts:
            self.failed_query_counts[client_ip] = [
                (ts, count) for ts, count in self.failed_query_counts[client_ip]
                if current_time - ts < self.window_size
            ]
    
    def add_to_blacklist(self, client_ip, reason="Rate limit exceeded"):
        """Add an IP to the blacklist"""
        self.blacklist.add(client_ip)
        logger.warning(f"Added {client_ip} to blacklist: {reason}")
        
        # In a real implementation, you might persist this to a database
        with open('logs/blacklist.log', 'a') as f:
            f.write(f"{time.time()},{client_ip},{reason}\n")
    
    def record_failed_query(self, client_ip):
        """Record a failed query from the client"""
        now = time.time()
        
        # Clean old entries
        self._clean_old_entries(client_ip, now)
        
        # Add failed query
        self.failed_query_counts[client_ip].append((now, 1))
        
        # Check if failed queries exceed threshold
        failed_count = sum(count for _, count in self.failed_query_counts[client_ip])
        current_window_size = min(self.window_size, now - min([ts for ts, _ in self.failed_query_counts[client_ip]] or [now]))
        failed_per_minute = (failed_count / current_window_size) * 60
        
        if failed_per_minute > self.failed_query_threshold:
            logger.warning(f"Failed query threshold exceeded for {client_ip}: {failed_per_minute:.2f}/min")
            self.add_to_blacklist(client_ip, "Excessive failed queries")
            return False
        
        return True

    def get_client_stats(self):
        """Return statistics about client query rates"""
        stats = {}
        now = time.time()
        
        for ip, queries in self.query_counts.items():
            # Clean old entries first
            valid_queries = [(ts, count) for ts, count in queries if now - ts < self.window_size]
            
            if valid_queries:
                total = sum(count for _, count in valid_queries)
                earliest_ts = min(ts for ts, _ in valid_queries)
                window = now - earliest_ts
                
                if window > 0:
                    rate = (total / window) * 60  # Queries per minute
                    stats[ip] = {
                        'count': total,
                        'rate': rate,
                        'is_blacklisted': ip in self.blacklist
                    }
        
        return stats

