from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
from datetime import datetime
import logging

from app.config import settings
from app.models.database import init_db, AsyncSessionLocal
from app.models.task import Task
from sqlalchemy import select
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
    
    # Seed initial tasks
    async with AsyncSessionLocal() as db:
        # Task 1: Legacy Route Addition
        result = await db.execute(
            select(Task).where(Task.name == "Route Addition Automation")
        )
        if not result.scalar_one_or_none():
            task1 = Task(
                name="Route Addition Automation",
                description="Legacy automation - Adds a few hardcoded routes for demonstration.",
                status="ready",
                script_path="app.automation_scripts.route_automation:run_automation",
                prerequisites=[]
            )
            db.add(task1)
            logger.info("Created Task 1: Route Addition Automation")
        
        # Task 2: Upload CSV Test
        result = await db.execute(
            select(Task).where(Task.name == "Upload CSV Test")
        )
        if not result.scalar_one_or_none():
            task2 = Task(
                name="Upload CSV Test",
                description="New automation - Upload and process CSV data to automatically add routes in bulk.",
                status="ready",
                script_path="app.automation_scripts.upload_csv_automation:run_automation",
                prerequisites=[{
                    "type": "file_upload",
                    "name": "csv_file",
                    "description": "A .csv or .xlsx file with 'start_location', 'end_location', and 'price' columns for bulk route addition.",
                    "required": True
                }]
            )
            db.add(task2)
            logger.info("Created Task 2: Upload CSV Test")
        
        await db.commit()
        logger.info("Database seeding completed")
    
    yield
    # On shutdown
    logger.info("Application shutting down...")

# Create FastAPI app
app = FastAPI(
    title="Browser Automation Studio",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
os.makedirs(settings.screenshot_dir, exist_ok=True)
os.makedirs(settings.upload_dir, exist_ok=True)

app.mount("/screenshots", StaticFiles(directory=settings.screenshot_dir), name="screenshots")
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

# Include routers
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(automation.router, prefix="/api/automation", tags=["automation"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])

@app.get("/")
async def root():
    return {
        "name": "Browser Automation Studio",
        "version": "2.0.0",
        "status": "operational",
        "tasks_enabled": True,
        "vnc_enabled": True
    }

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timezone": settings.timezone,
        "vnc_host": settings.vnc_host,
        "vnc_display": settings.vnc_display,
        "timestamp": datetime.now().isoformat(),
        "tasks_available": 2
    }

@app.get("/api/vnc/config")
async def get_vnc_config(request: Request):
    """Get VNC configuration for frontend"""
    
    # Dynamic hostname detection
    host = request.headers.get('host', 'localhost').split(':')[0]
    
    # In production, use environment variable
    vnc_host = os.getenv('VNC_PUBLIC_HOST', host)
    
    # For Docker internal communication
    if host == 'backend':
        vnc_host = 'vnc'
    
    return {
        "url": f"ws://{vnc_host}:7900/websockify",
        "vnc_url": f"http://{vnc_host}:7900/vnc.html",
        "password": None,  # No password for dev
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
            browser = await p.chromium.launch(
                headless=False,
                args=[
                    '--display=:1',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--start-maximized'
                ]
            )
            
            page = await browser.new_page()
            await page.goto('https://www.google.com')
            
            logger.info("Browser opened Google - visible in VNC")
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