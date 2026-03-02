import json
import os

class ConfigHealer:
    def __init__(self, config_filename: str = "nav_config.json"):
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_path = os.path.join(base_path, "configs", config_filename)

    async def scan_and_update(self, page, page_key: str):
        print(f"\n🕵️‍♂️ [HEALER]: Deep scanning for page '{page_key}'...")
        
        # 1. Capture elements with IDs AND specific checkout-related attributes
        # SauceDemo's finish button specifically uses id="finish"
        elements = await page.query_selector_all("button, input, a, .btn_action, select")
        new_entries = {}

        for el in elements:
            # Check for ID first
            element_id = await el.get_attribute("id")
            # If no ID, check for data-test attribute (common in QA sites)
            if not element_id:
                element_id = await el.get_attribute("data-test")

            # 2. FALLBACK: If no 'id', look for 'data-test' (Very common in SauceDemo)
            if not element_id:
                element_id = await el.get_attribute("data-test")

            # 3. FALLBACK: If still no ID, you could use a name or placeholder (Optional)
            if not element_id:
                element_id = await el.get_attribute("name")
            
            if not element_id: continue
            
            is_visible = await el.is_visible()
            if not is_visible: continue

            clean_key = element_id.replace("-", "_").lower()
           # Determine the correct CSS selector based on which attribute we found
            actual_id = await el.get_attribute("id")
            actual_data_test = await el.get_attribute("data-test")
            actual_name = await el.get_attribute("name")

            #building locator file as per gemini expectations
            if actual_id:
                locator = f"#{actual_id}"
            elif actual_data_test:
                locator = f"[data-test='{actual_data_test}']"
            elif actual_name:
                locator = f"[name='{actual_name}']"
            else:
                continue # Safety skip

            new_entries[clean_key] = {
                "locator": locator, 
                "uses": f"Action for {element_id}"
            }

        # Load current state
        try:
            with open(self.config_path, "r", encoding='utf-8') as f:
                config_data = json.load(f)
        except:
            config_data = {"base_url": "https://www.saucedemo.com/", "pages": []}

        # FIX: Find page in LIST instead of dict access
        target_page = next((p for p in config_data["pages"] if p.get("page_name") == page_key), None)
        
        if not target_page:
            path_id = page.url.split("/")[-1] or "root"
            target_page = {"page_name": page_key, "path_identifier": path_id, "selectors": {}}
            config_data["pages"].append(target_page)

        # Merge new selectors
        target_page["selectors"].update(new_entries)

        with open(self.config_path, "w", encoding='utf-8') as f:
            json.dump(config_data, f, indent=2)
        print(f"✅ [HEALER]: Successfully updated {page_key}.")