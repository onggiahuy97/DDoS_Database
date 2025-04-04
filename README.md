# PostgreSQL DDoS Protection

A lightweight, modular middleware solution for detecting and preventing DDoS attacks on PostgreSQL databases.

## Features

- **Real-time Attack Detection**: Monitors connection frequency and query patterns
- **Automated IP Blocking**: Temporarily blocks suspicious IP addresses
- **Rate Limiting**: Prevents excessive database connections
- **Admin Dashboard**: Monitor active connections and blocked IPs
- **Configurable Thresholds**: Customize security parameters
- **Middleware Architecture**: Easy integration with existing Flask applications

## Installation

### Prerequisites

- Python 3.7+
- PostgreSQL 10+
- pip

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/onggiahuy97/DDoS_Database.git
   cd DDoS_Database
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables or update `config.py`:
   ```bash
   export DB_NAME=your_database
   export DB_USER=postgres
   export DB_PASSWORD=your_password
   export DB_HOST=localhost
   export MAX_CONNECTIONS_PER_MINUTE=10
   ```

4. Run database setup:
   ```bash
   python -c "from app.database.db import setup_database; setup_database()"
   ```

5. Start the application:
   ```bash
   python run.py
   ```

## Configuration

| Parameter | Environment Variable | Default | Description |
|-----------|---------------------|---------|-------------|
| Database Name | `DB_NAME` | postgres | PostgreSQL database name |
| Database User | `DB_USER` | postgres | Database username |
| Database Password | `DB_PASSWORD` | password | Database password |
| Database Host | `DB_HOST` | localhost | Database server hostname |
| Database Port | `DB_PORT` | 5432 | Database server port |
| Connection Limit | `MAX_CONNECTIONS_PER_MINUTE` | 10 | Maximum connections allowed per minute from single IP |
| Query Limit | `MAX_QUERIES_PER_MINUTE` | 10 | Maximum queries allowed per minute from single IP |
| Block Duration | `BLOCK_DURATION_MINUTES` | 5 | Duration in minutes to block suspicious IPs |
| API Port | `API_PORT` | 5000 | Port for the Flask API server |
| Debug Mode | `DEBUG_MODE` | False | Enable Flask debug mode |

## Usage

### Basic Endpoint Access

The middleware automatically protects all registered endpoints:

```bash
# Access the customers endpoint
curl http://localhost:5000/customers

# Execute a custom query
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM customers LIMIT 5"}'
```

### Admin Dashboard

Monitor protection statistics:

```bash
# View active connections and blocked IPs
curl http://localhost:5000/admin/stats
```

### Integration with Existing Flask Applications

```python
from app.api.middleware import ddos_protection_middleware

@app.route('/your-endpoint')
@ddos_protection_middleware
def your_function():
    # Your code here
    return response
```

## API Documentation

### Public Endpoints

#### `GET /customers`
Returns the list of customers from the database.

**Parameters:**
- `username` (optional): Identifier for the requesting user

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
Executes a custom SQL query.

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

**Response:**
```json
{
  "most_active_ips": [
    {"ip": "192.168.1.1", "count": 150}
  ],
  "blocked_ips": [
    {"ip": "192.168.1.2", "blocked_at": "2023-04-01T14:30:00Z", "expires": "2023-04-01T14:40:00Z", "reason": "Too many connections: 120/min"}
  ]
}
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test category
pytest tests/test_protection.py
```

### Testing DDoS Protection

We provide a script to simulate attack traffic:

```bash
python scripts/simulate_ddos.py
```

## Project Structure

```
ddos_protection/
├── README.md
├── requirements.txt
├── config.py                   # Configuration settings
├── run.py                      # Application entry point
└── app/
    ├── __init__.py             # Application factory
    ├── models/                 # Database models
    ├── services/               # Business logic
    ├── database/               # Database operations
    └── api/                    # Web endpoints
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Extending the System

### Adding New Protection Rules

1. Add methods to `app/services/protection.py`
2. Update middleware in `app/api/middleware.py`

### Creating New Endpoints

Add route functions to existing blueprints or create new ones.

### Enhanced Analytics

Implement advanced analytics by extending the stats functionality in `app/services/protection.py`.

## License

This project is licensed under the MIT License - see the LICENSE file for details. DDoS Protection

