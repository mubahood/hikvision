"""
Upload Sync Controller
Handles webhook upload/sync operations for events
"""

import os
import json
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class UploadSyncController:
    """Controller for uploading/syncing events to webhook"""
    
    def __init__(self):
        from database import get_db
        from controllers.config_controller import ConfigController
        
        self.db = get_db()
        self.config = ConfigController()
        self.timeout = 15
    
    def get_webhook_config(self) -> Dict[str, Any]:
        """Get webhook configuration"""
        config = self.config.get_all_config()
        return {
            'webhook_url': config.get('webhook_url', ''),
            'api_key': config.get('webhook_api_key', ''),
            'configured': bool(config.get('webhook_url', '').strip())
        }
    
    def test_webhook(self) -> Dict[str, Any]:
        """Test webhook connectivity"""
        config = self.get_webhook_config()
        
        if not config['configured']:
            return {
                'success': False,
                'message': 'Webhook URL not configured'
            }
        
        try:
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'HikvisionBridge/1.0'
            }
            if config['api_key']:
                headers['X-API-Key'] = config['api_key']
            
            # Send properly formatted test payload as batch
            test_event = {
                'event_serial': f'TEST-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                'employee_no': '00000',
                'employee_name': 'Webhook Test',
                'event_time': datetime.now().isoformat(),
                'device_name': 'Test Device',
                'device_ip': '0.0.0.0',
                'verification_method': 'test',
                'raw_data': {
                    'test': True,
                    'message': 'Webhook connectivity test'
                }
            }
            
            # Wrap in events array for batch endpoint
            test_payload = {'events': [test_event]}
            
            # Use the webhook URL as configured (should already include /batch if needed)
            webhook_url = config['webhook_url'].rstrip('/')
            
            response = requests.post(
                webhook_url,
                json=test_payload,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'Webhook is reachable',
                    'response_time': response.elapsed.total_seconds(),
                    'status_code': response.status_code
                }
            else:
                return {
                    'success': False,
                    'message': f'HTTP {response.status_code}: {response.text[:100]}',
                    'status_code': response.status_code
                }
                
        except requests.exceptions.Timeout:
            return {'success': False, 'message': 'Connection timeout'}
        except requests.exceptions.ConnectionError:
            return {'success': False, 'message': 'Connection failed - check URL'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def get_sync_stats(self) -> Dict[str, Any]:
        """Get comprehensive sync statistics"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Overall counts
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN sync_status = 'synced' THEN 1 ELSE 0 END) as synced,
                    SUM(CASE WHEN sync_status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN sync_status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM events
            """)
            overall = cursor.fetchone()
            
            # Today's stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN sync_status = 'synced' THEN 1 ELSE 0 END) as synced,
                    SUM(CASE WHEN sync_status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN sync_status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM events
                WHERE DATE(created_at) = CURDATE()
            """)
            today = cursor.fetchone()
            
            # Recent failed events (last 10)
            cursor.execute("""
                SELECT id, employee_no, name, occur_time, sync_status, sync_attempts, sync_error
                FROM events
                WHERE sync_status = 'failed'
                ORDER BY created_at DESC
                LIMIT 10
            """)
            recent_failed = cursor.fetchall()
            
            # Sync rate (last 24 hours)
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN sync_status = 'synced' THEN 1 ELSE 0 END) as synced
                FROM events
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """)
            last_24h = cursor.fetchone()
            sync_rate = (last_24h['synced'] / last_24h['total'] * 100) if last_24h['total'] > 0 else 0
            
            cursor.close()
            conn.close()
            
            return {
                'overall': overall,
                'today': today,
                'recent_failed': recent_failed,
                'sync_rate_24h': round(sync_rate, 1),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting sync stats: {e}")
            return {
                'overall': {'total': 0, 'synced': 0, 'pending': 0, 'failed': 0},
                'today': {'total': 0, 'synced': 0, 'pending': 0, 'failed': 0},
                'recent_failed': [],
                'sync_rate_24h': 0,
                'error': str(e)
            }
    
    def get_pending_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get pending events that need to be synced"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT id, employee_no, name, occur_time, event_type, sync_status, sync_attempts
                FROM events
                WHERE sync_status IN ('pending', 'failed')
                ORDER BY occur_time DESC
                LIMIT %s
            """, (limit,))
            
            events = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting pending events: {e}")
            return []
    
    def sync_single_event(self, event_id: int) -> Dict[str, Any]:
        """Sync a single event to webhook"""
        config = self.get_webhook_config()
        
        if not config['configured']:
            return {'success': False, 'message': 'Webhook not configured'}
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Get event
            cursor.execute("SELECT * FROM events WHERE id = %s", (event_id,))
            event = cursor.fetchone()
            
            if not event:
                cursor.close()
                conn.close()
                return {'success': False, 'message': 'Event not found'}
            
            # Prepare payload matching Laravel endpoint format
            payload = {
                'event_serial': event.get('serial_no'),
                'employee_no': str(event.get('employee_no')) if event.get('employee_no') else None,
                'employee_name': event.get('name'),
                'event_time': str(event.get('occur_time')),
                'door_name': event.get('door_no'),
                'verification_method': event.get('verify_mode'),
                'device_name': event.get('device_id'),
                'device_ip': event.get('device_ip'),
                'raw_data': {
                    'event_id': event['id'],
                    'event_type': event.get('event_type'),
                    'attendance_status': event.get('attendance_status'),
                    'card_no': event.get('card_no')
                }
            }
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'HikvisionBridge/1.0'
            }
            if config['api_key']:
                headers['X-API-Key'] = config['api_key']
            
            # Wrap in events array for batch endpoint
            batch_payload = {'events': [payload]}
            
            response = requests.post(
                config['webhook_url'],
                json=batch_payload,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                # Update status to synced
                cursor.execute("""
                    UPDATE events 
                    SET sync_status = 'synced', 
                        synced_at = NOW(),
                        sync_attempts = sync_attempts + 1,
                        sync_error = NULL
                    WHERE id = %s
                """, (event_id,))
                conn.commit()
                cursor.close()
                conn.close()
                
                return {
                    'success': True,
                    'message': 'Synced successfully',
                    'event_id': event_id
                }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:100]}"
                cursor.execute("""
                    UPDATE events 
                    SET sync_status = 'failed',
                        sync_attempts = sync_attempts + 1,
                        sync_error = %s
                    WHERE id = %s
                """, (error_msg, event_id))
                conn.commit()
                cursor.close()
                conn.close()
                
                return {'success': False, 'message': error_msg, 'event_id': event_id}
                
        except requests.exceptions.Timeout:
            return {'success': False, 'message': 'Request timeout', 'event_id': event_id}
        except requests.exceptions.ConnectionError:
            return {'success': False, 'message': 'Connection failed', 'event_id': event_id}
        except Exception as e:
            logger.error(f"Error syncing event {event_id}: {e}")
            return {'success': False, 'message': str(e), 'event_id': event_id}
    
    def sync_batch(
        self, 
        limit: int = 100,
        sync_failed: bool = True,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Sync a batch of pending/failed events
        
        Args:
            limit: Maximum events to sync
            sync_failed: Include failed events in retry
            progress_callback: Optional callback(pct, msg)
            
        Returns:
            Dict with sync results
        """
        result = {
            'success': False,
            'total': 0,
            'synced': 0,
            'failed': 0,
            'skipped': 0,
            'errors': [],
            'started_at': datetime.now().isoformat(),
            'completed_at': None
        }
        
        config = self.get_webhook_config()
        if not config['configured']:
            result['message'] = 'Webhook URL not configured'
            return result
        
        # Test webhook first
        test = self.test_webhook()
        if not test['success']:
            result['message'] = f"Webhook test failed: {test['message']}"
            return result
        
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Get events to sync
            if sync_failed:
                cursor.execute("""
                    SELECT id, employee_no, name, occur_time, event_type, device_ip, device_id,
                           door_no, verify_mode, attendance_status, card_no, serial_no
                    FROM events
                    WHERE sync_status IN ('pending', 'failed')
                    ORDER BY occur_time ASC
                    LIMIT %s
                """, (limit,))
            else:
                cursor.execute("""
                    SELECT id, employee_no, name, occur_time, event_type, device_ip, device_id,
                           door_no, verify_mode, attendance_status, card_no, serial_no
                    FROM events
                    WHERE sync_status = 'pending'
                    ORDER BY occur_time ASC
                    LIMIT %s
                """, (limit,))
            
            events = cursor.fetchall()
            result['total'] = len(events)
            
            if not events:
                result['success'] = True
                result['message'] = 'No events to sync'
                cursor.close()
                conn.close()
                return result
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'HikvisionBridge/1.0'
            }
            if config['api_key']:
                headers['X-API-Key'] = config['api_key']
            
            for i, event in enumerate(events):
                try:
                    # Prepare payload matching Laravel endpoint format
                    payload = {
                        'event_serial': event.get('serial_no'),
                        'employee_no': str(event.get('employee_no')) if event.get('employee_no') else None,
                        'employee_name': event.get('name'),
                        'event_time': str(event.get('occur_time')),
                        'door_name': event.get('door_no'),
                        'verification_method': event.get('verify_mode'),
                        'device_name': event.get('device_id'),
                        'device_ip': event.get('device_ip'),
                        'raw_data': {
                            'event_id': event['id'],
                            'event_type': event.get('event_type'),
                            'attendance_status': event.get('attendance_status'),
                            'card_no': event.get('card_no')
                        }
                    }
                    
                    # Wrap in events array for batch endpoint
                    batch_payload = {'events': [payload]}
                    
                    response = requests.post(
                        config['webhook_url'],
                        json=batch_payload,
                        headers=headers,
                        timeout=self.timeout
                    )
                    
                    if response.status_code == 200:
                        # Parse response to check if it was processed or duplicate
                        try:
                            resp_data = response.json()
                            # Success if processed > 0 OR duplicates > 0 (already synced before)
                            if resp_data.get('stats', {}).get('processed', 0) > 0 or resp_data.get('stats', {}).get('duplicates', 0) > 0:
                                cursor.execute("""
                                    UPDATE events 
                                    SET sync_status = 'synced', 
                                        synced_at = NOW(),
                                        sync_attempts = sync_attempts + 1,
                                        sync_error = NULL
                                    WHERE id = %s
                                """, (event['id'],))
                                result['synced'] += 1
                            else:
                                # Had errors in processing
                                error_msg = f"Processing errors: {resp_data.get('errors', 'Unknown')}"
                                cursor.execute("""
                                    UPDATE events 
                                    SET sync_status = 'failed',
                                        sync_attempts = sync_attempts + 1,
                                        sync_error = %s
                                    WHERE id = %s
                                """, (error_msg[:500], event['id']))
                                result['failed'] += 1
                                result['errors'].append({'event_id': event['id'], 'error': error_msg})
                        except Exception as parse_err:
                            # If can't parse, just mark as synced since status was 200
                            cursor.execute("""
                                UPDATE events 
                                SET sync_status = 'synced', 
                                    synced_at = NOW(),
                                    sync_attempts = sync_attempts + 1,
                                    sync_error = NULL
                                WHERE id = %s
                            """, (event['id'],))
                            result['synced'] += 1
                    else:
                        error_msg = f"HTTP {response.status_code}"
                        cursor.execute("""
                            UPDATE events 
                            SET sync_status = 'failed',
                                sync_attempts = sync_attempts + 1,
                                sync_error = %s
                            WHERE id = %s
                        """, (error_msg, event['id']))
                        result['failed'] += 1
                        result['errors'].append({'event_id': event['id'], 'error': error_msg})
                        
                except Exception as e:
                    result['failed'] += 1
                    result['errors'].append({'event_id': event['id'], 'error': str(e)})
                
                # Progress callback
                if progress_callback and i % 5 == 0:
                    pct = (i + 1) / len(events) * 100
                    progress_callback(pct, f"Synced {result['synced']}/{i+1} events...")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            result['success'] = True
            result['completed_at'] = datetime.now().isoformat()
            result['message'] = f"Synced {result['synced']} events, {result['failed']} failed"
            
            if progress_callback:
                progress_callback(100, "Sync complete!")
            
            return result
            
        except Exception as e:
            logger.error(f"Batch sync error: {e}")
            result['message'] = str(e)
            return result
    
    def reset_failed_events(self) -> Dict[str, Any]:
        """Reset all failed events to pending for retry"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE events 
                SET sync_status = 'pending', sync_error = NULL
                WHERE sync_status = 'failed'
            """)
            
            affected = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': f'Reset {affected} failed events to pending',
                'count': affected
            }
            
        except Exception as e:
            logger.error(f"Error resetting failed events: {e}")
            return {'success': False, 'message': str(e)}
    
    def get_sync_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get sync history grouped by hour"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT 
                    DATE_FORMAT(synced_at, '%%Y-%%m-%%d %%H:00') as sync_hour,
                    COUNT(*) as count,
                    MIN(synced_at) as first_sync,
                    MAX(synced_at) as last_sync
                FROM events
                WHERE sync_status = 'synced' AND synced_at IS NOT NULL
                GROUP BY sync_hour
                ORDER BY sync_hour DESC
                LIMIT %s
            """, (limit,))
            
            history = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting sync history: {e}")
            return []


# Singleton instance
_upload_sync_controller = None

def get_upload_sync_controller() -> UploadSyncController:
    """Get the singleton upload sync controller instance"""
    global _upload_sync_controller
    if _upload_sync_controller is None:
        _upload_sync_controller = UploadSyncController()
    return _upload_sync_controller
