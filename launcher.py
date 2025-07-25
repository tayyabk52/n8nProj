#!/usr/bin/env python3
"""
Launcher Script for Google Maps Scraper - Dual Server Architecture
Manages both main scraper server and contact details server
"""

import os
import sys
import time
import subprocess
import threading
import requests
import json
from datetime import datetime

def check_server_health(url, name):
    """Check if server is running and healthy"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"✅ {name} is running and healthy")
            return True
        else:
            print(f"❌ {name} returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ {name} is not running")
        return False
    except Exception as e:
        print(f"❌ Error checking {name}: {e}")
        return False

def start_server(script_name, port, name):
    """Start a server in a separate process"""
    try:
        print(f"🚀 Starting {name} on port {port}...")
        process = subprocess.Popen([
            sys.executable, script_name
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a moment for server to start
        time.sleep(3)
        
        # Check if server is healthy
        health_url = f"http://127.0.0.1:{port}/health"
        if check_server_health(health_url, name):
            print(f"✅ {name} started successfully")
            return process
        else:
            print(f"❌ Failed to start {name}")
            process.terminate()
            return None
            
    except Exception as e:
        print(f"❌ Error starting {name}: {e}")
        return None

def test_scraping():
    """Test the scraping functionality"""
    print("\n🧪 Testing scraping functionality...")
    
    test_data = {
        "search_term": "car rental",
        "area_name": "DHA Phase 1",
        "latitude": 31.4704,
        "longitude": 74.4136,
        "radius_km": 5,
        "max_results": 5
    }
    
    try:
        response = requests.post(
            "http://127.0.0.1:5000/scrape",
            json=test_data,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                businesses = result.get("data", {}).get("businesses", [])
                print(f"✅ Scraping test successful! Found {len(businesses)} businesses")
                
                # Show sample results
                if businesses:
                    print("\n📋 Sample Results:")
                    for i, business in enumerate(businesses[:3]):
                        print(f"  {i+1}. {business.get('name', 'N/A')}")
                        print(f"     Phone: {business.get('phone', 'N/A')}")
                        print(f"     Website: {business.get('website', 'N/A')}")
                        print(f"     Email: {business.get('email', 'N/A')}")
                        print(f"     Facebook: {business.get('facebook', 'N/A')}")
                        print()
            else:
                print("❌ Scraping test failed - no success response")
        else:
            print(f"❌ Scraping test failed - status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error during scraping test: {e}")

def main():
    """Main launcher function"""
    print("🚀 Google Maps Scraper - Dual Server Launcher")
    print("=" * 50)
    
    # Check if required files exist
    required_files = ["main.py", "contact_server.py"]
    for file in required_files:
        if not os.path.exists(file):
            print(f"❌ Required file {file} not found")
            return
    
    # Start main scraper server
    main_process = start_server("main.py", 5000, "Main Scraper Server")
    if not main_process:
        print("❌ Failed to start main server")
        return
    
    # Start contact details server
    contact_process = start_server("contact_server.py", 5001, "Contact Details Server")
    if not contact_process:
        print("❌ Failed to start contact details server")
        main_process.terminate()
        return
    
    print("\n✅ Both servers started successfully!")
    print("📊 Main Server: http://127.0.0.1:5000")
    print("📊 Contact Server: http://127.0.0.1:5001")
    print("\n🔄 Servers are running... Press Ctrl+C to stop")
    
    try:
        # Test the system
        time.sleep(5)  # Wait for servers to fully initialize
        test_scraping()
        
        # Keep servers running
        while True:
            time.sleep(10)
            # Periodically check server health
            main_healthy = check_server_health("http://127.0.0.1:5000/health", "Main Server")
            contact_healthy = check_server_health("http://127.0.0.1:5001/health", "Contact Server")
            
            if not main_healthy or not contact_healthy:
                print("❌ One or more servers stopped responding")
                break
                
    except KeyboardInterrupt:
        print("\n🛑 Shutting down servers...")
    finally:
        # Cleanup
        if main_process:
            main_process.terminate()
            print("✅ Main server stopped")
        if contact_process:
            contact_process.terminate()
            print("✅ Contact server stopped")
        print("👋 Goodbye!")

if __name__ == "__main__":
    main() 