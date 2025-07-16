#!/usr/bin/env python3
"""
Debug server startup to see what's wrong.
"""

import sys
import os
import subprocess
import time
from pathlib import Path

def debug_server_start():
    """Debug server startup"""
    print("🔍 Debugging server startup")
    
    # Kill any existing server
    print("🔪 Killing existing servers...")
    subprocess.run(["pkill", "-f", "main.py"], check=False)
    time.sleep(1)
    
    # Start server with output capture
    print("🚀 Starting server with output capture...")
    server = subprocess.Popen(
        [sys.executable, "app/main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    print(f"  Server PID: {server.pid}")
    
    # Wait a bit and check
    time.sleep(3)
    
    if server.poll() is None:
        print("  ✅ Server is running")
        
        # Test server response
        try:
            import requests
            response = requests.get("http://localhost:5500/api/metadata", timeout=5)
            print(f"  ✅ Server responds: {response.status_code}")
        except Exception as e:
            print(f"  ❌ Server not responding: {e}")
        
        # Stop server
        print("🛑 Stopping server...")
        server.terminate()
        server.wait()
        print("  ✅ Server stopped")
        
    else:
        print("  ❌ Server died")
        
        # Get output
        stdout, stderr = server.communicate()
        
        print("📋 STDOUT:")
        print(stdout)
        print("\n📋 STDERR:")
        print(stderr)
        
        print(f"\n💀 Exit code: {server.returncode}")

if __name__ == "__main__":
    debug_server_start()