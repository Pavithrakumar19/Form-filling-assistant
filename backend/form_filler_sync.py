""" Form Filler Module - Keep Browser Open Version
"""

from playwright.sync_api import sync_playwright, Error as PlaywrightError
from typing import Dict, Tuple, Optional
from pathlib import Path
import traceback
import subprocess
import sys
import time


class GoogleFormFiller:
    """Synchronous Google Forms filler with persistent browser"""
    
    def __init__(self):
        self.output_dir = Path("outputs")
        self.output_dir.mkdir(exist_ok=True)
        self._ensure_browser_installed()
    
    def _ensure_browser_installed(self):
        """Check and install Playwright browsers if needed"""
        try:
            with sync_playwright() as p:
                try:
                    browser = p.chromium.launch(headless=True)
                    browser.close()
                    print("Chromium browser is available")
                    return True
                except PlaywrightError as e:
                    if "Executable doesn't exist" in str(e):
                        print("\nChromium browser not found. Installing...")
                        self._install_browsers()
                        return True
                    raise
        except Exception as e:
            print(f"Warning: Could not verify browser installation: {e}")
            return False
    
    def _install_browsers(self):
        """Install Playwright browsers"""
        try:
            print("Installing Chromium browser...")
            result = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode == 0:
                print("Chromium browser installed successfully")
            else:
                raise Exception("Browser installation failed")
        except Exception as e:
            print(f"Error installing browser: {e}")
            print("\nPlease manually run: playwright install chromium")
            raise
    
    def fill_form(
        self, 
        url: str, 
        data_dict: Dict[str, str]
    ) -> Tuple[int, int, Optional[str]]:
        """Fill Google Form with extracted data and keep browser open"""
        
        print(f"\nOpening form: {url}")
        print("="*60)
        
        # Convert /preview to /viewform
        if '/preview' in url:
            url = url.replace('/preview', '/viewform')
            print(f"Converted to viewform URL: {url}")
        
        try:
            with sync_playwright() as p:
                print("Launching browser...")
                browser = p.chromium.launch(
                    headless=False,  # Always visible
                    slow_mo=50,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox'
                    ]
                )
                print("✓ Browser launched")
                
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 1024},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                
                page = context.new_page()
                print("Page created")
                
                try:
                    print(f"Loading page...")
                    page.goto(url, wait_until='domcontentloaded', timeout=60000)
                    page.wait_for_timeout(3000)
                    print("Page loaded\n")
                    
                    filled = 0
                    total = 0
                    
                    # Wait for form to be fully loaded
                    page.wait_for_selector('[role="listitem"]', timeout=10000)
                    
                    # Get all form questions
                    print("Analyzing form structure...")
                    questions = page.query_selector_all('[role="listitem"]')
                    print(f"Found {len(questions)} form elements\n")
                    
                    for idx, q in enumerate(questions, 1):
                        try:
                            # Get question text - try multiple methods
                            q_text = self._get_question_text(q)
                            if not q_text:
                                continue
                            
                            q_text_lower = q_text.lower()
                            total += 1
                            
                            print(f"[{idx}] Question: {q_text}")
                            
                            # Get value for this field
                            value = self.get_value_for_field(q_text_lower, data_dict)
                            
                            if not value:
                                print(f"    No matching data (available: {list(data_dict.keys())})\n")
                                continue
                            
                            print(f"    → Attempting to fill with: {value}")
                            
                            # Try to fill the field
                            success = self._fill_field_advanced(page, q, value, q_text_lower)
                            
                            if success:
                                filled += 1
                                print(f"    Successfully filled!\n")
                            else:
                                print(f"    Could not fill field\n")
                        
                        except Exception as e:
                            print(f"    Error: {e}\n")
                            traceback.print_exc()
                            continue
                    
                    print("="*60)
                    print(f"FILLED {filled}/{total} FIELDS")
                    print("="*60 + "\n")
                    
                    # Capture screenshot
                    print("Capturing screenshot...")
                    page.wait_for_timeout(2000)
                    screenshot_name = 'filled_form.png'
                    screenshot_path = self.output_dir / screenshot_name
                    page.screenshot(path=str(screenshot_path), full_page=True)
                    print(f"✓ Screenshot saved: {screenshot_name}\n")
                    
                    # *** KEY CHANGE: Keep browser open indefinitely ***
                    print("\n" + "="*60)
                    print(" BROWSER WILL REMAIN OPEN")
                    print("="*60)
                    print("\n You can now:")
                    print("   • Fill any remaining fields manually")
                    print("   • Review the auto-filled data")
                    print("   • Submit the form when ready")
                    print("   • Close the browser window when done")
                    print("\n This terminal will wait until you close the browser...")
                    print("="*60 + "\n")
                    
                    # Wait for browser to be closed by user
                    try:
                        # Keep checking if browser is still open
                        while True:
                            try:
                                # Try to get page title - will fail if browser closed
                                page.title()
                                time.sleep(1)  # Check every second
                            except:
                                # Browser was closed
                                break
                    except KeyboardInterrupt:
                        print("\n\n Interrupted by user (Ctrl+C)")
                    
                    print("\n Browser closed. Cleaning up...")
                    
                    return filled, total, screenshot_name
                    
                except Exception as e:
                    print(f"\n Error during form filling: {e}")
                    traceback.print_exc()
                    
                    try:
                        page.screenshot(path=str(self.output_dir / 'error.png'))
                    except:
                        pass
                    
                    # Still keep browser open even on error
                    print("\n Error occurred, but browser will remain open for manual filling...")
                    try:
                        while True:
                            try:
                                page.title()
                                time.sleep(1)
                            except:
                                break
                    except KeyboardInterrupt:
                        pass
                    
                    browser.close()
                    raise
                    
        except Exception as e:
            print(f"\n Fatal Error: {e}")
            traceback.print_exc()
            raise
    
    def _get_question_text(self, question_element) -> str:
        """Extract question text using multiple strategies"""
        
        # Strategy 1: role="heading"
        try:
            heading = question_element.query_selector('[role="heading"]')
            if heading:
                text = heading.inner_text().strip()
                if text:
                    return text.replace('*', '').strip()
        except:
            pass
        
        # Strategy 2: Common Google Forms classes
        selectors = [
            '.freebirdFormviewerComponentsQuestionBaseTitle',
            '.freebirdFormviewerViewItemsItemItemTitle',
            '[data-item-id] > div > div > div',
            'div[dir="auto"]'
        ]
        
        for selector in selectors:
            try:
                elem = question_element.query_selector(selector)
                if elem:
                    text = elem.inner_text().strip()
                    if text and len(text) > 1:
                        return text.replace('*', '').strip()
            except:
                continue
        
        return ""
    
    def _fill_field_advanced(self, page, question_element, value: str, question_text: str) -> bool:
        """Advanced field filling with multiple strategies"""
        
        print(f"    → Strategy 1: Looking for input fields...")
        
        # Strategy 1: Direct input fields
        input_selectors = [
            'input[type="text"]',
            'input[type="email"]',
            'input[type="tel"]',
            'input[type="number"]',
            'input[aria-label]',
            'textarea'
        ]
        
        for selector in input_selectors:
            inputs = question_element.query_selector_all(selector)
            for inp in inputs:
                try:
                    if not inp.is_visible():
                        continue
                    
                    print(f"      → Found {selector}, attempting to fill...")
                    
                    # Scroll into view
                    inp.scroll_into_view_if_needed()
                    page.wait_for_timeout(500)
                    
                    # Click to focus
                    inp.click(timeout=3000)
                    page.wait_for_timeout(300)
                    
                    # Clear existing content
                    inp.fill('', timeout=3000)
                    page.wait_for_timeout(200)
                    
                    # Type the value
                    inp.type(str(value), delay=50)
                    page.wait_for_timeout(500)
                    
                    # Verify it worked
                    try:
                        filled_value = inp.input_value()
                        if filled_value == str(value):
                            print(f"      Verified: input contains '{filled_value}'")
                            return True
                    except:
                        pass
                    
                    return True
                    
                except Exception as e:
                    print(f"      Failed: {e}")
                    continue
        
        print(f"    → Strategy 2: Looking for contenteditable divs...")
        
        # Strategy 2: Content editable divs
        try:
            divs = question_element.query_selector_all('[contenteditable="true"]')
            for div in divs:
                try:
                    if not div.is_visible():
                        continue
                    
                    print(f"      → Found contenteditable div...")
                    div.click(timeout=3000)
                    page.wait_for_timeout(200)
                    
                    div.fill('', timeout=3000)
                    page.wait_for_timeout(200)
                    div.type(str(value), delay=50)
                    page.wait_for_timeout(300)
                    
                    return True
                except Exception as e:
                    print(f"      Failed: {e}")
                    continue
        except:
            pass
        
        print(f"     Strategy 3: Using JavaScript injection...")
        
        # Strategy 3: JavaScript injection as last resort
        try:
            inputs = question_element.query_selector_all('input, textarea')
            for inp in inputs:
                try:
                    if not inp.is_visible():
                        continue
                    
                    print(f"      Trying JavaScript fill...")
                    
                    page.evaluate(f'''(element) => {{
                        element.value = "{value}";
                        element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}''', inp)
                    
                    page.wait_for_timeout(300)
                    return True
                    
                except Exception as e:
                    print(f"       Failed: {e}")
                    continue
        except:
            pass
        
        print(f"    → All strategies failed")
        return False
    
    def get_value_for_field(self, field_name: str, data: Dict[str, str]) -> str:
        """Smart field matching"""
        field = field_name.lower()
        
        print(f"    → Matching '{field}' against available data...")
        
        # Name field
        if any(k in field for k in ['name', 'naam', 'full name', 'your name', 'applicant']):
            if 'name' in data:
                return data['name']
        
        # Email field
        if any(k in field for k in ['email', 'e-mail', 'mail', 'electronic']):
            if 'email' in data:
                return data['email']
        
        # Phone field
        if any(k in field for k in ['phone', 'mobile', 'contact', 'telephone', 'cell']):
            if 'phone' in data:
                return data['phone']
        
        # Aadhaar field
        if any(k in field for k in ['aadhaar', 'aadhar', 'uid', 'unique', 'adhaar','Aadhar number','Aadhar']):
            if 'aadhaar' in data:
                return data['aadhaar']
        
        # PAN field
        if any(k in field for k in ['pan', 'permanent account']):
            if 'pan' in data:
                return data['pan']
        
        # Address field
        if any(k in field for k in ['address', 'location', 'residence', 'street']):
            if 'address' in data:
                return data['address']
        
        # Pincode field
        if any(k in field for k in ['pin', 'postal', 'zip', 'pincode']):
            if 'pincode' in data:
                return data['pincode']
        
        # Date field
        if any(k in field for k in ['dob', 'birth', 'date']):
            if 'date' in data:
                return data['date']
        
        return ''
