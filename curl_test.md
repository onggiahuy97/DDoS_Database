# PostgreSQL DDoS Protection System - Manual Testing Guide

This guide demonstrates how to manually test the PostgreSQL DDoS Protection System using `curl` commands. It covers testing basic functionality, protection mechanisms, query analysis, and administration features.

## Prerequisites

Before starting:
1. Ensure PostgreSQL is running
2. Start the application with `python run.py`
3. Have `curl` installed on your system
4. Open a terminal window

## 1. Basic Functionality Testing

First, let's verify that the basic API endpoints work correctly.

### 1.1 Testing the Customers Endpoint

```bash
# Get all customers
curl http://localhost:5002/customers
```

Expected response: A JSON object with customer data or an empty array if no customers exist.

### 1.2 Testing Basic Query Execution

```bash
# Execute a simple SELECT query
curl -X POST http://localhost:5002/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM customers LIMIT 5"}'
```

Let's try a simple INSERT (if your database allows it):

```bash
# Insert a test customer
curl -X POST http://localhost:5002/query \
  -H "Content-Type: application/json" \
  -d '{"query": "INSERT INTO customers (name, email) VALUES ('"'"'Test User'"'"', '"'"'test@example.com'"'"') RETURNING *"}'
```

## 2. Testing Query Analysis and Risk Detection

The system analyzes queries for potential risks. Let's test queries with different risk levels.

### 2.1 Low-Risk Query

```bash
# Simple, specific query with a direct primary key lookup
curl -X POST http://localhost:5002/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM customers WHERE id = 1"}'
```

### 2.2 Medium-Risk Query

```bash
# Query with a JOIN operation
curl -X POST http://localhost:5002/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT c.*, o.* FROM customers c JOIN orders o ON c.id = o.customer_id LIMIT 10"}'
```

### 2.3 High-Risk Query

```bash
# Expensive query with multiple joins and LIKE patterns
curl -X POST http://localhost:5002/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM customers c1, customers c2 WHERE c1.name LIKE '"'"'%a%'"'"' AND c2.name LIKE '"'"'%b%'"'"'"}'
```

### 2.4 Potentially Dangerous Query

```bash
# Query that should be rejected due to high risk
curl -X POST http://localhost:5002/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT c1.*, c2.*, c3.* FROM customers c1 CROSS JOIN customers c2 CROSS JOIN customers c3 LIMIT 100"}'
```

## 3. Testing Connection Rate Limiting

The system blocks IPs that make too many connections per minute. Let's simulate this.

```bash
# Run this loop to simulate connection flooding
for i in {1..15}; do 
  echo "Request $i"
  curl http://localhost:5002/customers &
  sleep 0.2
done
```

After enough requests, you should get a response like:
```
{"error":"Your IP has been temporarily blocked due to too many requests."}
```

## 4. Testing Admin Features

The system provides admin endpoints to monitor database activity and manage protection.

### 4.1 Protection Statistics

```bash
# View current DDoS protection stats
curl http://localhost:5002/admin/stats
```

Expected response: JSON with most active IPs and any blocked IPs.

### 4.2 Query Statistics

```bash
# View statistics about query costs and risks
curl http://localhost:5002/admin/query-stats
```

Expected response: Information about high-cost and high-risk queries.

### 4.3 Resource Statistics

```bash
# View database resource statistics
curl http://localhost:5002/admin/resource-stats
```

Expected response: Current database load, load history, and high-risk clients.

### 4.4 Client Profile Management

```bash
# Get your own client profile (assuming 127.0.0.1 is your IP)
curl http://localhost:5002/admin/client-profile/127.0.0.1
```

Let's update the client profile:

```bash
# Manually update a client's risk profile
curl -X PUT http://localhost:5002/admin/client-profile/127.0.0.1 \
  -H "Content-Type: application/json" \
  -d '{"risk_score": 0.2, "timeout_multiplier": 0.8, "notes": "Test client with moderate restrictions"}'
```

## 5. Testing Dynamic Resource Controls

The system applies dynamic query timeouts based on client risk profiles and database load.

### 5.1 Testing with Default Timeout

```bash
# Run a query that sleeps for a short time
curl -X POST http://localhost:5002/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT pg_sleep(1), * FROM customers LIMIT 5"}'
```

### 5.2 Testing with Restricted Timeout

First, update your profile to have a very low timeout multiplier:

```bash
# Set a very restrictive timeout
curl -X PUT http://localhost:5002/admin/client-profile/127.0.0.1 \
  -H "Content-Type: application/json" \
  -d '{"timeout_multiplier": 0.1, "notes": "Testing with very low timeout"}'
```

Then try a longer query:

```bash
# This should timeout due to restrictive settings
curl -X POST http://localhost:5002/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT pg_sleep(2), * FROM customers"}'
```

### 5.3 Reset Client Profile

```bash
# Reset to normal values
curl -X PUT http://localhost:5002/admin/client-profile/127.0.0.1 \
  -H "Content-Type: application/json" \
  -d '{"risk_score": 0.0, "timeout_multiplier": 1.0, "notes": "Reset to default settings"}'
```

## 6. Testing Under High Load

Let's simulate a high-traffic situation by running many queries in rapid succession.

```bash
# Run many queries quickly
for i in {1..20}; do 
  curl -X POST http://localhost:5002/query \
    -H "Content-Type: application/json" \
    -d '{"query": "SELECT * FROM customers WHERE id = '$i' OR name LIKE '"'"'%Test%'"'"'"}' &
  sleep 0.3
done
```

Then check the load statistics:

```bash
curl http://localhost:5002/admin/resource-stats
```

## 7. Comprehensive End-to-End Test

This script simulates a complete scenario with normal usage, attempted attack, and monitoring.

```bash
#!/bin/bash

echo "STEP 1: Basic API testing"
curl http://localhost:5002/customers

echo -e "\n\nSTEP 2: Running a few normal queries"
curl -X POST http://localhost:5002/query -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM customers LIMIT 3"}'
sleep 1
curl -X POST http://localhost:5002/query -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM customers WHERE id = 1"}'

echo -e "\n\nSTEP 3: Checking initial client profile"
curl http://localhost:5002/admin/client-profile/127.0.0.1

echo -e "\n\nSTEP 4: Simulating moderate traffic"
for i in {1..10}; do
  curl -X POST http://localhost:5002/query -H "Content-Type: application/json" \
    -d '{"query": "SELECT * FROM customers WHERE id = '$i'"}' > /dev/null 2>&1
  sleep 0.2
done

echo -e "\n\nSTEP 5: Checking query statistics"
curl http://localhost:5002/admin/query-stats

echo -e "\n\nSTEP 6: Running a high-risk query"
curl -X POST http://localhost:5002/query -H "Content-Type: application/json" \
  -d '{"query": "SELECT c1.*, c2.* FROM customers c1, customers c2 WHERE c1.name LIKE '"'"'%a%'"'"'"}'

echo -e "\n\nSTEP 7: Checking protection statistics"
curl http://localhost:5002/admin/stats

echo -e "\n\nSTEP 8: Checking updated client profile"
curl http://localhost:5002/admin/client-profile/127.0.0.1

echo -e "\n\nSTEP 9: Attempting connection flood"
for i in {1..15}; do
  curl http://localhost:5002/customers > /dev/null 2>&1 &
  sleep 0.1
done
sleep 2

echo -e "\n\nSTEP 10: Checking final protection status"
curl http://localhost:5002/admin/stats
curl http://localhost:5002/admin/resource-stats
```

Save this as `test_protection.sh`, make it executable with `chmod +x test_protection.sh`, and run it with `./test_protection.sh`.

## 8. Troubleshooting

If you encounter issues with the pg_stat_statements extension:

```bash
# Run the fix script
python fix.py
```

This script modifies the resource monitor to work without requiring the pg_stat_statements extension.

## Next Steps

After testing, you might want to:

1. Tune configuration parameters in `config.py` based on test results
2. Experiment with different query patterns to identify false positives
3. Test under specific load conditions that match your production environment
4. Monitor database performance metrics during testing to assess overhead

This simulation covers the key features of the PostgreSQL DDoS Protection System and demonstrates its ability to detect and prevent various types of attack scenarios.
