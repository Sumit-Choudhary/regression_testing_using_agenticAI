import json
import os

class ConfigLoader:
    def __init__(self, config_filename="nav_config.json"):
        core_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(core_dir)
        self.config_path = os.path.join(project_root, "configs", config_filename)
        self.data = {}
        self.load_config()

    def load_config(self):
        """Loads the JSON content with a safe fallback."""
        if not os.path.exists(self.config_path):
            self.data = {"base_url": "https://www.saucedemo.com/", "pages": []}
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        except Exception as e:
            print(f"❌ [LOADER ERROR]: {e}")
            self.data = {"base_url": "https://www.saucedemo.com/", "pages": []}

    def get_base_url(self):
        return self.data.get("base_url", "")

    def get_page_details(self, current_url):
        """
        FIX: Sorts identifiers by length so 'inventory.html' matches 
        before the generic site root.
        """
        pages = self.data.get("pages", [])
        # Ensure we match the most specific URL first
        sorted_pages = sorted(pages, key=lambda x: len(x.get("path_identifier", "")), reverse=True)
        
        for page in sorted_pages:
            identifier = page.get("path_identifier")
            if identifier and identifier in current_url:
                return page
        return None