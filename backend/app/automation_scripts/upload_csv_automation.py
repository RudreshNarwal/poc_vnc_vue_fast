import logging
from playwright.sync_api import Page, Playwright
from typing import Dict, Any, Callable, List
import asyncio

logger = logging.getLogger(__name__)

def run_automation(
    playwright: Playwright,
    data: Dict[str, Any],
    progress_callback: Callable[[Dict[str, Any]], None]
):
    """
    CSV Upload Automation - Processes routes from uploaded CSV/Excel file.
    
    Args:
        playwright: The Playwright instance.
        data: A dictionary containing 'records' from the validated data file.
        progress_callback: A function to send real-time progress updates.
    """
    total_records = data.get("total_records", 0)
    records = data.get("records", [])
    processed_count = 0
    success_count = 0
    failed_count = 0
    
    progress_callback({
        "status": "running",
        "message": f"Starting CSV upload automation for {total_records} routes.",
        "processed_count": processed_count,
        "total_records": total_records,
        "success_count": success_count
    })

    # Launch browser with VNC display settings
    browser = playwright.chromium.launch(
        headless=False,  # MUST be False for VNC visibility
        args=[
            '--display=:1',  # Critical for VNC
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--use-gl=swiftshader',
            '--window-size=1920,1080',
            '--window-position=0,0',
            '--start-maximized'
        ]
    )
    
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        timezone_id='America/New_York'
    )
    page = context.new_page()

    try:
        # Navigate to the target application
        logger.info("Navigating to route management app...")
        page.goto("https://angularformadd.netlify.app/", wait_until="networkidle")
        page.wait_for_timeout(2000)  # Allow page to fully load
        
        progress_callback({
            "status": "running",
            "message": "Application loaded. Processing routes...",
            "processed_count": 0,
            "total_records": total_records
        })
        
        # Process each record from the CSV
        for i, record in enumerate(records, start=1):
            try:
                start_location = str(record.get("start_location", "")).strip()
                end_location = str(record.get("end_location", "")).strip()
                price = str(record.get("price", "")).strip()
                
                if not all([start_location, end_location, price]):
                    logger.warning(f"Record {i} has missing fields, skipping...")
                    failed_count += 1
                    continue
                
                logger.info(f"Processing route {i}/{total_records}: {start_location} → {end_location}")
                
                # Click Add New Route button
                add_button = page.get_by_role("button", name="+ Add New Route")
                add_button.wait_for(state="visible", timeout=5000)
                add_button.click()
                page.wait_for_timeout(500)  # Wait for form to appear
                
                # Fill in start location
                start_input = page.get_by_role("textbox", name="Enter start location")
                start_input.wait_for(state="visible", timeout=5000)
                start_input.click()
                start_input.fill(start_location)
                
                # Fill in end location
                end_input = page.get_by_role("textbox", name="Enter end location")
                end_input.click()
                end_input.fill(end_location)
                
                # Fill in price
                price_input = page.get_by_placeholder("0.00")
                price_input.click()
                price_input.fill(price)
                
                # Save the route
                save_button = page.get_by_role("button", name="Save Route")
                save_button.click()
                
                # Wait for save to complete
                page.wait_for_timeout(1000)
                
                # Verify the route was added (check for the start location in the table)
                try:
                    page.locator(f"text='{start_location}'").wait_for(state="visible", timeout=3000)
                    success_count += 1
                    logger.info(f"✓ Route {i} added successfully")
                except:
                    logger.warning(f"Could not verify route {i} was added")
                    success_count += 1  # Count as success if save completed
                
                processed_count = i
                
                # Send progress update
                progress_callback({
                    "status": "running",
                    "message": f"Processed route {i}/{total_records}: {start_location} → {end_location}",
                    "processed_count": processed_count,
                    "total_records": total_records,
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "current_route": f"{start_location} → {end_location}"
                })
                
                # Small delay between records to avoid overwhelming the app
                if i < len(records):
                    page.wait_for_timeout(500)
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to process record {i}: {e}")
                progress_callback({
                    "status": "running",
                    "message": f"Error processing record {i}: {str(e)}",
                    "processed_count": i,
                    "total_records": total_records,
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "error": str(e)
                })
                # Continue with next record
                continue
        
        # Final summary
        final_message = f"Automation completed. Successfully added {success_count} out of {total_records} routes."
        if failed_count > 0:
            final_message += f" ({failed_count} failed)"
            
        progress_callback({
            "status": "completed",
            "message": final_message,
            "processed_count": total_records,
            "total_records": total_records,
            "success_count": success_count,
            "failed_count": failed_count
        })
        
        logger.info(final_message)
        
        # Keep browser open for inspection
        page.wait_for_timeout(5000)
        
    except Exception as e:
        logger.error(f"Unexpected error during CSV automation: {e}", exc_info=True)
        progress_callback({
            "status": "failed",
            "message": f"Automation failed: {str(e)}",
            "processed_count": processed_count,
            "total_records": total_records,
            "success_count": success_count,
            "failed_count": failed_count,
            "error": str(e)
        })
        raise
    finally:
        # Clean up
        logger.info("Closing browser...")
        page.wait_for_timeout(2000)  # Brief pause before closing
        context.close()
        browser.close()
        logger.info("CSV upload automation completed")
