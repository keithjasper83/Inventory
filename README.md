# Inventory Platform (inventory.kjdev.uk)

A local-first, AI-assisted workshop inventory system designed for fast photo capture, accurate identification, and long-term data quality.

## Highlights
- Photo-first item capture (mobile-first)
- PostgreSQL Full-Text Search from v1
- Human-readable URLs + catch-all resolver
- AI-assisted OCR, duplicate detection, resistor colour-code decoding
- AI-scraping with evidence (PDF snapshot + datasheets) when confidence >= 95%
- Fully auditable AI actions with human approval required for conflicts

## Tech stack
- FastAPI (Python 3.12+)
- PostgreSQL (FTS)
- Redis + RQ (background jobs)
- TailwindCSS (UI)
- S3-compatible object storage (MinIO recommended)
- AI models hosted on Jarvis (desktop GPU) via VPN

## Security
- Basic username/password auth (v1)
- Jarvis AI endpoints never exposed publicly

## Repository notes
This repo contains product specifications and agent policy files intended to guide implementation.

## Files
- `SPECIFICATION.txt` — full product spec
- `agents.md` — AI policy and audit rules
- `config/ai_host.env.example` — template for AI host configuration

