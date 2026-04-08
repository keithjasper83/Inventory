# Jules Inventory Platform - TODO for V1

**Last Updated**: 2026-01-21  
**Status**: Post-Code Review  
**Version**: 1.0.0-beta

This document tracks outstanding tasks, known issues, and improvements needed before and after V1 release.

---

## 🔴 Critical - Must Fix Before V1 Release

### Security

- [ ] **Remove jules.db from repository** - SQLite database file is tracked in git (77KB)
  - Action: `git rm jules.db` and add `*.db` to .gitignore (already in .gitignore but file was committed before)
  - Risk: Database may contain sensitive data or test data that shouldn't be in repo

### Testing

- [ ] **Fix failing audit log tests** (9 test failures in test_security_enhancements.py)
  - `test_create_audit_log_basic` - audit.user_id is None, expected 1
  - `test_create_audit_log_with_states` - KeyError: 'before' (changes dict format mismatch)
  - `test_audit_log_approval_status` - AttributeError: module 'src.tasks' does not have attribute 'settings'
  - `test_validate_none` - TypeError: validate_ai_output() signature mismatch
  - `test_validate_wrong_type` - Assertion failure
  - `test_validate_empty_string` - TypeError: validate_ai_output() signature mismatch
  - `test_validate_empty_list` - TypeError: validate_ai_output() signature mismatch
  - `test_validate_empty_dict` - Test cut off, likely similar issue
  - `test_concurrent_processing_different_items` - Unknown failure
  - `test_scrape_task_logs_missing_item` - Unknown failure
  - `test_scrape_task_logs_no_query_text` - Unknown failure
  - **Action**: Review and fix `create_audit_log()` function signature and implementation in tasks.py
  - **Action**: Review and fix `validate_ai_output()` function signature in tasks.py

- [ ] **Run full test suite** - Only 4/5 test files verified working
  - Passing: test_api.py, test_counting_plus.py, test_tasks.py
  - Partially passing: test_security_enhancements.py (13/22 tests pass)
  - Status unknown: Need to run all tests together

---

## 🟡 High Priority - Should Fix Before V1 Release

### Code Quality

- [ ] **Fix inconsistent error handling in scrape_item_task()** (src/tasks.py:179-190)
  - Uses `db = next(get_db())` pattern incorrectly
  - Should use `db = SessionLocal()` with try/except/rollback/finally
  - Missing proper rollback on error
  - Reference: process_item_image() has correct pattern

- [ ] **Replace remaining print statements with logging**
  - Found in: src/storage.py:52 (possibly more not found)
  - Action: Search all .py files for `print(` and replace with logger calls

- [ ] **Review SQL injection risk in search fallback** (src/routers/search.py:36)
  - Currently: `Item.name.ilike(f"%{query}%")`
  - SQLAlchemy protects against injection but pattern is fragile
  - Action: Use explicit parameter binding or string concatenation
  - Suggestion: `Item.name.ilike("%" + query + "%")`

### Configuration & Deployment

- [ ] **Add production config validation to startup**
  - Implemented: `validate_production_config()` in src/config.py
  - Not called: Need to add call in src/main.py startup
  - Action: Add startup check when ENVIRONMENT=production

- [ ] **Document .env.production.example**
  - File renamed from .env.production
  - Update references in DEPLOYMENT.md and README.md
  - Ensure deployment guides reference .env.production.example

### Database

- [ ] **Verify database migrations**
  - Migration a1b2c3d4e5f6 adds role and audit fields
  - Verify migration applies cleanly on fresh database
  - Test both upgrade and downgrade paths
  - Action: `alembic upgrade head` on clean DB

- [ ] **Test SQLite compatibility**
  - Code has SQLite fallback logic (models.py:17-18)
  - Test suite may run in SQLite mode (TEST_MODE env var)
  - Verify FTS works in PostgreSQL mode
  - Document SQLite limitations clearly

---

## 🟢 Medium Priority - Nice to Have Before V1

### Documentation

- [ ] **Update SECURITY.md examples** - Some code examples reference features now implemented
  - Update line references if code moved
  - Verify all code examples compile and work
  - Add examples for `require_admin`, `require_reviewer` usage

- [ ] **Update README.md**
  - Reference .env.production.example not .env.production
  - Verify all setup instructions are accurate
  - Test quick-start.sh script works

- [ ] **Create CHANGELOG.md** - Track changes between versions
  - Document v1.0.0-beta features
  - List breaking changes from earlier versions
  - Include upgrade instructions

- [ ] **Add API documentation** - FastAPI auto-generates OpenAPI docs
  - Verify /docs endpoint works
  - Add descriptions to all endpoints
  - Include request/response examples
  - Document authentication requirements

### Testing

- [ ] **Add integration tests** - Current tests are mostly unit tests
  - Test complete workflows (create item → upload photo → AI processing)
  - Test search functionality end-to-end
  - Test approval workflows
  - Test role-based access across multiple endpoints

- [ ] **Add performance tests**
  - Test with 1000+ items
  - Test search performance with large dataset
  - Test bulk operations performance
  - Measure background job processing time

- [ ] **Test coverage analysis**
  - Run pytest with --cov flag
  - Generate coverage report
  - Target: 80%+ coverage on core modules
  - Identify untested code paths

### Code Quality

- [ ] **Add type checking with mypy**
  - Create mypy.ini configuration
  - Run mypy on all src/ files
  - Fix type hint errors
  - Add to CI/CD pipeline

- [ ] **Add linting with ruff or flake8**
  - Choose linter (ruff recommended for speed)
  - Create configuration file
  - Fix linting errors
  - Add to CI/CD pipeline

- [ ] **Code formatting with black**
  - Run black on all Python files
  - Add black configuration to pyproject.toml
  - Document code style in CONTRIBUTING.md

---

## 🔵 Low Priority - Post-V1 (V1.1 or V2.0)

### Features from VERSION_2_ROADMAP.md

#### Phase 1: Extended Bulk Operations (Q2 2026)
- [ ] Extend Counting+ to capacitors (read markings)
- [ ] Extend Counting+ to ICs (text markings)
- [ ] Extend Counting+ to SMD components
- [ ] CSV/Excel import with field mapping
- [ ] CSV/Excel export for inventory analysis
- [ ] Bulk update from spreadsheet
- [ ] Batch operations UI (select multiple items)
- [ ] Bulk move to location
- [ ] Bulk edit attributes
- [ ] Bulk delete with confirmation

#### Phase 2: AI-Assisted Workflow (Q3 2026)
- [ ] Project parts planning (suggest projects from stock)
- [ ] Parts reserve system (reserve for specific projects)
- [ ] Usage-based stocking recommendations
- [ ] Project failure analysis (track delays)
- [ ] Barcode generation for items
- [ ] QR code generation with URLs
- [ ] Batch scanning mode
- [ ] USB barcode scanner support

#### Phase 3: Storage Optimization (Q4 2026)
- [ ] AI suggests optimal storage layout
- [ ] Category-based organization
- [ ] Smart bin allocation
- [ ] Storage capacity planning

### Technical Debt

- [ ] **Refactor AI client** - Consolidate AI service calls
  - Create unified AI client interface
  - Handle Jarvis unavailability gracefully
  - Add AI service health checks
  - Cache AI responses when appropriate

- [ ] **Refactor media handling** - Simplify thumbnail generation
  - Move thumbnail logic to dedicated service
  - Support additional image formats
  - Add image optimization
  - Consider WebP format for smaller files

- [ ] **Improve error messages** - Make errors more user-friendly
  - Add user-facing error codes
  - Provide actionable error messages
  - Log detailed errors, show simple messages to users

- [ ] **Session management improvements**
  - Add session timeout
  - Add "remember me" option
  - Add session invalidation on password change
  - Add active session management

### Performance

- [ ] **Database query optimization**
  - Analyze slow queries with EXPLAIN
  - Add missing indexes based on query patterns
  - Consider query caching for read-heavy operations
  - Profile database performance under load

- [ ] **Background job optimization**
  - Monitor job queue depth
  - Optimize slow jobs (OCR, AI processing)
  - Consider job prioritization
  - Add job timeout handling

- [ ] **Frontend performance**
  - Minify CSS/JS
  - Enable gzip compression
  - Add browser caching headers
  - Lazy load images
  - Consider PWA service worker

### Monitoring & Observability

- [ ] **Structured logging improvements**
  - Add correlation IDs to all logs
  - Log to file in production
  - Add log rotation
  - Consider ELK stack integration

- [ ] **Metrics collection**
  - Add Prometheus metrics
  - Track request rate, latency, errors
  - Monitor background job metrics
  - Track AI service success/failure rates

- [ ] **Alerting**
  - Alert on high error rates
  - Alert on database connection failures
  - Alert on Redis connection failures
  - Alert on disk space low
  - Alert on background job queue backlog

### Security Enhancements

- [ ] **Rate limiting** - Prevent abuse
  - Add rate limits on login endpoint
  - Add rate limits on search endpoint
  - Add rate limits on API endpoints
  - Use slowapi or similar library

- [ ] **Security headers** - Add security headers to responses
  - Content-Security-Policy
  - X-Frame-Options
  - X-Content-Type-Options
  - Strict-Transport-Security
  - Use secure_headers middleware

- [ ] **CORS configuration** - Configure CORS properly
  - Document CORS requirements
  - Add CORS configuration to settings
  - Test CORS in production

- [ ] **Audit log retention** - Add retention policy
  - Define retention period (e.g., 1 year)
  - Add automated cleanup job
  - Add audit log export before cleanup
  - Document retention policy

### User Experience

- [ ] **Mobile app** - Native mobile app
  - Consider React Native or Flutter
  - Focus on camera capture workflow
  - Offline mode support
  - Sync when online

- [ ] **Dark mode** - Add dark mode theme
  - Add theme toggle
  - Store preference in session/user profile
  - Use CSS variables for theming

- [ ] **Keyboard shortcuts** - Power user features
  - Document shortcuts in help
  - Add shortcuts for common actions
  - Consider vim-like navigation

- [ ] **Improved search** - Enhanced search features
  - Search suggestions/autocomplete
  - Search filters (by category, location, date)
  - Search history
  - Saved searches

### DevOps & Operations

- [ ] **CI/CD pipeline** - Automated testing and deployment
  - GitHub Actions or similar
  - Run tests on PR
  - Run linters on PR
  - Run security scans on PR
  - Deploy to staging automatically
  - Deploy to production with approval

- [ ] **Database backups** - Automated backup strategy
  - Daily PostgreSQL dumps
  - S3/MinIO bucket backups
  - Test restore procedure
  - Document backup/restore process
  - Retention policy (keep 30 days)

- [ ] **Monitoring & Alerting setup**
  - Set up Prometheus/Grafana
  - Create dashboards for key metrics
  - Configure alerting rules
  - Document on-call procedures

- [ ] **Staging environment**
  - Create staging deployment
  - Mirror production configuration
  - Test deployments on staging first
  - Automate staging deploys from main branch

---

## 📊 Testing Status Summary

### Test Files
- ✅ `tests/test_api.py` - Status unknown, need to verify
- ✅ `tests/test_counting_plus.py` - Status unknown, need to verify
- ⚠️ `tests/test_security_enhancements.py` - 13/22 passing (59%)
- ✅ `tests/test_tasks.py` - Status unknown, need to verify
- ❓ `tests/conftest.py` - Fixtures file

### Test Coverage by Feature
- ✅ **RBAC (Role-Based Access Control)** - 4/4 tests passing
  - test_user_has_role_exact_match
  - test_user_has_role_hierarchy
  - test_user_lacks_role
  - test_reviewer_has_user_role
- ✅ **Retry Mechanism** - 4/4 tests passing
  - test_retry_success_on_first_attempt
  - test_retry_success_after_failures
  - test_retry_exhausts_attempts
  - test_retry_exponential_backoff
- ❌ **Audit Logging** - 0/3 tests passing (need fixes)
- ❌ **AI Validation** - 2/7 tests passing (need fixes)
- ✅ **Database Rollback** - 1/1 tests passing
- ❌ **Concurrent Processing** - 0/1 tests passing
- ❌ **Error Handling & Logging** - 0/2 tests passing

---

## 🎯 Code Review Findings Summary

### Issues Fixed (7 Critical/High)
1. ✅ RBAC features documented but not implemented - **FIXED**
2. ✅ Model/Migration mismatch for User.role - **FIXED**
3. ✅ Model/Migration mismatch for AuditLog enhanced fields - **FIXED**
4. ✅ Missing require_role, require_admin, require_reviewer functions - **FIXED**
5. ✅ Missing validate_production_config() function - **FIXED**
6. ✅ Logger not imported in tasks.py - **FIXED**
7. ✅ .env.production tracked in git - **FIXED** (renamed to .env.production.example)

### Issues Remaining (3)
1. ⚠️ Test failures in audit logging (3 tests)
2. ⚠️ Test failures in AI validation (5 tests)
3. ⚠️ Inconsistent error handling in scrape_item_task()

---

## 📝 Notes

### Known Limitations (By Design - Not Bugs)
These are intentional design decisions documented in VERSION_1_FEATURES.md:

1. **Jarvis AI Service** - Optional, not required for core functionality
2. **SQLite Mode** - Limited FTS capability (PostgreSQL recommended)
3. **Single Admin** - Only one admin account seeded by default
4. **No SSO** - Username/password only (not needed for personal workshop)
5. **Resistors Only for Counting+** - Other components in v2.0
6. **English Only** - UI and docs in English (not a priority)
7. **Single Organization** - No multi-tenancy (not needed)

### Breaking Changes Since Earlier Versions
- Added `role` column to `users` table (requires migration)
- Added enhanced audit fields to `audit_log` table (requires migration)
- Renamed `.env.production` to `.env.production.example`
- Updated `.gitignore` to exclude all `.env.*` files

### Upgrade Path from Pre-RBAC Version
1. Pull latest code
2. Run `alembic upgrade head` to add role and audit columns
3. Copy `.env.production.example` to `.env.production` if using
4. Update environment variables if needed
5. Restart application

---

## 🏁 Definition of Done for V1.0.0 Release

Before declaring V1.0.0 stable (no longer beta):

### Code Quality
- [ ] All tests passing (22/22 security tests + others)
- [ ] No critical or high priority issues remaining
- [ ] Code review findings addressed
- [ ] Linting passes with no errors
- [ ] Type checking passes (if mypy added)

### Security
- [ ] CodeQL scan shows 0 vulnerabilities
- [ ] No hardcoded secrets
- [ ] Production config validation working
- [ ] RBAC enforced on all sensitive endpoints
- [ ] Audit logging capturing all changes

### Documentation
- [ ] All docs accurate and up-to-date
- [ ] API documentation complete
- [ ] Deployment guide tested and working
- [ ] Quick-start script verified working
- [ ] CHANGELOG.md created

### Performance
- [ ] Application handles 1000+ items smoothly
- [ ] Search responds in < 200ms
- [ ] Background jobs process without blocking
- [ ] No memory leaks detected

### Deployment
- [ ] Docker deployment tested
- [ ] Migrations tested on clean database
- [ ] Backup/restore procedure documented and tested
- [ ] Staging environment deployed
- [ ] Production deployment successful

---

**End of TODO.md**
