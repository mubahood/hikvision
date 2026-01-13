# Hikvision Bridge → EHRMS EventLog Integration

## Overview

The Hikvision Bridge now sends events in batches to the EHRMS EventLog system via webhook API.

---

## ✅ What's Been Implemented

### 1. Laravel EHRMS Backend

#### EventLog Model & Migration
- **Location**: `app/Models/EventLog.php`
- **Migration**: `database/migrations/2026_01_13_000001_create_event_logs_table.php`
- **Status**: ✅ Migration run, table created
- **Fields**:
  - `event_serial` - Unique identifier from Hikvision (indexed)
  - `employee_no` - Employee number
  - `employee_name` - Employee name
  - `event_time` - When event occurred
  - `door_name` - Door identifier
  - `major_event_type` - Event major code
  - `minor_event_type` - Event minor code (75 = face recognition)
  - `verification_method` - face/card/PIN
  - `device_name` - Device identifier
  - `device_ip` - Device IP address
  - `process_status` - unprocessed/processed/failed
  - `error_message` - Processing errors
  - `processed_at` - Processing timestamp
  - `raw_data` - Full JSON from Hikvision

#### Webhook API Controller
- **Location**: `app/Http/Controllers/WebhookController.php`
- **Endpoints**:
  - `POST /api/webhook/events` - Single event (legacy)
  - `POST /api/webhook/events/batch` - Batch upload (current)
- **Features**:
  - Token authentication via X-API-Key header
  - Duplicate prevention via `event_serial`
  - JSON validation
  - Batch processing with status report

#### Admin Interface
- **Location**: `app/Admin/Controllers/EventLogController.php`
- **URL**: http://localhost:8888/muni-ehrms/admin/event-logs
- **Features**:
  - Grid view with filters
  - Search by employee/serial
  - Status badges (color-coded)
  - Export functionality
  - Detail view with JSON viewer
- **Status**: ✅ Menu item added to admin panel

### 2. Hikvision Bridge Updates

#### Batch Upload System
- **File**: `hikvision_bridge.py`
- **Changes**:
  - Added `event_batch` queue
  - Modified `_sync_event_immediately()` to queue events
  - New `_upload_batch()` method for bulk uploads
  - Automatic batch upload when queue reaches `BATCH_UPLOAD_SIZE`
  - Graceful shutdown uploads remaining events
  
#### Configuration
- **File**: `.env.example`
- **New Variables**:
  ```bash
  # Webhook endpoint (without /batch)
  WEBHOOK_URL=http://localhost:8888/muni-ehrms/api/webhook/events
  
  # API authentication key
  WEBHOOK_API_KEY=your_api_key_here
  
  # Events per batch (default: 10)
  BATCH_UPLOAD_SIZE=10
  ```

#### Payload Format
The bridge now sends events in this format:
```json
{
  "events": [
    {
      "event_serial": "12345-67890",
      "employee_no": "10001",
      "employee_name": "John Doe",
      "event_time": "2026-01-12T14:30:00",
      "door_name": "1",
      "major_event_type": 5,
      "minor_event_type": 75,
      "verification_method": "face",
      "device_name": "door1",
      "device_ip": "192.168.1.128",
      "raw_data": { /* full event */ }
    }
  ]
}
```

#### Response Format
Backend responds with:
```json
{
  "success": true,
  "success_count": 8,
  "duplicate_count": 2,
  "failed_count": 0,
  "total_received": 10
}
```

### 3. Testing Tool
- **File**: `test_webhook.py`
- **Purpose**: Test webhook connectivity before running bridge
- **Usage**: `python3 test_webhook.py`

---

## 🚀 Setup Instructions

### Step 1: Configure Laravel Backend

1. Add to `.env`:
   ```bash
   # Add webhook token (used by bridge)
   HIKVISION_WEBHOOK_TOKEN=your_secure_random_token_here
   ```

2. Verify EventLog menu appears in admin panel:
   - Login to http://localhost:8888/muni-ehrms/admin
   - Look for "Event Logs" in sidebar

### Step 2: Configure Bridge

1. Edit `/Users/mac/Desktop/github/hikvision/.env`:
   ```bash
   # Webhook Configuration
   WEBHOOK_URL=http://localhost:8888/muni-ehrms/api/webhook/events
   WEBHOOK_API_KEY=your_secure_random_token_here  # Same as Laravel .env
   
   # Batch settings
   BATCH_UPLOAD_SIZE=10  # Upload every 10 events
   ```

### Step 3: Test Connection

1. Run test script:
   ```bash
   cd /Users/mac/Desktop/github/hikvision
   python3 test_webhook.py
   ```

2. Check for success:
   ```
   ✅ Test successful!
      - Success: 2
      - Duplicates: 0
      - Failed: 0
   ```

3. Verify in admin panel:
   - Go to Event Logs
   - Look for TEST-001 and TEST-002 entries

### Step 4: Start Bridge

```bash
cd /Users/mac/Desktop/github/hikvision
./start.sh
```

Watch logs for batch uploads:
```
📤 Uploading batch of 10 events...
✅ Batch uploaded: 10 saved, 0 duplicates, 0 failed
```

---

## 📊 Monitoring

### Bridge Logs
```bash
tail -f /Users/mac/Desktop/github/hikvision/hikvision_bridge.log
```

Look for:
- `📤 Uploading batch of X events...` - Batch started
- `✅ Batch uploaded: X saved, Y duplicates, Z failed` - Success
- `❌ Batch upload failed` - Error

### Laravel Logs
```bash
tail -f /Applications/MAMP/htdocs/muni-ehrms/storage/logs/laravel.log
```

### Admin Panel
- URL: http://localhost:8888/muni-ehrms/admin/event-logs
- Filter by:
  - Process status (unprocessed/processed/failed)
  - Employee number
  - Date range
- Search by serial number or employee name

---

## 🔧 Troubleshooting

### Events Not Appearing

1. **Check Bridge Connection**:
   ```bash
   python3 test_webhook.py
   ```

2. **Verify API Token Matches**:
   - Bridge `.env`: `WEBHOOK_API_KEY=xxx`
   - Laravel `.env`: `HIKVISION_WEBHOOK_TOKEN=xxx`
   - Must be identical

3. **Check Laravel Route**:
   ```bash
   cd /Applications/MAMP/htdocs/muni-ehrms
   php artisan route:list | grep webhook
   ```
   Should show: `POST api/webhook/events/batch`

### Duplicate Events

- Events are deduplicated by `event_serial`
- Duplicates are counted but not inserted
- Check response: `"duplicate_count": X`

### Processing Errors

1. Check EventLog grid for errors:
   - Red badge = failed processing
   - Click to view error message

2. Reprocess failed events:
   ```php
   $failed = EventLog::where('process_status', 'failed')->get();
   // Implement retry logic in future
   ```

---

## 🎯 Next Steps

### Immediate
1. ✅ Test webhook endpoint
2. ✅ Configure both systems
3. ✅ Start bridge and verify events flow

### Future Enhancements
1. **Auto-processing**: Link events to attendance records
2. **Real-time Dashboard**: Show live event feed
3. **Retry Logic**: Auto-retry failed uploads
4. **Notifications**: Alert on processing errors
5. **Analytics**: Event statistics and reporting

---

## 📁 File Reference

### Laravel Files
```
/Applications/MAMP/htdocs/muni-ehrms/
├── app/
│   ├── Models/EventLog.php
│   ├── Admin/Controllers/EventLogController.php
│   └── Http/Controllers/WebhookController.php
├── database/migrations/2026_01_13_000001_create_event_logs_table.php
└── routes/api.php (webhook routes)
```

### Bridge Files
```
/Users/mac/Desktop/github/hikvision/
├── hikvision_bridge.py (batch upload logic)
├── test_webhook.py (connectivity tester)
├── .env (configuration)
└── README.md (updated documentation)
```

---

## 🔐 Security Notes

- **API Token**: Use strong random string (32+ chars)
- **HTTPS**: Use in production (not localhost)
- **Token Rotation**: Change periodically
- **IP Whitelist**: Consider restricting webhook access
- **Rate Limiting**: Add if needed in WebhookController

---

## 📈 Performance

- **Batch Size**: Default 10 events
  - Lower = More frequent uploads, more overhead
  - Higher = Less frequent, risk losing more on crash
  
- **Poll Interval**: Default 2 seconds
  - Adjust based on event frequency
  
- **Database**: Indexed on `event_serial` for fast duplicate checks

---

## Support

For issues:
1. Check logs (both systems)
2. Run test_webhook.py
3. Verify configurations match
4. Check network connectivity

---

**Status**: ✅ Ready for testing  
**Last Updated**: 2026-01-13  
**Version**: 1.0.0
