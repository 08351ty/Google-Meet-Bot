# import required modules
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import time
import re
import threading
from record_audio import AudioRecorder
from speech_to_text import SpeechToText
import os
import tempfile
import socket
from dotenv import load_dotenv

load_dotenv()

class JoinGoogleMeet:
    def __init__(self):
        # Email and password are now optional - only needed if not already logged in
        self.mail_address = os.getenv('EMAIL_ID')
        self.password = os.getenv('EMAIL_PASSWORD')
        # connect to existing chrome instance
        opt = Options()
        opt.add_argument('--disable-blink-features=AutomationControlled')
        # Connect to existing Chrome instance via remote debugging
        # Default port is 9222, can be overridden via CHROME_DEBUG_PORT env variable
        debug_port = os.getenv('CHROME_DEBUG_PORT', '9222')
        
        # Get Chrome user data directory (default location for Windows)
        user_data_dir = self._get_chrome_user_data_dir()
        
        # Check if Chrome is listening on the debug port
        if not self._check_debug_port(debug_port):
            chrome_path = self._get_chrome_path()
            raise ConnectionError(
                f"Chrome is not running with remote debugging on port {debug_port}.\n"
                f"Please close Chrome and restart it with:\n"
                f'"{chrome_path}" --remote-debugging-port={debug_port} --user-data-dir="{user_data_dir}"'
            )
        
        opt.add_experimental_option("debuggerAddress", f"localhost:{debug_port}")
        try:
            self.driver = webdriver.Chrome(options=opt)
            print(f"Successfully connected to existing Chrome instance on port {debug_port}")
        except WebDriverException as e:
            raise ConnectionError(
                f"Failed to connect to Chrome on port {debug_port}. "
                f"Make sure Chrome is running with --remote-debugging-port={debug_port} "
                f"and --user-data-dir pointing to your profile. "
                f"Error: {str(e)}"
            )
    
    def _get_chrome_user_data_dir(self):
        """Get the default Chrome user data directory path"""
        # Check if user specified a custom path
        custom_dir = os.getenv('CHROME_USER_DATA_DIR')
        if custom_dir:
            return custom_dir
        
        # Default Chrome profile location for Windows
        default_dir = os.path.join(
            os.path.expanduser('~'),
            'AppData', 'Local', 'Google', 'Chrome', 'User Data'
        )
        return default_dir
    
    def _get_chrome_path(self):
        """Get the Chrome executable path"""
        # Common Chrome installation paths on Windows
        possible_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.getenv('CHROME_PATH', '')
        ]
        
        for path in possible_paths:
            if path and os.path.exists(path):
                return path
        
        # Fallback if Chrome path not found
        return r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    
    def _check_debug_port(self, port):
        """Check if Chrome is listening on the specified debug port"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', int(port)))
            sock.close()
            return result == 0
        except Exception:
            return False

    def is_logged_in(self):
        """Check if the Chrome profile is already logged into a Google account"""
        try:
            # Navigate to Google account page to check login status
            self.driver.get('https://myaccount.google.com/')
            time.sleep(3)
            
            # Check if we're redirected to login page
            current_url = self.driver.current_url.lower()
            if 'accounts.google.com/signin' in current_url or 'servicelogin' in current_url:
                print("Not logged in: Redirected to login page")
                return False
            
            # Check for account indicators on the myaccount page
            try:
                # Look for various indicators that user is logged in
                # Check for account email or profile identifier
                account_indicators = [
                    (By.XPATH, '//*[contains(@href, "mail.google.com") or contains(text(), "@gmail.com")]'),
                    (By.CSS_SELECTOR, '[data-profile-identifier]'),
                    (By.CSS_SELECTOR, 'img[alt*="Account"], img[aria-label*="Account"]'),
                    (By.XPATH, '//*[contains(text(), "Account") and contains(@href, "/u/")]'),
                ]
                
                for selector_type, selector_value in account_indicators:
                    try:
                        WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located((selector_type, selector_value))
                        )
                        print("Logged in: Found account indicators on myaccount page")
                        return True
                    except TimeoutException:
                        continue
                        
            except Exception:
                pass
            
            # Alternative check: Try accessing Gmail to see if we're redirected to login
            try:
                self.driver.get('https://mail.google.com/')
                time.sleep(3)
                current_url = self.driver.current_url.lower()
                
                # If we're not redirected to signin, we're logged in
                if 'accounts.google.com/signin' not in current_url and 'servicelogin' not in current_url:
                    # Additional check: look for Gmail inbox indicators
                    gmail_indicators = [
                        (By.CSS_SELECTOR, '[role="button"][aria-label*="Compose"]'),
                        (By.XPATH, '//*[contains(text(), "Inbox")]'),
                        (By.CSS_SELECTOR, 'div[role="navigation"]'),
                        (By.CSS_SELECTOR, 'div[data-tooltip="Inbox"]'),
                    ]
                    
                    for selector_type, selector_value in gmail_indicators:
                        try:
                            WebDriverWait(self.driver, 2).until(
                                EC.presence_of_element_located((selector_type, selector_value))
                            )
                            print("Logged in: Can access Gmail inbox")
                            return True
                        except TimeoutException:
                            continue
                    
                    # If we're on Gmail but can't find specific indicators, still assume logged in
                    if 'mail.google.com' in current_url:
                        print("Logged in: On Gmail page (assumed logged in)")
                        return True
                else:
                    print("Not logged in: Redirected to login when accessing Gmail")
                    return False
            except Exception as e:
                print(f"Error checking Gmail access: {str(e)}")
                return False
                    
        except Exception as e:
            print(f"Error checking login status: {str(e)}")
            # If check fails, assume not logged in to be safe
            return False

    def Glogin(self):
        """Login to Google account if credentials are provided and user is not already logged in"""
        # Check if already logged in
        if self.is_logged_in():
            print("Already logged in to Google account. Skipping login procedure.")
            return
        
        # Check if credentials are provided
        if not self.mail_address or not self.password:
            raise ValueError(
                "Not logged in and no credentials provided. "
                "Please set EMAIL_ID and EMAIL_PASSWORD in your .env file, "
                "or ensure Chrome is logged into a Google account."
            )
        
        print("Not logged in. Attempting to log in with provided credentials...")
        # Login Page
        self.driver.get(
            'https://accounts.google.com/ServiceLogin?hl=en&passive=true&continue=https://www.google.com/&ec=GAZAAQ')
    
        # input Gmail
        self.driver.find_element(By.ID, "identifierId").send_keys(self.mail_address)
        self.driver.find_element(By.ID, "identifierNext").click()
        self.driver.implicitly_wait(10)
    
        # input Password
        self.driver.find_element(By.XPATH,
            '//*[@id="password"]/div[1]/div/div[1]/input').send_keys(self.password)
        self.driver.implicitly_wait(10)
        self.driver.find_element(By.ID, "passwordNext").click()
        self.driver.implicitly_wait(10)    
        # go to google home page
        self.driver.get('https://google.com/')
        self.driver.implicitly_wait(100)
        print("Gmail login activity: Done")
 
    def _dismiss_permission_prompts(self):
        """Dismiss any permission prompts or dialogs that might block controls"""
        try:
            # Try to dismiss any "Allow" buttons for microphone/camera permissions
            allow_selectors = [
                (By.XPATH, '//button[contains(text(), "Allow")]'),
                (By.XPATH, '//button[contains(text(), "Allow camera and microphone")]'),
                (By.XPATH, '//button[contains(@aria-label, "Allow")]'),
            ]
            for selector_type, selector_value in allow_selectors:
                try:
                    allow_button = self.driver.find_element(selector_type, selector_value)
                    if allow_button.is_displayed():
                        allow_button.click()
                        print("Dismissed permission prompt")
                        time.sleep(1)
                        break
                except (NoSuchElementException, Exception):
                    continue
        except Exception as e:
            # Ignore errors - permissions might already be granted
            pass

    def turnOffMicCam(self, meet_link):
        # Navigate to Google Meet URL
        print(f"Navigating to Google Meet: {meet_link}")
        self.driver.get(meet_link)
        
        # Wait for the page to load and controls to appear
        print("Waiting for Google Meet to load...")
        time.sleep(5)
        
        # Wait for the page to be interactive and controls to load
        try:
            # Wait for Google Meet interface to load
            WebDriverWait(self.driver, 30).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            print("Page loaded")
        except TimeoutException:
            print("Warning: Page took too long to load")
        
        # Handle any permission prompts
        self._dismiss_permission_prompts()
        
        # Additional wait for Google Meet specific elements to render
        print("Waiting for controls to appear...")
        time.sleep(5)  # Increased wait time for controls to fully render
        
        # Turn off Microphone - try multiple selectors (ordered by reliability)
        print("Attempting to turn off microphone...")
        mic_selectors = [
            # Try aria-label with case-insensitive matching (XPath)
            (By.XPATH, '//button[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "microphone")]'),
            (By.XPATH, '//div[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "microphone")]'),
            # Try exact case matches
            (By.XPATH, '//button[contains(@aria-label, "microphone") or contains(@aria-label, "Microphone")]'),
            (By.XPATH, '//div[contains(@aria-label, "microphone") or contains(@aria-label, "Microphone")]'),
            # Try data-tooltip attributes
            (By.XPATH, '//button[contains(translate(@data-tooltip, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "mic")]'),
            (By.XPATH, '//div[contains(translate(@data-tooltip, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "mic")]'),
            # Legacy selectors (fallback)
            (By.CSS_SELECTOR, 'div[jscontroller="t2mBxb"][data-anchor-id="hw0c9"]'),
            (By.XPATH, '//div[@jscontroller="t2mBxb"]'),
            # Try finding by button with mic-related classes or content
            (By.XPATH, '//button[contains(@class, "mic") or .//*[contains(@class, "mic")]]'),
        ]
        
        mic_found = False
        for selector_type, selector_value in mic_selectors:
            try:
                # First wait for element to be present
                mic_button = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((selector_type, selector_value))
                )
                # Scroll into view if needed
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", mic_button)
                time.sleep(0.5)
                # Wait for it to be clickable
                mic_button = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((selector_type, selector_value))
                )
                # Try JavaScript click as fallback if regular click fails
                try:
                    mic_button.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", mic_button)
                print("✓ Microphone turned off")
                mic_found = True
                break
            except (TimeoutException, NoSuchElementException) as e:
                continue
            except Exception as e:
                print(f"  Error trying selector {selector_value}: {str(e)}")
                continue
        
        if not mic_found:
            print("⚠ Warning: Could not find microphone button. It may already be off or the selector needs updating.")
        else:
            time.sleep(1)  # Brief pause between actions
    
        # Turn off Camera - try multiple selectors (ordered by reliability)
        print("Attempting to turn off camera...")
        camera_selectors = [
            # Try aria-label with case-insensitive matching (XPath)
            (By.XPATH, '//button[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "camera")]'),
            (By.XPATH, '//div[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "camera")]'),
            # Try exact case matches
            (By.XPATH, '//button[contains(@aria-label, "camera") or contains(@aria-label, "Camera")]'),
            (By.XPATH, '//div[contains(@aria-label, "camera") or contains(@aria-label, "Camera")]'),
            # Try data-tooltip attributes
            (By.XPATH, '//button[contains(translate(@data-tooltip, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "camera")]'),
            (By.XPATH, '//div[contains(translate(@data-tooltip, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "camera")]'),
            # Legacy selectors (fallback)
            (By.CSS_SELECTOR, 'div[jscontroller="bwqwSd"][data-anchor-id="psRWwc"]'),
            (By.XPATH, '//div[@jscontroller="bwqwSd"]'),
            # Try finding by button with camera-related classes
            (By.XPATH, '//button[contains(@class, "camera") or .//*[contains(@class, "camera")]]'),
        ]
        
        camera_found = False
        for selector_type, selector_value in camera_selectors:
            try:
                # First wait for element to be present
                camera_button = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((selector_type, selector_value))
                )
                # Scroll into view if needed
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", camera_button)
                time.sleep(0.5)
                # Wait for it to be clickable
                camera_button = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((selector_type, selector_value))
                )
                # Try JavaScript click as fallback if regular click fails
                try:
                    camera_button.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", camera_button)
                print("✓ Camera turned off")
                camera_found = True
                break
            except (TimeoutException, NoSuchElementException) as e:
                continue
            except Exception as e:
                print(f"  Error trying selector {selector_value}: {str(e)}")
                continue
        
        if not camera_found:
            print("⚠ Warning: Could not find camera button. It may already be off or the selector needs updating.")
        
        time.sleep(2)  # Wait for changes to take effect
        print("Mic/Cam control completed")
 
    def checkIfJoined(self):
        try:
            # Wait for the join button to appear
            join_button = WebDriverWait(self.driver, 60).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.uArJ5e.UQuaGc.Y5sE8d.uyXBBb.xKiqt'))
            )
            print("Meeting has been joined")
        except (TimeoutException, NoSuchElementException):
            print("Meeting has not been joined")
    
    def get_participant_count(self):
        """Try to detect the number of participants in the meeting.
        Returns the count if found, None if unable to determine.
        Note: Google Meet counts you as a participant, so 1 typically means only you."""
        participant_count_selectors = [
            # Try to find participant count in aria-labels
            (By.XPATH, '//button[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "participant")]'),
            (By.XPATH, '//span[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "participant")]'),
            (By.XPATH, '//div[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "participant")]'),
            # Try to find "people" or "person" indicators
            (By.XPATH, '//*[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "people")]'),
            (By.XPATH, '//*[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "person")]'),
            # Try finding participant list button (case-insensitive)
            (By.XPATH, '//button[contains(translate(@data-tooltip, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "participant")]'),
        ]
        
        for selector_type, selector_value in participant_count_selectors:
            try:
                elements = self.driver.find_elements(selector_type, selector_value)
                for elem in elements:
                    aria_label = elem.get_attribute("aria-label") or ""
                    text = elem.text or ""
                    combined_text = (aria_label + " " + text).lower()
                    
                    # Look for numbers in the text
                    numbers = re.findall(r'\d+', combined_text)
                    if numbers:
                        count = int(numbers[0])
                        return count
            except (NoSuchElementException, Exception):
                continue
        
        # Alternative: Check if we can find "Only you" or similar messages
        try:
            only_you_selectors = [
                (By.XPATH, '//*[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "only you")]'),
                (By.XPATH, '//*[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "waiting for others")]'),
            ]
            for selector_type, selector_value in only_you_selectors:
                if self.driver.find_elements(selector_type, selector_value):
                    return 1
        except Exception:
            pass
        
        return None
    
    def is_only_participant(self, consecutive_checks=2):
        """Check if we're the only participant left (others have left).
        Returns True if we're alone for consecutive_checks checks in a row."""
        alone_count = 0
        for _ in range(consecutive_checks):
            count = self.get_participant_count()
            if count is not None and count <= 1:
                alone_count += 1
            else:
                # Reset counter if we detect others
                alone_count = 0
            time.sleep(3)  # Wait 3 seconds between checks
        
        return alone_count >= consecutive_checks
    
    def leave_call(self):
        """Leave the Google Meet call"""
        print("\n" + "="*60)
        print("Leaving the meeting...")
        print("="*60)
        
        leave_button_selectors = [
            # Modern selectors
            (By.XPATH, '//button[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "leave call")]'),
            (By.XPATH, '//button[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "leave")]'),
            (By.XPATH, '//button[contains(., "Leave call")]'),
            (By.XPATH, '//button[contains(., "Leave")]'),
            # Try by text content
            (By.XPATH, '//span[contains(text(), "Leave")]/ancestor::button'),
            (By.XPATH, '//div[contains(text(), "Leave")]/ancestor::button'),
            # Look for end call button (red button) - case-insensitive
            (By.XPATH, '//button[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "end call")]'),
            (By.XPATH, '//button[contains(translate(@data-tooltip, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "leave")]'),
        ]
        
        for selector_type, selector_value in leave_button_selectors:
            try:
                leave_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((selector_type, selector_value))
                )
                # Scroll into view
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", leave_button)
                time.sleep(0.5)
                
                # Try clicking
                try:
                    leave_button.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", leave_button)
                
                print("✓ Left the meeting successfully")
                time.sleep(2)  # Wait for leave to process
                
                # Dismiss any feedback dialogs
                try:
                    dismiss_selectors = [
                        (By.XPATH, '//button[contains(., "Cancel") or contains(., "Close") or contains(., "Dismiss")]'),
                        (By.XPATH, '//button[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "close")]'),
                    ]
                    for ds_type, ds_value in dismiss_selectors:
                        dismiss_btn = self.driver.find_element(ds_type, ds_value)
                        if dismiss_btn.is_displayed():
                            dismiss_btn.click()
                            break
                except Exception:
                    pass
                
                return True
            except (TimeoutException, NoSuchElementException):
                continue
            except Exception as e:
                print(f"  Error trying to leave: {str(e)}")
                continue
        
        print("⚠ Warning: Could not find leave button. You may need to leave manually.")
        return False
    
    def AskToJoin(self, audio_path, duration, monitor_participants=True):
        """Click the join/ask to join button, start recording, and monitor for early exit conditions.
        
        Args:
            audio_path: Path to save the audio recording
            duration: Maximum recording duration in seconds
            monitor_participants: If True, monitor participant count and leave early if everyone else leaves
        """
        print("\n" + "="*60)
        print("Attempting to join the meeting...")
        print("="*60)
        
        # Wait for join button to appear
        time.sleep(3)
        
        # Multiple selectors for join button - Google Meet has different button texts
        join_button_selectors = [
            # Modern selectors - look for buttons with "Join" or "Ask to join" text
            (By.XPATH, '//button[contains(., "Join") or contains(., "join")]'),
            (By.XPATH, '//button[contains(., "Ask to join")]'),
            (By.XPATH, '//button[contains(., "Join now")]'),
            # Try aria-label
            (By.XPATH, '//button[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "join")]'),
            # Legacy selector
            (By.CSS_SELECTOR, 'button[jsname="Qx7uuf"]'),
            # Try by button text content (more specific)
            (By.XPATH, '//span[contains(text(), "Join") or contains(text(), "join")]/ancestor::button'),
            (By.XPATH, '//div[contains(text(), "Join") or contains(text(), "join")]/ancestor::button'),
            # Try finding the primary action button
            (By.CSS_SELECTOR, 'button[data-promo-anchor-id]'),
            (By.XPATH, '//button[@role="button" and contains(@class, "VfPpkd")]'),
        ]
        
        join_button_found = False
        for selector_type, selector_value in join_button_selectors:
            try:
                print(f"  Trying selector: {selector_value[:50]}...")
                # Wait for button to be present and clickable
                join_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((selector_type, selector_value))
                )
                # Scroll into view
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", join_button)
                time.sleep(0.5)
                
                # Try clicking
                try:
                    join_button.click()
                except Exception:
                    # Fallback to JavaScript click
                    self.driver.execute_script("arguments[0].click();", join_button)
                
                print("✓ Join button clicked successfully!")
                join_button_found = True
                break
            except (TimeoutException, NoSuchElementException):
                continue
            except Exception as e:
                print(f"  Error with selector: {str(e)}")
                continue
        
        if not join_button_found:
            print("⚠ Warning: Could not find join button automatically.")
            print("  Please check the browser window and manually join if needed.")
            print("  The script will wait 10 seconds before starting recording...")
            time.sleep(10)
        else:
            # Wait a bit for the meeting to join
            time.sleep(3)
        
        print("\n" + "="*60)
        print(f"Starting audio recording (max duration: {duration} seconds)...")
        if monitor_participants:
            print("Monitoring participants - will leave early if everyone else leaves")
        print("="*60)
        
        # Initialize recorder
        recorder = AudioRecorder()
        recorder.start_recording(audio_path)
        
        try:
            # Monitor the meeting while recording
            check_interval = 10  # Check every 10 seconds
            elapsed_time = 0
            early_exit = False
            
            while elapsed_time < duration and recorder.is_recording():
                # Wait for check interval or remaining time, whichever is shorter
                wait_time = min(check_interval, duration - elapsed_time)
                time.sleep(wait_time)
                elapsed_time += wait_time
                
                # Check participant count if monitoring is enabled
                if monitor_participants:
                    try:
                        participant_count = self.get_participant_count()
                        if participant_count is not None:
                            print(f"  [{elapsed_time:.0f}s] Participants detected: {participant_count}")
                            
                            # Check if we're the only participant (others have left)
                            if participant_count <= 1:
                                print(f"  [{elapsed_time:.0f}s] Only participant detected (others may have left)")
                                # Double-check by waiting a bit more
                                time.sleep(5)
                                participant_count = self.get_participant_count()
                                if participant_count is not None and participant_count <= 1:
                                    print(f"  [{elapsed_time:.0f}s] Confirmed: Only participant in meeting")
                                    print("  All other participants have left. Ending recording and leaving call...")
                                    early_exit = True
                                    break
                        else:
                            # Couldn't determine participant count - continue recording
                            if elapsed_time % 30 == 0:  # Log every 30 seconds if we can't detect
                                print(f"  [{elapsed_time:.0f}s] Recording in progress... (unable to detect participant count)")
                    except Exception as e:
                        # If participant detection fails, continue recording
                        if elapsed_time % 30 == 0:
                            print(f"  [{elapsed_time:.0f}s] Recording in progress... (error checking participants: {str(e)})")
                else:
                    # Not monitoring - just show progress
                    if elapsed_time % 30 == 0:
                        print(f"  [{elapsed_time:.0f}s] Recording in progress... ({elapsed_time}/{duration} seconds)")
            
            # Stop recording
            recorder.stop_recording()
            
            if early_exit:
                print("\n✓ Recording stopped early - all other participants left")
                # Leave the call
                self.leave_call()
            else:
                print(f"\n✓ Recording completed - full duration ({duration} seconds)")
                
        except KeyboardInterrupt:
            print("\n\nRecording interrupted by user")
            recorder.stop_recording()
            self.leave_call()
            raise
        except Exception as e:
            print(f"\n✗ Error during recording: {str(e)}")
            recorder.stop_recording()
            raise

def main():
    DO_ANALYSIS = True
    temp_dir = tempfile.mkdtemp()
    audio_path = os.path.join(temp_dir, "output.wav")
    # Get configuration from environment variables
    meet_link = os.getenv('MEET_LINK')
    duration = int(os.getenv('RECORDING_DURATION', 60))
    
    if not meet_link:
        raise ValueError("MEET_LINK environment variable is required. Please set it in your .env file.")
    
    print("\n" + "="*60)
    print("Google Meet Bot - Starting")
    print("="*60)
    print(f"Meet Link: {meet_link}")
    print(f"Recording Duration: {duration} seconds")
    print(f"Audio Output: {audio_path}")
    print("="*60 + "\n")
    
    try:
        obj = JoinGoogleMeet()
        obj.Glogin()
        obj.turnOffMicCam(meet_link)
        obj.AskToJoin(audio_path, duration)
        
        print("\n" + "="*60)
        print("Recording Phase Complete")
        print("="*60)
        
        if DO_ANALYSIS:
            print("\nStarting speech-to-text analysis...")
            SpeechToText().transcribe(audio_path)
        else:
            print("Analysis skipped (DO_ANALYSIS = False)")
            
    except KeyboardInterrupt:
        print("\n\nScript interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

#call the main function
if __name__ == "__main__":
    main()
