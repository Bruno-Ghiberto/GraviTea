# Gravitea ERP - Development Commands

## Running the Application

### With Docker (Recommended)
```bash
# Create shared network (one-time setup)
docker network create gravitea-shared

# Start core services (postgres, redis, web)
docker-compose up -d

# Start observability stack (prometheus, grafana, jaeger, loki)
docker-compose -f docker-compose.observability.yml up -d
```

### Local Development
```bash
# Activate virtual environment
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Unix

# Install dependencies
pip install -r requirements/development.txt

# Run migrations
python manage.py migrate

# Run development server
python manage.py runserver 0.0.0.0:8000
```

## Testing

### Run All Tests
```bash
pytest
```

### Run by Category (markers)
```bash
pytest -m unit                  # Fast unit tests
pytest -m integration           # Require database
pytest -m security              # Security tests
pytest -m performance           # N+1 detection, benchmarks
pytest -m property              # Hypothesis property-based
pytest -m docker                # Docker integration
pytest -m load                  # Locust load tests
pytest -m fuzz                  # API fuzzing (Schemathesis)
pytest -m observability         # Observability stack tests
pytest -m smoke                 # End-to-end smoke tests
```

### Coverage Report
```bash
pytest --cov=apps --cov-report=html:htmlcov
# Open htmlcov/index.html for coverage report
```

### Run Specific Test File
```bash
pytest tests/unit/test_rate_limiter.py -v
```

## Code Quality

### Formatting
```bash
black apps/ tests/              # Format Python code
isort apps/ tests/              # Sort imports
```

### Linting
```bash
flake8 apps/ tests/             # PEP8 linting
```

### Type Checking
```bash
mypy apps/                      # Static type analysis
```

### All Quality Checks
```bash
black apps/ tests/ && isort apps/ tests/ && flake8 apps/ tests/ && mypy apps/
```

## Django Management

### Database
```bash
python manage.py migrate                    # Apply migrations
python manage.py makemigrations            # Create migrations
python manage.py showmigrations            # List migrations
python manage.py dbshell                   # PostgreSQL shell
```

### Shell & Utils
```bash
python manage.py shell_plus               # Enhanced interactive shell
python manage.py createsuperuser          # Create admin user
```

### API Schema
```bash
python manage.py spectacular --file openapi-generated.yaml
```

## Docker Commands

### View Logs
```bash
docker-compose logs -f web       # Web service logs
docker-compose logs -f postgres  # Database logs
```

### Database Access
```bash
docker exec -it gravitea-postgres psql -U gravitea -d gravitea_dev
```

### Restart Services
```bash
docker-compose restart web
```

## Windows System Commands
```bash
# File listing
dir                             # List directory (cmd)
Get-ChildItem                   # List directory (PowerShell)

# Process management  
tasklist                        # List processes
taskkill /f /im python.exe     # Kill process

# Network
netstat -an | findstr :8000    # Check port usage
```

## Git Workflow
```bash
git status                      # Check current state
git branch                      # List branches
git checkout -b feature/xxx     # Create feature branch
git add .                       # Stage changes
git commit -m "description"     # Commit
git push -u origin branch-name  # Push branch
```
