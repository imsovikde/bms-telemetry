import asyncio
import re
from playwright import async_api
from playwright.async_api import expect

async def run_test():
    pw = None
    browser = None
    context = None

    try:
        # Start a Playwright session in asynchronous mode
        pw = await async_api.async_playwright().start()

        # Launch a Chromium browser in headless mode with custom arguments
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--window-size=1280,720",
                "--disable-dev-shm-usage",
                "--ipc=host",
                "--single-process"
            ],
        )

        # Create a new browser context (like an incognito window)
        context = await browser.new_context()
        # Wider default timeout to match the agent's DOM-stability budget;
        # auto-waiting Playwright APIs (expect, locator.wait_for) inherit this.
        context.set_default_timeout(15000)

        # Open a new page in the browser context
        page = await context.new_page()

        # Interact with the page elements to simulate user flow
        # -> navigate
        await page.goto("http://localhost:8989/")
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        
        # --> Assertions to verify final state
        
        # --> The Active Power metric control is visible in the cockpit header.
        await page.get_by_role("button", name="Metric: Active Power (mW)").nth(0).scroll_into_view_if_needed()
        # Assert-outcome: passed
        # Assert: The 'Metric: Active Power (mW)' control is visible.
        await expect(page.get_by_role("button", name="Metric: Active Power (mW)").nth(0)).to_be_visible(timeout=15000), "The 'Metric: Active Power (mW)' control is visible."
        
        # --> The live cockpit header controls (EXPORT JSON / IMPORT JSON) are visible.
        await page.get_by_role("button", name="EXPORT JSON").nth(0).scroll_into_view_if_needed()
        # Assert-outcome: passed
        # Assert: The 'EXPORT JSON' button is visible in the cockpit header.
        await expect(page.get_by_role("button", name="EXPORT JSON").nth(0)).to_be_visible(timeout=15000), "The 'EXPORT JSON' button is visible in the cockpit header."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    