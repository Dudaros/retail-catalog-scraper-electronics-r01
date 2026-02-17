"""Stage 1: fetch navigation menu JSON and export structured category levels to Excel."""

from pathlib import Path
import logging
import time

import pandas as pd
import requests
import yaml


CONFIG_PATH = Path(__file__).resolve().with_name("config.yaml")


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def load_config(config_path=CONFIG_PATH):
    with open(config_path, "r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


def fetch_json_data(url, retries=3, timeout=5):
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as e:
            logging.warning(f"Error fetching {url} (attempt {attempt}/{retries}): {e}")
            time.sleep(1)
    return None


# Function to recursively extract categories
def extract_categories(menu, level, parent_uniqueID, data):
    for category in menu:
        if category.get("level") == str(level):
            uniqueID = category.get("uniqueID")
            jcr_title = category.get("jcr:title")
            seo_url = category.get("seo_url")
            aem_url = category.get("aem_url")

            data.append(
                {
                    "Level": level,
                    "UniqueID": uniqueID,
                    "ParentUniqueID": parent_uniqueID,
                    "Title": jcr_title,
                    "SEO_URL": seo_url,
                    "AEM_URL": aem_url,
                }
            )

            # Recur for child menus
            if "childMenu" in category:
                extract_categories(category["childMenu"], level + 1, uniqueID, data)


def main():
    config = load_config()
    menu_endpoint = config["site"]["menu_endpoint"]
    nav_title = config["site"]["nav_title"]
    menu_excel_filename = config["io"]["menu_excel_filename"]
    menu_levels_to_export = int(config["io"]["menu_levels_to_export"])
    runtime_config = config.get("runtime", {})
    retries = int(runtime_config.get("request_retries", 3))
    timeout = int(runtime_config.get("request_timeout", 5))

    # Fetch JSON data
    json_data = fetch_json_data(menu_endpoint, retries=retries, timeout=timeout)
    if not isinstance(json_data, list):
        logging.error("Menu endpoint returned invalid JSON payload.")
        return

    # Start extraction from the main menu where navTitle matches config
    main_menu = None
    for item in json_data:
        if item.get("navTitle") == nav_title and isinstance(item.get("childMenu"), list):
            main_menu = item["childMenu"]
            break
    if main_menu is None:
        logging.error(f"Navigation section '{nav_title}' was not found.")
        return

    # List to hold extracted data
    data = []
    extract_categories(main_menu, 1, None, data)
    if not data:
        logging.error(f"No categories were extracted for nav title '{nav_title}'.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(data)
    if "Level" not in df.columns:
        logging.error("Extracted category data is missing required 'Level' column.")
        return

    # Create an Excel writer object
    with pd.ExcelWriter(menu_excel_filename) as writer:
        for level in range(1, menu_levels_to_export + 1):
            level_data = df[df["Level"] == level]
            level_data.to_excel(writer, sheet_name=f"Level_{level}", index=False)

        # Create sheet with Level 3 UniqueIDs and Titles
        level_3_data = df[df["Level"] == 3][["UniqueID", "Title"]]
        level_3_data.to_excel(writer, sheet_name="Level_3_UniqueIDs", index=False)


if __name__ == "__main__":
    main()
