#!/usr/bin/env python3
"""
Test script to verify Playwright works with VNC display
Run this inside the VNC container to test the setup
"""

import asyncio
from playwright.async_api import async_playwright
import os

async def test_vnc_integration():
    """Test if Playwright can open browser on VNC display"""
    print("Testing Playwright + VNC integration...")
    
    try:
        async with async_playwright() as p:
            print("Starting browser on VNC display :1...")
            
            browser = await p.chromium.launch(
                headless=False,  # MUST be False to see in VNC
                args=[
                    '--display=:1',  # Use VNC display
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--start-maximized',
                    '--window-position=0,0'
                ]
            )
            
            print("Browser launched! Creating page...")
            page = await browser.new_page()
            
            print("Navigating to Google...")
            await page.goto('https://www.google.com')
            
            print("Taking screenshot...")
            await page.screenshot(path='/screenshots/test_vnc.png')
            
            print("Waiting 10 seconds for you to see the browser in VNC...")
            await asyncio.sleep(10)
            
            print("Navigating to example.com...")
            await page.goto('https://example.com')
            
            print("Waiting another 5 seconds...")
            await asyncio.sleep(5)
            
            print("Closing browser...")
            await browser.close()
            
            print("✅ Test completed successfully!")
            print("You should have seen the browser open in your VNC viewer")
            print("Check /screenshots/test_vnc.png for the screenshot")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    return True

def test_environment():
    """Check if environment is properly set up"""
    print("Checking environment...")
    
    display = os.getenv('DISPLAY')
    print(f"DISPLAY: {display}")
    
    if display != ':1':
        print("⚠️  Warning: DISPLAY is not set to :1")
    
    # Check if X server is running
    import subprocess
    try:
        result = subprocess.run(['xdpyinfo', '-display', ':1'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ X server is running on :1")
        else:
            print("❌ X server not accessible on :1")
    except FileNotFoundError:
        print("⚠️  xdpyinfo not found, cannot check X server")

if __name__ == "__main__":
    print("=== Playwright VNC Test ===")
    test_environment()
    print()
    asyncio.run(test_vnc_integration())
