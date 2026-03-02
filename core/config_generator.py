import os
import json
from playwright.async_api import async_playwright
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()

class ConfigGenerator:
    def __init__(self):

        # Use the same environment variable for consistency
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

        # Initializing via LangChain's Google GenAI wrapper
        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0,
            convert_system_message_to_human=True
        )

    async def get_interactive_elements(self, page):
        """Extracts visible, interactive elements from the DOM."""
        selector = "button, input, a, select, [role='button']"
        elements = await page.query_selector_all(selector)
        
        extracted_data = []
        for el in elements:
            data = await el.evaluate("""(node) => {
                return {
                    tag: node.tagName,
                    id: node.id,
                    type: node.getAttribute('type') || '',
                    text: node.innerText.trim() || node.getAttribute('placeholder') || node.getAttribute('aria-label') || '',
                    isVisible: node.offsetWidth > 0 && node.offsetHeight > 0
                }
            }""")
            if data['id'] and data['isVisible']:
                extracted_data.append(data)
        return extracted_data

    async def generate_enriched_config(self, url, page_name, instructions):
        """
        Uses LangChain + Playwright to scan and classify elements.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            print(f"🌐 [SCANNING]: Navigating to {url}...")
            await page.goto(url)
            await page.wait_for_load_state("networkidle")
            
            elements = await self.get_interactive_elements(page)
            
            # Prepare the content for LangChain
            prompt_text = (
                f"{instructions}\n\n"
                f"PAGE NAME: {page_name}\n"
                f"DOM ELEMENTS: {json.dumps(elements)}"
            )

            print(f"🧠 [REASONING]: LangChain/Gemini is classifying {len(elements)} elements...")
            
            # Use LangChain's invoke method
            response = await self.llm.ainvoke([HumanMessage(content=prompt_text)])
            
            # Standardizing output by stripping markdown code blocks
            clean_text = response.content.replace("```json", "").replace("```", "").strip()
            
            try:
                enriched_data = json.loads(clean_text)
                await browser.close()
                return enriched_data
            except Exception as e:
                print(f"❌ [ERROR]: Failed to parse JSON from LLM: {e}")
                await browser.close()
                return None