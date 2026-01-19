#!/bin/bash
set -e

echo "Installing Jules Inventory Platform..."

# 1. Environment Setup
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt || pip install .

# 2. Config
if [ ! -f "config/ai_host.env" ]; then
    echo "Creating config/ai_host.env from example..."
    cp config/ai_host.env.example config/ai_host.env
fi

# 3. Database & Migrations
echo "Running migrations..."
alembic upgrade head

# 4. Storage
echo "Initializing storage..."
export PYTHONPATH=$PYTHONPATH:.
python scripts/init_storage.py

# 5. Seed Data
echo "Seeding data..."
python scripts/seed_data.py

echo "Installation complete."
echo "Run './start.sh' to start the application."
