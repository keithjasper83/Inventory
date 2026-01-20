#!/bin/bash
set -e

echo "================================================================"
echo "  Jules Inventory Platform - Quick Start with Docker"
echo "================================================================"
echo ""

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed"
    echo "Please install Docker from https://docs.docker.com/get-docker/"
    exit 1
fi

# Check for Docker Compose
if ! docker compose version &> /dev/null; then
    echo "ERROR: Docker Compose is not installed"
    echo "Please install Docker Compose from https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✓ Docker is installed"
echo "✓ Docker Compose is installed"
echo ""

# Check for curl
if ! command -v curl &> /dev/null; then
    echo "ERROR: curl is not installed"
    echo "Please install curl (required for health checks)"
    exit 1
fi

echo "✓ curl is installed"
echo ""

# Check for .env file
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.production .env
    
    echo ""
    echo "================================================================"
    echo "  IMPORTANT: Security Configuration Required"
    echo "================================================================"
    echo ""
    echo "Please set the following in .env file:"
    echo ""
    
    # Generate a secret key
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "")
    
    if [ -n "$SECRET_KEY" ]; then
        echo "1. SECRET_KEY (copy this generated value):"
        echo "   $SECRET_KEY"
        echo ""
        
        # Update .env with generated key
        if command -v sed &> /dev/null; then
            sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|" .env
            echo "   ✓ SECRET_KEY has been set automatically"
            echo ""
        fi
    else
        echo "1. SECRET_KEY (generate one with):"
        echo "   python3 -c \"import secrets; print(secrets.token_urlsafe(32))\""
        echo ""
    fi
    
    echo "2. ADMIN_PASSWORD (set a secure password, minimum 8 characters)"
    echo ""
    
    # Prompt for admin password
    read -p "Enter admin password: " -s ADMIN_PASSWORD
    echo ""
    
    if [ ${#ADMIN_PASSWORD} -lt 8 ]; then
        echo "ERROR: Password must be at least 8 characters"
        exit 1
    fi
    
    # Update .env with admin password
    if command -v sed &> /dev/null; then
        sed -i "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=$ADMIN_PASSWORD|" .env
        echo "✓ ADMIN_PASSWORD has been set"
    fi
    
    # Clear password from memory
    unset ADMIN_PASSWORD
    
    echo ""
    echo "3. S3/MinIO Storage Credentials (generating secure credentials)"
    echo ""
    
    # Generate MinIO credentials
    S3_ACCESS_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))" 2>/dev/null || echo "minio-$(date +%s)")
    S3_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "minio-secret-$(date +%s)")
    
    if [ -n "$S3_ACCESS_KEY" ] && [ -n "$S3_SECRET_KEY" ]; then
        if command -v sed &> /dev/null; then
            sed -i "s|^S3_ACCESS_KEY=.*|S3_ACCESS_KEY=$S3_ACCESS_KEY|" .env
            sed -i "s|^S3_SECRET_KEY=.*|S3_SECRET_KEY=$S3_SECRET_KEY|" .env
            echo "✓ S3_ACCESS_KEY has been generated and set"
            echo "✓ S3_SECRET_KEY has been generated and set"
        fi
    fi
    
    # Generate and set POSTGRES_PASSWORD
    echo ""
    echo "4. PostgreSQL Database Password (generating secure password)"
    echo ""
    
    POSTGRES_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))" 2>/dev/null || echo "postgres-$(date +%s)")
    
    if [ -n "$POSTGRES_PASSWORD" ]; then
        if command -v sed &> /dev/null; then
            sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$POSTGRES_PASSWORD|" .env
            # Update DATABASE_URL with the new password
            sed -i "s|^DATABASE_URL=.*|DATABASE_URL=postgresql+psycopg://postgres:$POSTGRES_PASSWORD@postgres:5432/jules_inventory|" .env
            echo "✓ POSTGRES_PASSWORD has been generated and set"
            echo "✓ DATABASE_URL has been updated with the password"
        fi
    fi
    
    # Clear passwords from memory
    unset POSTGRES_PASSWORD S3_ACCESS_KEY S3_SECRET_KEY
    
    echo ""
    echo "Configuration complete!"
    echo ""
else
    echo "✓ .env file already exists"
    
    # Check if SECRET_KEY is set
    if grep -q "^SECRET_KEY=$" .env || ! grep -q "^SECRET_KEY=" .env; then
        echo ""
        echo "ERROR: SECRET_KEY is not set in .env"
        echo "Please edit .env and set SECRET_KEY"
        exit 1
    fi
    
    # Check if ADMIN_PASSWORD is set
    if grep -q "^ADMIN_PASSWORD=$" .env || ! grep -q "^ADMIN_PASSWORD=" .env; then
        echo ""
        echo "ERROR: ADMIN_PASSWORD is not set in .env"
        echo "Please edit .env and set ADMIN_PASSWORD"
        exit 1
    fi
    
    echo "✓ Configuration looks good"
    echo ""
fi

echo "================================================================"
echo "  Starting Services"
echo "================================================================"
echo ""

# Pull images
echo "Pulling Docker images..."
docker compose pull

echo ""
echo "Starting services (this may take a minute)..."
docker compose up -d

echo ""
echo "================================================================"
echo "  Waiting for services to be ready..."
echo "================================================================"
echo ""

# Wait for health checks
sleep 5

MAX_WAIT=60
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "✓ Application is ready!"
        break
    fi
    echo "  Waiting for application... ($ELAPSED/$MAX_WAIT seconds)"
    sleep 5
    ELAPSED=$((ELAPSED + 5))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo ""
    echo "WARNING: Application didn't respond within $MAX_WAIT seconds"
    echo "Check logs with: docker compose logs app"
    echo ""
fi

echo ""
echo "================================================================"
echo "  Jules Inventory Platform is Running!"
echo "================================================================"
echo ""
echo "  Application:     http://localhost:8000"
echo "  MinIO Console:   http://localhost:9001"
echo ""
echo "  Login with:"
echo "    Username: admin"
echo "    Password: (the one you set)"
echo ""
echo "================================================================"
echo ""
echo "Useful commands:"
echo "  docker compose logs -f app    # View application logs"
echo "  docker compose ps             # View service status"
echo "  docker compose stop           # Stop services"
echo "  docker compose down           # Stop and remove containers"
echo "  docker compose down -v        # Stop and remove all data (WARNING!)"
echo ""
