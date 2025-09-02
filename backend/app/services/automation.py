from playwright.async_api import async_playwright, Browser, Page
import asyncio
import os
from datetime import datetime
import pytz
from typing import Dict, Any, Optional
import logging
import uuid

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
    
    async def execute_task(self, task_data: Dict[str, Any]):
        """Execute automation task"""
        try:
            self.is_running = True
            
            # Initialize browser
            if not await self.initialize_browser():
                return
            
            await self.send_status("running", "Starting automation...")
            
            # Execute steps
            steps = task_data.get('steps', [])
            for i, step in enumerate(steps):
                if not self.is_running:
                    break
                    
                # Check if paused
                while self.is_paused:
                    await asyncio.sleep(0.5)
                
                # Execute step
                await self.send_status(
                    "running", 
                    f"Executing step {i+1}: {step.get('action', 'unknown')}",
                    {"current_step": i+1, "total_steps": len(steps)}
                )
                
                await self.execute_step(step)
                
                # Take screenshot after each step
                screenshot_filename = f"{self.session_id}_step_{i+1}.png"
                screenshot_path = f"{settings.screenshot_dir}/{screenshot_filename}"
                await self.page.screenshot(path=screenshot_path)
                
                await self.send_status(
                    "step_complete",
                    f"Step {i+1} completed",
                    {"step": i+1, "screenshot": f"/screenshots/{screenshot_filename}"}
                )
            
            await self.send_status("completed", "Automation completed successfully")
            
        except Exception as e:
            logger.error(f"Automation error: {str(e)}")
            await self.send_status("error", f"Automation failed: {str(e)}")
        finally:
            await self.cleanup()
    
    async def execute_step(self, step: Dict[str, Any]):
        """Execute individual automation step"""
        action = step.get('action')
        target = step.get('target')
        value = step.get('value')
        
        try:
            if action == 'navigate':
                await self.page.goto(target, wait_until='networkidle', timeout=settings.playwright_timeout)
            
            elif action == 'click':
                await self.page.click(target, timeout=settings.playwright_timeout)
            
            elif action == 'type':
                await self.page.fill(target, value, timeout=settings.playwright_timeout)
            
            elif action == 'wait':
                if target == 'wait_for_element':
                    await self.page.wait_for_selector(value, timeout=settings.playwright_timeout)
                else:
                    await asyncio.sleep(int(value) / 1000)  # Convert ms to seconds
            
            elif action == 'select':
                await self.page.select_option(target, value, timeout=settings.playwright_timeout)
            
            elif action == 'screenshot':
                filename = f"{self.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await self.page.screenshot(path=f"{settings.screenshot_dir}/{filename}")
            
            elif action == 'interactive_pause':
                await self.send_status("paused", "Automation paused for interaction")
                self.is_paused = True
                while self.is_paused:
                    await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Step execution failed: {str(e)}")
            raise
    
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
