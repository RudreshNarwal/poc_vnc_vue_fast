from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
import json
import uuid
import os
from datetime import datetime
from typing import Dict, List, Optional
import logging

from app.config import settings
from app.models.database import init_db, AsyncSessionLocal
from app.models.task import Task
from sqlalchemy import select
from app.services.automation import AutomationEngine
from app.api import tasks, automation, files, websocket


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup
    await init_db()
    
    # Seed initial data
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Task).where(Task.name == "Route Addition Automation"))
        if not result.scalar_one_or_none():
            new_task = Task(
                name="Route Addition Automation",
                description="Upload a CSV/Excel file to add multiple routes to the system.",
                status="ready",
                script_path="app.automation_scripts.route_automation:run_automation",
                prerequisites=[{
                    "type": "file_upload",
                    "name": "routes_file",
                    "description": "A .csv or .xlsx file with 'start_location', 'end_location', and 'price' columns.",
                    "required": True
                }]
            )
            db.add(new_task)
            await db.commit()
    yield
    # On shutdown
    # (any cleanup logic here)

# Create FastAPI app
app = FastAPI(lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/screenshots", StaticFiles(directory=settings.screenshot_dir), name="screenshots")
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

# Include routers
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(automation.router, prefix="/api/automation", tags=["automation"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timezone": settings.timezone,
        "vnc_host": settings.vnc_host,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/vnc/config")
async def get_vnc_config(request: Request):
    """Get VNC configuration for frontend"""
    
    # Dynamic hostname detection
    host = request.headers.get('host', 'localhost').split(':')[0]
    
    # In production, you might want to use an environment variable
    vnc_host = os.getenv('VNC_PUBLIC_HOST', host)
    
    # For Docker internal communication
    if host == 'backend':
        vnc_host = 'vnc'
    
    return {
        "url": f"ws://{vnc_host}:7900/websockify",  # noVNC websockify endpoint
        "vnc_url": f"http://{vnc_host}:7900/vnc.html",  # noVNC HTTP interface
        "password": None,  # For dev only
        "autoconnect": True,
        "view_only": False,
        "show_dot_cursor": True,
        "timezone": settings.timezone
    }

@app.get("/api/test-browser")
async def test_browser():
    """Test Playwright browser on VNC display"""
    try:
        from playwright.async_api import async_playwright
        import asyncio
        
        logger.info("Starting browser test on VNC display")
        
        async with async_playwright() as p:
            # Launch browser on VNC display
            browser = await p.chromium.launch(
                headless=False,  # MUST be False to see in VNC
                args=[
                    '--display=:1',  # Use VNC display
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--start-maximized'
                ]
            )
            
            page = await browser.new_page()
            await page.goto('https://www.google.com')
            
            logger.info("Browser opened Google - should be visible in VNC")
            
            # Keep browser open for 5 seconds
            await asyncio.sleep(5)
            
            await browser.close()
            logger.info("Browser test completed successfully")
            
            return {
                "status": "success", 
                "message": "Browser test completed - check VNC viewer",
                "display": ":1"
            }
    except Exception as e:
        logger.error(f"Browser test failed: {str(e)}")
        return {
            "status": "error", 
            "message": str(e)
        }
