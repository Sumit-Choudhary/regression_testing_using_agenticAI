"""
Browser Lifecycle Controller
----------------------------
This module manages the Playwright browser instance, providing a clean 
interface for session initialization, navigation, and visual state capture.
It ensures that browser resources are handled safely within the async ecosystem.
"""

import asyncio
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

class BrowserManager:
    """
    Handles the automation of the Chromium browser. It encapsulates the 
    complexity of Playwright context management and provides vision-ready 
    outputs for the AI Agent.
    """

    def __init__(self, headless: bool = False):
        """
        Initializes the manager configuration.

        Args:
            headless (bool): If True, runs the browser without a GUI. 
                             Defaults to False for easier debugging.
        """
        self.headless = headless
        self.playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None

    async def start(self) -> Page:
        """
        Initializes the Playwright driver and launches a fresh browser session.
        
        Configures a standardized viewport optimized for multimodal LLM 
        vision processing (Gemini-friendly aspect ratio).

        Returns:
            Page: The initialized Playwright page object.
        """
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        
        # 2026 Best Practice: Viewport synchronization with LLM token limits
        # 1280x720 ensures clear text legibility while keeping screenshot size efficient.
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 720}
        )
        self.page = await self.context.new_page()
        return self.page

    async def get_screenshot(self) -> bytes:
        """
        Captures a screenshot of the current viewport. 
        Used specifically to feed the 'Vision' node of the AI Agent.

        Returns:
            bytes: Raw image data, ready for Base64 encoding.
        """
        if self.page:
            # Capturing at CSS scale ensures the visual representation 
            # matches the DOM coordinates for the Agent.
            return await self.page.screenshot(type="png", full_page=False, scale="css")
        return b""

    async def navigate_to(self, url: str):
        """
        Directs the browser to a target URL and waits for the page 
        to reach a stable state.

        Args:
            url (str): The destination web address.
        """
        if self.page:
            # 'networkidle' ensures the Agent doesn't analyze a half-loaded page.
            await self.page.goto(url, wait_until="networkidle")

    async def close(self):
        """
        Performs a graceful shutdown of all browser-related processes.
        Essential for preventing memory leaks and orphaned driver processes.
        """
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()