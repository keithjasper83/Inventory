import unittest
from unittest.mock import patch, MagicMock
from src.settings_manager import settings_manager, SettingsManager

class TestSettingsManager(unittest.TestCase):
    @patch("src.settings_manager.SessionLocal")
    def test_get_setting_found_in_db(self, mock_session_local):
        # Setup mock db session
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        # Setup mock setting returned from db
        mock_setting = MagicMock()
        mock_setting.value = "db_value"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_setting

        # Call get
        result = settings_manager.get("test_key")

        # Assertions
        self.assertEqual(result, "db_value")
        mock_db.close.assert_called_once()

    @patch("src.settings_manager.SessionLocal")
    def test_get_setting_not_found_default_provided(self, mock_session_local):
        # Setup mock db session
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        # Setup mock setting NOT returned from db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Call get with default
        result = settings_manager.get("test_key", default="provided_default")

        # Assertions
        self.assertEqual(result, "provided_default")
        mock_db.close.assert_called_once()

    @patch("src.settings_manager.SessionLocal")
    def test_get_setting_not_found_fallback_to_defaults(self, mock_session_local):
        # Setup mock db session
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        # Setup mock setting NOT returned from db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Ensure key is in _defaults
        test_key = "ai_confidence_threshold"
        expected_default = SettingsManager._defaults[test_key]

        # Call get without default
        result = settings_manager.get(test_key)

        # Assertions
        self.assertEqual(result, expected_default)
        mock_db.close.assert_called_once()
