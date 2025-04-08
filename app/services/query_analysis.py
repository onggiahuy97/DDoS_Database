# app/services/query_analysis.py
"""Service for analyzing SQL queries and detecting potentially harmful patterns."""
import re
import hashlib
from app.database.db import get_db_cursor
from app.models.security import QueryCostLog

def normalize_query(query):
    """
    Normalize a SQL query by replacing literals with placeholders.
    
    This helps identify similar query patterns regardless of specific values.
    """
    # Replace specific numeric literals with placeholders
    normalized = re.sub(r'\b\d+\b', ':num', query)
    
    # Replace string literals with placeholders
    normalized = re.sub(r"'[^']*'", ":str", normalized)
    
    # Replace multiple whitespace with a single space
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized

def generate_query_hash(normalized_query):
    """
    Generate a hash for a normalized query to uniquely identify query patterns.
    """
    return hashlib.md5(normalized_query.encode()).hexdigest()

def analyze_query_cost(query):
    """
    Analyze a query using PostgreSQL's EXPLAIN to estimate its cost.
    
    Returns:
        tuple: (estimated_cost, plan_json)
    """
    try:
        with get_db_cursor() as cursor:
            # Use EXPLAIN with JSON format to get detailed plan information
            cursor.execute(f"EXPLAIN (FORMAT JSON) {query}")
            plan = cursor.fetchone()[0]
            
            # Extract the estimated cost from the plan
            estimated_cost = extract_total_cost(plan)
            
            return estimated_cost, plan
    except Exception as e:
        # If EXPLAIN fails, return a high cost to indicate potential risk
        return 1000.0, {"error": str(e)}

def extract_total_cost(plan_json):
    """
    Extract the total cost from a PostgreSQL EXPLAIN plan in JSON format.
    """
    try:
        # Navigate the JSON structure to find the total cost
        plan_node = plan_json[0]['Plan']
        return float(plan_node.get('Total Cost', 1000.0))
    except (KeyError, IndexError, ValueError):
        # If we can't extract the cost, return a high value to be safe
        return 1000.0

def calculate_risk_score(query, estimated_cost, normalized_query):
    """
    Calculate a risk score for a query based on various factors.
    
    Factors considered:
    1. Estimated cost from EXPLAIN
    2. Presence of potentially harmful patterns
    3. Query complexity
    
    Returns:
        float: Risk score between 0.0 (safe) and 1.0 (high risk)
    """
    base_score = min(estimated_cost / 1000.0, 1.0)  # Normalize cost to 0-1 range
    
    # Check for potentially harmful patterns
    risk_patterns = [
        (r'\bDELETE\b', 0.3),              # DELETE operations
        (r'\bDROP\b', 0.4),                # DROP operations
        (r'\bTRUNCATE\b', 0.3),            # TRUNCATE operations
        (r'\bALTER\b', 0.2),               # ALTER operations
        (r'\bCREATE\b', 0.2),              # CREATE operations
        (r'\bUPDATE\b.*\bWHERE\b', 0.1),   # UPDATE with WHERE
        (r'\bSELECT\b.*\bFROM\b.*\bJOIN\b', 0.1),  # Joins can be expensive
        (r'\bSELECT\b.*\bFROM\b.*\bWHERE\b.*\bOR\b', 0.1),  # OR conditions
        (r'\bSELECT\b.*\bFROM\b.*\bWHERE\b.*\bLIKE\b', 0.1),  # LIKE operations
    ]
    
    pattern_score = 0.0
    for pattern, weight in risk_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            pattern_score += weight
    
    # Cap pattern score at 0.7
    pattern_score = min(pattern_score, 0.7)
    
    # Combine scores (60% cost, 40% pattern)
    final_score = (base_score * 0.6) + (pattern_score * 0.4)
    
    return min(final_score, 1.0)  # Ensure score is between 0 and 1

def log_query_analysis(ip_address, query):
    """
    Analyze a query and log its cost and risk information.
    
    Returns:
        tuple: (estimated_cost, risk_score)
    """
    # Normalize the query and generate a hash
    normalized_query = normalize_query(query)
    query_hash = generate_query_hash(normalized_query)
    
    # Analyze the query cost
    estimated_cost, _ = analyze_query_cost(query)
    
    # Calculate risk score
    risk_score = calculate_risk_score(query, estimated_cost, normalized_query)
    
    # Log the analysis results
    with get_db_cursor() as cursor:
        cursor.execute(
            QueryCostLog.insert_query(),
            (ip_address, query_hash, normalized_query, estimated_cost, risk_score)
        )
    
    return estimated_cost, risk_score

def is_query_suspicious(ip_address, query):
    """
    Determine if a query is suspicious based on its risk score and
    the recent query pattern history of the IP address.
    
    Returns:
        tuple: (is_suspicious, risk_score, reason)
    """
    # First, analyze the current query
    estimated_cost, risk_score = log_query_analysis(ip_address, query)
    
    # If the risk score is very high, immediately flag as suspicious
    if risk_score >= 0.9:
        return True, risk_score, f"High risk query (score: {risk_score:.2f})"
    
    # Check recent query pattern for this IP
    with get_db_cursor() as cursor:
        cursor.execute(
            QueryCostLog.get_recent_query_costs(ip_address), 
            (ip_address,)
        )
        result = cursor.fetchone()
        
        if result and result[0] is not None:
            avg_cost, avg_risk = result
            
            # If this query has significantly higher cost or risk than average
            if estimated_cost > avg_cost * 3 and estimated_cost > 100:
                return True, risk_score, f"Query cost ({estimated_cost:.2f}) significantly above average ({avg_cost:.2f})"
            
            if risk_score > avg_risk * 2 and risk_score > 0.7:
                return True, risk_score, f"Query risk ({risk_score:.2f}) significantly above average ({avg_risk:.2f})"
    
    # Not suspicious
    return False, risk_score, None
