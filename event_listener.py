#!/usr/bin/env python3
"""
Hikvision Event Listener (Push Mode)
Receives events pushed from Hikvision device via HTTP Listening Host.
Runs as a standalone HTTP server that saves events directly to the database.
"""

import os
import sys
import json
import logging
import traceback
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from typing import Optional, Dict, Any

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger('event_listener')

# Import database
try:
    from database import get_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


class EventListenerHandler(BaseHTTPRequestHandler):
    """HTTP handler for receiving pushed events from Hikvision device"""
    
    def log_message(self, format, *args):
        """Override to use our logger instead of stderr"""
        logger.debug(f"HTTP: {format % args}")
    
    def do_POST(self, *args, **kwargs):
        """Handle POST requests — device pushes events here"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_response(200, {'status': 'ok', 'message': 'empty'})
                return
            
            body = self.rfile.read(content_length)
            content_type = self.headers.get('Content-Type', '')
            
            events_saved = 0
            
            if 'json' in content_type.lower():
                events_saved = self._handle_json(body)
            elif 'multipart' in content_type.lower():
                events_saved = self._handle_multipart(body, content_type)
            elif 'xml' in content_type.lower():
                events_saved = self._handle_xml(body)
            else:
                # Try JSON first, then raw
                try:
                    events_saved = self._handle_json(body)
                except Exception:
                    events_saved = self._handle_raw(body)
            
            self._send_response(200, {
                'status': 'ok',
                'events_saved': events_saved,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error handling POST: {e}\n{traceback.format_exc()}")
            self._send_response(200, {'status': 'ok'})  # Always respond 200 to device
    
    def do_GET(self, *args, **kwargs):
        """Handle GET requests — device health check / keepalive"""
        self._send_response(200, {
            'status': 'listening',
            'service': 'HikvisionEventListener',
            'timestamp': datetime.now().isoformat()
        })
    
    def _send_response(self, code: int, data: dict):
        """Send JSON response"""
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def _handle_json(self, body: bytes) -> int:
        """Handle JSON event data"""
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received: {body[:200]}")
            return 0
        
        events_saved = 0
        
        # Hikvision sends events in various JSON formats
        # Format 1: {EventNotificationAlert: {...}}
        if 'EventNotificationAlert' in data:
            event = data['EventNotificationAlert']
            if self._save_pushed_event(event):
                events_saved += 1
        
        # Format 2: {AcsEvent: {InfoList: [...]}}
        elif 'AcsEvent' in data:
            info_list = data.get('AcsEvent', {}).get('InfoList', [])
            if isinstance(info_list, dict):
                info_list = [info_list]
            for event in info_list:
                if self._save_pushed_event(event):
                    events_saved += 1
        
        # Format 3: Direct event object with typical Hikvision fields
        elif any(k in data for k in ['serialNo', 'employeeNoString', 'major', 'minor']):
            if self._save_pushed_event(data):
                events_saved += 1
        
        # Format 4: List of events
        elif isinstance(data, list):
            for event in data:
                if isinstance(event, dict) and self._save_pushed_event(event):
                    events_saved += 1
        else:
            # Unknown format — save raw
            logger.info(f"Unknown JSON format, saving raw. Keys: {list(data.keys())[:10]}")
            if self._save_pushed_event(data):
                events_saved += 1
        
        if events_saved > 0:
            logger.info(f"📥 Received {events_saved} pushed event(s) from device")
        
        return events_saved
    
    def _handle_multipart(self, body: bytes, content_type: str) -> int:
        """Handle multipart/mixed data (alertStream format)"""
        events_saved = 0
        
        # Extract boundary
        boundary = None
        for part in content_type.split(';'):
            part = part.strip()
            if part.startswith('boundary='):
                boundary = part.split('=', 1)[1].strip('"')
                break
        
        if not boundary:
            # Try to parse as JSON anyway
            return self._handle_json(body)
        
        # Split by boundary
        parts = body.split(f'--{boundary}'.encode())
        for part in parts:
            part = part.strip()
            if not part or part == b'--':
                continue
            
            # Find the JSON body in each part (after headers)
            if b'\r\n\r\n' in part:
                _, part_body = part.split(b'\r\n\r\n', 1)
            elif b'\n\n' in part:
                _, part_body = part.split(b'\n\n', 1)
            else:
                continue
            
            part_body = part_body.strip()
            if part_body:
                try:
                    events_saved += self._handle_json(part_body)
                except Exception:
                    pass
        
        return events_saved
    
    def _handle_xml(self, body: bytes) -> int:
        """Handle XML event data"""
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(body)
            
            # Extract all text content into a dict
            event_data = {}
            for child in root.iter():
                tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                if child.text and child.text.strip():
                    event_data[tag] = child.text.strip()
            
            if event_data and self._save_pushed_event(event_data):
                return 1
        except Exception as e:
            logger.warning(f"XML parse error: {e}")
        
        return 0
    
    def _handle_raw(self, body: bytes) -> int:
        """Handle raw/unknown event data — save it anyway"""
        logger.info(f"Raw data received ({len(body)} bytes)")
        event_data = {
            'raw_body': body.decode('utf-8', errors='replace')[:5000],
            'received_at': datetime.now().isoformat()
        }
        if self._save_pushed_event(event_data):
            return 1
        return 0
    
    def _save_pushed_event(self, event: Dict[str, Any]) -> bool:
        """Save a pushed event to database"""
        if not DB_AVAILABLE:
            logger.warning("Database not available — event lost")
            return False
        
        try:
            db = get_db()
            device_ip = self.client_address[0] if self.client_address else 'unknown'
            
            # Extract fields from various Hikvision formats
            serial_no = event.get('serialNo') or event.get('eventId')
            employee_no = event.get('employeeNoString') or ''
            if not employee_no:
                raw_no = event.get('employeeNo')
                if raw_no is not None:
                    employee_no = str(raw_no)
            employee_no = employee_no.strip() if employee_no else None
            
            emp_name = event.get('name') or event.get('eventDescription') or ''
            emp_name = emp_name.strip() if emp_name else None
            
            occur_time = event.get('time') or event.get('dateTime') or event.get('eventTime')
            if occur_time and '+' in str(occur_time):
                occur_time = str(occur_time).split('+')[0]
            try:
                if occur_time:
                    occur_time = datetime.fromisoformat(str(occur_time))
                else:
                    occur_time = datetime.now()
            except Exception:
                occur_time = datetime.now()
            
            event_data = {
                'device_ip': device_ip,
                'device_id': event.get('deviceName') or event.get('deviceID') or os.getenv('DEVICE_ID', 'door1'),
                'event_type': event.get('eventType') or 'AccessControllerEvent',
                'event_state': event.get('eventState') or 'active',
                'occur_time': occur_time,
                'employee_no': employee_no,
                'name': emp_name,
                'card_no': event.get('cardNo'),
                'door_no': event.get('doorNo'),
                'verify_no': event.get('verifyNo'),
                'verify_mode': event.get('currentVerifyMode'),
                'major_event_type': event.get('major'),
                'sub_event_type': event.get('minor'),
                'serial_no': serial_no,
                'mac_address': event.get('macAddress'),
                'channel_id': event.get('channelID'),
                'protocol': 'PUSH',
                'port_no': None,
                'device_name': event.get('deviceName'),
                'card_type': event.get('cardType'),
                'card_reader_kind': event.get('cardReaderKind'),
                'attendance_status': event.get('attendanceStatus'),
                'mask': event.get('mask'),
                'helmet': event.get('helmet'),
                'raw_json': json.dumps(event, default=str),
                'json_file_path': None,
                'sync_status': 'pending',
                'sync_attempts': 0
            }
            
            # Check for duplicate by serial_no
            if serial_no:
                conn = None
                cursor = None
                try:
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute('SELECT 1 FROM events WHERE serial_no = %s LIMIT 1', (serial_no,))
                    if cursor.fetchone():
                        return False  # Already exists
                finally:
                    if cursor:
                        try: cursor.close()
                        except Exception: pass
                    if conn:
                        try: conn.close()
                        except Exception: pass
            
            event_id = db.insert_event(event_data)
            if event_id:
                logger.info(f"📥 Pushed event saved: ID={event_id}, serial={serial_no}, employee={employee_no or '-'}, name={emp_name or '-'}")
                
                # Try to sync to webhook immediately
                self._sync_to_webhook(event_id, event_data)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error saving pushed event: {e}\n{traceback.format_exc()}")
            return False
    
    def _sync_to_webhook(self, event_id: int, event_data: Dict[str, Any]):
        """Sync event to webhook in background"""
        try:
            webhook_url = None
            webhook_api_key = None
            
            db = get_db()
            config = db.get_config('webhook_url')
            if config and config.get('value'):
                webhook_url = config['value']
                key_config = db.get_config('webhook_api_key')
                if key_config:
                    webhook_api_key = key_config.get('value')
            
            if not webhook_url:
                webhook_url = os.getenv('WEBHOOK_URL')
                webhook_api_key = os.getenv('WEBHOOK_API_KEY')
            
            if not webhook_url:
                return
            
            import requests
            
            # Clean datetime for JSON
            occur_time = event_data.get('occur_time')
            if hasattr(occur_time, 'isoformat'):
                occur_time = occur_time.isoformat()
            
            payload = {
                'serial_no': event_data.get('serial_no'),
                'employee_no': event_data.get('employee_no'),
                'name': event_data.get('name'),
                'occur_time': occur_time,
                'event_type': event_data.get('event_type'),
                'door_no': event_data.get('door_no'),
                'verify_mode': event_data.get('verify_mode'),
                'device_ip': event_data.get('device_ip'),
                'device_id': event_data.get('device_id'),
                'major_event_type': event_data.get('major_event_type'),
                'sub_event_type': event_data.get('sub_event_type'),
                'card_no': event_data.get('card_no'),
                'protocol': 'PUSH',
            }
            payload = {k: v for k, v in payload.items() if v is not None}
            
            headers = {'Content-Type': 'application/json', 'User-Agent': 'HikvisionListener/1.0'}
            if webhook_api_key:
                headers['X-API-Key'] = webhook_api_key
            
            resp = requests.post(webhook_url, json={'events': [payload]}, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                db.update_sync_status(event_id, 'synced', response='Push+sync')
                logger.info(f"✅ Pushed event {event_id} synced to webhook")
            else:
                db.update_sync_status(event_id, 'failed', error=f'HTTP {resp.status_code}')
                
        except Exception as e:
            logger.debug(f"Webhook sync skipped: {e}")


class EventListener:
    """Manages the HTTP listener server"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 8090):
        self.host = host
        self.port = port
        self.server = None
        self.thread = None
    
    def start(self, background: bool = True):
        """Start the listener"""
        self.server = HTTPServer((self.host, self.port), EventListenerHandler)
        
        if background:
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            logger.info(f"📡 Event listener started on {self.host}:{self.port} (background)")
        else:
            logger.info(f"📡 Event listener started on {self.host}:{self.port}")
            self.server.serve_forever()
    
    def stop(self):
        """Stop the listener"""
        if self.server:
            self.server.shutdown()
            logger.info("Event listener stopped")
    
    def is_running(self) -> bool:
        """Check if listener is running"""
        return self.thread is not None and self.thread.is_alive()


# Standalone mode
if __name__ == '__main__':
    port = int(os.getenv('LISTENER_PORT', '8090'))
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('event_listener.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    print(f"Starting Hikvision Event Listener on port {port}")
    print(f"Configure your Hikvision device to push events to http://<this-server-ip>:{port}/")
    
    listener = EventListener(port=port)
    try:
        listener.start(background=False)
    except KeyboardInterrupt:
        listener.stop()
