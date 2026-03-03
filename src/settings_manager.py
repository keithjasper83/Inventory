from sqlalchemy.orm import Session
from src.models import SystemSetting
from src.database import SessionLocal
import json

class SettingsManager:
    _defaults = {
        "ai_confidence_threshold": 0.95,
        "scrape_timeout": 60,
        "presigned_url_expiry": 3600,
        "rq_retry_max": 3
    }

    def get(self, key: str, default=None):
        db = SessionLocal()
        try:
            setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
            if setting:
                return setting.value
            return default if default is not None else self._defaults.get(key)
        finally:
            db.close()

    def set(self, key: str, value):
        db = SessionLocal()
        try:
            setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
            if not setting:
                setting = SystemSetting(key=key, value=value)
                db.add(setting)
            else:
                setting.value = value
            db.commit()
        finally:
            db.close()

    def get_all(self):
        db = SessionLocal()
        try:
            # Start with a copy of defaults
            settings = self._defaults.copy()

            # Fetch all overrides from DB that exist in defaults
            overrides = db.query(SystemSetting).filter(SystemSetting.key.in_(self._defaults.keys())).all()
            for setting in overrides:
                settings[setting.key] = setting.value

            return settings
        finally:
            db.close()

settings_manager = SettingsManager()
