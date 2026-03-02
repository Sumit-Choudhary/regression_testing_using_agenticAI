import asyncio
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

class BrowserManager:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None

    async def start(self):
        """Initializes the browser session."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        # 2026 Best Practice: Use a viewport size that fits LLM vision models well
        self.context = await self.browser.new_context(viewport={'width': 1280, 'height': 720})
        self.page = await self.context.new_page()
        return self.page

    async def get_screenshot(self) -> str:
        """Captures a screenshot as a base64 string for the AI Agent's 'Vision'."""
        if self.page:
            # We use base64 to send the image directly to the LLM API
            return await self.page.screenshot(type="png", full_page=False, scale="css")
        return ""

    async def navigate_to(self, url: str):
        """Standard navigation with auto-waiting."""
        if self.page:
            await self.page.goto(url, wait_until="networkidle")

    async def close(self):
        """Gracefully shuts down the browser and playwright."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

# Example usage for testing Day 2 setup:
# manager = BrowserManager(headless=False)
# page = await manager.start()
# await manager.navigate_to("https://www.saucedemo.com")