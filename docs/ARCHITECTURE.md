# Jules Inventory Platform - Architecture & Design Decisions

## Table of Contents
1. [System Overview](#system-overview)
2. [Architectural Principles](#architectural-principles)
3. [Domain-Driven Design (DDD)](#domain-driven-design-ddd)
4. [Separation of Concerns (SOC)](#separation-of-concerns-soc)
5. [Technology Stack](#technology-stack)
6. [Data Architecture](#data-architecture)
7. [AI Integration Architecture](#ai-integration-architecture)
8. [Security Architecture](#security-architecture)
9. [Performance & Scalability](#performance--scalability)
10. [Design Decisions](#design-decisions)

---

## System Overview

Jules Inventory Platform is a **local-first, AI-assisted workshop inventory system** designed for rapid capture, accurate identification, and long-term data quality with full human control.

### Core Design Philosophy
- **Capture must never block on AI** - User experience is paramount
- **AI assists, never decides** - Human judgement is always final
- **All AI actions are auditable and reversible** - Complete transparency
- **Unknown data is acceptable; refine later** - Progressive enhancement
- **Data must be interrogable** - PostgreSQL FTS enables powerful search
- **Local-first and self-hostable** - User data stays under user control

---

## Architectural Principles

### 1. Local-First Architecture
- **Decision**: All user data is stored locally or in user-controlled infrastructure
- **Rationale**: Privacy, control, and independence from external services
- **Implementation**: Self-hosted PostgreSQL, Redis, and MinIO (S3-compatible)

### 2. Photo-First Capture
- **Decision**: Mobile-first UI optimized for camera capture
- **Rationale**: Workshop inventory benefits from visual documentation
- **Implementation**: Direct camera integration, immediate upload to S3, async processing

### 3. Progressive Enhancement
- **Decision**: Items can be created as drafts with minimal information
- **Rationale**: Capture workflow shouldn't be blocked by missing data
- **Implementation**: Draft mode, AI enrichment in background, manual refinement

### 4. Async-First Processing
- **Decision**: All AI and heavy processing tasks run asynchronously
- **Rationale**: Never block user interactions on slow operations
- **Implementation**: Redis + RQ for background job queue

---

## Domain-Driven Design (DDD)

### Bounded Contexts

The system is organized into four distinct bounded contexts:

#### 1. Inventory Context
**Domain Models**: Item, Category, Location, Stock

**Responsibilities**:
- Core inventory management
- Item lifecycle (create, update, archive)
- Category management with dynamic schemas
- Location hierarchy and stock tracking

**Repository Pattern**:
- `ItemRepository` - Item CRUD operations
- `CategoryRepository` - Category operations
- `LocationRepository` - Location hierarchy operations
- `StockRepository` - Stock level management

**Domain Services**:
- `ItemService` - Business logic for item creation, updates, validation
- `CategoryService` - Category schema management
- `LocationService` - Location hierarchy management

#### 2. Media Context
**Domain Models**: Media (photos, PDFs, datasheets)

**Responsibilities**:
- Photo upload and storage
- Thumbnail generation
- Datasheet management
- Source snapshot archival

**Repository Pattern**:
- `MediaRepository` - Media CRUD operations

**Integration**:
- S3-compatible storage (MinIO)
- Async thumbnail generation
- Presigned URLs for secure access

#### 3. AI Assistance Context
**Domain Models**: AuditLog (includes AI suggestions and actions)

**Responsibilities**:
- OCR processing
- Image embeddings for duplicate detection
- Resistor color band identification
- AI scraping with confidence scoring
- Suggestion management and approval workflow

**Key Concepts**:
- Confidence-based approval (95% threshold)
- Human-in-the-loop for uncertain suggestions
- Complete audit trail with before/after states

#### 4. Search Context
**Responsibilities**:
- PostgreSQL Full-Text Search
- URL intent resolution
- Catch-all routing with AI fallback

**Implementation**:
- GIN indexes on tsvector columns
- Deterministic routing first, AI only if ambiguous
- Human-readable URL patterns

### Domain Services

Domain services encapsulate business logic that doesn't naturally belong to a single entity:

```
src/domain/
  ├── services.py        # Business logic services
  ├── repositories.py    # Data access layer
  └── __init__.py
```

**Benefits of Domain Services**:
- Clear separation of business logic from infrastructure
- Testable without database
- Reusable across different contexts
- Explicit modeling of domain concepts

---

## Separation of Concerns (SOC)

### Layered Architecture

```
┌─────────────────────────────────────────┐
│         Presentation Layer              │
│  (FastAPI routes, Jinja2 templates)    │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│          Application Layer              │
│     (Domain Services, Use Cases)        │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│           Domain Layer                  │
│    (Models, Business Rules, Logic)      │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│       Infrastructure Layer              │
│  (Database, S3, Redis, External APIs)   │
└─────────────────────────────────────────┘
```

### Layer Responsibilities

#### Presentation Layer (`src/routers/`)
- HTTP request/response handling
- Input validation (FastAPI models)
- Session management
- Template rendering
- **NO business logic**

#### Application Layer (`src/domain/services.py`)
- Orchestrates domain operations
- Transaction management
- Integration between bounded contexts
- Use case implementation

#### Domain Layer (`src/models.py`, `src/domain/`)
- Business entities
- Business rules
- Domain logic
- **Independent of infrastructure**

#### Infrastructure Layer (`src/database.py`, `src/storage.py`, `src/ai.py`)
- Database connections
- External service clients
- File storage
- Caching
- Message queues

### Dependency Inversion

- High-level modules (domain) don't depend on low-level modules (infrastructure)
- Both depend on abstractions (repositories, service interfaces)
- Infrastructure implements interfaces defined by domain

---

## Technology Stack

### Backend
- **Python 3.12+** - Modern Python with type hints
- **FastAPI** - High-performance async web framework
- **SQLAlchemy 2.x** - Modern ORM with async support
- **Alembic** - Database migrations
- **Pydantic v2** - Data validation and settings management

### Data Storage
- **PostgreSQL 15+** - Primary database with FTS
- **Redis 7+** - Message queue and caching
- **MinIO** - S3-compatible object storage (self-hosted)

### Background Processing
- **RQ (Redis Queue)** - Background job processing
- Retry with exponential backoff
- Job monitoring and management

### Frontend
- **Jinja2** - Server-side templating
- **TailwindCSS** - Utility-first CSS framework
- **Vanilla JavaScript** - Minimal, no framework lock-in
- **Mobile-first responsive design**

### AI/ML (Optional - Jarvis)
- **PaddleOCR** - Text recognition
- **OpenCLIP** - Image embeddings
- **Local LLM** - Structured extraction
- All models run on separate GPU server (Jarvis)

---

## Data Architecture

### Database Schema Design

#### Items Table
```sql
CREATE TABLE items (
    id SERIAL PRIMARY KEY,
    name VARCHAR,
    slug VARCHAR UNIQUE,
    category_id INTEGER REFERENCES categories(id),
    data JSONB DEFAULT '{}',                    -- Dynamic attributes
    pending_changes JSONB DEFAULT '{}',         -- AI suggestions
    is_draft BOOLEAN DEFAULT TRUE,
    search_vector TSVECTOR GENERATED,           -- Full-text search
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ix_items_search_vector ON items USING GIN(search_vector);
```

**Design Decisions**:
- **JSONB for dynamic data** - Categories define their own schemas
- **Generated FTS vector** - Automatic search index updates
- **Slug for human-readable URLs** - SEO and usability
- **Draft mode** - Progressive data quality

#### Audit Log
```sql
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR NOT NULL,
    entity_id INTEGER NOT NULL,
    action VARCHAR NOT NULL,                    -- CREATE, UPDATE, DELETE, SUGGEST
    changes JSONB NOT NULL,
    source VARCHAR DEFAULT 'USER',              -- USER, AI_GENERATED, AI_SCRAPED
    confidence FLOAT,                           -- AI confidence 0-1
    user_id INTEGER REFERENCES users(id),
    before_state JSONB,                         -- Complete before state
    after_state JSONB,                          -- Complete after state
    approval_status VARCHAR,                    -- auto_approved, pending, needs_review
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ix_audit_log_entity ON audit_log (entity_type, entity_id);
CREATE INDEX ix_audit_log_user_id ON audit_log (user_id);
CREATE INDEX ix_audit_log_approval_status ON audit_log (approval_status);
```

**Design Decisions**:
- **Complete state snapshots** - Full auditability and undo capability
- **Confidence scoring** - Enables confidence-based workflows
- **Approval workflow** - Human oversight for uncertain AI actions
- **Indexed for performance** - Fast queries by entity, user, or status

### S3 Bucket Structure

```
inventory-media/
  └── items/
      └── {item_id}/
          ├── original-{uuid}-{filename}
          ├── medium-{uuid}-{filename}
          └── thumbnail-{uuid}-{filename}

inventory-docs/
  └── items/
      └── {item_id}/
          ├── datasheet-{uuid}.pdf
          ├── snapshot-{uuid}.pdf
          └── reference-{uuid}.pdf
```

**Design Decisions**:
- **Organized by item** - Easy to locate all media for an item
- **UUID in filenames** - Prevents collisions, enables versioning
- **Multiple sizes** - Performance optimization for different use cases
- **Separate buckets** - Different access policies and lifecycle rules

---

## AI Integration Architecture

### Design Principles

1. **Fail-Safe**: UI continues working if Jarvis is unavailable
2. **Async-First**: All AI tasks queued, never block user
3. **Confidence-Based**: High confidence → auto-apply, Low → review
4. **Auditable**: Every AI action logged with evidence

### AI Service Separation

```
┌──────────────┐           ┌──────────────┐
│   Web App    │  ◄─VPN──► │    Jarvis    │
│  (FastAPI)   │           │  (GPU Host)  │
└──────┬───────┘           └──────────────┘
       │                          │
       │ Queue Jobs               │ Execute Models
       ▼                          ▼
┌──────────────┐           ┌──────────────┐
│     Redis    │           │  PaddleOCR   │
│   (RQ Jobs)  │           │   OpenCLIP   │
└──────────────┘           │   Local LLM  │
                           └──────────────┘
```

**Why Separate Jarvis Server?**
- **Resource isolation** - GPU-intensive models don't impact web server
- **Scalability** - Can scale web and AI independently
- **Security** - Jarvis not exposed to internet
- **Flexibility** - Can upgrade GPU without touching web server

### Confidence-Based Workflow

```python
if confidence >= 0.95:
    # Auto-apply
    apply_changes(item, ai_data)
    create_audit_log(source="AI_SCRAPED", approval_status="auto_approved")
    
elif confidence >= 0.80:
    # Pending review
    item.pending_changes = ai_data
    create_audit_log(source="AI_GENERATED", approval_status="pending")
    
else:
    # Needs review
    create_audit_log(source="AI_GENERATED", approval_status="needs_review")
```

### Retry Strategy

All AI tasks use exponential backoff:
- Attempt 1: Immediate
- Attempt 2: 2 seconds delay
- Attempt 3: 4 seconds delay
- Attempt 4: 8 seconds delay

After 3 retries, job marked as failed with audit log entry.

---

## Security Architecture

### Defense in Depth

1. **Authentication** - Username/password (bcrypt hashing)
2. **Authorization** - Role-based access control (user, reviewer, admin)
3. **Session Security** - Secure session middleware
4. **Input Validation** - Pydantic models at API boundary
5. **SQL Injection Protection** - SQLAlchemy ORM, parameterized queries
6. **Secret Management** - Environment variables, never in code
7. **Audit Logging** - Complete trail of all changes

### Role-Based Access Control (RBAC)

```python
# Role hierarchy
admin (level 3)
  └─ reviewer (level 2)
      └─ user (level 1)

# Permission matrix
Action                  | User | Reviewer | Admin
------------------------|------|----------|------
Create/Edit Items       |  ✓   |    ✓     |   ✓
Review AI Suggestions   |  ✗   |    ✓     |   ✓
View Audit Logs         |  ✗   |    ✗     |   ✓
Manage Users            |  ✗   |    ✗     |   ✓
```

### Configuration Security

- **No default credentials in production** - Validation at startup
- **Secret key rotation** - Documented procedure
- **Environment-based config** - Development, staging, production
- **Secure defaults** - HTTPS required in production

---

## Performance & Scalability

### Current Architecture (Single Server)

```
Docker Compose Stack:
  ├── PostgreSQL (1 container)
  ├── Redis (1 container)
  ├── MinIO (1 container)
  ├── Web App (1 container)
  └── Worker (1 container)
```

**Suitable for**: Development, small teams (< 50 users), < 10k items

### Scalable Architecture (Production)

```
Load Balancer
  └─ Web App (N containers, scaled horizontally)
       ├─ PostgreSQL (managed service, read replicas)
       ├─ Redis (managed service, clustered)
       ├─ S3/MinIO (object storage, CDN)
       └─ Worker (M containers, scaled based on queue depth)
```

**Scalability Strategies**:
1. **Horizontal scaling** - Add more web/worker containers
2. **Database optimization** - Read replicas, connection pooling
3. **Caching** - Redis for frequently accessed data
4. **CDN** - Serve media through CDN
5. **Background jobs** - Scale workers independently

### Performance Optimizations

#### Database
- **GIN indexes** - Fast full-text search
- **JSONB indexes** - Fast queries on dynamic attributes
- **Generated columns** - Pre-computed search vectors
- **Connection pooling** - Reuse database connections

#### Application
- **Async I/O** - FastAPI's async capabilities
- **Gzip compression** - Reduce bandwidth
- **Lazy loading** - Load data only when needed
- **Batch operations** - Process multiple items efficiently

#### Media
- **Multiple sizes** - Serve appropriate size for context
- **Presigned URLs** - Direct S3 access, bypass app server
- **Lazy thumbnail generation** - Generate on upload, not on view
- **CDN-ready** - S3/MinIO can front with CloudFlare, etc.

---

## Design Decisions

### Decision Log

#### 1. PostgreSQL over NoSQL
**Decision**: Use PostgreSQL as primary database  
**Rationale**: 
- Mature FTS capabilities essential for search
- JSONB provides flexibility where needed
- ACID transactions for data integrity
- Well-understood operational model
**Trade-offs**: Horizontal scaling requires more planning than NoSQL

#### 2. Server-Side Rendering over SPA
**Decision**: Jinja2 templates, not React/Vue  
**Rationale**:
- Simpler deployment (single service)
- Better SEO and initial load time
- Lower JavaScript bundle size
- Progressive enhancement friendly
**Trade-offs**: Less dynamic UI, more page refreshes

#### 3. MinIO over AWS S3
**Decision**: Self-hosted MinIO as default, S3-compatible API  
**Rationale**:
- Local-first philosophy
- User controls their data
- No AWS vendor lock-in
- Can still use real S3 if desired
**Trade-offs**: User must manage storage infrastructure

#### 4. RQ over Celery
**Decision**: Redis Queue (RQ) for background jobs  
**Rationale**:
- Simpler than Celery
- Redis already required for caching
- Sufficient for current needs
- Easy monitoring and management
**Trade-offs**: Less feature-rich than Celery, Redis-only

#### 5. Separate Jarvis AI Server
**Decision**: Don't run AI models on web server  
**Rationale**:
- Resource isolation
- Security (Jarvis not internet-facing)
- Flexibility in GPU hardware
- Optional feature (app works without it)
**Trade-offs**: More infrastructure to manage

#### 6. Confidence-Based Auto-Apply
**Decision**: Auto-apply AI suggestions ≥95% confidence  
**Rationale**:
- Reduces manual review burden
- 95% threshold balances automation and accuracy
- Complete audit trail for accountability
- User can undo if wrong
**Trade-offs**: Occasional wrong auto-applies (logged and reversible)

#### 7. Draft Mode for Items
**Decision**: Allow creating items with minimal data  
**Rationale**:
- Never block capture workflow
- Progressive enhancement philosophy
- AI can enrich later
- Better than no capture at all
**Trade-offs**: Some items may remain incomplete

#### 8. Human-Readable URLs
**Decision**: Use slugs like `/i/resistor-10k-abc123`  
**Rationale**:
- Better SEO
- Easier to share and remember
- Catch-all resolver handles ambiguity
- Professional appearance
**Trade-offs**: Slug generation and collision handling

#### 9. Monolithic Repository
**Decision**: Single repo for all code  
**Rationale**:
- Simpler for small/medium teams
- Atomic commits across features
- Easier local development
- No versioning complexity between services
**Trade-offs**: Larger repo, more comprehensive CI

#### 10. Environment-Based Config
**Decision**: `.env` files, not config database  
**Rationale**:
- 12-factor app principles
- Easy to version control templates
- Clear separation of code and config
- Standard practice in modern apps
**Trade-offs**: Requires restart to change config

---

## Future Considerations

### Potential Improvements (Version 2)

1. **Real-time Updates** - WebSockets for live updates
2. **Multi-tenancy** - Support multiple organizations
3. **Advanced Search** - Elasticsearch for complex queries
4. **API-First** - RESTful API for mobile apps
5. **Internationalization** - Multi-language support
6. **Advanced Analytics** - Usage patterns, predictions
7. **Batch Import** - CSV/Excel import
8. **Barcode Scanning** - Native app integration
9. **Collaboration** - Comments, tags, assignments
10. **Offline Mode** - Progressive Web App capabilities

### Migration Path

Current architecture supports gradual evolution:
- Add API endpoints without breaking UI
- Introduce React components gradually
- Migrate to microservices if needed
- Scale services independently

---

## Conclusion

The Jules Inventory Platform architecture is designed for:
- **Simplicity** - Easy to understand, deploy, and maintain
- **Flexibility** - Can scale and evolve as needs grow
- **Reliability** - Fail-safe design, complete audit trail
- **User Control** - Local-first, self-hostable, no vendor lock-in

The architecture balances pragmatism with best practices, delivering a production-ready system that can grow with the user's needs.

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-21  
**Maintained by**: Development Team

## Beta Hardening Improvements (Phase 1-5)

### Database Constraints and Connections
The PostgreSQL database engine is properly tuned with explicit `pool_size` limits, `max_overflow`, and `pool_pre_ping` protections, preventing DB thread crashes under API load spikes. Data structures have explicitly transitioned from arbitrary server dates to explicit UTC-timezone-aware definitions, keeping time boundaries in the frontend unambiguous.
- We utilize optimistic locking (`version_id` column) on core `Item` mutations.
- List queries explicitly truncate resultsets at 100 elements bounding JSON serialization latency. Eager `joinedload` queries prevent N+1 database roundtrips.

### Idempotency and Throttling
Heavy routes (like form uploads) rely on slowapi rate limits and explicit Idempotency headers stored temporarily in Redis. Concurrent clicks by users no longer queue multiple duplicate AI Background processing tasks due to the Idempotent locking API middleware.

### Deployment Safety
To safely deploy the API in containerized environments with race-conditions (Compose clusters mapping to slow internal MinIO or Postgres processes), we inject explicit `wait_for_services.py` bootstrap barriers in `.dockerignore` optimized runtime containers.
