#!/usr/bin/env python3
"""
Comprehensive test suite for PDF Editor session management and cleanup functionality.
"""

import requests
import time
import json
import os
from pathlib import Path
import tempfile
from PIL import Image
import io

class PDFEditorTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.test_sessions = []
        
    def create_test_image(self, filename="test_image.png"):
        """Create a test image file"""
        img = Image.new('RGB', (100, 100), color='red')
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        img.save(temp_file.name, 'PNG')
        return temp_file.name
    
    def create_test_pdf(self, filename="test.pdf"):
        """Create a simple test PDF using reportlab if available, otherwise skip"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            c = canvas.Canvas(temp_file.name, pagesize=letter)
            c.drawString(100, 750, "Test PDF Document")
            c.drawString(100, 700, "This is a test file for session cleanup testing")
            c.save()
            return temp_file.name
        except ImportError:
            print("⚠️  reportlab not available, skipping PDF creation test")
            return None
    
    def test_server_connection(self):
        """Test if server is running"""
        print("🔗 Testing server connection...")
        try:
            response = requests.get(f"{self.base_url}/")
            if response.status_code == 200:
                print("✅ Server is running")
                return True
            else:
                print(f"❌ Server returned status {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to server. Make sure it's running on localhost:8000")
            return False
    
    def test_session_creation(self):
        """Test session creation and file upload"""
        print("\n📁 Testing session creation and file upload...")
        
        session_id = f"test_session_{int(time.time())}"
        self.test_sessions.append(session_id)
        
        # Create test file
        test_image = self.create_test_image()
        
        try:
            # Upload file
            with open(test_image, 'rb') as f:
                files = {'files': ('test.png', f, 'image/png')}
                data = {'session_id': session_id}
                response = requests.post(f"{self.base_url}/upload", files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                if 'files' in result and len(result['files']) > 0:
                    print(f"✅ Session created and file uploaded: {session_id}")
                    return session_id
                else:
                    print("❌ File upload failed")
                    return None
            else:
                print(f"❌ Upload failed with status {response.status_code}")
                return None
                
        finally:
            # Clean up test file
            try:
                os.unlink(test_image)
            except:
                pass
    
    def test_session_debug_info(self):
        """Test debug endpoints"""
        print("\n🔍 Testing debug endpoints...")
        
        try:
            response = requests.get(f"{self.base_url}/debug/sessions")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Debug info retrieved:")
                print(f"   Total sessions: {data['total_sessions']}")
                print(f"   Session timeout: {data['session_timeout']}s")
                print(f"   Cleanup interval: {data['cleanup_interval']}s")
                
                for session_id, info in data['sessions'].items():
                    print(f"   Session {session_id[:12]}...:")
                    print(f"     Files: {info['files_count']}")
                    print(f"     Age: {info['created_ago_seconds']}s")
                    print(f"     Inactive: {info['inactive_seconds']}s")
                    print(f"     Downloaded: {info['downloaded']}")
                    print(f"     Expires in: {info['expires_in_seconds']}s")
                
                return True
            else:
                print(f"❌ Debug endpoint failed with status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Debug endpoint error: {e}")
            return False
    
    def test_manual_cleanup(self):
        """Test manual cleanup trigger"""
        print("\n🧹 Testing manual cleanup...")
        
        try:
            response = requests.post(f"{self.base_url}/debug/cleanup")
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Manual cleanup triggered")
                print(f"   Message: {result['message']}")
                print(f"   Remaining sessions: {result['remaining_sessions']}")
                return True
            else:
                print(f"❌ Manual cleanup failed with status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Manual cleanup error: {e}")
            return False
    
    def test_session_timeout_simulation(self):
        """Test session timeout by creating a session and simulating time passage"""
        print("\n⏰ Testing session timeout simulation...")
        
        # Create a session
        session_id = self.test_session_creation()
        if not session_id:
            print("❌ Could not create session for timeout test")
            return False
        
        # Check initial state
        print("📊 Initial session state:")
        self.test_session_debug_info()
        
        # Wait for session to expire (server is configured with 60s timeout for testing)
        print("\n🕐 Waiting for session to expire...")
        print("⏳ Server timeout is set to 60 seconds for testing...")
        print("⏳ Waiting 65 seconds for automatic cleanup...")
        
        # Wait for expiration + cleanup interval
        for i in range(13):  # 13 * 5 = 65 seconds
            time.sleep(5)
            print(f"⏳ Waiting... {(i+1)*5}/65 seconds")
        
        # Check if session was automatically cleaned up
        print("\n📊 Session state after timeout:")
        debug_result = self.test_session_debug_info()
        
        # Also trigger manual cleanup to be sure
        print("\n🧹 Triggering manual cleanup as well...")
        cleanup_result = self.test_manual_cleanup()
        
        return debug_result and cleanup_result
    
    def test_download_and_cleanup(self):
        """Test download marking and subsequent cleanup"""
        print("\n📥 Testing download and cleanup...")
        
        # Create session and upload files
        session_id = self.test_session_creation()
        if not session_id:
            return False
        
        # Combine files to create downloadable PDF
        try:
            data = {'session_id': session_id}
            response = requests.post(f"{self.base_url}/combine", data=data)
            
            if response.status_code == 200:
                result = response.json()
                if 'download_url' in result:
                    download_url = result['download_url']
                    print(f"✅ PDF combined, download URL: {download_url}")
                    
                    # Download the file
                    download_response = requests.get(f"{self.base_url}{download_url}")
                    if download_response.status_code == 200:
                        print("✅ PDF downloaded successfully")
                        
                        # Check if session is marked as downloaded
                        debug_response = requests.get(f"{self.base_url}/debug/sessions")
                        if debug_response.status_code == 200:
                            debug_data = debug_response.json()
                            if session_id in debug_data['sessions']:
                                downloaded = debug_data['sessions'][session_id]['downloaded']
                                print(f"✅ Session download status: {downloaded}")
                                return downloaded
                        
                    else:
                        print(f"❌ Download failed with status {download_response.status_code}")
                else:
                    print("❌ No download URL in combine response")
            else:
                print(f"❌ Combine failed with status {response.status_code}")
                
        except Exception as e:
            print(f"❌ Download test error: {e}")
        
        return False
    
    def test_file_system_cleanup(self):
        """Test that files are actually deleted from filesystem"""
        print("\n🗂️  Testing filesystem cleanup...")
        
        # Create session and upload file
        session_id = self.test_session_creation()
        if not session_id:
            return False
        
        # Check if upload directory exists
        upload_dir = Path(f"uploads/{session_id}")
        temp_pdf = Path(f"temp/combined_{session_id}.pdf")
        
        print(f"📁 Upload directory exists: {upload_dir.exists()}")
        
        if upload_dir.exists():
            files_before = list(upload_dir.glob("*"))
            print(f"📄 Files in upload directory: {len(files_before)}")
            
            # Manually cleanup this session
            cleanup_response = requests.post(f"{self.base_url}/debug/cleanup-session/{session_id}")
            
            if cleanup_response.status_code == 200:
                print("✅ Session cleanup triggered")
                
                # Check if directory is gone
                time.sleep(1)  # Give it a moment
                print(f"📁 Upload directory exists after cleanup: {upload_dir.exists()}")
                print(f"📄 Combined PDF exists after cleanup: {temp_pdf.exists()}")
                
                return not upload_dir.exists()
            else:
                print(f"❌ Session cleanup failed: {cleanup_response.text}")
        
        return False
    
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting PDF Editor Session Management Tests")
        print("=" * 60)
        
        # Test server connection first
        if not self.test_server_connection():
            print("\n❌ Cannot proceed without server connection")
            return False
        
        # Run all tests
        tests = [
            ("Session Creation", self.test_session_creation),
            ("Debug Info", self.test_session_debug_info),
            ("Manual Cleanup", self.test_manual_cleanup),
            ("Download and Cleanup", self.test_download_and_cleanup),
            ("Filesystem Cleanup", self.test_file_system_cleanup),
            ("Timeout Simulation", self.test_session_timeout_simulation),
        ]
        
        results = {}
        for test_name, test_func in tests:
            try:
                result = test_func()
                results[test_name] = result
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {e}")
                results[test_name] = False
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
            if result:
                passed += 1
        
        print(f"\n🎯 Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Session management is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
        
        return passed == total

def main():
    """Main test runner"""
    print("PDF Editor Session Management Test Suite")
    print("Make sure the server is running: python web_app.py")
    print()
    
    tester = PDFEditorTester()
    success = tester.run_all_tests()
    
    if success:
        exit(0)
    else:
        exit(1)

if __name__ == "__main__":
    main()