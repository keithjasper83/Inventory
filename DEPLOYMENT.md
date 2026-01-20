# Deployment Guide - Jules Inventory Platform

## Table of Contents
1. [Quick Start with Docker](#quick-start-with-docker)
2. [Production Deployment](#production-deployment)
3. [Manual Installation](#manual-installation)
4. [Configuration](#configuration)
5. [Backup and Restore](#backup-and-restore)
6. [Troubleshooting](#troubleshooting)

## Quick Start with Docker

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/keithjasper83/Inventory.git
   cd Inventory
   ```

2. **Generate a secret key**
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

3. **Create .env file**
   ```bash
   cp .env.production .env
   # Edit .env and set SECRET_KEY and ADMIN_PASSWORD
   nano .env
   ```

4. **Start all services**
   ```bash
   docker-compose up -d
   ```

5. **Access the application**
   - Application: http://localhost:8000
   - MinIO Console: http://localhost:9001

6. **Login**
   - Username: `admin`
   - Password: (the one you set in ADMIN_PASSWORD)

## Production Deployment

### Security Checklist

- [ ] Set a strong, unique `SECRET_KEY` (32+ characters)
- [ ] Set a strong `ADMIN_PASSWORD` (8+ characters, not "admin")
- [ ] Change `POSTGRES_PASSWORD` from default
- [ ] Change MinIO credentials (`S3_ACCESS_KEY`, `S3_SECRET_KEY`)
- [ ] Use HTTPS with reverse proxy (nginx, Traefik)
- [ ] Enable firewall rules
- [ ] Configure log rotation
- [ ] Set up regular backups
- [ ] Configure monitoring

### Deployment Options

#### Option 1: All-in-One Container (Recommended for Small Deployments)

All services (PostgreSQL, Redis, MinIO, App) run in Docker.

```bash
# Use the default docker-compose.yml
docker-compose up -d
```

**Pros:**
- Simple setup
- All services managed together
- Easy to backup/restore

**Cons:**
- Single point of failure
- Limited scalability

#### Option 2: Split Services (Recommended for Production)

Use external database, Redis, and S3 for better scalability and reliability.

1. **Set up external services**
   - PostgreSQL 15+ (managed or self-hosted)
   - Redis 7+ (managed or self-hosted)
   - MinIO or AWS S3

2. **Update .env with external service URLs**
   ```bash
   DATABASE_URL=postgresql+psycopg://user:pass@db-host:5432/jules
   REDIS_URL=redis://redis-host:6379/0
   S3_ENDPOINT_URL=https://s3.amazonaws.com
   S3_ACCESS_KEY=your-access-key
   S3_SECRET_KEY=your-secret-key
   ```

3. **Comment out internal services in docker-compose.yml**
   ```yaml
   # Comment out postgres, redis, minio services
   # Only keep app and worker
   ```

4. **Start application services only**
   ```bash
   docker-compose up -d app worker
   ```

### Reverse Proxy Configuration (nginx)

```nginx
server {
    listen 80;
    server_name inventory.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name inventory.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check endpoint (don't require auth)
    location /health {
        proxy_pass http://localhost:8000/health;
        access_log off;
    }
}
```

## Manual Installation

For development or when Docker is not available.

### Prerequisites
- Python 3.12+
- PostgreSQL 15+
- Redis 7+
- MinIO or S3-compatible storage

### Steps

1. **Install system dependencies**
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install python3.12 python3.12-venv postgresql redis-server
   ```

2. **Clone and setup**
   ```bash
   git clone https://github.com/keithjasper83/Inventory.git
   cd Inventory
   chmod +x install.sh start.sh
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   nano .env
   ```

4. **Run installation**
   ```bash
   ./install.sh
   ```

5. **Start the application**
   ```bash
   ./start.sh
   ```

## Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | **CRITICAL** - Application secret key | Generated string |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg://...` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_PASSWORD` | (none) | Initial admin password |
| `ENVIRONMENT` | `development` | `development`, `production` |
| `TOKEN_EXPIRY_SECONDS` | `86400` | Session timeout (24 hours) |
| `AI_AUTO_APPLY_CONFIDENCE` | `0.95` | AI auto-apply threshold |
| `JARVIS_BASE_URL` | (empty) | AI service endpoint |

### AI Configuration (Optional)

If using the Jarvis AI service:

1. Create `config/ai_host.env`:
   ```bash
   mkdir -p config
   cp config/ai_host.env.example config/ai_host.env
   ```

2. Edit `config/ai_host.env`:
   ```bash
   JARVIS_BASE_URL=http://jarvis.internal:8500
   JARVIS_HEALTH_PATH=/health
   ```

## Backup and Restore

### Backup

```bash
# Backup database
docker exec jules-postgres pg_dump -U postgres jules_inventory > backup.sql

# Backup MinIO data
docker exec jules-minio mc mirror /data backup-minio/

# Backup volumes
docker run --rm -v jules_postgres_data:/data -v $(pwd):/backup \
  ubuntu tar czf /backup/postgres-backup.tar.gz /data
```

### Restore

```bash
# Restore database
docker exec -i jules-postgres psql -U postgres jules_inventory < backup.sql

# Restore MinIO data
docker exec jules-minio mc mirror backup-minio/ /data

# Restore volumes
docker run --rm -v jules_postgres_data:/data -v $(pwd):/backup \
  ubuntu tar xzf /backup/postgres-backup.tar.gz -C /
```

## Troubleshooting

### Application won't start

**Check logs:**
```bash
docker-compose logs app
docker-compose logs worker
```

**Common issues:**
- Database not ready: Wait for PostgreSQL to be healthy
- Missing SECRET_KEY: Check .env file
- Port already in use: Change port mapping in docker-compose.yml

### Database connection errors

**Check PostgreSQL:**
```bash
docker-compose ps postgres
docker-compose logs postgres
```

**Test connection:**
```bash
docker exec jules-postgres pg_isready -U postgres
```

### Background jobs not working

**Check Redis:**
```bash
docker-compose ps redis
docker-compose logs redis
```

**Check worker:**
```bash
docker-compose logs worker
```

### Storage (MinIO) issues

**Check MinIO:**
```bash
docker-compose ps minio
docker-compose logs minio
```

**Access MinIO Console:**
- URL: http://localhost:9001
- Username: minioadmin (or your S3_ACCESS_KEY)
- Password: minioadmin (or your S3_SECRET_KEY)

### Health Check Endpoints

```bash
# Check application health
curl http://localhost:8000/health

# Check readiness (includes dependencies)
curl http://localhost:8000/readiness
```

### Reset Everything

```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: This deletes all data!)
docker-compose down -v

# Start fresh
docker-compose up -d
```

## Monitoring

### Check Service Status

```bash
docker-compose ps
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f app
docker-compose logs -f worker
```

### Resource Usage

```bash
docker stats
```

## Upgrading

1. **Backup data** (see Backup section)

2. **Pull latest code**
   ```bash
   git pull
   ```

3. **Rebuild containers**
   ```bash
   docker-compose build
   ```

4. **Restart services**
   ```bash
   docker-compose up -d
   ```

5. **Verify health**
   ```bash
   curl http://localhost:8000/health
   ```

## Support

For issues or questions:
- Check the logs: `docker-compose logs`
- Check health endpoints: `/health` and `/readiness`
- Review configuration in `.env`
- Ensure all required services are running

## Security Notes

1. **Never commit .env files to version control**
2. **Use strong passwords** for all services
3. **Enable HTTPS** in production with reverse proxy
4. **Regular backups** of database and storage
5. **Monitor logs** for suspicious activity
6. **Update dependencies** regularly
7. **Restrict network access** to necessary ports only

## Performance Tuning

### Database
- Increase PostgreSQL shared_buffers for better performance
- Add indexes for frequently queried columns
- Regular VACUUM ANALYZE

### Redis
- Increase maxmemory if needed
- Enable persistence (AOF or RDB)

### Application
- Increase worker count for heavy workloads
- Use external Redis for better performance
- Use CDN for static files

## License

See LICENSE file in the repository.
