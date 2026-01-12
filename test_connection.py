#!/usr/bin/env python3
"""
Test script to verify Hikvision device connectivity without locking the account
"""

import os
import sys
import xml.etree.ElementTree as ET
from requests.auth import HTTPDigestAuth
import requests
from dotenv import load_dotenv

load_dotenv()

DEVICE_IP = os.getenv('DEVICE_IP', '192.168.1.128')
DEVICE_USER = os.getenv('DEVICE_USER', 'admin')
DEVICE_PASS = os.getenv('DEVICE_PASS', '')

def check_device_status():
    """Check device lock status"""
    url = f"http://{DEVICE_IP}/ISAPI/System/deviceInfo"
    auth = HTTPDigestAuth(DEVICE_USER, DEVICE_PASS)
    
    print(f"\n🔍 Checking device at {DEVICE_IP}...")
    print(f"   Username: {DEVICE_USER}")
    print(f"   Password: {'*' * len(DEVICE_PASS)}")
    
    try:
        response = requests.get(url, auth=auth, timeout=5)
        
        print(f"\n📡 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Authentication successful!")
            print("\nDevice Info:")
            print(response.text[:500])
            return True
            
        elif response.status_code == 401:
            print("❌ Authentication failed (401)")
            
            # Parse the error response
            try:
                root = ET.fromstring(response.content)
                
                is_activated = root.find('.//isActivated')
                lock_status = root.find('.//lockStatus')
                unlock_time = root.find('.//unlockTime')
                
                if is_activated is not None:
                    print(f"   Device Activated: {is_activated.text}")
                
                if lock_status is not None and lock_status.text == 'lock':
                    print(f"   ⚠️  DEVICE IS LOCKED")
                    if unlock_time is not None:
                        seconds = int(unlock_time.text)
                        minutes = seconds // 60
                        print(f"   ⏰  Unlock in: {minutes} minutes {seconds % 60} seconds")
                    print("\n   💡 Too many failed login attempts.")
                    print("      Wait for unlock time or reset device from web UI.")
                else:
                    print("   ⚠️  Wrong username or password")
                    print("      Check your credentials in .env file")
                    
            except Exception as e:
                print(f"   Error parsing response: {e}")
                print(f"\n   Raw response:\n{response.text}")
            
            return False
            
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            print(response.text[:500])
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to device at {DEVICE_IP}")
        print("   Check:")
        print("   • Device is powered on")
        print("   • IP address is correct")
        print("   • Network connectivity")
        return False
        
    except requests.exceptions.Timeout:
        print(f"❌ Connection timeout to {DEVICE_IP}")
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_alertstream():
    """Test alertStream endpoint availability"""
    url = f"http://{DEVICE_IP}/ISAPI/Event/notification/alertStream"
    auth = HTTPDigestAuth(DEVICE_USER, DEVICE_PASS)
    
    print(f"\n🔍 Testing alertStream endpoint...")
    
    try:
        response = requests.get(url, auth=auth, stream=True, timeout=5)
        
        if response.status_code == 200:
            print("✅ alertStream endpoint is accessible!")
            print("   Service is ready to receive events")
            return True
        else:
            print(f"❌ alertStream returned: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"⚠️  Could not test alertStream: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("Hikvision Device Connection Test")
    print("=" * 60)
    
    # Check credentials are set
    if not DEVICE_PASS or DEVICE_PASS == 'your_password_here':
        print("❌ DEVICE_PASS not set in .env file")
        sys.exit(1)
    
    # Test device status
    if check_device_status():
        print("\n✅ Device authentication OK")
        
        # Test alertStream
        test_alertstream()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed! You can run the bridge service now:")
        print("   python hikvision_bridge.py")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ Connection test failed")
        print("   Fix the issues above before running the bridge")
        print("=" * 60)
        sys.exit(1)
