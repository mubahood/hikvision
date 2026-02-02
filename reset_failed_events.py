#!/usr/bin/env python3
"""
Reset failed events to pending for automatic retry
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from controllers.upload_sync_controller import UploadSyncController

def reset_failed_events():
    """Reset all failed events to pending status"""
    
    print("=" * 60)
    print("Resetting Failed Events to Pending")
    print("=" * 60)
    
    sync_controller = UploadSyncController()
    
    # Get current sync stats
    stats = sync_controller.get_sync_stats()
    overall = stats.get('overall', {})
    
    print(f"Current status:")
    print(f"  - Total: {overall.get('total', 0)}")
    print(f"  - Synced: {overall.get('synced', 0)}")
    print(f"  - Pending: {overall.get('pending', 0)}")
    print(f"  - Failed: {overall.get('failed', 0)}")
    
    if overall.get('failed', 0) == 0:
        print("✅ No failed events to reset")
        return True
    
    # Reset failed events
    result = sync_controller.reset_failed_events()
    
    if result.get('success', False):
        affected = result.get('affected', 0)
        print(f"✅ Reset {affected} failed events to pending status")
        print("These events will now be retried automatically by the bridge")
        return True
    else:
        print(f"❌ Failed to reset events: {result.get('message', 'Unknown error')}")
        return False

if __name__ == "__main__":
    reset_failed_events()