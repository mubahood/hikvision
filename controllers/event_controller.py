"""
Event Controller
Handles business logic for events
"""

import os
import requests
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from models.event import Event
from database import get_db
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class EventController:
    """Controller for event operations"""
    
    def __init__(self):
        self.db = get_db()
    
    def create_event(self, event_data: Dict[str, Any]) -> Optional[int]:
        """Create a new event from device data"""
        event = Event.from_device_event(event_data)
        event_dict = event.to_dict()
        
        # Remove None id for insert
        if 'id' in event_dict:
            del event_dict['id']
        
        return self.db.insert_event(event_dict)
    
    def get_event(self, event_id: int) -> Optional[Event]:
        """Get a single event by ID"""
        events = self.db.get_events(limit=1, filters={'id': event_id})
        if events:
            return Event.from_dict(events[0])
        return None
    
    def get_events(
        self,
        limit: int = 100,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[str] = None,
        employee_no: Optional[str] = None
    ) -> List[Event]:
        """Get events with optional filters"""
        filters = {}
        
        if start_date:
            filters['start_date'] = start_date
        if end_date:
            filters['end_date'] = end_date
        if event_type and event_type != 'All':
            filters['event_type'] = event_type
        if employee_no:
            filters['employee_no'] = employee_no
        
        events_data = self.db.get_events(limit=limit, offset=offset, filters=filters)
        return [Event.from_dict(e) for e in events_data]
    
    def get_events_as_dicts(
        self,
        limit: int = 100,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get events as dictionaries (for dataframe)"""
        filters = {}
        
        if start_date:
            filters['start_date'] = start_date
        if end_date:
            filters['end_date'] = end_date
        if event_type and event_type != 'All':
            filters['event_type'] = event_type
        
        return self.db.get_events(limit=limit, offset=offset, filters=filters)
    
    def get_event_count(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[str] = None
    ) -> int:
        """Get total event count with optional filters"""
        filters = {}
        
        if start_date:
            filters['start_date'] = start_date
        if end_date:
            filters['end_date'] = end_date
        if event_type and event_type != 'All':
            filters['event_type'] = event_type
        
        return self.db.get_event_count(filters=filters)
    
    def get_today_stats(self) -> Dict[str, Any]:
        """Get today's statistics"""
        return self.db.get_today_stats()
    
    def get_hourly_stats(self, days: int = 1) -> List[Dict[str, Any]]:
        """Get hourly event statistics"""
        return self.db.get_hourly_stats(days=days)
    
    def get_top_users(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top users by access count"""
        return self.db.get_top_users(limit=limit)
    
    def get_recent_events(self, limit: int = 10) -> List[Event]:
        """Get most recent events"""
        events_data = self.db.get_events(limit=limit)
        return [Event.from_dict(e) for e in events_data]
    
    def delete_old_events(self, days: int = 90) -> int:
        """Delete events older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        conn = None
        cursor = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM events WHERE occur_time < %s", (cutoff_date,))
            deleted = cursor.rowcount
            return deleted
        except Exception as e:
            logger.error(f"Error deleting old events: {e}")
            return 0
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def delete_event(self, event_id: int) -> bool:
        """Delete a single event by ID"""
        conn = None
        cursor = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM events WHERE id = %s", (event_id,))
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting event {event_id}: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def delete_events_by_ids(self, event_ids: list) -> int:
        """Delete multiple events by IDs"""
        if not event_ids:
            return 0
        conn = None
        cursor = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            placeholders = ','.join(['%s'] * len(event_ids))
            cursor.execute(f"DELETE FROM events WHERE id IN ({placeholders})", tuple(event_ids))
            return cursor.rowcount
        except Exception as e:
            logger.error(f"Error deleting events by IDs: {e}")
            return 0
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def delete_all_events(self) -> int:
        """Delete all events"""
        conn = None
        cursor = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM events")
            return cursor.rowcount
        except Exception as e:
            logger.error(f"Error deleting all events: {e}")
            return 0
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def export_events_csv(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> str:
        """Export events to CSV format"""
        events = self.get_events_as_dicts(
            limit=10000,
            start_date=start_date,
            end_date=end_date
        )
        
        if not events:
            return ""
        
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=events[0].keys())
        writer.writeheader()
        writer.writerows(events)
        
        return output.getvalue()
    
    def get_pending_sync_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events pending sync"""
        return self.db.get_pending_sync_events(limit=limit)
    
    def get_sync_stats(self) -> Dict[str, int]:
        """Get sync statistics"""
        return self.db.get_sync_stats()
    
    def sync_event_to_webhook(self, event_id: int, webhook_url: str, 
                               api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Sync a single event to webhook
        
        Returns:
            Dict with 'success', 'message', and optionally 'response'
        """
        # Get event data
        events = self.db.get_events(limit=1, filters={})
        event_data = None
        for e in self.db.get_events(limit=1000):
            if e['id'] == event_id:
                event_data = e
                break
        
        if not event_data:
            return {'success': False, 'message': f'Event {event_id} not found'}
        
        # Prepare webhook payload in the same format as batch sync
        payload = {
            'event_serial': event_data.get('serial_no'),
            'employee_no': str(event_data.get('employee_no')) if event_data.get('employee_no') else None,
            'employee_name': event_data.get('name'),
            'event_time': str(event_data.get('occur_time')),
            'door_name': event_data.get('door_no'),
            'verification_method': event_data.get('verify_mode'),
            'device_name': event_data.get('device_id'),
            'device_ip': event_data.get('device_ip'),
            'raw_data': {
                'event_id': event_data['id'],
                'event_type': event_data.get('event_type'),
                'attendance_status': event_data.get('attendance_status'),
                'card_no': event_data.get('card_no')
            }
        }
        
        # Wrap in events array for batch endpoint (like working batch sync does)
        batch_payload = {'events': [payload]}
        
        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'HikvisionBridge/1.0'
        }
        if api_key:
            headers['X-API-Key'] = api_key
        
        try:
            response = requests.post(
                webhook_url,
                json=batch_payload,  # Send as batch format like working methods
                timeout=10,
                headers=headers
            )
            
            if response.status_code == 200:
                # Parse response to check if it was processed (like batch sync does)
                try:
                    resp_data = response.json()
                    # Success if processed > 0 OR duplicates > 0 (already synced before)
                    if resp_data.get('stats', {}).get('processed', 0) > 0 or resp_data.get('stats', {}).get('duplicates', 0) > 0:
                        # Update sync status
                        self.db.update_sync_status(
                            event_id, 
                            'synced', 
                            response=response.text[:500] if response.text else 'OK'
                        )
                        return {
                            'success': True, 
                            'message': 'Event synced successfully',
                            'response': response.text[:200]
                        }
                    else:
                        # Had errors in processing
                        error_msg = f"Processing errors: {resp_data.get('errors', 'Unknown')}"
                        self.db.update_sync_status(event_id, 'failed', error=error_msg[:500])
                        return {'success': False, 'message': error_msg}
                except Exception as parse_err:
                    # If can't parse, just mark as synced since status was 200
                    self.db.update_sync_status(
                        event_id, 
                        'synced', 
                        response=response.text[:500] if response.text else 'OK'
                    )
                    return {
                        'success': True, 
                        'message': 'Event synced successfully',
                        'response': response.text[:200]
                    }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                self.db.update_sync_status(event_id, 'failed', error=error_msg)
                return {'success': False, 'message': error_msg}
                
        except requests.exceptions.Timeout:
            error_msg = "Request timeout"
            self.db.update_sync_status(event_id, 'failed', error=error_msg)
            return {'success': False, 'message': error_msg}
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: {str(e)[:100]}"
            self.db.update_sync_status(event_id, 'failed', error=error_msg)
            return {'success': False, 'message': error_msg}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)[:100]}"
            self.db.update_sync_status(event_id, 'failed', error=error_msg)
            return {'success': False, 'message': error_msg}
    
    def sync_pending_events(self, webhook_url: str, api_key: Optional[str] = None,
                            limit: int = 50) -> Dict[str, Any]:
        """
        Sync all pending events to webhook
        
        Returns:
            Dict with 'total', 'synced', 'failed', 'errors'
        """
        pending_events = self.get_pending_sync_events(limit=limit)
        
        results = {
            'total': len(pending_events),
            'synced': 0,
            'failed': 0,
            'errors': []
        }
        
        for event in pending_events:
            result = self.sync_event_to_webhook(event['id'], webhook_url, api_key)
            if result['success']:
                results['synced'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({
                    'event_id': event['id'],
                    'error': result['message']
                })
        
        return results
