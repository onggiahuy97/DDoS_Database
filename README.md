# PostgreSQL DDoS Protection System

A sophisticated, multi-layered protection system for PostgreSQL databases that detects and prevents DDoS attacks through query analysis, resource monitoring, and adaptive controls.

## Overview

This system provides comprehensive protection for PostgreSQL databases against denial-of-service attacks through a combination of query analysis, resource monitoring, and dynamic controls. Unlike simple connection limiters, our solution analyzes query patterns, estimates execution costs, builds client risk profiles, and applies adaptive resource limits to ensure database availability even under attack.

## Key Features

### Query Analysis (Phase 1)
- **EXPLAIN-based Cost Estimation**: Pre-execution analysis of query cost
- **Query Pattern Normalization**: Detection of similar malicious query patterns 
- **Risk Scoring Algorithm**: Multi-factor risk assessment of each query

### Resource Controls (Phase 2)
- **Real-time Performance Monitoring**: Integration with pg_stat_statements
- **Dynamic Query Timeouts**: Adaptive timeouts based on client risk and system load
- **Client Risk Profiles**: Historical tracking of client behavior patterns

### Protection Mechanisms
- **Automatic IP Blocking**: Temporary blocks for suspicious behavior
- **Query Rejection**: Prevention of high-risk or resource-intensive queries
- **Connection Rate Limiting**: Protection against connection floods

### Administration
- **Comprehensive Admin Dashboard**: Monitor active connections, blocked IPs, and query statistics
- **Client Profile Management**: Review and adjust individual client risk profiles
- **Database Load Monitoring**: Track performance metrics and load history

## Technical Architecture

![Architecture Diagram](https://example.com/architecture.png)

The system consists of several key components:

1. **Middleware Layer**: Flask-based API middleware that intercepts and processes requests
2. **Query Analysis Engine**: Pre-execution analysis of SQL queries for cost and risk
3. **Resource Monitoring Service**: Real-time tracking of database performance metrics
4. **Client Profile Manager**: Maintains and updates risk profiles for each client
5. **Admin Dashboard**: Web interface for monitoring and configuration

## Installation

### Prerequisites

- Python 3.7+
- PostgreSQL 10+ with pg_stat_statements extension
- pip

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/username/postgresql-ddos-protection.git
   cd postgresql-ddos-protection
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your database settings in `config.py` or use environment variables:
   ```bash
   export DB_NAME=your_database
   export DB_USER=postgres
   export DB_PASSWORD=your_password
   export DB_HOST=localhost
   ```

4. Enable the pg_stat_statements extension in PostgreSQL:
   ```bash
   psql -U postgres -d your_database -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"
   ```

5. Start the application:
   ```bash
   python run.py
   ```

## Configuration

| Parameter | Environment Variable | Default | Description |
|-----------|---------------------|---------|-------------|
| Database Name | `DB_NAME` | testdb | PostgreSQL database name |
| Database User | `DB_USER` | huyong97 | Database username |
| Database Password | `DB_PASSWORD` | password | Database password |
| Database Host | `DB_HOST` | localhost | Database server hostname |
| Database Port | `DB_PORT` | 5432 | Database server port |
| Connection Limit | `MAX_CONNECTION_PER_MINUTE` | 10 | Maximum connections allowed per minute |
| Statement Timeout | `DEFAULT_STATEMENT_TIMEOUT` | 5000 | Default query timeout (ms) |
| Min Timeout | `MIN_STATEMENT_TIMEOUT` | 500 | Minimum query timeout (ms) |
| Max Connections | `MAX_CONNECTIONS` | 100 | Maximum database connections |
| Query Volume Threshold | `QUERY_VOLUME_THRESHOLD` | 100 | Queries per hour threshold |
| Block Duration | `BLOCK_DURATION_MINUTES` | 5 | Minutes to block suspicious IPs |
| API Port | `API_PORT` | 5002 | Port for the Flask API server |
| Debug Mode | `DEBUG_MODE` | False | Enable Flask debug mode |

## Manual Testing and Demonstration

### Step 1: Start the Application and Verify Setup

Start the application and ensure all tables are created:

```bash
# Start the application
python run.py

# Verify database tables (in another terminal)
psql -U your_username -d your_database -c "\dt"

# Verify pg_stat_statements extension
psql -U your_username -d your_database -c "SELECT * FROM pg_extension WHERE extname = 'pg_stat_statements';"
```

### Step 2: Basic Query Testing

Test the basic endpoints to ensure everything is working:

```bash
# Get all customers
curl http://localhost:5002/customers

# Run a simple query
curl -X POST http://localhost:5002/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM customers LIMIT 5"}'
```

### Step 3: Testing Query Analysis

Run queries with different complexity levels to see risk scoring in action:

```bash
# Simple, low-risk query
curl -X POST http://localhost:5002/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM customers WHERE id = 1"}'

# Medium-risk query with JOIN
curl -X POST http://localhost:5002/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT c.*, o.* FROM customers c JOIN orders o ON c.id = o.customer_id"}'

# High-risk query with multiple joins
curl -X POST http://localhost:5002/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM customers c1, customers c2, customers c3 WHERE c1.name LIKE '%a%'"}'
```

Check the query stats in admin dashboard:

```bash
curl http://localhost:5002/admin/query-stats
```

### Step 4: Testing Resource Controls

Check your client's risk profile and database load:

```bash
# View database load statistics
curl http://localhost:5002/admin/resource-stats

# Check your client profile
curl http://localhost:5002/admin/client-profile/127.0.0.1
```

Test dynamic timeouts by running slow queries before and after modifying your timeout multiplier:

```bash
# Run a slow query
curl -X POST http://localhost:5002/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT pg_sleep(2), * FROM customers"}'

# Modify your profile for stricter timeouts
curl -X PUT http://localhost:5002/admin/client-profile/127.0.0.1 \
  -H "Content-Type: application/json" \
  -d '{"timeout_multiplier": 0.2, "notes": "Testing reduced timeout"}'

# Run the same slow query again (should timeout faster)
curl -X POST http://localhost:5002/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT pg_sleep(2), * FROM customers"}'
```

### Step 5: Simulating Attack Conditions

Simulate high traffic by running many queries in rapid succession:

```bash
# Run many queries quickly
for i in {1..20}; do 
  curl -X POST http://localhost:5002/query \
    -H "Content-Type: application/json" \
    -d '{"query": "SELECT * FROM customers WHERE id = '$i'"}'; 
  sleep 0.2; 
done

# Check if connection limits are working
for i in {1..30}; do 
  curl http://localhost:5002/customers &
  sleep 0.1; 
done
```

Test if suspicious queries are rejected:

```bash
curl -X POST http://localhost:5002/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM customers c1 CROSS JOIN customers c2 CROSS JOIN customers c3"}'
```

### Step 6: Admin Dashboard Exploration

Review protection statistics:

```bash
# View DDoS protection statistics
curl http://localhost:5002/admin/stats

# View query statistics
curl http://localhost:5002/admin/query-stats

# View resource statistics and client profiles
curl http://localhost:5002/admin/resource-stats
```

## Implementation Details

### Phase 1: Query Analysis

The query analysis system provides pre-execution protection by:

1. **EXPLAIN Analysis**: Using PostgreSQL's EXPLAIN to estimate query cost without execution
2. **Query Normalization**: Converting queries to a standardized form to identify patterns
3. **Risk Scoring**: Evaluating queries based on:
   - Estimated execution cost
   - Presence of risky patterns (JOINs, wildcards, etc.)
   - Complexity indicators

Key files:
- `app/services/query_analysis.py`: Core query analysis functions
- `app/models/security.py`: Database schema for tracking query metrics

### Phase 2: Resource Controls

The resource control system provides execution-time protection by:

1. **Performance Monitoring**: Tracking database metrics via pg_stat_statements
2. **Client Risk Profiles**: Building behavioral profiles for each client
3. **Dynamic Timeouts**: Adjusting statement timeouts based on:
   - Client risk level
   - Current database load
   - Query complexity

Key files:
- `app/services/resource_monitor.py`: Database monitoring and client profiling
- `app/models/client_profiles.py`: Schema for risk profiles and load history
- `app/api/middleware.py`: Request handling and timeout enforcement

## API Documentation

### Public Endpoints

#### `GET /customers`
Returns the list of customers from the database.

**Response:**
```json
{
  "customers": [
    {"id": 1, "name": "John Doe", "email": "john@example.com", "signup_date": "2023-01-01T12:00:00Z"},
    ...
  ]
}
```

#### `POST /query`
Executes a custom SQL query with protection checks.

**Request Body:**
```json
{
  "query": "SELECT * FROM customers WHERE name LIKE 'J%'"
}
```

**Response:**
```json
{
  "results": [
    {"id": 1, "name": "John Doe", "email": "john@example.com"}
  ]
}
```

### Admin Endpoints

#### `GET /admin/stats`
Returns DDoS protection statistics.

#### `GET /admin/query-stats`
Returns query cost and risk statistics.

#### `GET /admin/resource-stats`
Returns database resource usage statistics.

#### `GET /admin/client-profile/<ip_address>`
Returns detailed risk profile for a specific client.

#### `PUT /admin/client-profile/<ip_address>`
Updates a client's risk profile.

## Future Enhancements

The current implementation includes Phase 1 (Query Analysis) and Phase 2 (Resource Controls). Future phases could include:

1. **Query Queuing**: Priority-based query processing during high load
2. **Advanced Pattern Detection**: ML-based identification of attack patterns
3. **Performance Optimization**: Additional indexes and cleanup routines

## Performance Considerations

The protection system adds minimal overhead to normal database operations:

- Query analysis typically adds <5ms to query processing
- Resource monitoring uses efficient PostgreSQL extensions
- Client profiles are cached to reduce lookup times
- Adaptive timeouts prevent resource exhaustion

## Contributing

Contributions are welcome! Please feel free to submit pull requests.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
