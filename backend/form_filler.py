"""
Google Form Filler Module
=========================
Automatically fills Google Forms using Playwright
"""

from playwright.async_api import async_playwright
from typing import Dict, Tuple, Optional
import asyncio
from pathlib import Path
import traceback


class GoogleFormFiller:
    """Intelligent Google Forms filler with retry logic"""
    
    def __init__(self):
        self.output_dir = Path("outputs")
        self.output_dir.mkdir(exist_ok=True)
    
    async def fill_form(
        self, 
        url: str, 
        data_dict: Dict[str, str]
    ) -> Tuple[int, int, Optional[str]]:
        """
        Fill Google Form with extracted data
        
        Args:
            url: Google Form URL
            data_dict: Dictionary of field_name: value pairs
            
        Returns:
            (fields_filled, total_fields, screenshot_filename)
        """
        print(f"\n🌐 Opening form: {url}")
        print("="*60)
        
        try:
            async with async_playwright() as p:
                # Launch browser
                print("Launching browser...")
                browser = await p.chromium.launch(
                    headless=True,  # Set to False to see browser
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox'
                    ]
                )
                print("✓ Browser launched")
                
                # Create context
                context = await browser.new_context(
                    viewport={'width': 1280, 'height': 1024},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                
                page = await context.new_page()
                print("✓ Page created")
                
                try:
                    # Load page
                    print(f"Loading page: {url}")
                    await page.goto(url, wait_until='networkidle', timeout=60000)
                    await page.wait_for_timeout(3000)
                    print("✓ Page loaded\n")
                    
                    filled = 0
                    total = 0
                    
                    # Get all form questions
                    print("Looking for form questions...")
                    questions = await page.query_selector_all('[role="listitem"]')
                    print(f"Found {len(questions)} potential form questions\n")
                    
                    for idx, q in enumerate(questions, 1):
                        try:
                            # Get question text
                            heading = await q.query_selector('[role="heading"]')
                            if not heading:
                                continue
                            
                            q_text = (await heading.inner_text()).strip()
                            q_text = q_text.replace('*', '').strip().lower()
                            
                            if not q_text or len(q_text) < 2:
                                continue
                            
                            total += 1
                            print(f"[{idx}] Question: {q_text[:60]}...")
                            
                            # Get value for this field
                            value = self.get_value_for_field(q_text, data_dict)
                            
                            if not value:
                                print(f"    ✗ No matching data found\n")
                                continue
                            
                            # Try to fill the field
                            success = await self.fill_field(page, q, value)
                            
                            if success:
                                filled += 1
                                print(f"    ✅ Filled with: {value}\n")
                            else:
                                print(f"    ⚠️  Could not fill field\n")
                        
                        except Exception as e:
                            print(f"    ❌ Error processing question: {e}\n")
                            traceback.print_exc()
                            continue
                    
                    print("="*60)
                    print(f"✅ FILLED {filled}/{total} FIELDS")
                    print("="*60 + "\n")
                    
                    # Capture screenshot
                    print("Capturing screenshot...")
                    await page.wait_for_timeout(2000)
                    screenshot_name = 'filled_form.png'
                    screenshot_path = self.output_dir / screenshot_name
                    await page.screenshot(path=str(screenshot_path), full_page=True)
                    print(f"✓ Screenshot saved: {screenshot_name}\n")
                    
                    await browser.close()
                    return filled, total, screenshot_name
                    
                except Exception as e:
                    print(f"\n❌ Error during form filling: {e}")
                    print("Full traceback:")
                    traceback.print_exc()
                    await browser.close()
                    raise
                    
        except Exception as e:
            print(f"\n❌ Fatal Error in fill_form: {e}")
            print("Error type:", type(e).__name__)
            print("Full traceback:")
            traceback.print_exc()
            raise
    
    async def fill_field(self, page, question_element, value: str) -> bool:
        """
        Try multiple methods to fill a field
        
        Returns:
            True if successfully filled
        """
        # Method 1: Text inputs
        text_inputs = await question_element.query_selector_all(
            'input[type="text"], input[type="email"], input[type="tel"], textarea'
        )
        
        for inp in text_inputs:
            try:
                # Check if visible
                is_visible = await inp.is_visible()
                if not is_visible:
                    continue
                
                # Scroll into view
                await inp.scroll_into_view_if_needed()
                await page.wait_for_timeout(500)
                
                # Focus
                await inp.focus()
                await page.wait_for_timeout(300)
                
                # Clear and fill
                await inp.fill('')
                await page.wait_for_timeout(200)
                await inp.type(str(value), delay=50)
                await page.wait_for_timeout(300)
                
                return True
                
            except Exception as e:
                print(f"      Error filling text input: {e}")
                continue
        
        # Method 2: Radio buttons / checkboxes
        try:
            labels = await question_element.query_selector_all('label')
            for label in labels:
                label_text = (await label.inner_text()).strip().lower()
                if str(value).lower() in label_text:
                    await label.click()
                    await page.wait_for_timeout(300)
                    return True
        except Exception as e:
            print(f"      Error with radio/checkbox: {e}")
            pass
        
        # Method 3: Dropdowns
        try:
            dropdowns = await question_element.query_selector_all('select')
            for dropdown in dropdowns:
                await dropdown.select_option(label=str(value))
                await page.wait_for_timeout(300)
                return True
        except Exception as e:
            print(f"      Error with dropdown: {e}")
            pass
        
        return False
    
    def get_value_for_field(self, field_name: str, data: Dict[str, str]) -> str:
        """
        Smart field matching - maps question text to data keys
        
        Args:
            field_name: Question text from form (lowercase)
            data: Extracted data dictionary
            
        Returns:
            Value to fill, or empty string if no match
        """
        field = field_name.lower()
        
        # Name field
        if any(k in field for k in ['name', 'naam', 'full name', 'your name', 'applicant name']):
            return data.get('name', '')
        
        # Email field
        elif any(k in field for k in ['email', 'e-mail', 'mail', 'electronic']):
            return data.get('email', '')
        
        # Phone field
        elif any(k in field for k in ['phone', 'mobile', 'contact', 'telephone', 'cell']):
            return data.get('phone', '')
        
        # Aadhaar field
        elif any(k in field for k in ['aadhaar', 'aadhar', 'uid', 'unique id']):
            return data.get('aadhaar', '')
        
        # PAN field
        elif any(k in field for k in ['pan', 'permanent account']):
            return data.get('pan', '')
        
        # Address field
        elif any(k in field for k in ['address', 'location', 'residence', 'residential']):
            return data.get('address', '')
        
        # Pincode field
        elif any(k in field for k in ['pin', 'postal', 'zip', 'pincode']):
            return data.get('pincode', '')
        
        # Date field
        elif any(k in field for k in ['dob', 'birth', 'date of birth']):
            return data.get('date', '')
        
        return ''