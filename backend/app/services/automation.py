from playwright.async_api import async_playwright, Browser, Page
import asyncio
import os
from datetime import datetime
import pytz
from typing import Dict, Any, Optional
import logging
import httpx

from app.config import settings
from tempfile import NamedTemporaryFile
from app.services.data_loader import load_and_validate_records
from app.services.storage import get_storage_service
from app.models.database import AsyncSessionLocal
from app.models.execution import Execution

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
        self.vnc_session: Optional[Dict[str, Any]] = None
        self.task_id: Optional[int] = None
        
        # Set timezone
        self.timezone = pytz.timezone(settings.timezone)
        os.environ['TZ'] = settings.timezone
    
    async def initialize_browser(self):
        """Initialize browser with proper VNC configuration"""
        try:
            self.playwright = await async_playwright().start()
            
            # Determine display (single-session default or per-session)
            display = settings.vnc_display
            if settings.enable_multi_session:
                try:
                    async with httpx.AsyncClient() as client:
                        resp = await client.post(
                            f"{settings.session_manager_url}/api/sessions/create",
                            json={
                                "user_id": self.session_id,
                                "task_id": self.task_id,
                                "timeout_minutes": 30
                            },
                            timeout=30.0
                        )
                        resp.raise_for_status()
                        self.vnc_session = resp.json()
                        display = f":{self.vnc_session['display']}"
                except Exception as e:
                    logger.error(f"Failed to allocate VNC session: {e}")
                    raise

            # Browser launch arguments optimized for VNC
            browser_args = [
                f'--display={display}',  # CRITICAL: Use VNC display
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
            
            # Show a visible page immediately so VNC is not blank
            start_url = os.getenv('AUTOMATION_START_URL', 'https://rhobots.ai')
            await self.page.goto(start_url)
            
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
    
    async def execute_task(self, task_data: Dict[str, Any], file = None, execution_id: Optional[int] = None):
        self.is_running = True
        logger.info(f"Session {self.session_id}: Executing task '{task_data['name']}'")

        # Record task id for session allocation
        try:
            self.task_id = int(task_data.get('id')) if task_data and task_data.get('id') is not None else None
        except Exception:
            self.task_id = None

        # Always initialize the browser so VNC displays activity
        if not await self.initialize_browser():
            logger.error(f"Session {self.session_id}: Halting task due to browser initialization failure.")
            await self.cleanup()
            return

        try:
            # Resolve records from provided file (required)
            if file is None:
                raise ValueError("No file provided. Upload a CSV/XLSX and start again.")

            storage_backend = settings.STORAGE_BACKEND
            local_path = None
            tmp_path = None
            try:
                if storage_backend == "minio":
                    storage = get_storage_service()
                    with NamedTemporaryFile(delete=False, suffix=f".{getattr(file, 'file_type', 'csv')}") as tmp:
                        tmp_path = tmp.name
                    storage.download_file(file.storage_path, tmp_path)
                    local_path = tmp_path
                else:
                    # local storage; file.storage_path is typically an absolute path
                    local_path = file.storage_path if os.path.isabs(file.storage_path) else os.path.join(settings.upload_dir, file.storage_path)

                parsed = load_and_validate_records(local_path)
                records = parsed.get("records", [])
                if not records:
                    raise ValueError("No valid data rows found after parsing the file.")

                # Mark execution as running with total steps
                if execution_id is not None:
                    await self._update_execution(execution_id, {
                        "status": "running",
                        "start_time": datetime.now(self.timezone),
                        "total_steps": len(records),
                        "current_step": 0,
                        "error_message": None
                    })

                # Run the actual route automation script with async browser workflow
                logger.info(f"Session {self.session_id}: Running route automation script for {len(records)} records.")
                await self.run_route_automation(records, execution_id)
                await self.send_status("completed", "Route automation finished. Manual control is now active.")
                if execution_id is not None:
                    await self._update_execution(execution_id, {
                        "status": "completed",
                        "end_time": datetime.now(self.timezone)
                    })
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass

            # Keep the browser open for manual interaction (no time limit)
            logger.info(f"Session {self.session_id}: Browser will remain open indefinitely for manual inspection.")
            
            # Wait indefinitely - user can manually close or use stop command
            while self.is_running:
                await asyncio.sleep(10)  # Check every 10 seconds if still running

        except Exception as e:
            logger.error(f"Session {self.session_id}: Task execution failed: {e}", exc_info=True)
            await self.send_status("error", f"Automation failed: {str(e)}")
            if execution_id is not None:
                await self._update_execution(execution_id, {
                    "status": "failed",
                    "end_time": datetime.now(self.timezone),
                    "error_message": str(e)
                })
        finally:
            # Intentionally not cleaning up immediately to keep VNC visible
            # await self.cleanup()
            logger.info(f"Session {self.session_id}: Task finished. Browser will remain open.")



    async def run_route_automation(self, records, execution_id: Optional[int] = None):
        """Run the actual route automation script using existing browser.

        This calls the async route_automation function with the current page instance.
        """
        try:
            # Import the async route automation function
            from app.automation_scripts.route_automation import run_automation_async
            
            # Define progress callback (async version for route automation)
            async def progress_callback(progress_data: Dict[str, Any]):
                await self.send_status("progress", "Route automation progress", progress_data)
                try:
                    # Update current step if provided
                    step = None
                    if "processed_count" in progress_data:
                        step = progress_data.get("processed_count")
                    elif "step" in progress_data:
                        step = progress_data.get("step")
                    if execution_id is not None and step is not None:
                        await self._update_execution(execution_id, {"current_step": int(step)})
                except Exception:
                    # Do not disrupt automation on telemetry failures
                    pass

            # Run the automation script with existing page
            await run_automation_async(self.page, progress_callback, records)
            
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
    
    async def pause(self, execution_id: Optional[int] = None):
        """Pause automation"""
        self.is_paused = True
        await self.send_status("paused", "Automation paused")
        if execution_id is not None:
            await self._update_execution(execution_id, {"status": "paused"})
    
    async def resume(self, execution_id: Optional[int] = None):
        """Resume automation"""
        self.is_paused = False
        await self.send_status("running", "Automation resumed")
        if execution_id is not None:
            await self._update_execution(execution_id, {"status": "running"})
    
    async def stop(self, execution_id: Optional[int] = None):
        """Stop automation"""
        self.is_running = False
        self.is_paused = False
        await self.send_status("stopped", "Automation stopped")
        if execution_id is not None:
            await self._update_execution(execution_id, {
                "status": "stopped",
                "end_time": datetime.now(self.timezone)
            })
        # Do NOT cleanup here to allow manual control via VNC after stopping
        return

    async def end_session(self):
        """Fully end the session and cleanup resources (used when user closes the session)"""
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

        # Destroy VNC session if allocated
        try:
            if settings.enable_multi_session and getattr(self, 'vnc_session', None):
                sid = self.vnc_session.get('session_id')
                if sid:
                    async with httpx.AsyncClient() as client:
                        await client.delete(f"{settings.session_manager_url}/api/sessions/{sid}", timeout=15.0)
        except Exception as e:
            logger.error(f"Session cleanup error: {str(e)}")

    async def _update_execution(self, execution_id: int, fields: Dict[str, Any]):
        """Update execution row in DB."""
        try:
            async with AsyncSessionLocal() as db:
                exec_obj = await db.get(Execution, execution_id)
                if not exec_obj:
                    return
                for k, v in (fields or {}).items():
                    setattr(exec_obj, k, v)
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to update execution {execution_id}: {e}")

# Global automation engines
automation_engines: Dict[str, AutomationEngine] = {}
