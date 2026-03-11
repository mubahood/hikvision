#!/usr/bin/env python3
"""
Hikvision ISAPI Bridge Service
Connects to Hikvision device via ISAPI polling and forwards events to a webhook.
Uses polling-based event retrieval for devices that don't support alertStream.
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Set
import json
import signal

import requests
from requests.auth import HTTPDigestAuth
from dotenv import load_dotenv

# Import database module
try:
    from database import get_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("Warning: database.py not found. Events will only be saved to JSON files.")


class HikvisionBridge:
    """Bridge service to connect Hikvision ISAPI to webhook endpoint using polling"""
    
    def __init__(self):
        """Initialize the bridge with configuration from environment"""
        load_dotenv()
        
        # Device configuration: DB config table first, .env fallback
        # This ensures dashboard "Save Device" changes take effect on restart
        db_config = {}
        if DB_AVAILABLE:
            try:
                db_config = get_db().get_config()  # {key_name: value}
            except Exception:
                pass
        
        self.device_ip = db_config.get('device_ip') or os.getenv('DEVICE_IP', '192.168.1.128')
        self.device_user = db_config.get('device_user') or os.getenv('DEVICE_USER', 'admin')
        self.device_pass = os.getenv('DEVICE_PASS', '')  # password stays in .env only
        self.device_id = db_config.get('device_id') or os.getenv('DEVICE_ID', self.device_ip)
        
        # Polling configuration
        self.poll_interval = int(os.getenv('POLL_INTERVAL', '2'))  # seconds between polls
        self.batch_size = int(os.getenv('BATCH_SIZE', '30'))  # max events per poll
        
        # Data storage configuration
        self.data_base_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(self.data_base_dir, exist_ok=True)
        self.event_counter = 0
        
        # Logging configuration
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        log_file = os.getenv('LOG_FILE', 'hikvision_bridge.log')
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # State management
        self.running = True
        self.last_serial_no = 0  # Track last processed event serial number
        self.processed_serials: Set[int] = set()  # Track processed events to avoid duplicates
        
        # Batch upload management
        self.event_batch = []  # Queue for batching events
        self.batch_upload_size = int(os.getenv('BATCH_UPLOAD_SIZE', '10'))  # Events per batch
        
        # Database connection
        self.db = get_db() if DB_AVAILABLE else None
        if self.db:
            self.logger.info("Database connection established")
            # Load last processed serial from database
            self._load_last_serial()
        
        # Load webhook configuration from database
        self._load_webhook_config()
        
        # Validate configuration
        self._validate_config()
        
        # HTTP session for connection pooling
        self.session = requests.Session()
        self.session.auth = HTTPDigestAuth(self.device_user, self.device_pass)
        
        self.logger.info(f"Bridge initialized for device {self.device_ip}")
        self.logger.info(f"Polling mode: every {self.poll_interval} seconds")
        if self.webhook_url:
            url_display = self.webhook_url[:50] if len(self.webhook_url) > 50 else self.webhook_url
            self.logger.info(f"Auto-sync enabled: {url_display}...")
        else:
            self.logger.info("Auto-sync disabled (no webhook URL configured)")
    
    def _validate_config(self):
        """Validate required configuration"""
        if not self.device_pass:
            self.logger.error("DEVICE_PASS not set in environment")
            raise ValueError("DEVICE_PASS is required")
    
    def _load_last_serial(self):
        """Load the last processed serial number from database"""
        if self.db:
            conn = None
            cursor = None
            try:
                conn = self.db.get_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute('SELECT MAX(serial_no) as max_serial FROM events WHERE device_ip = %s', (self.device_ip,))
                result = cursor.fetchone()
                if result and result['max_serial']:
                    self.last_serial_no = result['max_serial']
                    self.logger.info(f"Resuming from serial number: {self.last_serial_no}")
            except Exception as e:
                self.logger.warning(f"Could not load last serial: {e}")
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
    
    def _load_webhook_config(self):
        """Load webhook configuration from database"""
        self.webhook_url = None
        self.webhook_api_key = None
        self.webhook_secret = None
        
        if self.db:
            try:
                config = self.db.get_config('webhook_url')
                if config and config.get('value'):
                    self.webhook_url = config.get('value')
                    api_key_config = self.db.get_config('webhook_api_key')
                    if api_key_config:
                        self.webhook_api_key = api_key_config.get('value')
                    self.logger.info(f"Loaded webhook config from database")
            except Exception as e:
                self.logger.warning(f"Could not load webhook config: {e}")
        
        # Fallback to environment variables
        if not self.webhook_url:
            self.webhook_url = os.getenv('WEBHOOK_URL')
            self.webhook_api_key = os.getenv('WEBHOOK_API_KEY')
            self.webhook_secret = os.getenv('WEBHOOK_SECRET')
    
    def _clean_for_json(self, obj):
        """Clean object for JSON serialization by converting datetime objects"""
        if hasattr(obj, 'isoformat'):  # datetime object
            return obj.isoformat()
        elif hasattr(obj, 'item'):  # numpy types
            return obj.item()
        elif isinstance(obj, dict):
            return {key: self._clean_for_json(value) for key, value in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._clean_for_json(item) for item in obj]
        else:
            return obj

    def _sync_event_immediately(self, event_id: int, event_data: Dict[str, Any]) -> bool:
        """Upload single event immediately to webhook"""
        if not self.webhook_url:
            self.logger.debug("No webhook URL configured, skipping auto-sync")
            return False
        
        try:
            # Clean event_data of any datetime objects for JSON serialization
            cleaned_event_data = self._clean_for_json(event_data)
            
            # Convert occur_time to string if it's a datetime object
            occur_time = cleaned_event_data.get('occur_time')
            if isinstance(occur_time, str) and 'T' not in occur_time:
                # Handle timestamp strings that aren't ISO format
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(occur_time.replace(' ', 'T'))
                    occur_time = dt.isoformat()
                except:
                    occur_time = str(occur_time)
            
            # Prepare comprehensive payload with ALL fields
            payload = {
                # Core identification
                'serial_no': cleaned_event_data.get('serial_no'),
                'event_serial': cleaned_event_data.get('serial_no'),  # Alias for compatibility
                
                # Employee information
                'employee_no': str(cleaned_event_data.get('employee_no')) if cleaned_event_data.get('employee_no') else None,
                'name': cleaned_event_data.get('name'),
                'employee_name': cleaned_event_data.get('name'),  # Alias
                
                # Event timing
                'occur_time': occur_time,
                'event_time': occur_time,  # Alias
                
                # Event classification
                'event_type': cleaned_event_data.get('event_type'),
                'event_state': cleaned_event_data.get('event_state'),
                'major': cleaned_event_data.get('major_event_type'),
                'major_event_type': cleaned_event_data.get('major_event_type'),
                'minor': cleaned_event_data.get('sub_event_type'),
                'minor_event_type': cleaned_event_data.get('sub_event_type'),
                'sub_event_type': cleaned_event_data.get('sub_event_type'),
                
                # Location and device
                'device_ip': cleaned_event_data.get('device_ip'),
                'device_id': cleaned_event_data.get('device_id'),
                'device_name': cleaned_event_data.get('device_name'),
                'door_no': cleaned_event_data.get('door_no'),
                'doorNo': cleaned_event_data.get('door_no'),  # Alias
                'channel_id': cleaned_event_data.get('channel_id'),
                
                # Verification
                'verify_mode': cleaned_event_data.get('verify_mode'),
                'currentVerifyMode': cleaned_event_data.get('verify_mode'),  # Alias
                'verify_no': cleaned_event_data.get('verify_no'),
                
                # Card information
                'card_no': cleaned_event_data.get('card_no'),
                'card_type': str(cleaned_event_data.get('card_type')) if cleaned_event_data.get('card_type') else None,
                'cardType': cleaned_event_data.get('card_type'),
                'card_reader_kind': cleaned_event_data.get('card_reader_kind'),
                
                # Health and safety
                'mask': cleaned_event_data.get('mask'),
                'helmet': cleaned_event_data.get('helmet'),
                'attendance_status': cleaned_event_data.get('attendance_status'),
                
                # Network
                'mac_address': cleaned_event_data.get('mac_address'),
                'protocol': cleaned_event_data.get('protocol'),
                'port_no': cleaned_event_data.get('port_no'),
                
                # Raw data - send as string if it's JSON string
                'raw_json': cleaned_event_data.get('raw_json'),  # Keep as string for proper parsing
                'raw_data': cleaned_event_data,  # Send complete cleaned event data
            }
            
            # Remove None values to reduce payload size
            payload = {k: v for k, v in payload.items() if v is not None}
            
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'HikvisionBridge/1.0'
            }
            
            if self.webhook_api_key:
                headers['X-API-Key'] = self.webhook_api_key
            
            # Upload immediately as single event in array format
            self.logger.info(f"⚡ Uploading event immediately: {event_data.get('serial_no')}")
            
            response = requests.post(
                self.webhook_url,
                json={'events': [payload]},  # Wrap in array
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"✅ Event uploaded successfully")
                
                # Update sync status
                if self.db:
                    self.db.update_sync_status(event_id, 'synced', response='Uploaded immediately')
                
                return True
            else:
                error_msg = f"HTTP {response.status_code}"
                self.logger.warning(f"❌ Upload failed: {error_msg}")
                
                # Mark as failed
                if self.db:
                    self.db.update_sync_status(event_id, 'failed', response=error_msg)
                
                return False
                
        except requests.exceptions.Timeout:
            self.logger.error("⏱️ Upload timeout")
            if self.db:
                self.db.update_sync_status(event_id, 'failed', response='Timeout')
            return False
            
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"🔌 Connection error: {e}")
            if self.db:
                self.db.update_sync_status(event_id, 'failed', response=f'Connection error: {str(e)[:100]}')
            return False
            
        except Exception as e:
            self.logger.error(f"💥 Unexpected error: {e}")
            if self.db:
                self.db.update_sync_status(event_id, 'failed', response=f'Error: {str(e)[:100]}')
            return False
    
    def _upload_batch(self) -> bool:
        """Upload batched events to webhook"""
        if not self.event_batch:
            return True
        
        if not self.webhook_url:
            self.event_batch.clear()
            return False
        
        batch_payloads = [item['payload'] for item in self.event_batch]
        event_ids = [item['event_id'] for item in self.event_batch]
        
        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'HikvisionBridge/1.0'
        }
        
        # Use X-API-Key for authentication
        if self.webhook_api_key:
            headers['X-API-Key'] = self.webhook_api_key
        
        # Use the webhook_url directly (should already point to /webhook/events)
        webhook_url = self.webhook_url.rstrip('/')
        
        try:
            self.logger.info(f"📤 Uploading batch of {len(batch_payloads)} events...")
            
            response = requests.post(
                webhook_url,
                json={'events': batch_payloads},
                timeout=30,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                success_count = result.get('success_count', 0)
                duplicate_count = result.get('duplicate_count', 0)
                failed_count = result.get('failed_count', 0)
                
                self.logger.info(
                    f"✅ Batch uploaded: {success_count} saved, "
                    f"{duplicate_count} duplicates, {failed_count} failed"
                )
                
                # Update sync status for successful events
                if self.db and success_count > 0:
                    for event_id in event_ids:
                        self.db.update_sync_status(event_id, 'synced', response='Batch uploaded')
                
                # Clear batch
                self.event_batch.clear()
                return True
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                self.logger.warning(f"❌ Batch upload failed: {error_msg}")
                
                # Mark events as failed
                if self.db:
                    for event_id in event_ids:
                        self.db.update_sync_status(event_id, 'failed', error=error_msg)
                
                # Clear batch to avoid infinite retry
                self.event_batch.clear()
                return False
                
        except requests.exceptions.Timeout:
            error_msg = "Request timeout"
            self.logger.error(f"❌ Batch upload timeout")
            self.event_batch.clear()
            return False
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: {str(e)[:100]}"
            self.logger.error(f"❌ Batch upload connection error")
            self.event_batch.clear()
            return False
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)[:100]}"
            self.logger.error(f"❌ Batch upload error: {e}")
            self.event_batch.clear()
            return False
    
    def _poll_events(self) -> list:
        """Poll device for new events using POST to /ISAPI/AccessControl/AcsEvent"""
        url = f"http://{self.device_ip}/ISAPI/AccessControl/AcsEvent?format=json"
        
        # Build search condition - get events after last serial number
        # Use time-based filtering as primary, serial as secondary
        now = datetime.now()
        start_time = (now - timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%S+03:00')
        end_time = now.strftime('%Y-%m-%dT%H:%M:%S+03:00')
        
        search_cond = {
            'AcsEventCond': {
                'searchID': str(int(time.time())),
                'searchResultPosition': 0,
                'maxResults': self.batch_size,
                'major': 5,  # Access events
                'minor': 0,  # All sub-types (will include 75 for face recognition)
                'startTime': start_time,
                'endTime': end_time,
            }
        }
        
        # Note: beginSerialNo causes 400 error on this device, so we filter in code instead
        
        try:
            response = self.session.post(url, json=search_cond, timeout=10)
            
            if response.status_code != 200:
                self.logger.error(f"Poll failed: HTTP {response.status_code}")
                return []
            
            data = response.json()
            acs_event = data.get('AcsEvent', {})
            total = acs_event.get('totalMatches', 0)
            info_list = acs_event.get('InfoList', [])
            
            if info_list:
                self.logger.debug(f"Polled {len(info_list)} events (total: {total})")
            
            return info_list
            
        except requests.exceptions.Timeout:
            self.logger.error("Poll timeout")
            return []
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Poll connection error: {e}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Poll JSON decode error: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Poll error: {e}")
            return []
    
    def _parse_polled_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a polled event into our standard format"""
        try:
            serial_no = event.get('serialNo', 0)
            
            # Skip if already processed
            if serial_no in self.processed_serials:
                return None
            
            # Parse time
            event_time = event.get('time', datetime.now().isoformat())
            
            # Build event data
            event_data = {
                'device_ip': self.device_ip,
                'device_id': self.device_id,
                'event_type': 'AccessControllerEvent',
                'event_state': 'active',
                'occur_time': event_time,
                'serial_no': serial_no,
                
                # Access control fields
                'major_event_type': event.get('major'),
                'sub_event_type': event.get('minor'),
                'employee_no': event.get('employeeNoString') or event.get('employeeNo'),
                'name': event.get('name'),
                'card_no': event.get('cardNo'),
                'door_no': event.get('doorNo'),
                'verify_mode': event.get('currentVerifyMode'),
                'card_type': event.get('cardType'),
                'card_reader_kind': event.get('cardReaderKind'),
                'attendance_status': event.get('attendanceStatus'),
                'mask': event.get('mask'),
                'helmet': event.get('helmet'),
                
                # Raw data
                'raw_json': event,
            }
            
            return event_data
            
        except Exception as e:
            self.logger.error(f"Error parsing polled event: {e}")
            return None
    
    def _save_event(self, event_data: Dict[str, Any]) -> Optional[int]:
        """Save event data to database (only events with employee ID)"""
        try:
            # Get event details
            employee_no = event_data.get('employee_no')
            name = event_data.get('name')
            verify_mode = event_data.get('verify_mode', 'unknown')
            sub_event = event_data.get('sub_event_type', 'N/A')
            major_event = event_data.get('major_event_type', 'N/A')
            serial_no = event_data.get('serial_no', 0)
            
            # Filter: Only save events with employee ID (successful recognition)
            if not employee_no:
                self.logger.debug(f"⏭️ Skipping: no employee ID (serial={serial_no}, mode={verify_mode})")
                return None
            
            self.logger.info(f"✅ New event: serial={serial_no}, employee={employee_no}, name={name}, mode={verify_mode}")
            
            # Increment counter
            self.event_counter += 1
            
            # Add metadata
            event_data['saved_at'] = datetime.now().isoformat()
            event_data['sync_status'] = 'pending'
            event_data['sync_attempts'] = 0
            
            # Save to database
            if self.db:
                try:
                    event_id = self.db.insert_event(event_data)
                    if event_id:
                        self.logger.info(f"💾 Event saved to database: ID {event_id}")
                        
                        # Mark as processed
                        self.processed_serials.add(serial_no)
                        self.last_serial_no = max(self.last_serial_no, serial_no)
                        
                        # Immediately sync to webhook
                        self._sync_event_immediately(event_id, event_data)
                        
                        return event_id
                except Exception as e:
                    self.logger.error(f"Database save failed: {e}")
                    return None
            else:
                self.logger.error("Database not available")
                return None
            
        except Exception as e:
            self.logger.error(f"Failed to save event: {e}")
            return None
    
    def _check_device_status(self) -> bool:
        """Check if device is responding"""
        url = f"http://{self.device_ip}/ISAPI/System/deviceInfo"
        
        try:
            response = self.session.get(url, timeout=5)
            if response.status_code == 200:
                self.logger.info(f"Device {self.device_ip} is online")
                return True
            elif response.status_code == 401:
                self.logger.error("Authentication failed. Check DEVICE_USER and DEVICE_PASS")
                return False
            else:
                self.logger.warning(f"Device returned HTTP {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"Device check failed: {e}")
            return False
    
    def run(self):
        """Main polling loop"""
        self.logger.info("Starting Hikvision ISAPI Bridge (Polling Mode)")
        
        # Initial device check
        if not self._check_device_status():
            self.logger.error("Device not accessible. Check connection and credentials.")
            return
        
        self.logger.info("🟢 Bridge is running. Waiting for face recognition events...")
        
        # Track consecutive errors for backoff
        consecutive_errors = 0
        
        while self.running:
            try:
                # Poll for new events
                events = self._poll_events()
                
                if events:
                    consecutive_errors = 0  # Reset error count on success
                    
                    # Process each event
                    new_events = 0
                    for event in events:
                        event_data = self._parse_polled_event(event)
                        if event_data:
                            serial_no = event_data.get('serial_no', 0)
                            
                            # Skip if already processed (by serial number)
                            if serial_no <= self.last_serial_no:
                                continue
                            
                            if serial_no in self.processed_serials:
                                continue
                            
                            # Save event
                            event_id = self._save_event(event_data)
                            if event_id:
                                new_events += 1
                    
                    if new_events > 0:
                        self.logger.info(f"📊 Processed {new_events} new event(s)")
                else:
                    consecutive_errors = 0  # No events is not an error
                
                # Wait before next poll
                time.sleep(self.poll_interval)
                
            except KeyboardInterrupt:
                self.logger.info("Interrupted by user")
                self.stop()
                break
            except Exception as e:
                consecutive_errors += 1
                self.logger.error(f"Error in polling loop: {e}")
                
                # Backoff on consecutive errors
                if consecutive_errors > 5:
                    backoff = min(30, consecutive_errors * 2)
                    self.logger.warning(f"Multiple errors, backing off for {backoff}s")
                    time.sleep(backoff)
                else:
                    time.sleep(self.poll_interval)
        
        self.logger.info("Bridge stopped")
    
    def stop(self):
        """Gracefully stop the bridge"""
        self.logger.info("Stopping bridge...")
        self.running = False
        
        # Upload any remaining events in batch
        if self.event_batch:
            self.logger.info(f"Uploading remaining {len(self.event_batch)} events...")
            self._upload_batch()


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logging.info(f"Received signal {signum}")
    if 'bridge' in globals():
        bridge.stop()
    sys.exit(0)


if __name__ == '__main__':
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and run bridge
    bridge = HikvisionBridge()
    bridge.run()
