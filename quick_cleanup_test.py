#!/usr/bin/env python3
"""
Quick test to verify background cleanup is working
"""

import requests
import time
from PIL import Image
import tempfile
import os

def create_test_image():
    """Create a test image file"""
    img = Image.new('RGB', (100, 100), color='blue')
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    img.save(temp_file.name, 'PNG')
    return temp_file.name

def test_background_cleanup():
    base_url = "http://localhost:8000"
    
    print("🧪 Quick Background Cleanup Test")
    print("=" * 40)
    
    # Test server connection
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code != 200:
            print("❌ Server not running")
            return False
    except:
        print("❌ Cannot connect to server")
        return False
    
    print("✅ Server is running")
    
    # Create a session
    session_id = f"quick_test_{int(time.time())}"
    test_image = create_test_image()
    
    try:
        # Upload file
        with open(test_image, 'rb') as f:
            files = {'files': ('test.png', f, 'image/png')}
            data = {'session_id': session_id}
            response = requests.post(f"{base_url}/upload", files=files, data=data)
        
        if response.status_code == 200:
            print(f"✅ Created session: {session_id}")
        else:
            print("❌ Failed to create session")
            return False
    finally:
        os.unlink(test_image)
    
    # Check initial state
    response = requests.get(f"{base_url}/debug/sessions")
    if response.status_code == 200:
        data = response.json()
        print(f"📊 Initial sessions: {data['total_sessions']}")
        print(f"⏰ Session timeout: {data['session_timeout']}s")
        print(f"🔄 Cleanup interval: {data['cleanup_interval']}s")
        
        if session_id in data['sessions']:
            session_info = data['sessions'][session_id]
            print(f"📁 Session files: {session_info['files_count']}")
            print(f"⏳ Session age: {session_info['created_ago_seconds']}s")
            print(f"💤 Inactive for: {session_info['inactive_seconds']}s")
            print(f"⏰ Expires in: {session_info['expires_in_seconds']}s")
    
    # Wait and monitor
    print(f"\n⏳ Waiting for background cleanup to run...")
    print("🔍 Monitoring session status every 10 seconds...")
    
    for i in range(12):  # Monitor for 2 minutes
        time.sleep(10)
        
        response = requests.get(f"{base_url}/debug/sessions")
        if response.status_code == 200:
            data = response.json()
            
            if session_id in data['sessions']:
                session_info = data['sessions'][session_id]
                inactive = session_info['inactive_seconds']
                expires_in = session_info['expires_in_seconds']
                
                print(f"⏱️  {(i+1)*10}s: Session still exists, inactive for {inactive}s, expires in {expires_in}s")
                
                if expires_in <= 0:
                    print("⚠️  Session should have expired but still exists")
            else:
                print(f"🎉 Session cleaned up after {(i+1)*10} seconds!")
                print("✅ Background cleanup is working!")
                return True
    
    print("⚠️  Session was not cleaned up within 2 minutes")
    print("🔧 Try triggering manual cleanup...")
    
    # Manual cleanup as fallback
    response = requests.post(f"{base_url}/debug/cleanup")
    if response.status_code == 200:
        result = response.json()
        print(f"🧹 Manual cleanup: {result['message']}")
        print(f"📊 Remaining sessions: {result['remaining_sessions']}")
    
    return False

if __name__ == "__main__":
    print("Make sure the server is running: python web_app.py")
    print()
    
    success = test_background_cleanup()
    
    if success:
        print("\n🎉 Background cleanup is working correctly!")
        exit(0)
    else:
        print("\n⚠️  Background cleanup may not be working properly")
        exit(1)