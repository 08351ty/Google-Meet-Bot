"""
Simple test script to verify Chrome remote debugging connection is working
"""
import os
import socket
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from dotenv import load_dotenv

load_dotenv()

def check_debug_port(port):
    """Check if Chrome is listening on the specified debug port"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', int(port)))
        sock.close()
        return result == 0
    except Exception:
        return False

def get_chrome_user_data_dir():
    """Get the default Chrome user data directory path"""
    custom_dir = os.getenv('CHROME_USER_DATA_DIR')
    if custom_dir:
        return custom_dir
    
    default_dir = os.path.join(
        os.path.expanduser('~'),
        'AppData', 'Local', 'Google', 'Chrome', 'User Data'
    )
    return default_dir

def get_chrome_path():
    """Get the Chrome executable path"""
    possible_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.getenv('CHROME_PATH', '')
    ]
    
    for path in possible_paths:
        if path and os.path.exists(path):
            return path
    
    return r"C:\Program Files\Google\Chrome\Application\chrome.exe"

def test_connection():
    """Test the Chrome remote debugging connection"""
    debug_port = os.getenv('CHROME_DEBUG_PORT', '9222')
    user_data_dir = get_chrome_user_data_dir()
    chrome_path = get_chrome_path()
    
    print("=" * 60)
    print("Chrome Remote Debugging Connection Test")
    print("=" * 60)
    print(f"\nChrome Path: {chrome_path}")
    print(f"User Data Dir: {user_data_dir}")
    print(f"Debug Port: {debug_port}")
    print()
    
    # Check if port is open
    print("Step 1: Checking if Chrome is running with remote debugging...")
    if not check_debug_port(debug_port):
        print(f"[X] FAILED: Chrome is not listening on port {debug_port}")
        print(f"\nPlease start Chrome with:")
        print(f'"{chrome_path}" --remote-debugging-port={debug_port} --user-data-dir="{user_data_dir}"')
        print(f"\nOr run: .\\start_chrome_debug.ps1")
        return False
    else:
        print(f"[OK] SUCCESS: Chrome is listening on port {debug_port}")
    
    # Try to connect with Selenium
    print("\nStep 2: Attempting to connect with Selenium...")
    opt = Options()
    opt.add_argument('--disable-blink-features=AutomationControlled')
    opt.add_experimental_option("debuggerAddress", f"localhost:{debug_port}")
    
    try:
        driver = webdriver.Chrome(options=opt)
        print("[OK] SUCCESS: Selenium connected to Chrome!")
        
        # Test navigation
        print("\nStep 3: Testing navigation...")
        driver.get('https://www.google.com')
        title = driver.title
        print(f"[OK] SUCCESS: Navigated to Google (Page title: {title})")
        
        # Get current URL to verify we're using the existing profile
        current_url = driver.current_url
        print(f"[OK] Current URL: {current_url}")
        
        # Check if we can see the browser window
        print(f"[OK] Window handle: {driver.current_window_handle}")
        
        driver.quit()
        print("\n" + "=" * 60)
        print("[OK] ALL TESTS PASSED! Chrome connection is working correctly.")
        print("=" * 60)
        print("\nYou can now run your main script (join_google_meet.py)")
        return True
        
    except WebDriverException as e:
        print(f"[X] FAILED: Could not connect to Chrome")
        print(f"Error: {str(e)}")
        print(f"\nMake sure Chrome is running with --remote-debugging-port={debug_port}")
        return False
    except Exception as e:
        print(f"[X] FAILED: Unexpected error")
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    test_connection()

