from playwright.async_api import async_playwright, Browser, Page
import asyncio
import os
from datetime import datetime
import pytz
from typing import Dict, Any, Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)

class WebSocketManager:
    """WebSocket connection manager"""
    def __init__(self):
        self.connections: Dict[str, Any] = {}
    
    async def connect(self, websocket, session_id: str):
        """Connect a WebSocket"""
        await websocket.accept()
        self.connections[session_id] = websocket
        logger.info(f"WebSocket connected for session: {session_id}")
    
    def disconnect(self, session_id: str):
        """Disconnect a WebSocket"""
        if session_id in self.connections:
            del self.connections[session_id]
            logger.info(f"WebSocket disconnected for session: {session_id}")
    
    async def send_to_session(self, session_id: str, message: Dict):
        """Send message to specific session"""
        if session_id in self.connections:
            try:
                await self.connections[session_id].send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to session {session_id}: {str(e)}")
                self.disconnect(session_id)

# Global WebSocket manager instance
websocket_manager = WebSocketManager()

class AutomationEngine:
    def __init__(self, session_id: str, websocket_manager: WebSocketManager):
        self.session_id = session_id
        self.ws_manager = websocket_manager
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.is_paused = False
        self.is_running = False
        
        # Set timezone
        self.timezone = pytz.timezone(settings.timezone)
        os.environ['TZ'] = settings.timezone
    
    async def initialize_browser(self):
        """Initialize browser with proper VNC configuration"""
        try:
            self.playwright = await async_playwright().start()
            
            # Browser launch arguments optimized for VNC
            browser_args = [
                f'--display={settings.vnc_display}',  # CRITICAL: Use VNC display
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-software-rasterizer',
                f'--window-size={settings.playwright_viewport_width},{settings.playwright_viewport_height}',
                '--window-position=0,0',
                '--start-maximized',
                '--force-device-scale-factor=1',
                f'--lang=en-US',
                f'--timezone={settings.timezone}'
            ]
            
            # Launch browser - MUST be headless=False for VNC visibility
            self.browser = await self.playwright.chromium.launch(
                headless=False,  # CRITICAL: Must be False to see in VNC
                args=browser_args
            )
            
            # Create context with timezone
            context = await self.browser.new_context(
                viewport={
                    'width': settings.playwright_viewport_width,
                    'height': settings.playwright_viewport_height
                },
                timezone_id=settings.timezone,
                locale='en-US',
                device_scale_factor=1
            )
            
            self.page = await context.new_page()
            
            # Test navigation to verify it's working
            await self.page.goto('about:blank')
            
            # Log browser info
            logger.info(f"Browser initialized for session {self.session_id}")
            logger.info(f"Timezone: {settings.timezone}")
            logger.info(f"Display: {settings.vnc_display}")
            logger.info("Browser should be visible in VNC viewer")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize browser: {str(e)}")
            await self.send_status("error", f"Browser initialization failed: {str(e)}")
            return False
    
    async def send_status(self, status: str, message: str, data: Dict = None):
        """Send status update via WebSocket"""
        await self.ws_manager.send_to_session(
            self.session_id,
            {
                "type": "status",
                "status": status,
                "message": message,
                "data": data or {},
                "timestamp": datetime.now(self.timezone).isoformat()
            }
        )
    
    async def execute_task(self, task_data: Dict[str, Any], file = None):
        self.is_running = True
        logger.info(f"Session {self.session_id}: Executing task '{task_data['name']}'")

        # Always initialize the browser so VNC displays activity
        if not await self.initialize_browser():
            logger.error(f"Session {self.session_id}: Halting task due to browser initialization failure.")
            await self.cleanup()
            return

        try:
            # Run the actual route automation script with async browser workflow
            logger.info(f"Session {self.session_id}: Running route automation script.")
            await self.run_route_automation()
            await self.send_status("completed", "Route automation finished. Manual control is now active.")

            # Keep the browser open for manual interaction (no time limit)
            logger.info(f"Session {self.session_id}: Browser will remain open indefinitely for manual inspection.")
            
            # Wait indefinitely - user can manually close or use stop command
            while self.is_running:
                await asyncio.sleep(10)  # Check every 10 seconds if still running

        except Exception as e:
            logger.error(f"Session {self.session_id}: Task execution failed: {e}", exc_info=True)
            await self.send_status("error", f"Automation failed: {str(e)}")
        finally:
            # Intentionally not cleaning up immediately to keep VNC visible
            # await self.cleanup()
            logger.info(f"Session {self.session_id}: Task finished. Browser will remain open.")



    async def run_route_automation(self):
        """Run the actual route automation script using existing browser.

        This calls the async route_automation function with the current page instance.
        """
        try:
            # Import the async route automation function
            from app.automation_scripts.route_automation import run_automation_async
            
            # Define progress callback (async version for route automation)
            async def progress_callback(progress_data: Dict[str, Any]):
                await self.send_status("progress", "Route automation progress", progress_data)
            
            # Run the automation script with existing page
            await run_automation_async(self.page, progress_callback)
            
        except Exception as e:
            logger.error(f"Route automation failed: {str(e)}")
            await self.send_status("error", f"Route automation failed: {str(e)}")
            raise

    # =============================================================================
    # OLD DEMO FLOW - COMMENTED OUT FOR TESTING PURPOSES
    # Uncomment this method if you want to test the original demo flow
    # =============================================================================
    
    # async def run_demo_flow(self):
    #     """Run a demo flow that inserts 7 route records.
    #
    #     This is used when a task does not provide structured steps. The flow opens
    #     the demo site and performs route insertions, which should be visible via VNC.
    #     """
    #     try:
    #         # Navigate to the sample app
    #         await self.page.goto("https://angularformadd.netlify.app/")
    #
    #         # Define 7 route records to insert
    #         routes = [
    #             {"start_location": "New York", "end_location": "Boston", "price": "45.99"},
    #             {"start_location": "Los Angeles", "end_location": "San Francisco", "price": "89.50"},
    #             {"start_location": "Chicago", "end_location": "Detroit", "price": "67.25"},
    #             {"start_location": "Miami", "end_location": "Orlando", "price": "34.75"},
    #             {"start_location": "Seattle", "end_location": "Portland", "price": "52.00"},
    #             {"start_location": "Houston", "end_location": "Dallas", "price": "41.30"},
    #             {"start_location": "Denver", "end_location": "Phoenix", "price": "73.85"}
    #         ]
    #
    #         # Insert all 7 routes
    #         for i, route in enumerate(routes, 1):
    #             await self.send_status("running", f"Adding route {i}/7: {route['start_location']} → {route['end_location']}")
    #             
    #             # Click the "Add New Route" button
    #             await self.page.get_by_role("button", name="+ Add New Route").click()
    #             
    #             # Fill in the start location
    #             await self.page.get_by_role("textbox", name="Enter start location").fill(route["start_location"])
    #             
    #             # Fill in the end location  
    #             await self.page.get_by_role("textbox", name="Enter end location").fill(route["end_location"])
    #             
    #             # Fill in the price
    #             await self.page.get_by_placeholder("0.00").fill(route["price"])
    #             
    #             # Save the route
    #             await self.page.get_by_role("button", name="Save Route").click()
    #             
    #             # Small delay to see the action and allow UI to update
    #             await asyncio.sleep(1)
    #
    #         # Final status update
    #         await self.send_status("running", f"Successfully added all {len(routes)} routes!")
    #         
    #         # Click the FAB button (⚡) to show the results
    #         await self.page.get_by_role("button", name="⚡").click()
    #         
    #         # Take a screenshot to capture the final state
    #         screenshot_path = f"/screenshots/demo_result_{self.session_id}.png"
    #         await self.page.screenshot(path=screenshot_path)
    #         logger.info(f"Screenshot saved: {screenshot_path}")
    #         await self.send_status("running", f"Screenshot captured: {screenshot_path}")
    #         
    #         # Wait to ensure all UI updates are visible
    #         await asyncio.sleep(3)
    #
    #     except Exception as e:
    #         logger.error(f"Demo flow failed: {str(e)}")
    #         await self.send_status("error", f"Demo flow failed: {str(e)}")
    #         raise
    
    async def pause(self):
        """Pause automation"""
        self.is_paused = True
        await self.send_status("paused", "Automation paused")
    
    async def resume(self):
        """Resume automation"""
        self.is_paused = False
        await self.send_status("running", "Automation resumed")
    
    async def stop(self):
        """Stop automation"""
        self.is_running = False
        self.is_paused = False
        await self.send_status("stopped", "Automation stopped")
        await self.cleanup()
    
    async def cleanup(self):
        """Clean up browser resources"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")

# Global automation engines
automation_engines: Dict[str, AutomationEngine] = {}
