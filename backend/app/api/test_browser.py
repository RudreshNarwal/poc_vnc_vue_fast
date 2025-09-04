from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.config import settings
from playwright.async_api import async_playwright
import httpx
import asyncio
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

async def _launch_chromium_on_display(session_id: str):
    """Background task: launch Chromium on the session's DISPLAY, open Google and type 'test'."""
    try:
        # 1) Resolve session info from Session Manager
        base = settings.session_manager_url.rstrip("/")
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{base}/api/sessions/{session_id}")
            resp.raise_for_status()
            session = resp.json()
        display = f":{session['display']}"

        logger.info(f"TestBrowser: Launching Chromium on DISPLAY {display} for session {session_id}")

        # 2) Launch Chromium with Playwright on the given DISPLAY
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=[
                    f"--display={display}",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--start-maximized",
                ],
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                timezone_id=settings.timezone,
                locale="en-US",
                device_scale_factor=1,
            )
            page = await context.new_page()

            # 3) Open target site (updated per request)
            await page.goto("https://rhobots.ai", timeout=60000)

            # 4) Keep it visible in VNC for a while (2 minutes)
            await asyncio.sleep(120)

            # Optional: do not close to keep visible; but closing after 120s prevents runaway processes
            await browser.close()

        logger.info(f"TestBrowser: Completed for session {session_id}")

    except Exception as e:
        logger.error(f"TestBrowser error for session {session_id}: {e}", exc_info=True)

@router.post("/session/{session_id}")
async def open_chromium_and_type(session_id: str, background_tasks: BackgroundTasks):
    """Trigger Chromium on the session's DISPLAY, navigate to Google and type 'test'."""
    try:
        # Quick check that session exists
        base = settings.session_manager_url.rstrip("/")
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{base}/api/sessions/{session_id}")
            if r.status_code == 404:
                raise HTTPException(status_code=404, detail="Session not found")
            r.raise_for_status()

        # Schedule background task to open browser
        background_tasks.add_task(_launch_chromium_on_display, session_id)
        return {"status": "scheduled", "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to schedule test browser for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
