import pytest
from unittest.mock import patch
from src.config import Settings, validate_production_config, settings

def test_validate_production_config_with_default_admin_password():
    with patch('src.config.settings') as mock_settings:
        mock_settings.TEST_MODE = False
        mock_settings.SECRET_KEY = "secure_key_123"
        mock_settings.DATABASE_URL = "postgresql+psycopg://user:pass@localhost/db"
        mock_settings.S3_ACCESS_KEY = "secure_access"
        mock_settings.S3_SECRET_KEY = "secure_secret"
        mock_settings.ADMIN_PASSWORD = "admin"

        with pytest.raises(ValueError) as excinfo:
            validate_production_config()

        assert "ADMIN_PASSWORD is using default/insecure value" in str(excinfo.value)

def test_validate_production_config_with_short_admin_password():
    with patch('src.config.settings') as mock_settings:
        mock_settings.TEST_MODE = False
        mock_settings.SECRET_KEY = "secure_key_123"
        mock_settings.DATABASE_URL = "postgresql+psycopg://user:pass@localhost/db"
        mock_settings.S3_ACCESS_KEY = "secure_access"
        mock_settings.S3_SECRET_KEY = "secure_secret"
        mock_settings.ADMIN_PASSWORD = "short"

        with pytest.raises(ValueError) as excinfo:
            validate_production_config()

        assert "ADMIN_PASSWORD is using default/insecure value" in str(excinfo.value)

def test_validate_production_config_success():
    with patch('src.config.settings') as mock_settings:
        mock_settings.TEST_MODE = False
        mock_settings.SECRET_KEY = "secure_key_123"
        mock_settings.DATABASE_URL = "postgresql+psycopg://user:pass@localhost/db"
        mock_settings.S3_ACCESS_KEY = "secure_access"
        mock_settings.S3_SECRET_KEY = "secure_secret"
        mock_settings.ADMIN_PASSWORD = "secure_password_123"

        # Should not raise an exception
        validate_production_config()
