"""
Database module for Hikvision Bridge
Handles all MySQL database operations
"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import mysql.connector
from mysql.connector import pooling, Error
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Database:
    """MySQL database manager with connection pooling"""
    
    def __init__(self):
        """Initialize database connection pool"""
        self.pool = None
        self._create_pool()
    
    def _create_pool(self):
        """Create MySQL connection pool"""
        try:
            db_config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': int(os.getenv('DB_PORT', 3306)),
                'user': os.getenv('DB_USER', 'root'),
                'password': os.getenv('DB_PASS', 'root'),
                'database': os.getenv('DB_NAME', 'hikvision'),
                'charset': 'utf8mb4',
                'collation': 'utf8mb4_unicode_ci',
                'autocommit': True
            }
            
            # Only use unix_socket if explicitly set in .env
            db_socket = os.getenv('DB_SOCKET', '').strip()
            if db_socket:
                db_config['unix_socket'] = db_socket
            
            self.pool = pooling.MySQLConnectionPool(
                pool_name="hikvision_pool",
                pool_size=5,
                pool_reset_session=True,
                **db_config
            )
            logger.info("Database connection pool created successfully")
            
        except Error as e:
            logger.error(f"Error creating database pool: {e}")
            raise
    
    def get_connection(self):
        """Get a connection from the pool"""
        try:
            return self.pool.get_connection()
        except Error as e:
            logger.error(f"Error getting connection from pool: {e}")
            raise
    
    def insert_event(self, event_data: Dict[str, Any]) -> Optional[int]:
        """
        Insert an event into the database
        
        Args:
            event_data: Dictionary containing event information
            
        Returns:
            Event ID if successful, None otherwise
        """
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            sql = """
            INSERT INTO events (
                device_ip, device_id, event_type, event_state, occur_time,
                employee_no, name, card_no, door_no, verify_no, verify_mode,
                major_event_type, sub_event_type, serial_no, mac_address,
                channel_id, protocol, port_no, device_name, card_type,
                card_reader_kind, attendance_status, mask, helmet,
                raw_json, json_file_path, sync_status, sync_attempts
            ) VALUES (
                %(device_ip)s, %(device_id)s, %(event_type)s, %(event_state)s, %(occur_time)s,
                %(employee_no)s, %(name)s, %(card_no)s, %(door_no)s, %(verify_no)s, %(verify_mode)s,
                %(major_event_type)s, %(sub_event_type)s, %(serial_no)s, %(mac_address)s,
                %(channel_id)s, %(protocol)s, %(port_no)s, %(device_name)s, %(card_type)s,
                %(card_reader_kind)s, %(attendance_status)s, %(mask)s, %(helmet)s,
                %(raw_json)s, %(json_file_path)s, %(sync_status)s, %(sync_attempts)s
            )
            """
            
            # Convert occur_time to datetime if it's a string
            if isinstance(event_data.get('occur_time'), str):
                try:
                    # Handle ISO format with timezone
                    occur_time_str = event_data['occur_time']
                    if '+' in occur_time_str:
                        occur_time_str = occur_time_str.split('+')[0]
                    event_data['occur_time'] = datetime.fromisoformat(occur_time_str)
                except:
                    event_data['occur_time'] = datetime.now()
            
            # Convert raw_json to string if it's a dict
            if isinstance(event_data.get('raw_json'), dict):
                import json
                event_data['raw_json'] = json.dumps(event_data['raw_json'])
            
            # Ensure all required keys exist with default None values
            all_fields = [
                'device_ip', 'device_id', 'event_type', 'event_state', 'occur_time',
                'employee_no', 'name', 'card_no', 'door_no', 'verify_no', 'verify_mode',
                'major_event_type', 'sub_event_type', 'serial_no', 'mac_address',
                'channel_id', 'protocol', 'port_no', 'device_name', 'card_type',
                'card_reader_kind', 'attendance_status', 'mask', 'helmet',
                'raw_json', 'json_file_path', 'sync_status', 'sync_attempts'
            ]
            for field in all_fields:
                if field not in event_data:
                    event_data[field] = None
            
            # Set default sync values
            if event_data.get('sync_status') is None:
                event_data['sync_status'] = 'pending'
            if event_data.get('sync_attempts') is None:
                event_data['sync_attempts'] = 0
            
            cursor.execute(sql, event_data)
            event_id = cursor.lastrowid
            
            logger.info(f"Event inserted with ID: {event_id}")
            return event_id
            
        except Error as e:
            logger.error(f"Error inserting event: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def get_events(self, limit: int = 100, offset: int = 0, 
                   filters: Optional[Dict] = None) -> List[Dict]:
        """
        Get events from database with optional filters
        
        Args:
            limit: Maximum number of events to return
            offset: Number of events to skip
            filters: Dictionary of filter conditions
            
        Returns:
            List of event dictionaries
        """
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = "SELECT * FROM events WHERE 1=1"
            params = []
            
            if filters:
                if 'start_date' in filters:
                    sql += " AND occur_time >= %s"
                    params.append(filters['start_date'])
                if 'end_date' in filters:
                    sql += " AND occur_time <= %s"
                    params.append(filters['end_date'])
                if 'event_type' in filters:
                    sql += " AND event_type = %s"
                    params.append(filters['event_type'])
                if 'employee_no' in filters:
                    sql += " AND employee_no = %s"
                    params.append(filters['employee_no'])
                if 'door_no' in filters:
                    sql += " AND door_no = %s"
                    params.append(filters['door_no'])
            
            sql += " ORDER BY occur_time DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cursor.execute(sql, params)
            return cursor.fetchall()
            
        except Error as e:
            logger.error(f"Error fetching events: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def get_event_count(self, filters: Optional[Dict] = None) -> int:
        """Get total count of events"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            sql = "SELECT COUNT(*) FROM events WHERE 1=1"
            params = []
            
            if filters:
                if 'start_date' in filters:
                    sql += " AND occur_time >= %s"
                    params.append(filters['start_date'])
                if 'end_date' in filters:
                    sql += " AND occur_time <= %s"
                    params.append(filters['end_date'])
            
            cursor.execute(sql, params)
            return cursor.fetchone()[0]
            
        except Error as e:
            logger.error(f"Error counting events: {e}")
            return 0
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def get_today_stats(self) -> Dict:
        """Get statistics for today"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("SELECT * FROM event_stats_today")
            result = cursor.fetchone()
            return result if result else {}
            
        except Error as e:
            logger.error(f"Error fetching today stats: {e}")
            return {}
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def get_hourly_stats(self, days: int = 7) -> List[Dict]:
        """Get hourly event statistics"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("SELECT * FROM event_stats_by_hour LIMIT %s", (days * 24,))
            return cursor.fetchall()
            
        except Error as e:
            logger.error(f"Error fetching hourly stats: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def get_top_users(self, limit: int = 10) -> List[Dict]:
        """Get top users by access count"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("SELECT * FROM top_users LIMIT %s", (limit,))
            return cursor.fetchall()
            
        except Error as e:
            logger.error(f"Error fetching top users: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def update_bridge_status(self, status: str, pid: Optional[int] = None, 
                            error: Optional[str] = None):
        """Update bridge status"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            sql = """
            INSERT INTO bridge_status (status, pid, started_at, error_message)
            VALUES (%s, %s, %s, %s)
            """
            
            cursor.execute(sql, (status, pid, datetime.now() if status == 'running' else None, error))
            logger.info(f"Bridge status updated: {status}")
            
        except Error as e:
            logger.error(f"Error updating bridge status: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def get_latest_bridge_status(self) -> Optional[Dict]:
        """Get latest bridge status"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("SELECT * FROM bridge_status ORDER BY created_at DESC LIMIT 1")
            return cursor.fetchone()
            
        except Error as e:
            logger.error(f"Error fetching bridge status: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def get_config(self, key: Optional[str] = None) -> Dict:
        """Get configuration value(s)"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            if key:
                cursor.execute("SELECT * FROM config WHERE key_name = %s", (key,))
                result = cursor.fetchone()
                return result if result else {}
            else:
                cursor.execute("SELECT * FROM config")
                results = cursor.fetchall()
                return {row['key_name']: row['value'] for row in results}
            
        except Error as e:
            logger.error(f"Error fetching config: {e}")
            return {}
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def update_config(self, key: str, value: str):
        """Update configuration value"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            sql = """
            INSERT INTO config (key_name, value)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE value = %s
            """
            
            cursor.execute(sql, (key, value, value))
            logger.info(f"Config updated: {key} = {value}")
            
        except Error as e:
            logger.error(f"Error updating config: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def update_sync_status(self, event_id: int, status: str, 
                          error: Optional[str] = None, 
                          response: Optional[str] = None) -> bool:
        """
        Update sync status for an event
        
        Args:
            event_id: The event ID to update
            status: 'pending', 'synced', or 'failed'
            error: Error message if failed
            response: Webhook response if successful
            
        Returns:
            True if successful, False otherwise
        """
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if status == 'synced':
                sql = """
                UPDATE events 
                SET sync_status = %s, 
                    synced_at = NOW(),
                    sync_attempts = sync_attempts + 1,
                    webhook_response = %s,
                    sync_error = NULL
                WHERE id = %s
                """
                cursor.execute(sql, (status, response, event_id))
            else:
                sql = """
                UPDATE events 
                SET sync_status = %s,
                    sync_attempts = sync_attempts + 1,
                    sync_error = %s
                WHERE id = %s
                """
                cursor.execute(sql, (status, error, event_id))
            
            logger.info(f"Event {event_id} sync status updated to: {status}")
            return True
            
        except Error as e:
            logger.error(f"Error updating sync status: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def get_pending_sync_events(self, limit: int = 100) -> List[Dict]:
        """
        Get events pending sync
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of event dictionaries
        """
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = """
            SELECT * FROM events 
            WHERE sync_status = 'pending' OR (sync_status = 'failed' AND sync_attempts < 5)
            ORDER BY occur_time ASC 
            LIMIT %s
            """
            cursor.execute(sql, (limit,))
            return cursor.fetchall()
            
        except Error as e:
            logger.error(f"Error fetching pending sync events: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def get_sync_stats(self) -> Dict:
        """Get sync statistics"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = """
            SELECT 
                sync_status,
                COUNT(*) as count
            FROM events
            GROUP BY sync_status
            """
            cursor.execute(sql)
            results = cursor.fetchall()
            return {row['sync_status']: row['count'] for row in results}
            
        except Error as e:
            logger.error(f"Error fetching sync stats: {e}")
            return {}
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()


# Global database instance
_db_instance = None

def get_db() -> Database:
    """Get global database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
