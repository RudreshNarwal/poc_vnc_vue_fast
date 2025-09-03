#!/usr/bin/env python3
"""
Test script to verify Playwright works with VNC display
Run this inside the VNC container to test the setup
"""

import asyncio
from playwright.async_api import async_playwright
import os

async def test_vnc_integration():
    """Test if Playwright can open browser on VNC display and insert 7 route records"""
    print("Testing Playwright + VNC integration with route automation...")
    
    # Define 7 route records to insert
    routes = [
        {"start_location": "New York", "end_location": "Boston", "price": "45.99"},
        {"start_location": "Los Angeles", "end_location": "San Francisco", "price": "89.50"},
        {"start_location": "Chicago", "end_location": "Detroit", "price": "67.25"},
        {"start_location": "Miami", "end_location": "Orlando", "price": "34.75"},
        {"start_location": "Seattle", "end_location": "Portland", "price": "52.00"},
        {"start_location": "Houston", "end_location": "Dallas", "price": "41.30"},
        {"start_location": "Denver", "end_location": "Phoenix", "price": "73.85"}
    ]
    
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
            
            print("Navigating to route automation app...")
            await page.goto('https://angularformadd.netlify.app/')
            
            print("Taking initial screenshot...")
            await page.screenshot(path='/screenshots/before_routes.png')
            
            print(f"Starting to insert {len(routes)} route records...")
            
            for i, route in enumerate(routes, 1):
                print(f"Inserting route {i}/{len(routes)}: {route['start_location']} -> {route['end_location']}")
                
                # Click the "Add New Route" button
                await page.get_by_role("button", name="+ Add New Route").click()
                
                # Fill in the start location
                await page.get_by_role("textbox", name="Enter start location").fill(route["start_location"])
                
                # Fill in the end location  
                await page.get_by_role("textbox", name="Enter end location").fill(route["end_location"])
                
                # Fill in the price
                await page.get_by_placeholder("0.00").fill(route["price"])
                
                # Save the route
                await page.get_by_role("button", name="Save Route").click()
                
                # Small delay to see the action
                await asyncio.sleep(1)
                
                print(f"✅ Route {i} added successfully")
            
            print("Taking final screenshot...")
            await page.screenshot(path='/screenshots/after_routes.png')
            
            print("Waiting 15 seconds for you to see all routes in VNC...")
            await asyncio.sleep(15)
            
            print("Closing browser...")
            await browser.close()
            
            print("✅ Test completed successfully!")
            print(f"Successfully inserted {len(routes)} route records")
            print("You should have seen the browser open in your VNC viewer")
            print("Check /screenshots/before_routes.png and /screenshots/after_routes.png for screenshots")
            
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
