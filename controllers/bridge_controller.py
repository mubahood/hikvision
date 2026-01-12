"""
Bridge Controller
Advanced controller for managing the Hikvision bridge process
Provides start/stop/restart, status monitoring, and live log streaming
"""

import subprocess
import os
import signal
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class BridgeController:
    """Controller for bridge service operations with advanced monitoring"""
    
    BRIDGE_SCRIPT = 'hikvision_bridge.py'
    LOG_FILE = 'hikvision_bridge.log'
    PID_FILE = 'bridge.pid'
    
    def __init__(self, base_path: str = None):
        if base_path:
            self.base_path = Path(base_path)
        else:
            self.base_path = Path(__file__).parent.parent
        
        self.pid_file = self.base_path / self.PID_FILE
        self.log_file = self.base_path / self.LOG_FILE
        self.script_path = self.base_path / self.BRIDGE_SCRIPT
        self.venv_python = self.base_path / '.venv' / 'bin' / 'python'
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive bridge status with process metrics"""
        status = {
            "running": False,
            "pid": None,
            "cpu_percent": None,
            "memory_mb": None,
            "uptime_seconds": None,
            "uptime_formatted": None,
            "started_at": None,
            "threads": None,
            "status_text": "Stopped",
        }
        
        # First check PID file
        pid = self._read_pid()
        
        # Also search for running process (in case PID file is missing)
        if not pid:
            pid = self._find_bridge_process()
        
        if pid and self._is_process_running(pid):
            status["running"] = True
            status["pid"] = pid
            status["status_text"] = "Running"
            
            # Get detailed metrics with psutil
            if PSUTIL_AVAILABLE:
                try:
                    proc = psutil.Process(pid)
                    status["cpu_percent"] = round(proc.cpu_percent(interval=0.1), 1)
                    status["memory_mb"] = round(proc.memory_info().rss / 1024 / 1024, 1)
                    status["threads"] = proc.num_threads()
                    
                    # Calculate uptime
                    create_time = proc.create_time()
                    status["started_at"] = datetime.fromtimestamp(create_time).strftime('%Y-%m-%d %H:%M:%S')
                    uptime = time.time() - create_time
                    status["uptime_seconds"] = int(uptime)
                    status["uptime_formatted"] = self._format_uptime(uptime)
                except Exception:
                    pass
        else:
            # Clean up stale PID file
            self._remove_pid_file()
        
        return status
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format"""
        seconds = int(seconds)
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            mins = seconds // 60
            secs = seconds % 60
            return f"{mins}m {secs}s"
        elif seconds < 86400:
            hours = seconds // 3600
            mins = (seconds % 3600) // 60
            return f"{hours}h {mins}m"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days}d {hours}h"
    
    def is_running(self) -> bool:
        """Quick check if bridge is running"""
        return self.get_status().get("running", False)
    
    def start(self) -> Dict[str, Any]:
        """Start the bridge process"""
        if self.is_running():
            return {"success": False, "message": "Bridge is already running"}
        
        # Verify script exists
        if not self.script_path.exists():
            return {"success": False, "message": f"Bridge script not found: {self.script_path}"}
        
        # Verify Python interpreter exists
        if not self.venv_python.exists():
            return {"success": False, "message": f"Python not found: {self.venv_python}"}
        
        try:
            # Start the bridge process
            process = subprocess.Popen(
                [str(self.venv_python), str(self.script_path)],
                stdout=open(self.log_file, 'a'),
                stderr=subprocess.STDOUT,
                cwd=str(self.base_path),
                start_new_session=True,  # Detach from terminal
                env={**os.environ, 'PYTHONUNBUFFERED': '1'}  # Unbuffered output
            )
            
            # Save PID
            self._write_pid(process.pid)
            
            # Wait a moment and verify it started
            time.sleep(1.5)
            
            if self._is_process_running(process.pid):
                return {
                    "success": True, 
                    "message": f"Bridge started (PID: {process.pid})",
                    "pid": process.pid
                }
            else:
                self._remove_pid_file()
                # Check log for errors
                recent_logs = self.get_logs(lines=10)
                error_hint = ""
                if "Error" in recent_logs or "error" in recent_logs:
                    error_hint = " Check logs for details."
                return {"success": False, "message": f"Bridge failed to start.{error_hint}"}
                
        except Exception as e:
            return {"success": False, "message": f"Error starting bridge: {str(e)}"}
    
    def stop(self) -> Dict[str, Any]:
        """Stop the bridge process gracefully"""
        status = self.get_status()
        
        if not status["running"]:
            self._remove_pid_file()
            return {"success": False, "message": "Bridge is not running"}
        
        pid = status["pid"]
        
        try:
            # Send SIGTERM for graceful shutdown
            os.kill(pid, signal.SIGTERM)
            
            # Wait for graceful shutdown (max 5 seconds)
            for _ in range(10):
                time.sleep(0.5)
                if not self._is_process_running(pid):
                    self._remove_pid_file()
                    return {"success": True, "message": "Bridge stopped gracefully"}
            
            # Force kill if still running
            try:
                os.kill(pid, signal.SIGKILL)
                time.sleep(0.5)
            except ProcessLookupError:
                pass
            
            self._remove_pid_file()
            return {"success": True, "message": "Bridge stopped (forced)"}
            
        except ProcessLookupError:
            self._remove_pid_file()
            return {"success": True, "message": "Bridge stopped"}
        except Exception as e:
            return {"success": False, "message": f"Error stopping bridge: {str(e)}"}
    
    def restart(self) -> Dict[str, Any]:
        """Restart the bridge process"""
        stop_result = self.stop()
        
        # Wait for process to fully terminate
        time.sleep(1)
        
        start_result = self.start()
        
        if start_result["success"]:
            return {"success": True, "message": "Bridge restarted successfully", "pid": start_result.get("pid")}
        else:
            return {"success": False, "message": f"Restart failed: {start_result['message']}"}
    
    def get_logs(self, lines: int = 50) -> str:
        """Get recent log content"""
        if not self.log_file.exists():
            return "No log file found. Bridge may not have run yet."
        
        try:
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                return ''.join(all_lines[-lines:])
        except Exception as e:
            return f"Error reading logs: {str(e)}"
    
    def get_log_lines(self, lines: int = 50, filter_text: str = None) -> List[Dict[str, Any]]:
        """Get recent log lines as structured data for display"""
        if not self.log_file.exists():
            return []
        
        try:
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                recent = all_lines[-lines:]
            
            result = []
            for line in recent:
                line = line.rstrip()
                if not line:
                    continue
                
                # Optional filtering
                if filter_text and filter_text.lower() not in line.lower():
                    continue
                
                # Determine log level/type for styling
                log_type = "info"
                if "ERROR" in line or "❌" in line:
                    log_type = "error"
                elif "WARNING" in line:
                    log_type = "warning"
                elif "✅" in line or "synced successfully" in line:
                    log_type = "success"
                elif "💾" in line or "saved to database" in line:
                    log_type = "database"
                elif "📊" in line or "Processed" in line:
                    log_type = "process"
                elif "🟢" in line or "running" in line.lower():
                    log_type = "running"
                
                result.append({
                    "text": line,
                    "type": log_type
                })
            
            return result
        except Exception:
            return []
    
    def get_recent_events_from_log(self, lines: int = 20) -> List[Dict[str, Any]]:
        """Extract recent event notifications from log"""
        log_lines = self.get_log_lines(lines=200)
        events = []
        
        for entry in log_lines:
            line = entry["text"]
            # Look for event lines
            if "New event:" in line or "Event captured:" in line:
                events.append({
                    "text": line,
                    "type": "event"
                })
            elif "Event #" in line and "synced" in line:
                events.append({
                    "text": line,
                    "type": "sync"
                })
            elif "saved to database" in line:
                events.append({
                    "text": line,
                    "type": "database"
                })
        
        return events[-lines:]
    
    def clear_logs(self) -> Dict[str, Any]:
        """Clear the log file"""
        try:
            if self.log_file.exists():
                with open(self.log_file, 'w') as f:
                    f.write(f"--- Log cleared at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                return {"success": True, "message": "Logs cleared"}
            return {"success": False, "message": "Log file not found"}
        except Exception as e:
            return {"success": False, "message": f"Error clearing logs: {str(e)}"}
    
    def get_log_file_size(self) -> str:
        """Get log file size in human-readable format"""
        if not self.log_file.exists():
            return "0 B"
        
        size = self.log_file.stat().st_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    # Private helper methods
    
    def _read_pid(self) -> Optional[int]:
        """Read PID from file"""
        if not self.pid_file.exists():
            return None
        try:
            with open(self.pid_file, 'r') as f:
                return int(f.read().strip())
        except (ValueError, IOError):
            return None
    
    def _write_pid(self, pid: int):
        """Write PID to file"""
        try:
            with open(self.pid_file, 'w') as f:
                f.write(str(pid))
        except IOError:
            pass
    
    def _remove_pid_file(self):
        """Remove PID file"""
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
        except IOError:
            pass
    
    def _is_process_running(self, pid: int) -> bool:
        """Check if process with given PID is running and is our bridge"""
        if not pid:
            return False
        
        try:
            if PSUTIL_AVAILABLE:
                proc = psutil.Process(pid)
                cmdline = ' '.join(proc.cmdline())
                return proc.is_running() and self.BRIDGE_SCRIPT in cmdline
            else:
                # Fallback: send signal 0 to check if process exists
                os.kill(pid, 0)
                return True
        except (psutil.NoSuchProcess, ProcessLookupError, PermissionError):
            return False
        except Exception:
            return False
    
    def _find_bridge_process(self) -> Optional[int]:
        """Find bridge process by searching running processes"""
        if not PSUTIL_AVAILABLE:
            return None
        
        try:
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info.get('cmdline', []))
                    if self.BRIDGE_SCRIPT in cmdline and 'python' in cmdline.lower():
                        return proc.info['pid']
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        
        return None
