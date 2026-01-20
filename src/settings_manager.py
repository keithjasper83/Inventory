"""
SettingsManager: Dynamic configuration from database
Provides centralized access to system settings stored in DB
"""
from typing import Optional
from sqlalchemy.orm import Session
from src.models import SystemSetting


class SettingsManager:
    """Manage system settings from database"""
    
    @staticmethod
    def get(db: Session, key: str, default=None):
        """Get setting value by key"""
        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if setting:
            return setting.value
        return default
    
    @staticmethod
    def set(db: Session, key: str, value: str, description: str = ""):
        """Set or update setting"""
        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if setting:
            setting.value = value
            if description:
                setting.description = description
        else:
            setting = SystemSetting(key=key, value=value, description=description)
            db.add(setting)
        db.commit()
        return setting
    
    @staticmethod
    def get_all(db: Session):
        """Get all settings"""
        return db.query(SystemSetting).all()
