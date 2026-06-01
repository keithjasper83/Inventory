from sqlalchemy.orm import Session
from src.models import SystemSetting
from src.database import SessionLocal
import json
import time


class SettingsManager:
    _defaults = {
        "ai_confidence_threshold": 0.95,
        "scrape_timeout": 60,
        "presigned_url_expiry": 3600,
        "rq_retry_max": 3,
    }

    def __init__(self, ttl: int = 60):
        self._cache = {}
        self._cache_time = {}
        self.ttl = ttl

    def get(self, key: str, default=None):
        now = time.time()
        if key in self._cache and (now - self._cache_time.get(key, 0)) < self.ttl:
            return self._cache[key]

        db = SessionLocal()
        try:
            setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
            if setting:
                val = setting.value
            else:
                val = default if default is not None else self._defaults.get(key)

            self._cache[key] = val
            self._cache_time[key] = now
            return val
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

            self._cache[key] = value
            self._cache_time[key] = time.time()
        finally:
            db.close()

    def get_all(self):
        db = SessionLocal()
        try:
            # Start with a copy of defaults
            settings = self._defaults.copy()

            # Fetch all overrides from DB that exist in defaults
            # Memory note suggests querying (SystemSetting.key, SystemSetting.value) directly
            overrides = (
                db.query(SystemSetting.key, SystemSetting.value)
                .filter(SystemSetting.key.in_(self._defaults.keys()))
                .all()
            )

            override_dict = dict(overrides)
            settings.update(override_dict)

            now = time.time()
            for k, v in settings.items():
                self._cache[k] = v
                self._cache_time[k] = now

            return settings
        finally:
            db.close()


settings_manager = SettingsManager()
