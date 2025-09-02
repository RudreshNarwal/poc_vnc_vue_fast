from playwright.async_api import async_playwright, Browser, Page
import asyncio
import os
from datetime import datetime
import pytz
from typing import Dict, Any, Optional
import logging
import uuid

from app.config import settings
from app.services.data_loader import load_and_validate_records
from app.models.file import File

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
    
    async def execute_task(self, task_data: Dict[str, Any], file: File = None):
        self.is_running = True
        logger.info(f"Session {self.session_id}: Executing task '{task_data['name']}'")

        try:
            if task_data.get("script_path"):
                await self.execute_script_based_task(task_data, file)
            elif task_data.get("steps"):
                await self.execute_step_based_task(task_data)
            else:
                # Default to a simple demo if no steps or script
                await self.run_demo_flow()
        except Exception as e:
            logger.error(f"Session {self.session_id}: Task execution failed: {e}", exc_info=True)
            await self.send_status("error", f"Automation failed: {str(e)}")
        finally:
            await self.cleanup()

    async def execute_script_based_task(self, task_data: Dict[str, Any], file: File):
        script_path = task_data["script_path"]
        logger.info(f"Session {self.session_id}: Running script-based task from '{script_path}'")

        if not file:
            raise ValueError("This task requires a data file, but none was provided.")

        # Download the file from storage
        storage = get_storage_service()
        local_path = f"/tmp/{file.filename}"
        storage.download_file(file.storage_path, local_path)
        
        # Load records from the downloaded file
        data = load_and_validate_records(local_path)
        if not data["is_valid"]:
            raise ValueError(f"Data file is invalid: {data['error']}")
        
        # Dynamically import the automation script
        try:
            module_path, func_name = script_path.rsplit(':', 1)
            module = importlib.import_module(module_path)
            automation_func = getattr(module, func_name)
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Could not import automation function '{script_path}': {e}")
        
        # Define progress callback
        async def progress_callback(progress_data: Dict[str, Any]):
            await self.send_status("progress", "Automation progress", progress_data)
            
        # Run the automation script
        async with async_playwright() as p:
            # Note: The script itself is synchronous, so we'd need to run it in a thread
            # to avoid blocking the asyncio event loop. For simplicity in this example,
            # we'll assume the script is fast or this is run in a separate process.
            # A production implementation should use `loop.run_in_executor`.
            automation_func(p, data, progress_callback)
        
        logger.info(f"Session {self.session_id}: Script-based task completed.")

    async def execute_step_based_task(self, task_data: Dict[str, Any]):
        """Execute data-driven automation from a validated CSV/Excel file."""
        import os
        file_path = os.path.join(settings.upload_dir, filename)
        data = load_and_validate_records(file_path)
        records = data["records"]

        await self.send_status("running", f"Processing {len(records)} records from file.")
        await self.page.goto("https://angularformadd.netlify.app/")

        for i, record in enumerate(records, 1):
            if not self.is_running:
                break
            while self.is_paused:
                await asyncio.sleep(0.5)
            await self.send_status(
                "running",
                f"Processing record {i}/{len(records)}: {record['start_location']}",
                {"current_step": i, "total_steps": len(records)}
            )

            await self.page.get_by_role("button", name="+ Add New Route").click()
            await self.page.get_by_role("textbox", name="Enter start location").fill(record["start_location"]) 
            await self.page.get_by_role("textbox", name="Enter end location").fill(record["end_location"]) 
            await self.page.get_by_placeholder("0.00").fill(str(record["price"]))
            await self.page.get_by_role("button", name="Save Route").click()
            await asyncio.sleep(0.5)

    async def run_demo_flow(self):
        """Run a demo flow equivalent to the provided sync Playwright script.

        This is used when a task does not provide structured steps. The flow opens
        the demo site and performs a short interaction, which should be visible via VNC.
        """
        try:
            # Navigate to the sample app
            await self.page.goto("https://angularformadd.netlify.app/")

            # Interact per the script
            await self.page.get_by_role("button", name="+ Add New Route").click()
            await self.page.get_by_role("textbox", name="Enter start location").click()
            await self.page.get_by_role("textbox", name="Enter start location").fill("test")
            await self.page.get_by_role("textbox", name="Enter end location").click()
            await self.page.get_by_role("textbox", name="Enter end location").fill("test")
            await self.page.get_by_placeholder("0.00").click()
            await self.page.get_by_placeholder("0.00").fill("100")
            await self.page.get_by_role("button", name="Save Route").click()
            await self.page.get_by_role("button", name="⚡").click()
            await self.page.get_by_role("button", name="▶️ Run Demo (2 Routes)").click()

            # Small wait to ensure UI updates are visible
            await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Demo flow failed: {str(e)}")
            await self.send_status("error", f"Demo flow failed: {str(e)}")
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
