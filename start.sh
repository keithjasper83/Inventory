#!/bin/bash
set -e

echo "Starting Jules Inventory Platform..."

# Load environment
if [ -f .env ]; then
    echo "Loading environment from .env..."
    export $(grep -v '^#' .env | xargs)
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Check required services
echo "Checking service availability..."

# Check PostgreSQL
if ! python3 -c "from sqlalchemy import create_engine; import os, sys; url = os.environ.get('DATABASE_URL'); engine = create_engine(url); conn = engine.connect(); conn.close()" 2>/dev/null; then
    echo "⚠ WARNING: PostgreSQL not available at $DATABASE_URL"
    echo "  The application will fail to start without database connectivity."
    echo "  Please ensure PostgreSQL is running and DATABASE_URL is correct."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check Redis
if ! python3 -c "import redis; redis.from_url('$REDIS_URL', socket_connect_timeout=3).ping()" 2>/dev/null; then
    echo "⚠ WARNING: Redis not available at $REDIS_URL"
    echo "  Background jobs will not work without Redis."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Start RQ worker in background
echo "Starting background worker..."
python3 -m src.worker &
WORKER_PID=$!
echo "Worker started with PID $WORKER_PID"

# Start FastAPI application
echo "Starting FastAPI application..."
echo "Access the application at: http://localhost:8000"
echo "Press Ctrl+C to stop"

# Trap Ctrl+C to gracefully shutdown
trap "echo 'Shutting down...'; kill $WORKER_PID 2>/dev/null; exit 0" INT TERM

# Determine whether to enable auto-reload (development only)
RELOAD_FLAG=""
if [ "${ENVIRONMENT}" = "development" ]; then
    RELOAD_FLAG="--reload"
fi

# Start uvicorn
uvicorn src.main:app --host 0.0.0.0 --port 8000 $RELOAD_FLAG
