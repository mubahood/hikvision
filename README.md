# 🛡️ HikVision Bulletproof

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.30+-red.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**A production-ready Python bridge for Hikvision DS-K1T680 series face recognition terminals.** Captures access control events via ISAPI polling, stores them in MySQL, and syncs to your backend webhook in real-time.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Real-time Event Capture** | Polls Hikvision device every 2 seconds for face recognition events |
| **MySQL Storage** | All events stored with full metadata, JSON backup, and sync status |
| **Auto Webhook Sync** | Automatically POSTs events to your Laravel/PHP backend |
| **Modern Dashboard** | Streamlit-based UI with live monitoring, statistics, and controls |
| **Device Sync** | Manual sync up to 1000 historical events from device |
| **Upload Sync** | Batch upload pending/failed events to webhook |
| **Process Management** | Start/stop/restart bridge from dashboard |
| **Bulletproof Design** | Handles connection drops, retries failed syncs, duplicate detection |

---

## 🏗️ Architecture

```
┌─────────────────┐    ISAPI/HTTP     ┌──────────────────┐
│   Hikvision     │◄─────────────────►│  Python Bridge   │
│   DS-K1T680DF   │   (Polling)       │  hikvision_bridge│
└─────────────────┘                   └────────┬─────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
                    ▼                          ▼                          ▼
           ┌────────────────┐         ┌────────────────┐         ┌────────────────┐
           │     MySQL      │         │   JSON Files   │         │    Webhook     │
           │   Database     │         │   (Backup)     │         │   (Laravel)    │
           └────────────────┘         └────────────────┘         └────────────────┘
                    │
                    ▼
           ┌────────────────┐
           │   Streamlit    │
           │   Dashboard    │
           └────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- MySQL 5.7+ or MariaDB 10.3+
- Hikvision DS-K1T680 series terminal on same network

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/hikvision-bulletproof.git
cd hikvision-bulletproof

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
nano .env  # Edit with your settings
```

### 3. Setup Database

```bash
mysql -u root -p < create_tables.sql
```

### 4. Run

**Quick Start (Recommended):**
```bash
./start.sh          # Starts bridge + dashboard
./stop.sh           # Stops everything
```

**Manual:**
```bash
# Terminal 1: Start Bridge
python hikvision_bridge.py

# Terminal 2: Start Dashboard
streamlit run dashboard.py --server.port 8502
```

### 5. Access Dashboard

Open **http://localhost:8502** in your browser.

---

## ⚙️ Configuration

Create a `.env` file with:

```env
# Device Configuration
DEVICE_IP=192.168.1.128
DEVICE_USER=admin
DEVICE_PASS=your_device_password

# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_NAME=hikvision
DB_USER=root
DB_PASS=your_db_password

# Webhook Configuration (optional)
WEBHOOK_URL=https://your-backend.com/api/hikvision/events
WEBHOOK_API_KEY=your_api_key_here

# Optional Settings
DEVICE_ID=door1
POLL_INTERVAL=2
LOG_LEVEL=INFO
```

---

## 📊 Dashboard Pages

| Page | Description |
|------|-------------|
| **Overview** | System status, today's stats, recent events, quick actions |
| **Events** | Browse all events, filter by date/type, view details |
| **Statistics** | Charts for activity trends, top users, door usage |
| **Bridge Control** | Start/stop bridge, view live events and logs |
| **Device Sync** | Manually sync events from device to database |
| **Upload Sync** | Sync pending events to webhook, retry failed |
| **Logs** | Full bridge logs with filtering |
| **Settings** | Webhook configuration, test connectivity |
| **Configuration** | Device settings, system settings |

---

## 🔌 Webhook Integration

Events are POSTed to your webhook URL as JSON:

```json
{
  "event_id": 123,
  "device_id": "door1",
  "device_ip": "192.168.1.128",
  "event_type": "AccessControllerEvent",
  "employee_no": "10001",
  "name": "John Doe",
  "door_no": 1,
  "verify_mode": "face",
  "occur_time": "2026-01-12T14:30:00",
  "attendance_status": "checkIn",
  "serial_no": 12345
}
```

**Headers:**
- `Content-Type: application/json`
- `X-API-Key: your_api_key_here`
- `User-Agent: HikvisionBridge/1.0`

**Expected Response:** HTTP 200 OK

---

## 🗄️ Database Schema

```sql
CREATE TABLE events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_ip VARCHAR(45) NOT NULL,
    device_id VARCHAR(50) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    occur_time DATETIME NOT NULL,
    employee_no VARCHAR(50),
    name VARCHAR(100),
    card_no VARCHAR(50),
    door_no INT,
    verify_mode VARCHAR(50),
    serial_no INT,
    sync_status ENUM('pending', 'synced', 'failed') DEFAULT 'pending',
    sync_attempts INT DEFAULT 0,
    synced_at DATETIME,
    sync_error TEXT,
    raw_json JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_occur_time (occur_time),
    INDEX idx_sync_status (sync_status),
    UNIQUE KEY unique_serial (device_id, serial_no)
);
```

---

## 🛠️ Troubleshooting

### Device Connection Failed
```bash
# Test device connectivity
curl -v --digest -u admin:password http://192.168.1.128/ISAPI/System/deviceInfo
```

### No Events Captured
1. Ensure device is on same network
2. Check device password (note: may end with `.`)
3. Verify ISAPI is enabled on device

### Webhook Sync Failed
1. Test webhook URL manually
2. Check API key is correct
3. Check `sync_error` column in events table

---

## 📁 Project Structure

```
hikvision-bulletproof/
├── hikvision_bridge.py          # Main bridge (polling + sync)
├── dashboard.py                 # Streamlit dashboard
├── database.py                  # MySQL connection
├── controllers/
│   ├── event_controller.py      # Event operations
│   ├── config_controller.py     # Configuration
│   ├── bridge_controller.py     # Process control
│   ├── device_controller.py     # Device communication
│   └── upload_sync_controller.py # Webhook sync
├── models/
│   ├── event.py                 # Event model
│   └── config.py                # Config model
├── create_tables.sql            # Database schema
├── requirements.txt             # Dependencies
├── start.sh / stop.sh           # Run scripts
└── .env.example                 # Config template
```

---

## 🔒 Security

- Store credentials in `.env` (never commit)
- Use HTTPS for webhook in production
- Firewall device access appropriately
- Database should not be public

---

## 📝 License

MIT License - free for personal and commercial use.

---

**Made with ❤️ for access control integration**
