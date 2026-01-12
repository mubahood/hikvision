"""
Event Model
Represents access control events from Hikvision devices
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import json


@dataclass
class Event:
    """Event entity representing an access control event"""
    
    # Primary key
    id: Optional[int] = None
    
    # Device information
    device_ip: str = ""
    device_id: str = ""
    mac_address: Optional[str] = None
    
    # Event details
    event_type: str = ""
    event_state: str = ""
    occur_time: Optional[datetime] = None
    
    # Access details
    door_no: Optional[str] = None
    door_name: Optional[str] = None
    verify_mode: Optional[str] = None
    
    # User information
    employee_no: Optional[str] = None
    name: Optional[str] = None
    card_no: Optional[str] = None
    user_type: Optional[str] = None
    
    # Additional fields
    serial_no: Optional[int] = None
    major_event: Optional[int] = None
    minor_event: Optional[int] = None
    channel_id: Optional[str] = None
    
    # Raw data storage
    raw_json: Optional[str] = None
    
    # Metadata
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create Event from dictionary"""
        # Handle datetime conversion
        occur_time = data.get('occur_time')
        if occur_time and isinstance(occur_time, str):
            try:
                occur_time = datetime.fromisoformat(occur_time.replace('Z', '+00:00'))
            except:
                occur_time = None
        
        created_at = data.get('created_at')
        if created_at and isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except:
                created_at = None
        
        return cls(
            id=data.get('id'),
            device_ip=data.get('device_ip', ''),
            device_id=data.get('device_id', ''),
            mac_address=data.get('mac_address'),
            event_type=data.get('event_type', ''),
            event_state=data.get('event_state', ''),
            occur_time=occur_time,
            door_no=data.get('door_no'),
            door_name=data.get('door_name'),
            verify_mode=data.get('verify_mode'),
            employee_no=data.get('employee_no'),
            name=data.get('name'),
            card_no=data.get('card_no'),
            user_type=data.get('user_type'),
            serial_no=data.get('serial_no'),
            major_event=data.get('major_event'),
            minor_event=data.get('minor_event'),
            channel_id=data.get('channel_id'),
            raw_json=data.get('raw_json'),
            created_at=created_at
        )
    
    @classmethod
    def from_device_event(cls, event_data: Dict[str, Any]) -> 'Event':
        """Create Event from device event payload"""
        raw_json = json.dumps(event_data) if event_data else None
        
        # Parse occur_time
        occur_time = None
        if event_data.get('occur_time'):
            try:
                occur_time = datetime.fromisoformat(
                    event_data['occur_time'].replace('Z', '+00:00')
                )
            except:
                occur_time = datetime.now()
        else:
            occur_time = datetime.now()
        
        return cls(
            device_ip=event_data.get('device_ip', ''),
            device_id=event_data.get('device_id', ''),
            mac_address=event_data.get('mac_address'),
            event_type=event_data.get('event_type', ''),
            event_state=event_data.get('event_state', ''),
            occur_time=occur_time,
            door_no=event_data.get('door_no'),
            door_name=event_data.get('door_name'),
            verify_mode=event_data.get('verify_mode'),
            employee_no=event_data.get('employee_no'),
            name=event_data.get('name'),
            card_no=event_data.get('card_no'),
            user_type=event_data.get('user_type'),
            serial_no=event_data.get('serial_no'),
            major_event=event_data.get('major_event'),
            minor_event=event_data.get('minor_event'),
            channel_id=event_data.get('channel_id'),
            raw_json=raw_json
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Event to dictionary"""
        return {
            'id': self.id,
            'device_ip': self.device_ip,
            'device_id': self.device_id,
            'mac_address': self.mac_address,
            'event_type': self.event_type,
            'event_state': self.event_state,
            'occur_time': self.occur_time.isoformat() if self.occur_time else None,
            'door_no': self.door_no,
            'door_name': self.door_name,
            'verify_mode': self.verify_mode,
            'employee_no': self.employee_no,
            'name': self.name,
            'card_no': self.card_no,
            'user_type': self.user_type,
            'serial_no': self.serial_no,
            'major_event': self.major_event,
            'minor_event': self.minor_event,
            'channel_id': self.channel_id,
            'raw_json': self.raw_json,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self) -> str:
        return f"Event(id={self.id}, type={self.event_type}, user={self.name or self.employee_no})"
