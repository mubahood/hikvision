"""
Config Controller
Handles system configuration operations
"""

from typing import Dict, Any, Optional
from models.config import Config
from database import get_db


class ConfigController:
    """Controller for configuration operations"""
    
    def __init__(self):
        self.db = get_db()
    
    def get_config(self, key: str, default: str = '') -> str:
        """Get a single config value"""
        config = self.db.get_config()
        return config.get(key, default)
    
    def get_all_config(self) -> Dict[str, str]:
        """Get all configuration values"""
        return self.db.get_config()
    
    def set_config(self, key: str, value: str) -> bool:
        """Set a configuration value"""
        return self.db.update_config(key, value)
    
    def set_multiple(self, configs: Dict[str, str]) -> bool:
        """Set multiple configuration values"""
        success = True
        for key, value in configs.items():
            if not self.db.update_config(key, value):
                success = False
        return success
    
    # Convenience methods for common settings
    def get_device_ip(self) -> str:
        return self.get_config('device_ip', '192.168.1.128')
    
    def get_device_user(self) -> str:
        return self.get_config('device_user', 'admin')
    
    def get_device_id(self) -> str:
        return self.get_config('device_id', 'door1')
    
    def get_log_level(self) -> str:
        return self.get_config('log_level', 'INFO')
    
    def get_data_retention_days(self) -> int:
        return int(self.get_config('data_retention_days', '90'))
    
    def is_auto_backup_enabled(self) -> bool:
        return self.get_config('auto_backup_enabled', 'true').lower() == 'true'
