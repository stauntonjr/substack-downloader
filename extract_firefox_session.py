#!/usr/bin/env python3
"""
Extract Substack cookies from Firefox and create substack_session.json
"""

import json
import os
import sys
import time

def get_firefox_cookies():
    """Extract cookies from Firefox for substack.com"""
    try:
        from selenium import webdriver
        from selenium.webdriver.firefox.options import Options
        from selenium.webdriver.firefox.service import Service
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError:
        print("Selenium not installed. Installing...")
        os.system("pip install selenium")
        from selenium import webdriver
        from selenium.webdriver.firefox.options import Options
        from selenium.webdriver.firefox.service import Service

    # Find Firefox profile
    # macOS: ~/Library/Application Support/Firefox/Profiles/
    profile_path = os.path.expanduser("~/Library/Application Support/Firefox/Profiles/")
    
    if not os.path.exists(profile_path):
        print(f"Firefox profile not found at {profile_path}")
        print("Please make sure Firefox is installed and has a profile with Substack logged in.")
        sys.exit(1)
    
    print(f"Looking for Firefox profiles in: {profile_path}")
    profiles = [d for d in os.listdir(profile_path) if d.endswith('.default-release')]
    
    if not profiles:
        print("No Firefox profiles found with .default-release suffix")
        sys.exit(1)
    
    profile_dir = os.path.join(profile_path, profiles[0])
    print(f"Using profile: {profile_dir}")
    
    # Configure Firefox to use the profile
    options = Options()
    options.add_argument(f"-profile")
    options.add_argument(profile_dir)
    options.headless = True
    
    # Create a temporary copy of the profile to avoid locking issues
    temp_profile = "/tmp/firefox_substack_profile"
    if os.path.exists(temp_profile):
        import shutil
        shutil.rmtree(temp_profile)
    import shutil
    shutil.copytree(profile_dir, temp_profile)
    
    options.add_argument(f"-profile")
    options.add_argument(temp_profile)
    
    # Initialize Firefox
    service = Service("/usr/bin/firefox")
    driver = webdriver.Firefox(options=options, service=service)
    
    try:
        # Navigate to Substack
        print("Navigating to substack.com...")
        driver.get("https://substack.com")
        
        # Wait for page to load
        time.sleep(5)
        
        # Get cookies
        cookies = driver.get_cookies()
        
        # Get local storage
        local_storage = driver.execute_script("return JSON.stringify(localStorage);")
        
        # Get user agent
        user_agent = driver.execute_script("return navigator.userAgent;")
        
        # Save session
        session_data = {
            "cookies": cookies,
            "local_storage": json.loads(local_storage),
            "user_agent": user_agent
        }
        
        with open("substack_session.json", "w") as f:
            json.dump(session_data, f, indent=2)
        
        print("Session saved to substack_session.json")
        
        # Cleanup
        driver.quit()
        shutil.rmtree(temp_profile, ignore_errors=True)
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        # Cleanup
        try:
            driver.quit()
        except:
            pass
        try:
            import shutil
            shutil.rmtree(temp_profile, ignore_errors=True)
        except:
            pass
        return False

if __name__ == "__main__":
    success = get_firefox_cookies()
    sys.exit(0 if success else 1)
