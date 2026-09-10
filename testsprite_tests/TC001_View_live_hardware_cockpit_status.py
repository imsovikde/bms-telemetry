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
        
        # --> The cockpit shows the State of Charge KPI label and a pack capacity metric.
        # Assert-outcome: passed
        # Assert: The State of Charge (SoC) KPI label is visible.
        await expect(page.locator("xpath=/html/body/div/div[1]/div[5]/div[1]/div[1]/div/div[3]").nth(0)).to_have_text("SoC", timeout=15000), "The State of Charge (SoC) KPI label is visible."
        # Assert-outcome: passed
        # Assert: A pack capacity value (mWh) is present in the audit/metrics table.
        await expect(page.locator("#s5-audit-tbody").nth(0)).to_contain_text("mWh", timeout=15000), "A pack capacity value (mWh) is present in the audit/metrics table."
        
        # --> Active power metric and a cycle counter entry are displayed on the page.
        # Assert-outcome: passed
        # Assert: The Active Power metric control is visible in the header.
        await expect(page.locator("xpath=/html/body/div/header/div[2]/div[1]/button").nth(0)).to_have_text("Metric: Active Power (mW)", timeout=15000), "The Active Power metric control is visible in the header."
        # Assert-outcome: passed
        # Assert: A cycle counter value is present in the audit ledger table.
        await expect(page.locator("#s5-audit-tbody").nth(0)).to_contain_text("Cyc", timeout=15000), "A cycle counter value is present in the audit ledger table."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    