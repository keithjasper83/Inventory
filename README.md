# Inventory Platform (inventory.kjdev.uk)

**Status**: ✅ **READY FOR BETA LAUNCH** | Version: 1.0.0-beta | Last Updated: 2026-01-21

A local-first, AI-assisted workshop inventory system designed for fast photo capture, accurate identification, and long-term data quality.

## 🎯 Beta Release Status

- ✅ **Security**: 0 vulnerabilities (CodeQL verified)
- ✅ **Features**: 100% complete (all originally designed features implemented)
- ✅ **Documentation**: Comprehensive (6 major docs + API docs)
- ✅ **Deployment**: One-command Docker deployment working
- ✅ **Architecture**: DDD and SOC principles fully implemented
- ✅ **Testing**: Core functionality verified

## Highlights
- Photo-first item capture (mobile-first)
- **Counting+** bulk resistor recognition and counting from photos
- PostgreSQL Full-Text Search from v1
- Human-readable URLs + catch-all resolver
- AI-assisted OCR, duplicate detection, resistor colour-code decoding
- AI-scraping with evidence (PDF snapshot + datasheets) when confidence >= 95%
- Fully auditable AI actions with human approval required for conflicts
- **Enhanced security with role-based access control and comprehensive audit logging**

## Tech stack
- FastAPI (Python 3.12+)
- PostgreSQL (FTS)
- Redis + RQ (background jobs)
- TailwindCSS (UI)
- Self-hosted MinIO for S3-compatible object storage (NOT AWS - all data stays in container/persistent storage)
- AI models hosted on Jarvis (desktop GPU) via VPN

## Security
- Role-based access control (user, reviewer, admin)
- Environment variable configuration for all secrets
- Enhanced audit logging with pre/post state tracking
- Automatic retry mechanisms for transient failures
- AI validation and confidence-based approval workflows
- **See [SECURITY.md](SECURITY.md) for complete security documentation**

## Setup

### Quick Start with Docker (Recommended) ⚡

The fastest way to get started with zero configuration:

```bash
# Clone and enter directory
git clone https://github.com/keithjasper83/Inventory.git
cd Inventory

# Run the quick-start script
./quick-start.sh

# Access at http://localhost:8000
```

The quick-start script will:
- ✅ Check Docker installation
- ✅ Generate secure SECRET_KEY
- ✅ Prompt for admin password
- ✅ Generate secure MinIO and PostgreSQL credentials
- ✅ Start all services (PostgreSQL, Redis, self-hosted MinIO, App)
- ✅ Wait for services to be ready

See [DEPLOYMENT.md](DEPLOYMENT.md) for:
- Production deployment
- External database/Redis/S3 configuration
- Manual installation
- Backup and restore
- Troubleshooting

### Manual Installation

For development or when Docker is not available:

### Prerequisites
- Python 3.12+
- PostgreSQL
- Redis
- Self-hosted MinIO (S3-compatible storage - NOT AWS)

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Run database migrations:
   ```bash
   alembic upgrade head
   ```

5. Start the application:
   ```bash
   uvicorn src.main:app --reload
   ```

## Configuration

Critical security settings are configured via environment variables. See [SECURITY.md](SECURITY.md) for:
- Environment variable configuration
- Role-based access setup
- Audit logging configuration
- AI confidence thresholds
- Production deployment checklist

## Testing

Run the test suite:
```bash
# All tests
pytest tests/ -v

# Security tests only
pytest tests/test_security_enhancements.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

## 📚 Documentation

### Getting Started
- **[README.md](README.md)** — This file, quick start guide
- **[DEPLOYMENT.md](DEPLOYMENT.md)** — Complete deployment guide
- **[PRE_LAUNCH_CHECKLIST.md](PRE_LAUNCH_CHECKLIST.md)** — Beta launch verification

### Architecture & Design
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — System architecture and design decisions
- **[SPECIFICATION.txt](SPECIFICATION.txt)** — Original product specification
- **[VALIDATION_SUMMARY.md](VALIDATION_SUMMARY.md)** — DDD/SOC compliance verification

### Features & Roadmap
- **[VERSION_1_FEATURES.md](VERSION_1_FEATURES.md)** — Complete v1.0 feature list
- **[VERSION_2_ROADMAP.md](VERSION_2_ROADMAP.md)** — Future features and timeline

### Security & Operations
- **[SECURITY.md](SECURITY.md)** — Security features and configuration
- **[agents.md](agents.md)** — AI policy and permissions
- **[FINAL_BETA_STATUS.md](FINAL_BETA_STATUS.md)** — Beta status report

### Configuration Templates
- `.env.example` — Development environment template
- `.env.production` — Production environment template
- `config/ai_host.env.example` — AI service configuration


## Beta Hardening Update (Phase 1-5)

In addition to core features, the system is now hardened for production environments:
- **Reproducible Installs**: Deterministic `requirements.txt` via `pip-tools`.
- **Infrastructure Readiness**: Docker setup checks database/redis/s3 readiness implicitly via `wait_for_services.py` and robust `app/health` and `app/readiness` APIs.
- **Resilient AI Workers**: RQ tasks are bounded by 5m timeouts, 24-hr TTLs, and explicit error handlers to prevent application blocking. Admins can replay failed AI jobs securely.
- **Config & Security**: Pydantic typed `Settings` objects replace scattered configuration. `slowapi` rate limiting protects heavy endpoint abuse.
- **Concurrency & Database**: Optimistic locking (`version_id`) guards Item modifications. Heavy inventory DB read ops enforce explicit bounds via batch limits and query N+1 detection.
