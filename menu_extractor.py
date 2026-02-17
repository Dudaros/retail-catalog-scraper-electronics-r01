"""Stage 1: fetch navigation menu JSON and export structured category levels to Excel."""

from pathlib import Path

import pandas as pd
import requests
import yaml


CONFIG_PATH = Path(__file__).resolve().with_name("config.yaml")


def load_config(config_path=CONFIG_PATH):
    with open(config_path, "r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


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

    # Fetch JSON data
    response = requests.get(menu_endpoint)
    json_data = response.json()

    # Start extraction from the main menu where navTitle matches config
    main_menu = None
    for item in json_data:
        if item.get("navTitle") == nav_title:
            main_menu = item["childMenu"]
            break

    # List to hold extracted data
    data = []
    extract_categories(main_menu, 1, None, data)

    # Convert to DataFrame
    df = pd.DataFrame(data)

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
