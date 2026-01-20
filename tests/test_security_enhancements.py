"""
Enhanced test coverage for security and stability improvements.
Tests for retry mechanisms, role-based access, and enhanced audit logging.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.tasks import (
    retry_with_backoff,
    create_audit_log,
    validate_ai_output,
    process_item_image,
    scrape_item_task,
    MAX_RETRIES
)
from src.models import Item, Media, User, AuditLog
from src.dependencies import require_role
from fastapi import HTTPException
import time


class TestRetryMechanism:
    """Test retry and backoff functionality for Redis/RQ jobs."""
    
    def test_retry_success_on_first_attempt(self):
        """Test that function succeeds on first attempt without retry."""
        call_count = 0
        
        @retry_with_backoff(max_retries=3)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_function()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_success_after_failures(self):
        """Test that function retries and eventually succeeds."""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, initial_backoff=0.1)
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"
        
        result = flaky_function()
        assert result == "success"
        assert call_count == 3
    
    def test_retry_exhausts_attempts(self):
        """Test that function fails after exhausting all retries."""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, initial_backoff=0.1)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Permanent failure")
        
        with pytest.raises(RuntimeError, match="Permanent failure"):
            always_fails()
        
        assert call_count == 3
    
    def test_retry_exponential_backoff(self):
        """Test that retry uses exponential backoff."""
        attempts = []
        
        @retry_with_backoff(max_retries=3, initial_backoff=0.1)
        def track_timing():
            attempts.append(time.time())
            if len(attempts) < 3:
                raise Exception("Retry me")
            return "success"
        
        result = track_timing()
        assert result == "success"
        assert len(attempts) == 3
        
        # Verify exponential backoff (approximate timing)
        if len(attempts) >= 3:
            delay1 = attempts[1] - attempts[0]
            delay2 = attempts[2] - attempts[1]
            # Second delay should be roughly 2x first delay
            assert delay2 > delay1


class TestAuditLogging:
    """Test enhanced audit logging with pre/post states."""
    
    @patch("src.tasks.SessionLocal")
    def test_create_audit_log_basic(self, mock_session_cls):
        """Test basic audit log creation."""
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        
        audit = create_audit_log(
            db=mock_db,
            entity_type="Item",
            entity_id=1,
            action="UPDATE",
            changes={"name": "new_name"},
            source="USER",
            user_id=1
        )
        
        assert audit.entity_type == "Item"
        assert audit.entity_id == 1
        assert audit.action == "UPDATE"
        assert audit.source == "USER"
        assert audit.user_id == 1
        mock_db.add.assert_called_once()
    
    @patch("src.tasks.SessionLocal")
    def test_create_audit_log_with_states(self, mock_session_cls):
        """Test audit log creation with before/after states."""
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        
        before = {"name": "old_name", "value": 10}
        after = {"name": "new_name", "value": 20}
        
        audit = create_audit_log(
            db=mock_db,
            entity_type="Item",
            entity_id=1,
            action="UPDATE",
            changes={"name": "changed"},
            source="AI_GENERATED",
            confidence=85,
            before_state=before,
            after_state=after
        )
        
        assert audit.changes["before"] == before
        assert audit.changes["after"] == after
        assert audit.confidence == 85
        assert audit.approval_status == "pending"
    
    @patch("src.tasks.SessionLocal")
    @patch("src.tasks.settings")
    def test_audit_log_approval_status(self, mock_settings, mock_session_cls):
        """Test automatic approval status based on confidence."""
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        mock_settings.AI_AUTO_APPLY_CONFIDENCE = 0.95
        mock_settings.AI_MANUAL_REVIEW_THRESHOLD = 0.80
        
        # High confidence - auto approved
        audit_high = create_audit_log(
            db=mock_db,
            entity_type="Item",
            entity_id=1,
            action="SUGGEST",
            changes={},
            source="AI_SCRAPED",
            confidence=98
        )
        assert audit_high.approval_status == "auto_approved"
        
        # Medium confidence - pending
        audit_medium = create_audit_log(
            db=mock_db,
            entity_type="Item",
            entity_id=2,
            action="SUGGEST",
            changes={},
            source="AI_GENERATED",
            confidence=85
        )
        assert audit_medium.approval_status == "pending"
        
        # Low confidence - needs review
        audit_low = create_audit_log(
            db=mock_db,
            entity_type="Item",
            entity_id=3,
            action="SUGGEST",
            changes={},
            source="AI_GENERATED",
            confidence=70
        )
        assert audit_low.approval_status == "needs_review"


class TestAIValidation:
    """Test AI output validation."""
    
    def test_validate_valid_string(self):
        """Test validation of valid string data."""
        assert validate_ai_output("valid string", "test_field", str) is True
    
    def test_validate_none(self):
        """Test validation of None values."""
        assert validate_ai_output(None, "test_field") is False
    
    def test_validate_wrong_type(self):
        """Test validation of wrong type."""
        assert validate_ai_output(123, "test_field", str) is False
    
    def test_validate_empty_string(self):
        """Test validation of empty strings."""
        assert validate_ai_output("", "test_field") is False
    
    def test_validate_empty_list(self):
        """Test validation of empty lists."""
        assert validate_ai_output([], "test_field") is False
    
    def test_validate_valid_dict(self):
        """Test validation of valid dictionaries."""
        assert validate_ai_output({"key": "value"}, "test_field", dict) is True
    
    def test_validate_empty_dict(self):
        """Test validation of empty dictionaries."""
        assert validate_ai_output({}, "test_field") is False


class TestRoleBasedAccess:
    """Test role-based access control."""
    
    def test_user_has_role_exact_match(self):
        """Test user has exact role match."""
        user = User(id=1, username="test", password_hash="hash", role="admin")
        assert user.has_role("admin") is True
    
    def test_user_has_role_hierarchy(self):
        """Test user has higher role in hierarchy."""
        user = User(id=1, username="test", password_hash="hash", role="admin")
        assert user.has_role("user") is True
        assert user.has_role("reviewer") is True
    
    def test_user_lacks_role(self):
        """Test user lacks required role."""
        user = User(id=1, username="test", password_hash="hash", role="user")
        assert user.has_role("admin") is False
        assert user.has_role("reviewer") is False
    
    def test_reviewer_has_user_role(self):
        """Test reviewer has user privileges."""
        user = User(id=1, username="test", password_hash="hash", role="reviewer")
        assert user.has_role("user") is True
        assert user.has_role("reviewer") is True
        assert user.has_role("admin") is False


class TestDatabaseRollback:
    """Test database rollback scenarios."""
    
    @patch("src.tasks.SessionLocal")
    @patch("src.tasks.storage")
    @patch("src.tasks.ai_client")
    def test_process_item_rollback_on_error(self, mock_ai, mock_storage, mock_session_cls):
        """Test that database rolls back on processing errors."""
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        
        item = Item(id=1, name=None, is_draft=True, data={}, pending_changes={})
        media = Media(id=1, s3_key="test/key", type="image")
        
        # Return item and media for each retry attempt (MAX_RETRIES * 2 calls)
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            item, media,  # First attempt
            item, media,  # Second attempt  
            item, media   # Third attempt
        ][:MAX_RETRIES * 2]
        
        # Simulate storage error
        mock_storage.s3_client.download_fileobj.side_effect = Exception("S3 error")
        
        with pytest.raises(Exception):
            process_item_image(1, 1)
        
        # Verify rollback was called (at least once, possibly more due to retries)
        assert mock_db.rollback.called
        assert mock_db.close.called


class TestConcurrentTasks:
    """Test multi-task concurrency scenarios."""
    
    @patch("src.tasks.SessionLocal")
    @patch("src.tasks.storage")
    @patch("src.tasks.ai_client")
    @patch("src.tasks.Image")
    def test_concurrent_processing_different_items(
        self, mock_image, mock_ai, mock_storage, mock_session_cls
    ):
        """Test processing multiple items concurrently."""
        # Create separate DB sessions for each task
        mock_db1 = MagicMock()
        mock_db2 = MagicMock()
        mock_session_cls.side_effect = [mock_db1, mock_db2]
        
        item1 = Item(id=1, name=None, is_draft=True, data={}, pending_changes={})
        media1 = Media(id=1, s3_key="test/key1", type="image")
        
        item2 = Item(id=2, name=None, is_draft=True, data={}, pending_changes={})
        media2 = Media(id=2, s3_key="test/key2", type="image")
        
        mock_db1.query.return_value.filter.return_value.first.side_effect = [item1, media1]
        mock_db2.query.return_value.filter.return_value.first.side_effect = [item2, media2]
        
        # Mock storage and AI
        mock_storage.bucket_media = "test-bucket"
        mock_storage.s3_client.download_fileobj = MagicMock()
        
        mock_img_instance = MagicMock()
        mock_img_instance.format = "JPEG"
        mock_image.open.return_value = mock_img_instance
        
        mock_ai.ocr_image = AsyncMock(return_value={"text": "Item 1", "confidence": 0.99})
        mock_ai.identify_resistor = AsyncMock(return_value={"is_resistor": False})
        
        # Process first item
        process_item_image(1, 1)
        
        # Mock for second item
        mock_ai.ocr_image = AsyncMock(return_value={"text": "Item 2", "confidence": 0.99})
        
        # Process second item
        process_item_image(2, 2)
        
        # Verify both sessions were committed and closed
        mock_db1.commit.assert_called()
        mock_db1.close.assert_called()
        mock_db2.commit.assert_called()
        mock_db2.close.assert_called()


class TestErrorHandlingAndLogging:
    """Test error handling and logging in tasks."""
    
    @patch("src.tasks.SessionLocal")
    @patch("src.tasks.logger")
    def test_scrape_task_logs_missing_item(self, mock_logger, mock_session_cls):
        """Test that missing items are logged properly."""
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        scrape_item_task(999)
        
        mock_logger.error.assert_called()
        assert "not found" in str(mock_logger.error.call_args)
    
    @patch("src.tasks.SessionLocal")
    @patch("src.tasks.logger")
    def test_scrape_task_logs_no_query_text(self, mock_logger, mock_session_cls):
        """Test that items without query text are logged."""
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        
        item = Item(id=1, name=None, is_draft=True, data={}, pending_changes={})
        mock_db.query.return_value.filter.return_value.first.return_value = item
        
        scrape_item_task(1)
        
        mock_logger.warning.assert_called()
        assert "No text available" in str(mock_logger.warning.call_args)
