# Security Enhancements Documentation

## Overview

This document describes the comprehensive security and stability enhancements implemented in the Inventory Management Platform. These improvements address critical areas including audit logging, access control, error handling, and configuration management.

## Table of Contents

1. [Environment Variables and Configuration](#environment-variables-and-configuration)
2. [Enhanced Audit Logging](#enhanced-audit-logging)
3. [Role-Based Access Control](#role-based-access-control)
4. [Redis and RQ Retry Mechanisms](#redis-and-rq-retry-mechanisms)
5. [AI Task Validation](#ai-task-validation)
6. [Database Index Optimization](#database-index-optimization)
7. [Security Best Practices](#security-best-practices)
8. [Testing](#testing)

---

## Environment Variables and Configuration

### Critical Security Settings

All sensitive configuration values have been moved to environment variables to prevent hardcoded secrets in the codebase.

#### Required Environment Variables

```bash
# Application Security
SECRET_KEY=your-secure-secret-key-here

# Database
DATABASE_URL=postgresql+psycopg://user:pass@host:port/dbname

# Redis Queue
REDIS_URL=redis://localhost:6379/0

# S3/MinIO Storage
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_REGION_NAME=us-east-1
BUCKET_MEDIA=inventory-media
BUCKET_DOCS=inventory-docs

# Security Configuration
TOKEN_EXPIRY_SECONDS=86400  # 24 hours
AI_AUTO_APPLY_CONFIDENCE=0.95  # 95% confidence threshold
AI_MANUAL_REVIEW_THRESHOLD=0.80  # 80% review threshold

# Environment
ENVIRONMENT=production  # development, staging, production
STRICT_CONFIG_VALIDATION=true  # Enable in production
```

### Configuration Validation

The system includes automatic configuration validation that runs at startup:

```python
from src.config import validate_production_config

# Call during application startup
if os.environ.get("ENVIRONMENT") == "production":
    validate_production_config()
```

**Validation Checks:**
- SECRET_KEY is not using default value
- DATABASE_URL does not contain default credentials in production
- S3 credentials are not using default values in production

### Setup Instructions

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Generate a secure SECRET_KEY:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

3. Update all values in `.env` with production credentials

4. **IMPORTANT**: Never commit `.env` to version control

---

## Enhanced Audit Logging

### Overview

The audit logging system has been significantly enhanced to provide comprehensive tracking of all AI-modified changes with complete pre/post states and approval workflows.

### Audit Log Features

#### 1. Pre/Post State Tracking

All audit logs now capture:
- **Before state**: Entity state before changes
- **After state**: Entity state after changes
- **Changes**: Specific fields that were modified
- **User tracking**: Which user initiated the action
- **Approval status**: Workflow state (pending, approved, rejected)

#### 2. Approval Workflow

AI suggestions are automatically categorized based on confidence:

```python
# Confidence >= 95% → auto_approved
# Confidence >= 80% → pending
# Confidence < 80% → needs_review
```

#### 3. Error Tracking

Failed operations are logged with:
- Error message
- Stack trace information
- Retry attempt count
- Timestamp of failure

### Using the Enhanced Audit System

```python
from src.tasks import create_audit_log

# Create a comprehensive audit log
audit = create_audit_log(
    db=db_session,
    entity_type="Item",
    entity_id=item.id,
    action="UPDATE",
    changes={"field": "new_value"},
    source="AI_GENERATED",
    confidence=85,
    user_id=current_user.id,
    before_state={"field": "old_value"},
    after_state={"field": "new_value"}
)
```

### Audit Log Actions

- **CREATE**: Entity was created
- **UPDATE**: Entity was updated
- **DELETE**: Entity was deleted
- **SUGGEST**: AI suggested a change (pending approval)
- **APPROVE**: User approved an AI suggestion
- **REJECT**: User rejected an AI suggestion

### Audit Log Sources

- **USER**: Human user action
- **AI_GENERATED**: AI suggestion (< 95% confidence)
- **AI_SCRAPED**: High-confidence AI data (≥ 95% confidence)

---

## Role-Based Access Control

### User Roles

The system supports three user roles with hierarchical privileges:

1. **user**: Basic access (can create/edit items)
2. **reviewer**: Can review and approve AI suggestions
3. **admin**: Full system access including audit log review

### Role Hierarchy

```
admin (level 3)
  └─ reviewer (level 2)
      └─ user (level 1)
```

Administrators inherit all reviewer privileges, and reviewers inherit all user privileges.

### Implementing Role-Based Access

#### In Route Handlers

```python
from fastapi import Depends
from src.dependencies import require_admin, require_reviewer, require_user

@router.get("/admin/audit-logs")
async def view_audit_logs(user = Depends(require_admin)):
    """Only admins can access this endpoint."""
    # Implementation
    pass

@router.post("/approve-suggestion/{id}")
async def approve_suggestion(id: int, user = Depends(require_reviewer)):
    """Reviewers and admins can approve suggestions."""
    # Implementation
    pass

@router.post("/items")
async def create_item(user = Depends(require_user)):
    """All authenticated users can create items."""
    # Implementation
    pass
```

#### Programmatic Role Checks

```python
# Check if user has specific role
if user.has_role("admin"):
    # Admin-only logic
    pass

# Check within business logic
def perform_sensitive_operation(user: User):
    if not user.has_role("reviewer"):
        raise PermissionError("Insufficient privileges")
    # Perform operation
```

### Migration for Role Support

Run the database migration to add role support:

```bash
alembic upgrade head
```

This adds:
- `role` column to `users` table (default: "user")
- Enhanced audit log columns
- Performance indices for audit queries

---

## Redis and RQ Retry Mechanisms

### Automatic Retry with Exponential Backoff

All background tasks now include automatic retry logic to handle transient failures:

```python
@retry_with_backoff(max_retries=3, initial_backoff=2)
def process_item_image(item_id: int, media_id: int):
    # Task implementation
    pass
```

### Retry Configuration

- **Max retries**: 3 attempts
- **Initial backoff**: 2 seconds
- **Max backoff**: 60 seconds
- **Backoff strategy**: Exponential (2^attempt * initial_backoff)

### Retry Behavior

```
Attempt 1: Immediate
Attempt 2: Wait 2 seconds
Attempt 3: Wait 4 seconds
Attempt 4: Wait 8 seconds (capped at MAX_BACKOFF)
```

### Error Handling

- **Transient errors**: Automatically retried (network issues, temporary unavailability)
- **Permanent errors**: Logged to audit system after all retries exhausted
- **Critical errors**: Trigger database rollback

### Monitoring Failed Jobs

All failed jobs are logged with:
- Attempt count
- Error message
- Timestamp
- Entity information

Check logs for failed tasks:

```bash
grep "ERROR" logs/app.log | grep "retry"
```

---

## AI Task Validation

### Input Validation

All AI outputs are validated before being applied to the database:

```python
from src.tasks import validate_ai_output

# Validate AI response
if validate_ai_output(ai_response, "field_name", expected_type):
    # Safe to use
    apply_changes(ai_response)
else:
    # Log warning and skip
    logger.warning(f"Invalid AI output for {field_name}")
```

### Validation Checks

1. **Null checks**: Reject None values
2. **Type validation**: Ensure correct data types
3. **Empty value checks**: Reject empty strings, lists, or dicts
4. **Range validation**: Ensure numeric values are within acceptable ranges

### Confidence Thresholds

Configurable confidence thresholds control AI behavior:

```python
# From config
AI_AUTO_APPLY_CONFIDENCE = 0.95  # Auto-apply above this
AI_MANUAL_REVIEW_THRESHOLD = 0.80  # Manual review below this
```

### AI Suggestion Workflow

```
AI Confidence ≥ 95%
  └─ Auto-approved → Applied to item
  └─ Logged as AI_SCRAPED

AI Confidence ≥ 80% and < 95%
  └─ Pending review → Awaiting manual approval
  └─ Logged as AI_GENERATED (pending)

AI Confidence < 80%
  └─ Needs review → Flagged for attention
  └─ Logged as AI_GENERATED (needs_review)
```

---

## Database Index Optimization

### Audit Log Indices

Three new indices have been added to optimize audit log queries:

#### 1. Composite Entity Index

```sql
CREATE INDEX ix_audit_log_entity ON audit_log (entity_type, entity_id);
```

**Purpose**: Fast lookup of audit history for specific entities  
**Use case**: "Show me all changes to Item #123"  
**Performance**: O(log n) lookups

#### 2. User Activity Index

```sql
CREATE INDEX ix_audit_log_user_id ON audit_log (user_id);
```

**Purpose**: Fast lookup of all actions by a user  
**Use case**: "Show me everything user John did"  
**Performance**: O(log n) lookups

#### 3. Approval Status Index

```sql
CREATE INDEX ix_audit_log_approval_status ON audit_log (approval_status);
```

**Purpose**: Fast lookup of pending AI suggestions  
**Use case**: "Show me all suggestions awaiting review"  
**Performance**: O(log n) lookups

### Index Performance Monitoring

Monitor index usage:

```sql
-- PostgreSQL index usage statistics
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename = 'audit_log';
```

### Index Maintenance

For optimal performance:

1. **Monitor index bloat** regularly
2. **REINDEX** if needed: `REINDEX TABLE audit_log;`
3. **VACUUM ANALYZE** after bulk operations
4. **Review query plans** for slow queries

---

## Security Best Practices

### 1. Secret Management

- ✅ Use environment variables for all secrets
- ✅ Generate strong SECRET_KEY values
- ✅ Rotate credentials regularly
- ✅ Use different credentials per environment
- ❌ Never commit `.env` files
- ❌ Never log sensitive values

### 2. Access Control

- ✅ Implement least privilege principle
- ✅ Use role-based access for sensitive operations
- ✅ Require authentication for all non-public endpoints
- ✅ Log all administrative actions
- ❌ Don't use default passwords
- ❌ Don't skip authentication checks

### 3. AI Operations

- ✅ Validate all AI outputs before applying
- ✅ Require manual review for low-confidence suggestions
- ✅ Log all AI operations with confidence scores
- ✅ Implement rate limiting on AI endpoints
- ❌ Don't auto-apply low-confidence suggestions
- ❌ Don't skip validation steps

### 4. Database Security

- ✅ Use parameterized queries (SQLAlchemy ORM)
- ✅ Implement proper transaction management
- ✅ Log all data modifications
- ✅ Regular backups
- ❌ Don't use string concatenation for queries
- ❌ Don't expose raw SQL errors to users

### 5. Error Handling

- ✅ Log all errors with context
- ✅ Implement retry logic for transient failures
- ✅ Graceful degradation when services unavailable
- ✅ User-friendly error messages
- ❌ Don't expose stack traces to end users
- ❌ Don't ignore error conditions

---

## Testing

### Running Security Tests

```bash
# Run all security enhancement tests
pytest tests/test_security_enhancements.py -v

# Run specific test categories
pytest tests/test_security_enhancements.py::TestRetryMechanism -v
pytest tests/test_security_enhancements.py::TestAuditLogging -v
pytest tests/test_security_enhancements.py::TestRoleBasedAccess -v
```

### Test Coverage

The security test suite covers:

- ✅ Retry mechanisms with exponential backoff
- ✅ Enhanced audit logging with pre/post states
- ✅ AI output validation
- ✅ Role-based access control
- ✅ Database rollback scenarios
- ✅ Concurrent task execution
- ✅ Error handling and logging

### Running All Tests

```bash
# Run complete test suite
pytest tests/ -v

# With coverage report
pytest tests/ --cov=src --cov-report=html
```

---

## Deployment Checklist

Before deploying to production:

- [ ] Set all environment variables in `.env`
- [ ] Generate secure SECRET_KEY
- [ ] Update database credentials
- [ ] Update S3/MinIO credentials
- [ ] Set `ENVIRONMENT=production`
- [ ] Enable `STRICT_CONFIG_VALIDATION=true`
- [ ] Run database migrations: `alembic upgrade head`
- [ ] Verify configuration: Run `validate_production_config()`
- [ ] Test role-based access controls
- [ ] Review audit log configuration
- [ ] Test Redis/RQ connectivity
- [ ] Verify AI confidence thresholds
- [ ] Run full test suite
- [ ] Review security logs
- [ ] Set up monitoring and alerts

---

## Support and Maintenance

### Monitoring

Monitor these key metrics:

1. **Failed job rate**: Track RQ job failures
2. **Retry attempts**: Monitor how often retries occur
3. **AI confidence distribution**: Track suggestion quality
4. **Pending reviews**: Monitor review queue size
5. **Audit log growth**: Track storage requirements

### Log Files

Important log locations:

- Application logs: Check for ERROR and WARNING messages
- Redis logs: Monitor queue health
- Database logs: Watch for slow queries
- Audit logs: Review in database `audit_log` table

### Troubleshooting

Common issues and solutions:

1. **Jobs failing repeatedly**
   - Check Redis connectivity
   - Verify AI service availability
   - Review error logs for patterns

2. **Slow audit queries**
   - Check index usage statistics
   - Run VACUUM ANALYZE
   - Consider archiving old audit logs

3. **Permission denied errors**
   - Verify user roles in database
   - Check role-based access implementation
   - Review authentication flow

---

## Version History

- **v2.0.0** (2026-01-20): Initial security enhancements
  - Environment variable configuration
  - Enhanced audit logging
  - Role-based access control
  - Redis retry mechanisms
  - AI validation improvements
  - Database index optimization
  - Comprehensive test coverage

---

For questions or issues, please refer to the main README.md or contact the development team.

## Beta Security & Hardening Extensions (Phase 1-5)
- **Settings Configuration Strictness**: Defaults such as `admin/admin` or `supersecretkey` configurations are forcefully blocked during production environments starting the runtime (`ENVIRONMENT=production`).
- **Dependencies Review & Upgrades**: Pinned dependencies using pip-tools and managed via Dependabot `ci.yml` scanning preventing supply chain poisoning attacks.
- **Throttling Abuse Vectors**: `slowapi` restricts users submitting thousands of AI ingestion processes concurrently per minute from overloading internal Redis caches or consuming GPU limits.
- **Graceful Failure Isolation**: The FastAPI frontend explicitly degrades on Background Job connection issues instead of crashing 500 routes if external task pipelines fail. Admins have specific privileged roles to review and requeue tasks natively from the DB.
