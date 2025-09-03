import logging
import asyncio
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

async def run_automation_async(
    page,  # Use existing page from AutomationEngine
    progress_callback: Callable[[Dict[str, Any]], None]
):
    """
    Async function for the Route Addition Automation script.
    
    Args:
        page: The Playwright page instance from AutomationEngine.
        progress_callback: A function to send real-time progress updates.
    """
    # Define 7 hardcoded route records (same as run_demo_flow)
    records = [
        {"start_location": "New York", "end_location": "Boston", "price": "45.99"},
        {"start_location": "Los Angeles", "end_location": "San Francisco", "price": "89.50"},
        {"start_location": "Chicago", "end_location": "Detroit", "price": "67.25"},
        {"start_location": "Miami", "end_location": "Orlando", "price": "34.75"},
        {"start_location": "Seattle", "end_location": "Portland", "price": "52.00"},
        {"start_location": "Houston", "end_location": "Dallas", "price": "41.30"},
    ]
    
    total_records = len(records)
    processed_count = 0
    success_count = 0
    
    await progress_callback({
        "status": "running",
        "message": f"Starting automation for {total_records} hardcoded records.",
        "processed_count": processed_count,
        "total_records": total_records,
        "success_count": success_count
    })

    try:
        # Navigate to the sample app (using existing page)
        await page.goto("https://angularformadd.netlify.app/")
        
        # Insert all 7 routes
        for i, record in enumerate(records, 1):
            try:
                start_location = record.get("start_location")
                end_location = record.get("end_location")
                price = record.get("price")

                if not all([start_location, end_location, price is not None]):
                    raise ValueError("Record is missing required fields.")

                await progress_callback({
                    "message": f"Adding route {i}/7: {start_location} → {end_location}",
                    "processed_count": i,
                    "success_count": success_count
                })

                # Click the "Add New Route" button
                await page.get_by_role("button", name="+ Add New Route").click()
                
                # Fill in the start location
                await page.get_by_role("textbox", name="Enter start location").fill(str(start_location))
                
                # Fill in the end location  
                await page.get_by_role("textbox", name="Enter end location").fill(str(end_location))
                
                # Fill in the price
                await page.get_by_placeholder("0.00").fill(str(price))
                
                # Save the route
                await page.get_by_role("button", name="Save Route").click()
                
                # Small delay to see the action and allow UI to update
                await asyncio.sleep(1)

                success_count += 1
                
                await progress_callback({
                    "message": f"Successfully processed record {i}/{total_records}.",
                    "processed_count": i,
                    "success_count": success_count
                })
                
            except Exception as e:
                logger.error(f"Failed to process record {i}: {e}")
                await progress_callback({
                    "message": f"Error processing record {i}: {e}",
                    "processed_count": i,
                    "error": str(e)
                })
        
        # Final status update
        await progress_callback({
            "status": "completed",
            "message": f"Successfully added all {success_count} routes!",
            "success_count": success_count
        })
        
        # Click the FAB button (⚡) to show the results
        await page.get_by_role("button", name="⚡").click()
        
        # Take a screenshot to capture the final state
        import time
        timestamp = int(time.time())
        screenshot_path = f"/screenshots/route_automation_result_{timestamp}.png"
        await page.screenshot(path=screenshot_path)
        logger.info(f"Screenshot saved: {screenshot_path}")
        await progress_callback({
            "message": f"Screenshot captured: {screenshot_path}",
            "screenshot": screenshot_path
        })
        
        # Wait to ensure all UI updates are visible
        await asyncio.sleep(3)

    except Exception as e:
        logger.error(f"An unexpected error occurred during automation: {e}", exc_info=True)
        await progress_callback({
            "status": "failed",
            "message": f"An unexpected error occurred: {e}",
            "error": str(e)
        })
        raise


