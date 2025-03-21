ddos-db-protection/
├── README.md                        # Project documentation and overview
├── src/                             # Source code
│   ├── monitor/                     # Query monitoring server
│   │   ├── __init__.py
│   │   ├── server.py                # Main server implementation
│   │   ├── query_analyzer.py        # Query parsing and analysis
│   │   ├── rate_limiter.py          # Rate limiting implementation
│   │   └── db_connector.py          # Database connection handler
│   ├── detection/                   # Anomaly detection logic
│   │   ├── __init__.py
│   │   ├── baseline.py              # Baseline traffic analysis
│   │   ├── anomaly.py               # Anomaly detection algorithms
│   │   └── patterns.py              # Attack pattern definitions
│   └── alerts/                      # Alerting system
│       ├── __init__.py
│       ├── notifier.py              # Notification logic
│       └── reporters.py             # Report generation
├── config/                          # Configuration files
│   ├── server.yml                   # Server configuration
│   ├── detection.yml                # Detection thresholds and settings
│   ├── alerts.yml                   # Alert configuration
│   └── dbms/                        # DBMS-level configurations
│       ├── postgresql/              # PostgreSQL specific configurations
│       │   ├── postgresql.conf      # Main configuration with security settings
│       │   ├── pg_hba.conf          # Client authentication configuration
│       │   └── resource_governor.sql # Resource limit triggers
│       ├── mysql/                   # MySQL specific configurations
│       │   ├── my.cnf               # Main configuration file
│       │   └── connection_control.sql # Connection control plugin setup
│       └── sqlserver/               # SQL Server specific configurations
│           └── resource_governor.sql # Resource Governor configuration
├── dbms_scripts/                    # DBMS-level protection scripts
│   ├── postgresql/
│   │   ├── connection_limiter.sql   # Connection limiting trigger
│   │   ├── query_monitor.sql        # Query monitoring function
│   │   └── blacklist_trigger.sql    # IP blacklisting trigger
│   ├── mysql/
│   │   ├── connection_limiter.sql   # Connection limiting procedure
│   │   └── blacklist_procedure.sql  # IP blacklisting procedure
│   └── sqlserver/
│       ├── resource_pool_setup.sql  # Resource pools for workload management
│       └── classification_function.sql # Workload classification function
├── logs/                            # Log storage
│   ├── queries.log                  # Query logs
│   ├── alerts.log                   # Alert logs
│   └── system.log                   # System logs
├── tests/                           # Testing framework
│   ├── __init__.py
│   ├── test_server.py               # Server tests
│   ├── test_detection.py            # Detection algorithm tests
│   ├── test_dbms_protection.py      # Tests for DBMS-level protections
│   ├── simulate_traffic.py          # Normal traffic simulator
│   └── simulate_attack.py           # Attack traffic simulator
├── dashboard/                       # Optional web dashboard
│   ├── app.py                       # Dashboard application
│   ├── templates/                   # Frontend templates
│   └── static/                      # Static assets
├── docs/                            # Documentation
│   ├── architecture.md              # System design
│   ├── api.md                       # API documentation
│   ├── setup.md                     # Setup instructions
│   └── dbms_protection.md           # Documentation of DBMS-level protections
├── requirements.txt                 # Python dependencies
└── main.py                          # Application entry point
