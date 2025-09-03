from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright
import asyncio
import os
from datetime import datetime
import pytz
from typing import Dict, Any, Optional
import logging
import uuid
import importlib
from concurrent.futures import ThreadPoolExecutor
import threading

from app.config import settings
from app.services.data_loader import load_and_validate_records
from app.models.file import File
from app.services.storage import get_storage_service

logger = logging.getLogger(__name__)

# Thread pool for running synchronous Playwright scripts
executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="playwright_")

class WebSocketManager:
    """WebSocket connection manager"""
    def __init__(self):
        self.connections: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    async def connect(self, websocket, session_id: str):
        """Connect a WebSocket"""
        await websocket.accept()
        with self._lock:
            self.connections[session_id] = websocket
        logger.info(f"WebSocket connected for session: {session_id}")
    
    def disconnect(self, session_id: str):
        """Disconnect a WebSocket"""
        with self._lock:
            if session_id in self.connections:
                del self.connections[session_id]
        logger.info(f"WebSocket disconnected for session: {session_id}")
    
    async def send_to_session(self, session_id: str, message: Dict):
        """Send message to specific session"""
        websocket = None
        with self._lock:
            websocket = self.connections.get(session_id)
        
        if websocket:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to session {session_id}: {str(e)}")
                self.disconnect(session_id)

# Global WebSocket manager instance
websocket_manager = WebSocketManager()

class AutomationEngine:
    def __init__(self, session_id: str, websocket_manager: WebSocketManager):
        self.session_id = session_id
        self.ws_manager = websocket_manager
        self.is_paused = False
        self.is_running = False
        self.should_stop = False
        
        # Set timezone
        self.timezone = pytz.timezone(settings.timezone)
        os.environ['TZ'] = settings.timezone
        
        # Track script execution
        self.script_future = None
        self.script_thread = None
    
    async def send_status(self, status: str, message: str, data: Dict = None):
        """Send status update via WebSocket"""
        await self.ws_manager.send_to_session(
            self.session_id,
            {
                "type": "status",
                "status": status,
                "message": message,
                "data": data or {},
                "timestamp": datetime.now(self.timezone).isoformat(),
                "session_id": self.session_id
            }
        )
    
    async def execute_task(self, task_data: Dict[str, Any], file: File = None):
        """Execute a task - determines if it's script-based or step-based"""
        self.is_running = True
        self.should_stop = False
        
        logger.info(f"Session {self.session_id}: Starting task '{task_data['name']}'")
        await self.send_status("starting", f"Initializing task: {task_data['name']}")
        
        try:
            # Check if this is a script-based task
            script_path = task_data.get("script_path")
            
            if script_path and file:
                # Script-based task with file
                await self.execute_script_based_task(task_data, file)
            elif task_data.get("steps"):
                # Step-based task (legacy support)
                await self.execute_step_based_task(task_data)
            else:
                # Demo flow for testing
                await self.execute_demo_flow()
            
        except Exception as e:
            logger.error(f"Session {self.session_id}: Task execution failed: {e}", exc_info=True)
            await self.send_status("error", f"Automation failed: {str(e)}")
        finally:
            self.is_running = False
            logger.info(f"Session {self.session_id}: Task completed")
    
    async def execute_script_based_task(self, task_data: Dict[str, Any], file: File):
        """Execute a Playwright script with proper VNC integration"""
        script_path = task_data["script_path"]
        logger.info(f"Session {self.session_id}: Running script '{script_path}'")
        
        await self.send_status("running", "Loading and validating data file...")
        
        # Download and validate file
        storage = get_storage_service()
        local_path = f"/tmp/{self.session_id}_{file.filename}"
        
        try:
            # Get file from storage
            if hasattr(storage, 'download_file'):
                storage.download_file(file.storage_path, local_path)
            else:
                # For local storage, the path is already local
                local_path = file.storage_path
            
            # Load and validate records
            data = load_and_validate_records(local_path)
            if not data.get("is_valid", True):
                raise ValueError(f"Data file validation failed: {data.get('error', 'Unknown error')}")
            
            await self.send_status(
                "running", 
                f"Data validated. Processing {data.get('total_rows', 0)} records..."
            )
            
            # Import the automation script
            module_path, func_name = script_path.rsplit(':', 1)
            module = importlib.import_module(module_path)
            automation_func = getattr(module, func_name)
            
            # Create async wrapper for progress callback
            progress_queue = asyncio.Queue()
            
            def sync_progress_callback(progress_data: Dict[str, Any]):
                """Synchronous callback that puts data in queue"""
                try:
                    # Use thread-safe method to schedule coroutine
                    asyncio.run_coroutine_threadsafe(
                        progress_queue.put(progress_data),
                        loop
                    )
                except Exception as e:
                    logger.error(f"Progress callback error: {e}")
            
            # Run the script in a thread (since it's synchronous)
            loop = asyncio.get_running_loop()
            
            # Create task to process progress updates
            async def process_progress():
                while True:
                    try:
                        progress_data = await asyncio.wait_for(
                            progress_queue.get(), 
                            timeout=1.0
                        )
                        await self.send_status(
                            progress_data.get("status", "running"),
                            progress_data.get("message", "Processing..."),
                            progress_data
                        )
                        if progress_data.get("status") in ["completed", "failed"]:
                            break
                    except asyncio.TimeoutError:
                        if not self.is_running:
                            break
                        continue
                    except Exception as e:
                        logger.error(f"Progress processing error: {e}")
                        break
            
            # Start progress processor
            progress_task = asyncio.create_task(process_progress())
            
            # Run the Playwright script in executor
            self.script_future = loop.run_in_executor(
                executor,
                self._run_playwright_script,
                automation_func,
                data,
                sync_progress_callback
            )
            
            # Wait for script completion
            await self.script_future
            
            # Ensure progress task completes
            await progress_queue.put({"status": "completed", "message": "Automation finished"})
            await progress_task
            
            logger.info(f"Session {self.session_id}: Script execution completed")
            
        except Exception as e:
            logger.error(f"Script execution failed: {e}", exc_info=True)
            await self.send_status("error", f"Script execution failed: {str(e)}")
            raise
        finally:
            # Cleanup temp file
            if os.path.exists(local_path) and local_path.startswith('/tmp/'):
                try:
                    os.remove(local_path)
                except:
                    pass
    
    def _run_playwright_script(self, automation_func, data, progress_callback):
        """Run synchronous Playwright script (executes in thread)"""
        try:
            # Set environment for thread (removed VNC display setting)
            # os.environ['DISPLAY'] = ':1'  # Commented out for local development
            
            with sync_playwright() as playwright:
                automation_func(playwright, data, progress_callback)
                
        except Exception as e:
            logger.error(f"Playwright script error: {e}", exc_info=True)
            progress_callback({
                "status": "failed",
                "message": f"Script error: {str(e)}",
                "error": str(e)
            })
            raise
    
    async def execute_step_based_task(self, task_data: Dict[str, Any]):
        """Execute a step-based automation task"""
        steps = task_data.get("steps", [])
        total_steps = len(steps)
        
        await self.send_status("running", f"Executing {total_steps} steps...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                for i, step in enumerate(steps, 1):
                    if self.should_stop:
                        break
                    
                    while self.is_paused:
                        await asyncio.sleep(0.5)
                    
                    await self.send_status(
                        "running",
                        f"Executing step {i}/{total_steps}: {step.get('action')}",
                        {"current_step": i, "total_steps": total_steps}
                    )
                    
                    # Execute step based on action type
                    await self._execute_step(page, step)
                    await asyncio.sleep(0.5)
                
                await self.send_status("completed", "Task completed successfully")
                
            finally:
                await browser.close()
    
    async def _execute_step(self, page, step):
        """Execute a single automation step"""
        action = step.get("action")
        target = step.get("target", "")
        value = step.get("value", "")
        
        if action == "navigate":
            await page.goto(target)
        elif action == "click":
            await page.click(target)
        elif action == "type":
            await page.fill(target, value)
        elif action == "wait":
            if target == "delay":
                await asyncio.sleep(int(value) / 1000)
            else:
                await page.wait_for_selector(target)
        # Add more actions as needed
    
    async def execute_demo_flow(self):
        """Execute a demo flow for testing"""
        await self.send_status("running", "Running demo automation...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            
            page = await browser.new_page()
            await page.goto("https://angularformadd.netlify.app/")
            await asyncio.sleep(3)
            
            await self.send_status("completed", "Demo completed")
            await browser.close()
    
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
        self.should_stop = True
        self.is_running = False
        
        # Cancel script if running
        if self.script_future and not self.script_future.done():
            self.script_future.cancel()
        
        await self.send_status("stopped", "Automation stopped")

# Global automation engines registry - supports parallel execution
automation_engines: Dict[str, AutomationEngine] = {}
