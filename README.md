# Inventory Platform (inventory.kjdev.uk)

A local-first, AI-assisted workshop inventory system designed for fast photo capture, accurate identification, and long-term data quality.

## Highlights
- Photo-first item capture (mobile-first)
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
- S3-compatible object storage (MinIO recommended)
- AI models hosted on Jarvis (desktop GPU) via VPN

## Security
- Role-based access control (user, reviewer, admin)
- Environment variable configuration for all secrets
- Enhanced audit logging with pre/post state tracking
- Automatic retry mechanisms for transient failures
- AI validation and confidence-based approval workflows
- **See [SECURITY.md](SECURITY.md) for complete security documentation**

## Setup

### Prerequisites
- Python 3.12+
- PostgreSQL
- Redis
- S3-compatible storage (MinIO)

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

## Repository notes
This repo contains product specifications and agent policy files intended to guide implementation.

## Files
- `SPECIFICATION.txt` — full product spec
- `SECURITY.md` — comprehensive security documentation
- `agents.md` — AI policy and audit rules
- `config/ai_host.env.example` — template for AI host configuration
- `.env.example` — template for environment variables

