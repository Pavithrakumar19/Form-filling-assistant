"""
Playwright Setup Script
=======================
Ensures Playwright browsers are properly installed
"""

import subprocess
import sys
from pathlib import Path


def check_playwright_installed():
    """Check if playwright package is installed"""
    try:
        import playwright
        print("✓ Playwright package is installed")
        return True
    except ImportError:
        print("❌ Playwright package is not installed")
        print("\nPlease run: pip install playwright")
        return False


def check_browser_installed():
    """Check if Chromium browser is installed"""
    try:
        from playwright.sync_api import sync_playwright
        
        print("\nChecking browser installation...")
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                print("✓ Chromium browser is installed and working")
                return True
            except Exception as e:
                if "Executable doesn't exist" in str(e):
                    print("❌ Chromium browser is not installed")
                    return False
                else:
                    print(f"⚠️  Error checking browser: {e}")
                    return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def install_browsers():
    """Install Playwright browsers"""
    print("\n" + "="*60)
    print("Installing Chromium browser...")
    print("="*60)
    print("\nThis may take a few minutes (downloading ~150MB)...\n")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=False,
            text=True,
            timeout=600  # 10 minutes timeout
        )
        
        if result.returncode == 0:
            print("\n" + "="*60)
            print("✅ Chromium browser installed successfully!")
            print("="*60)
            return True
        else:
            print("\n" + "="*60)
            print("❌ Browser installation failed")
            print("="*60)
            return False
            
    except subprocess.TimeoutExpired:
        print("\n❌ Installation timed out")
        return False
    except Exception as e:
        print(f"\n❌ Error during installation: {e}")
        return False


def main():
    """Main setup function"""
    print("\n" + "="*60)
    print("🎭 PLAYWRIGHT SETUP CHECK")
    print("="*60 + "\n")
    
    # Check if playwright is installed
    if not check_playwright_installed():
        return
    
    # Check if browser is installed
    if check_browser_installed():
        print("\n" + "="*60)
        print("✅ ALL CHECKS PASSED!")
        print("="*60)
        print("\nYour system is ready to run the form filler.")
        print("You can now start the backend server:")
        print("  python main.py")
        print()
        return
    
    # Offer to install browsers
    print("\n" + "="*60)
    print("Browser installation required")
    print("="*60)
    
    response = input("\nWould you like to install Chromium now? (y/n): ").strip().lower()
    
    if response == 'y':
        if install_browsers():
            print("\n✅ Setup complete! You can now run:")
            print("  python main.py")
        else:
            print("\n⚠️  Please try manual installation:")
            print("  playwright install chromium")
    else:
        print("\nTo install later, run:")
        print("  playwright install chromium")
    
    print()


if __name__ == "__main__":
    main()