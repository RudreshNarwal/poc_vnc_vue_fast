import logging
from playwright.sync_api import Page, expect, Playwright
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

def run_automation(
    playwright: Playwright,
    data: Dict[str, Any],
    progress_callback: Callable[[Dict[str, Any]], None]
):
    """
    Main function for the Route Addition Automation script.
    
    Args:
        playwright: The Playwright instance.
        data: A dictionary containing 'records' from the validated data file.
        progress_callback: A function to send real-time progress updates.
    """
    total_records = data.get("total_records", 0)
    records = data.get("records", [])
    processed_count = 0
    success_count = 0
    
    progress_callback({
        "status": "running",
        "message": f"Starting automation for {total_records} records.",
        "processed_count": processed_count,
        "total_records": total_records,
        "success_count": success_count
    })

    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    try:
        page.goto("https://angularformadd.netlify.app/")
        
        for i, record in enumerate(records):
            try:
                start_location = record.get("start_location")
                end_location = record.get("end_location")
                price = record.get("price")

                if not all([start_location, end_location, price is not None]):
                    raise ValueError("Record is missing required fields.")

                page.get_by_role("button", name="+ Add New Route").click()
                
                page.get_by_role("textbox", name="Enter start location").fill(str(start_location))
                page.get_by_role("textbox", name="Enter end location").fill(str(end_location))
                page.get_by_placeholder("0.00").fill(str(price))
                
                page.get_by_role("button", name="Save Route").click()
                
                # Verify the route was added
                expect(page.locator(f"//td[text()='{start_location}']")).to_be_visible()

                success_count += 1
                
                progress_callback({
                    "message": f"Successfully processed record {i+1}/{total_records}.",
                    "processed_count": i + 1,
                    "success_count": success_count
                })
                
            except Exception as e:
                logger.error(f"Failed to process record {i+1}: {e}")
                progress_callback({
                    "message": f"Error processing record {i+1}: {e}",
                    "processed_count": i + 1,
                    "error": str(e)
                })
        
        progress_callback({
            "status": "completed",
            "message": "Automation finished successfully.",
            "success_count": success_count
        })

    except Exception as e:
        logger.error(f"An unexpected error occurred during automation: {e}", exc_info=True)
        progress_callback({
            "status": "failed",
            "message": f"An unexpected error occurred: {e}",
            "error": str(e)
        })
        raise
    finally:
        # Keep the browser open for a short period for manual inspection if needed
        page.wait_for_timeout(30000) # 30 seconds
        
        context.close()
        browser.close()
