"""
Device Controller
Handles direct communication with Hikvision device for manual sync operations
"""

import os
import json
import logging
import requests
from requests.auth import HTTPDigestAuth
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class DeviceController:
    """Controller for direct device communication and manual sync"""
    
    def __init__(self):
        self.device_ip = os.getenv('DEVICE_IP', '192.168.1.128')
        self.device_user = os.getenv('DEVICE_USER', 'admin')
        self.device_pass = os.getenv('DEVICE_PASS', '11111111.')
        self.base_url = f"http://{self.device_ip}"
        self.auth = HTTPDigestAuth(self.device_user, self.device_pass)
        self.timeout = 15
        
        # Import database here to avoid circular imports
        from database import get_db
        self.db = get_db()
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to the device
        
        Returns:
            Dict with success status, message, and device info
        """
        try:
            # Try to get device info - first try JSON, then XML
            url = f"{self.base_url}/ISAPI/System/deviceInfo?format=json"
            response = requests.get(url, auth=self.auth, timeout=self.timeout)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    device_info = data.get('DeviceInfo', {})
                    return {
                        'success': True,
                        'message': 'Connected successfully',
                        'device_name': device_info.get('deviceName', 'Unknown'),
                        'model': device_info.get('model', 'Unknown'),
                        'serial_number': device_info.get('serialNumber', 'Unknown'),
                        'firmware': device_info.get('firmwareVersion', 'Unknown'),
                        'mac_address': device_info.get('macAddress', 'Unknown')
                    }
                except:
                    # Try parsing as XML if JSON fails
                    import xml.etree.ElementTree as ET
                    try:
                        root = ET.fromstring(response.text)
                        # Handle namespaces
                        ns = {'hik': 'http://www.hikvision.com/ver20/XMLSchema'}
                        
                        def get_text(elem_name):
                            elem = root.find(f'.//hik:{elem_name}', ns) or root.find(f'.//{elem_name}')
                            return elem.text if elem is not None else 'Unknown'
                        
                        return {
                            'success': True,
                            'message': 'Connected successfully',
                            'device_name': get_text('deviceName'),
                            'model': get_text('model'),
                            'serial_number': get_text('serialNumber'),
                            'firmware': get_text('firmwareVersion'),
                            'mac_address': get_text('macAddress')
                        }
                    except:
                        # Connection works but can't parse response
                        return {
                            'success': True,
                            'message': 'Connected (device info unavailable)',
                            'device_name': 'Hikvision Device',
                            'model': '-',
                            'serial_number': '-',
                            'firmware': '-',
                            'mac_address': '-'
                        }
            elif response.status_code == 401:
                return {
                    'success': False,
                    'message': 'Authentication failed - check credentials'
                }
            else:
                return {
                    'success': False,
                    'message': f'HTTP {response.status_code}: {response.text[:100]}'
                }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'message': f'Connection timeout - device at {self.device_ip} not responding'
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'message': f'Connection failed - cannot reach {self.device_ip}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
    
    def get_device_status(self) -> Dict[str, Any]:
        """
        Get comprehensive device status
        
        Returns:
            Dict with device status information
        """
        result = {
            'connected': False,
            'device_name': '-',
            'model': '-',
            'serial_number': '-',
            'firmware': '-',
            'ip_address': self.device_ip,
            'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        conn_test = self.test_connection()
        if conn_test['success']:
            result['connected'] = True
            result['device_name'] = conn_test.get('device_name', '-')
            result['model'] = conn_test.get('model', '-')
            result['serial_number'] = conn_test.get('serial_number', '-')
            result['firmware'] = conn_test.get('firmware', '-')
        
        return result
    
    def fetch_events_page(
        self, 
        start_position: int = 0, 
        max_results: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Tuple[List[Dict], int, Optional[str]]:
        """
        Fetch a page of events from the device
        
        Args:
            start_position: Starting position for pagination
            max_results: Maximum results per page (max 100)
            start_time: Optional start time filter
            end_time: Optional end time filter
            
        Returns:
            Tuple of (events_list, total_matches, error_message)
        """
        try:
            url = f"{self.base_url}/ISAPI/AccessControl/AcsEvent?format=json"
            
            # Default time range: last 30 days
            if not end_time:
                end_time = datetime.now()
            if not start_time:
                start_time = end_time - timedelta(days=30)
            
            # Format times for API
            start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S+03:00')
            end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S+03:00')
            
            payload = {
                'AcsEventCond': {
                    'searchID': str(int(datetime.now().timestamp())),
                    'searchResultPosition': start_position,
                    'maxResults': min(max_results, 100),
                    'major': 5,  # Access control events
                    'minor': 0,
                    'startTime': start_str,
                    'endTime': end_str
                }
            }
            
            response = requests.post(
                url, 
                auth=self.auth, 
                json=payload, 
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                acs_event = data.get('AcsEvent', {})
                total_matches = acs_event.get('totalMatches', 0)
                info_list = acs_event.get('InfoList', [])
                
                return info_list, total_matches, None
            else:
                return [], 0, f'HTTP {response.status_code}: {response.text[:200]}'
                
        except requests.exceptions.Timeout:
            return [], 0, 'Request timeout'
        except requests.exceptions.ConnectionError:
            return [], 0, 'Connection failed'
        except Exception as e:
            return [], 0, str(e)
    
    def sync_events_from_device(
        self, 
        max_events: int = 1000,
        days_back: int = 30,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Sync events from device to database
        
        Args:
            max_events: Maximum number of events to sync (default 1000)
            days_back: How many days back to fetch (default 30)
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict with sync results
        """
        result = {
            'success': False,
            'total_fetched': 0,
            'new_events': 0,
            'duplicates': 0,
            'errors': 0,
            'message': '',
            'started_at': datetime.now().isoformat(),
            'completed_at': None
        }
        
        try:
            # Test connection first
            conn_test = self.test_connection()
            if not conn_test['success']:
                result['message'] = f"Connection failed: {conn_test['message']}"
                return result
            
            # Calculate time range
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days_back)
            
            # First, get total count
            _, total_on_device, error = self.fetch_events_page(
                start_position=0, 
                max_results=1,
                start_time=start_time,
                end_time=end_time
            )
            
            if error:
                result['message'] = f"Failed to query device: {error}"
                return result
            
            logger.info(f"Device has {total_on_device} events in last {days_back} days")
            
            # Fetch events in batches
            batch_size = 100
            position = 0
            all_events = []
            
            while position < min(total_on_device, max_events):
                events, _, error = self.fetch_events_page(
                    start_position=position,
                    max_results=batch_size,
                    start_time=start_time,
                    end_time=end_time
                )
                
                if error:
                    logger.warning(f"Error fetching batch at position {position}: {error}")
                    result['errors'] += 1
                    break
                
                if not events:
                    break
                
                all_events.extend(events)
                position += len(events)
                
                # Progress callback
                if progress_callback:
                    progress = min(position / min(total_on_device, max_events) * 100, 100)
                    progress_callback(progress, f"Fetched {position} events...")
                
                logger.info(f"Fetched {len(events)} events (total: {len(all_events)})")
            
            result['total_fetched'] = len(all_events)
            
            # Now save to database, checking for duplicates
            if progress_callback:
                progress_callback(50, "Saving to database...")
            
            for i, event in enumerate(all_events):
                try:
                    # Check if event already exists by serial_no
                    serial_no = event.get('serialNo')
                    if serial_no and self._event_exists(serial_no):
                        result['duplicates'] += 1
                        continue
                    
                    # Transform and save event
                    event_data = self._transform_device_event(event)
                    event_id = self.db.insert_event(event_data)
                    
                    if event_id:
                        result['new_events'] += 1
                    else:
                        result['errors'] += 1
                        
                except Exception as e:
                    logger.error(f"Error saving event: {e}")
                    result['errors'] += 1
                
                # Progress callback for save phase
                if progress_callback and i % 50 == 0:
                    progress = 50 + (i / len(all_events) * 50)
                    progress_callback(progress, f"Saved {result['new_events']} new events...")
            
            result['success'] = True
            result['completed_at'] = datetime.now().isoformat()
            result['message'] = f"Synced {result['new_events']} new events, {result['duplicates']} duplicates skipped"
            
            if progress_callback:
                progress_callback(100, "Sync complete!")
            
            logger.info(f"Sync complete: {result}")
            return result
            
        except Exception as e:
            result['message'] = f"Sync failed: {str(e)}"
            logger.error(f"Sync error: {e}")
            return result
    
    def _event_exists(self, serial_no: int) -> bool:
        """Check if an event with this serial number already exists"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM events WHERE serial_no = %s LIMIT 1",
                (serial_no,)
            )
            exists = cursor.fetchone() is not None
            cursor.close()
            conn.close()
            return exists
        except Exception as e:
            logger.error(f"Error checking event existence: {e}")
            return False
    
    def _transform_device_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Transform device event format to database format"""
        # Parse time
        occur_time = event.get('time', '')
        if occur_time and '+' in occur_time:
            occur_time = occur_time.split('+')[0]
        try:
            occur_time = datetime.fromisoformat(occur_time) if occur_time else datetime.now()
        except:
            occur_time = datetime.now()
        
        return {
            'device_ip': self.device_ip,
            'device_id': event.get('deviceName', ''),
            'event_type': 'AccessControllerEvent',
            'event_state': 'active',
            'occur_time': occur_time,
            'employee_no': event.get('employeeNoString', ''),
            'name': event.get('name', ''),
            'card_no': event.get('cardNo', ''),
            'door_no': event.get('doorNo', 1),
            'verify_no': event.get('verifyNo'),
            'verify_mode': event.get('currentVerifyMode', ''),
            'major_event_type': event.get('major', 5),
            'sub_event_type': event.get('minor', 0),
            'serial_no': event.get('serialNo'),
            'mac_address': event.get('netUser', {}).get('MACAddr', ''),
            'channel_id': event.get('channelID'),
            'protocol': 'ISAPI',
            'port_no': 80,
            'device_name': event.get('deviceName', ''),
            'card_type': event.get('cardType'),
            'card_reader_kind': event.get('cardReaderKind'),
            'attendance_status': event.get('attendanceStatus', ''),
            'mask': event.get('mask'),
            'helmet': event.get('helmet'),
            'raw_json': json.dumps(event),
            'json_file_path': None,
            'sync_status': 'pending',
            'sync_attempts': 0
        }
    
    def get_sync_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent sync history from database
        This queries events grouped by sync time to show sync batches
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Get summary of recent syncs by looking at created_at timestamps
            cursor.execute("""
                SELECT 
                    DATE(created_at) as sync_date,
                    COUNT(*) as event_count,
                    MIN(occur_time) as earliest_event,
                    MAX(occur_time) as latest_event,
                    SUM(CASE WHEN sync_status = 'synced' THEN 1 ELSE 0 END) as synced_count,
                    SUM(CASE WHEN sync_status = 'pending' THEN 1 ELSE 0 END) as pending_count
                FROM events
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY DATE(created_at)
                ORDER BY sync_date DESC
                LIMIT %s
            """, (limit,))
            
            history = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting sync history: {e}")
            return []
    
    def get_event_count_on_device(self, days_back: int = 30) -> Dict[str, Any]:
        """Get count of events on device without downloading them"""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days_back)
            
            _, total, error = self.fetch_events_page(
                start_position=0,
                max_results=1,
                start_time=start_time,
                end_time=end_time
            )
            
            if error:
                return {'success': False, 'count': 0, 'error': error}
            
            return {
                'success': True,
                'count': total,
                'days_back': days_back,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }
            
        except Exception as e:
            return {'success': False, 'count': 0, 'error': str(e)}


# Singleton instance
_device_controller = None

def get_device_controller() -> DeviceController:
    """Get the singleton device controller instance"""
    global _device_controller
    if _device_controller is None:
        _device_controller = DeviceController()
    return _device_controller
