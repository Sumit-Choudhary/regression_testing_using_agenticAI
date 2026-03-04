"""
Dynamic Configuration Healer
----------------------------
This module provides self-healing capabilities for the agent's navigation 
configuration. It performs real-time DOM introspection to discover and 
persist UI selectors that may be missing or altered in the primary config file.
"""

import json
import os

class ConfigHealer:
    """
    Scans the live browser DOM to extract interactive element metadata 
    and updates the navigation configuration JSON dynamically.
    """

    def __init__(self, config_filename: str = "nav_config.json"):
        """
        Initializes the Healer with a path to the configuration repository.

        Args:
            config_filename (str): The name of the JSON configuration file.
        """
        # Resolve absolute path to the configs directory
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_path = os.path.join(base_path, "configs", config_filename)

    async def scan_and_update(self, page, page_key: str):
        """
        Performs an exhaustive scan of the current page for interactive elements 
        and merges new findings into the local configuration file.

        Args:
            page (playwright.async_api.Page): The active Playwright page instance.
            page_key (str): The logical identifier for the current page state.
        """
        print(f"[HEALER]: Initializing deep-scan for state: '{page_key}'...")
        
        # 1. Selector Extraction: Target standard interactive tags and specific action classes
        elements = await page.query_selector_all("button, input, a, .btn_action, select")
        new_entries = {}

        for el in elements:
            # Multi-layer identification logic: ID > data-test > name
            element_id = await el.get_attribute("id")
            
            # Fallback 1: Check for 'data-test' attributes (standard in SauceDemo and modern QA)
            if not element_id:
                element_id = await el.get_attribute("data-test")

            # Fallback 2: Redundant check for data-test (maintained as per original logic)
            if not element_id:
                element_id = await el.get_attribute("data-test")

            # Fallback 3: Check for the 'name' attribute
            if not element_id:
                element_id = await el.get_attribute("name")
            
            # Skip elements that provide no viable unique identification
            if not element_id: 
                continue
            
            # Visibility filtering: Only document elements the agent can actually see
            is_visible = await el.is_visible()
            if not is_visible: 
                continue

            # Standardize the key for the JSON dictionary (e.g., "login-button" -> "login_button")
            clean_key = element_id.replace("-", "_").lower()
            
            # Retrieve raw attributes for CSS locator construction
            actual_id = await el.get_attribute("id")
            actual_data_test = await el.get_attribute("data-test")
            actual_name = await el.get_attribute("name")

            # 2. Locator Construction: Priority-based CSS selector generation
            if actual_id:
                locator = f"#{actual_id}"
            elif actual_data_test:
                locator = f"[data-test='{actual_data_test}']"
            elif actual_name:
                locator = f"[name='{actual_name}']"
            else:
                continue # Safety break if no valid selector strategy found

            new_entries[clean_key] = {
                "locator": locator, 
                "uses": f"Action for {element_id}"
            }

        # 3. Configuration Persistence: Load, Merge, and Save
        try:
            # Attempt to read existing configuration
            with open(self.config_path, "r", encoding='utf-8') as f:
                config_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Default structure if file is missing or corrupted
            config_data = {"base_url": "https://www.saucedemo.com/", "pages": []}

        # Find existing page entry or create a new one in the 'pages' list
        target_page = next((p for p in config_data["pages"] if p.get("page_name") == page_key), None)
        
        if not target_page:
            # Derive path_identifier from the URL slug if creating a new entry
            path_id = page.url.split("/")[-1] or "root"
            target_page = {"page_name": page_key, "path_identifier": path_id, "selectors": {}}
            config_data["pages"].append(target_page)

        # Merge newly discovered selectors into the target page schema
        target_page["selectors"].update(new_entries)

        # Write synchronized configuration back to disk
        with open(self.config_path, "w", encoding='utf-8') as f:
            json.dump(config_data, f, indent=2)
            
        print(f"[HEALER SUCCESS]: Configuration synchronized for '{page_key}'.")