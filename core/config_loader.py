"""
Configuration Management Utility
-------------------------------
This module provides a centralized interface for loading and querying the 
navigation metadata stored in JSON format. It handles path resolution, 
file I/O with safety fallbacks, and URL-to-page mapping.
"""

import json
import os

class ConfigLoader:
    """
    Handles the ingestion and parsing of the agent's navigation maps.
    It serves as the 'memory' that tells the agent which selectors belong 
    to which web page based on the current URL.
    """

    def __init__(self, config_filename: str = "nav_config.json"):
        """
        Initializes the loader and automatically triggers the configuration load.

        Args:
            config_filename (str): The filename within the 'configs' directory.
        """
        # Resolve pathing relative to this file's location in the project tree
        core_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(core_dir)
        self.config_path = os.path.join(project_root, "configs", config_filename)
        
        self.data = {}
        self.load_config()

    def load_config(self):
        """
        Ingests the JSON configuration file. 
        Implements a safe fallback to a default structure if the file is 
        missing or contains malformed data.
        """
        if not os.path.exists(self.config_path):
            print(f"[LOADER]: Config file not found at {self.config_path}. Initializing default state.")
            self.data = {"base_url": "https://www.saucedemo.com/", "pages": []}
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        except Exception as e:
            # Prevent system crash on JSON parse errors
            print(f"[LOADER ERROR]: Resource ingestion failed. Error: {e}")
            self.data = {"base_url": "https://www.saucedemo.com/", "pages": []}

    def get_base_url(self) -> str:
        """
        Retrieves the entry-point URL for the application under test.

        Returns:
            str: The base URL defined in the configuration.
        """
        return self.data.get("base_url", "")

    def get_page_details(self, current_url: str):
        """
        Identifies the logical page name and associated selectors by matching 
        the current URL against path identifiers in the configuration.

        Logic: 
        Sorts identifiers by length (descending) to ensure specific sub-pages 
        (e.g., 'cart.html') are matched before more generic root identifiers.

        Args:
            current_url (str): The active URL from the browser session.

        Returns:
            dict: The matching page configuration object, or None if no match is found.
        """
        pages = self.data.get("pages", [])
        
        # Priority Logic: Longest path identifiers are most specific and should be checked first
        sorted_pages = sorted(pages, key=lambda x: len(x.get("path_identifier", "")), reverse=True)
        
        for page in sorted_pages:
            identifier = page.get("path_identifier")
            # Substring matching to determine if the URL corresponds to this page definition
            if identifier and identifier in current_url:
                return page
                
        return None