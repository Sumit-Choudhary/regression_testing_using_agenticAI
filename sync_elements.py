import asyncio
import os
from playwright.async_api import async_playwright
from core.config_healer import ConfigHealer

class PageSynchronizer:
    def __init__(self):
        # 1. Robust Path Handling:
        # Get the absolute path of the current script's directory (root)
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        
        # Point specifically to the configs folder inside the project root
        config_path = os.path.join(self.project_root, "configs", "nav_config.json")
        
        print(f"📂 [INIT]: Target Config: {config_path}")
        self.healer = ConfigHealer("nav_config.json")

    async def login(self, page):
        """Standard login to bypass the entry wall."""
        print("🔐 [LOGIN]: Authenticating at SauceDemo...")
        await page.goto("https://www.saucedemo.com/")
        await page.fill("#user-name", "standard_user")
        await page.fill("#password", "secret_sauce")
        await page.click("#login-button")
        await page.wait_for_load_state("networkidle")

    async def sync_page(self, url: str, page_name: str, needs_login: bool = True):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()

            if needs_login:
                await self.login(page)

            print(f"🚀 [SYNC]: Navigating to {page_name} -> {url}")
            
            # We do the waiting HERE, inside the function where 'page' exists
            await page.goto(url)
            await page.wait_for_load_state("networkidle")
            
            # Add a 2-second buffer for SauceDemo animations
            await asyncio.sleep(2) 

            print(f"🔍 [SYNC]: Scanning elements...")
            await self.healer.scan_and_update(page, page_name)
            
            await browser.close()

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    sync = PageSynchronizer()
    
    # List of internal pages to "teach" the agent
    pages = [
        {"name": "inventory_page", "url": "https://www.saucedemo.com/inventory.html"},
        {"name": "cart_page", "url": "https://www.saucedemo.com/cart.html"},
        {"name": "checkout_step_one_page", "url": "https://www.saucedemo.com/checkout-step-one.html"},
        {"name": "checkout_step_two_page", "url": "https://www.saucedemo.com/checkout-step-two.html"}
    ]

    async def run_sync():
        for p in pages:
            await sync.sync_page(p["url"], p["name"])
            print(f"--- Finished {p['name']} ---")
            print("-" * 40)

    asyncio.run(run_sync())