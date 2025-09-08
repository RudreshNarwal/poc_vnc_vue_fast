from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from app.config import settings
from playwright.async_api import async_playwright
import httpx
import asyncio
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

async def _launch_chromium_on_display(session_id: str, url: str | None = None):
    """Background task: launch Chromium on the session's DISPLAY and open the provided URL (or default)."""
    try:
        # 1) Resolve session info from Session Manager
        base = settings.session_manager_url.rstrip("/")
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{base}/api/sessions/{session_id}")
            resp.raise_for_status()
            session = resp.json()
        display = f":{session['display']}"
        target_url = url or "https://rhobots.ai"
        logger.info(f"TestBrowser: Starting chromium on DISPLAY {display} for session {session_id} -> {target_url}")

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
                    "--start-fullscreen",
                    "--window-size=1920,1080",
                    "--disable-web-security",
                    "--allow-running-insecure-content"
                ],
            )
            # Use a robust context to avoid HTTPS/CSP issues
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                timezone_id=settings.timezone,
                locale="en-US",
                device_scale_factor=1,
                ignore_https_errors=True,
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            )
            page = await context.new_page()

            # 3) Open target site with retries and proper waits
            nav_ok = False
            last_err = None
            for attempt in range(1, 4):
                try:
                    logger.info(f"TestBrowser: Navigating to {target_url} (attempt {attempt})")
                    await page.goto(target_url, wait_until="domcontentloaded", timeout=90000)
                    try:
                        await page.wait_for_load_state("networkidle", timeout=20000)
                    except Exception:
                        # Some sites never reach networkidle; ignore
                        pass
                    nav_ok = True
                    break
                except Exception as e:
                    last_err = e
                    await asyncio.sleep(2)

            if not nav_ok:
                logger.error(f"TestBrowser: Navigation to {target_url} failed: {last_err}")
            else:
                logger.info(f"TestBrowser: Navigation to {target_url} succeeded")
                # Try to enforce fullscreen at the window and page level
                try:
                    await page.bring_to_front()
                    # F11 toggles fullscreen in Chromium on many WMs
                    await page.keyboard.press("F11")
                except Exception as e:
                    logger.warning(f"Fullscreen F11 failed: {e}")

            # Save a screenshot for debugging
            try:
                shot_path = f"/app/screenshots/testbrowser_{session_id}.png"
                await page.screenshot(path=shot_path, full_page=False)
                logger.info(f"TestBrowser: Screenshot saved to {shot_path}")
            except Exception as e:
                logger.warning(f"TestBrowser: Failed to take screenshot: {e}")

            # 4) Keep it visible in VNC for a while (2 minutes)
            await asyncio.sleep(120)

            # Optional: auto-close after delay to prevent runaway processes
            await browser.close()

        logger.info(f"TestBrowser: Completed for session {session_id}")

    except Exception as e:
        logger.error(f"TestBrowser error for session {session_id}: {e}", exc_info=True)

@router.post("/session/{session_id}")
async def open_chromium_and_type(session_id: str, request: Request, background_tasks: BackgroundTasks):
    """Trigger Chromium on the session's DISPLAY, navigate to provided URL (or default)."""
    try:
        # Quick check that session exists
        base = settings.session_manager_url.rstrip("/")
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{base}/api/sessions/{session_id}")
            if r.status_code == 404:
                raise HTTPException(status_code=404, detail="Session not found")
            r.raise_for_status()

        # Optional URL parameter
        url = None
        try:
            body = await request.json()
            if isinstance(body, dict):
                url = body.get("url")
        except Exception:
            url = None

        # Schedule background task to open browser
        background_tasks.add_task(_launch_chromium_on_display, session_id, url)
        return {"status": "scheduled", "session_id": session_id, "url": url or "default"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to schedule test browser for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
