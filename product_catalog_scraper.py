"""Stage 2: read category Excel, scrape paginated products, enrich availability in parallel, and export results."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import concurrent.futures
import logging
import time

import pandas as pd
import requests
import yaml


CONFIG_PATH = Path(__file__).resolve().with_name("config.yaml")


def load_config(config_path=CONFIG_PATH):
    with open(config_path, "r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


CONFIG = load_config()
SITE_CONFIG = CONFIG["site"]
API_CONFIG = CONFIG["api"]
IO_CONFIG = CONFIG["io"]
RUNTIME_CONFIG = CONFIG["runtime"]

# Initialize logging to log information and errors.
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def fetch_json_data(url, retries=None, timeout=None):
    """
    Fetch JSON data from a given URL.

    Parameters:
        url (str): The URL to fetch data from.
        retries (int): Number of retry attempts.
        timeout (int): Timeout in seconds for the request.

    Returns:
        dict: The JSON data fetched from the URL. Returns None if fetching fails.
    """
    retries = RUNTIME_CONFIG["request_retries"] if retries is None else retries
    timeout = RUNTIME_CONFIG["request_timeout"] if timeout is None else timeout

    for _ in range(retries):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as e:
            logging.warning(f"Error fetching {url}: {e}")
            time.sleep(1)
    return None


def fetch_additional_info(aem_url_parts):
    """
    Fetch additional information for a product based on its AEM URL parts.

    Parameters:
        aem_url_parts (list): List of AEM URL parts.

    Returns:
        dict: Additional information about the product.
    """
    aem_path = "/".join(aem_url_parts)
    url = API_CONFIG["product_model_template"].format(aem_path=aem_path)
    data = fetch_json_data(url)
    if data is not None:
        return data
    else:
        # Handle the case where no data is returned
        logging.warning(f"No data returned for URL: {url}")
        return {}


def fetch_single_availability(sku_id):
    """
    Fetch availability status for a single SKU ID.

    Parameters:
        sku_id (str): The SKU ID to check.

    Returns:
        str: The availability status. Returns "N/A" if status can't be fetched.
    """
    url = API_CONFIG["availability_template"].format(
        sku_id=sku_id,
        store_id=API_CONFIG["store_id"],
    )
    data = fetch_json_data(url)
    status = data.get("availableStatusKey", "N/A") if data else "N/A"
    logging.info(f"Fetched availability for SKU ID {sku_id}: {status}")
    return status


def fetch_availability_statuses(single_sku_ids):
    """
    Fetch availability statuses for a batch of SKU IDs using multithreading.

    Parameters:
        single_sku_ids (list): List of SKU IDs to check.

    Returns:
        dict: A dictionary mapping SKU IDs to their availability statuses.
    """
    unique_sku_ids = []
    seen_sku_ids = set()
    for sku_id in single_sku_ids:
        if sku_id is None or (isinstance(sku_id, float) and pd.isna(sku_id)):
            continue
        if sku_id in seen_sku_ids:
            continue
        seen_sku_ids.add(sku_id)
        unique_sku_ids.append(sku_id)

    if not unique_sku_ids:
        return {}

    statuses = {}
    max_workers = 12
    batch_size = 200
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for batch_start in range(0, len(unique_sku_ids), batch_size):
            batch_sku_ids = unique_sku_ids[batch_start:batch_start + batch_size]
            future_to_sku = {executor.submit(fetch_single_availability, sku_id): sku_id for sku_id in batch_sku_ids}
            for future in concurrent.futures.as_completed(future_to_sku):
                sku = future_to_sku[future]
                try:
                    statuses[sku] = future.result()
                except Exception as e:
                    logging.warning(f"Availability fetch failed for SKU ID {sku}: {e}")
                    statuses[sku] = "N/A"
                completed += 1
                if completed % 10 == 0:
                    logging.info(f"Completed fetching availability for {completed}/{len(unique_sku_ids)} SKU IDs.")
    return statuses


def save_to_excel(data, filename):
    """
    Save data to an Excel file.

    Parameters:
        data (list): List of dictionaries containing the data.
        filename (str): The name of the Excel file to save data to.
    """
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)
    logging.info(f"Data saved to {filename}")


def main(limit=None):
    all_data = []
    try:
        # Read Excel file into a DataFrame
        df = pd.read_excel(IO_CONFIG["menu_excel_filename"], sheet_name=IO_CONFIG["menu_sheet_name"])
        total_rows = len(df)

        single_sku_ids = []
        product_count = 0

        for index, row in enumerate(df.itertuples()):
            if limit is not None and product_count >= limit:
                break

            aem_url = getattr(row, "AEM_URL", None)
            if not isinstance(aem_url, str) or not aem_url.strip():
                logging.warning(f"Skipping row {index + 1}/{total_rows}: missing AEM_URL")
                continue
            aem_url_parts = [part for part in aem_url.split("/") if part][-3:]
            if not aem_url_parts:
                logging.warning(f"Skipping row {index + 1}/{total_rows}: invalid AEM_URL '{aem_url}'")
                continue

            additional_info = fetch_additional_info(aem_url_parts)

            logging.info(f"Collecting product info {index + 1}/{total_rows}")

            category_info = {
                "Category_ID_number": additional_info.get("categoryId", "N/A"),
                "Category_Title": additional_info.get("title", "N/A"),
                "Category_URL": additional_info.get("remoteSPAUrl", "N/A"),
            }

            page_number = 1
            consecutive_page_failures = 0
            max_consecutive_page_failures = 3
            while True:
                if limit is not None and product_count >= limit:
                    break

                specific_url = API_CONFIG["category_search_template"].format(
                    store_id=API_CONFIG["store_id"],
                    category_slug=aem_url_parts[-1],
                    page_number=page_number,
                    page_size=API_CONFIG["page_size"],
                    catalog_id=API_CONFIG["catalog_id"],
                    currency=API_CONFIG["currency"],
                    lang_id=API_CONFIG["lang_id"],
                    order_by=API_CONFIG["order_by"],
                )
                data = fetch_json_data(specific_url)
                if data is None:
                    consecutive_page_failures += 1
                    logging.warning(
                        f"Failed to fetch category page {page_number} for '{aem_url_parts[-1]}' "
                        f"({consecutive_page_failures}/{max_consecutive_page_failures})"
                    )
                    if consecutive_page_failures >= max_consecutive_page_failures:
                        logging.error(
                            f"Stopping category '{aem_url_parts[-1]}' after repeated page fetch failures."
                        )
                        break
                    page_number += 1
                    continue

                consecutive_page_failures = 0
                if not data.get("catalogEntryView", []):
                    break

                for product in data["catalogEntryView"]:
                    product_info = category_info.copy()
                    keys_to_extract = [
                        "uniqueID",
                        "singleSKUCatalogEntryID",
                        "partNumber",
                        "shortDescription",
                        "name",
                        "manufacturer",
                        "buyable",
                    ]
                    for key in keys_to_extract:
                        product_info[key] = product.get(key, "N/A")

                    # Splitting the Category_URL and extracting the levels
                    category_levels = product_info["Category_URL"].strip("/").split("/")
                    level_keys = ["Level 1", "Level 2", "Level 3"]
                    for i, level_key in enumerate(level_keys):
                        product_info[level_key] = category_levels[i] if i < len(category_levels) else None

                    user_data = product.get("UserData")
                    user_data_first = user_data[0] if isinstance(user_data, list) and user_data else {}
                    if not isinstance(user_data_first, dict):
                        user_data_first = {}

                    seo_url = user_data_first.get("seo_url", "N/A")
                    if isinstance(seo_url, str):
                        product_info["Link"] = f"{SITE_CONFIG['web_base_url'].rstrip('/')}/{seo_url.lstrip('/')}"
                    else:
                        product_info["Link"] = "N/A"

                    # Extracting price information
                    prices = product.get("price", [])
                    original_price, current_price = "N/A", "N/A"  # Default values
                    for price in prices:
                        if price.get("usage") == "Display":
                            original_price = price.get("value", "N/A")  # Interpreted as the old price
                        elif price.get("usage") == "Offer":
                            current_price = price.get("value", "N/A")  # Interpreted as the new price

                    product_info["Original_Price"] = original_price
                    product_info["Current_Price"] = current_price

                    sku_id = product.get("singleSKUCatalogEntryID", None)
                    if sku_id is not None:
                        single_sku_ids.append(sku_id)

                    all_data.append(product_info)
                    product_count += 1

                page_number += 1

        logging.info("Gathering availability statuses...")
        availability_statuses = fetch_availability_statuses(single_sku_ids)

        availability_translation = {
            "EXHAUSTED": "Εξαντλημένο",
            "EXPECTED_SOON": "Αναμένεται Σύντομα",
            "IMMEDIATELY_AVAILABLE": "Άμεσα διαθέσιμο",
            "LAST_PIECES": "Τελευταία τεμάχια",
            "N/A": "N/A",
            "NOT_AVAILABLE": "Μη διαθέσιμο",
            "ON_ORDER": "Σε παραγγελία",
            "Preorderable": "Διαθέσιμο για προπαραγγελία",
            "SPECIAL_ORDER": "Ειδική Παραγγελία",
            "": "",  # for any blank values
        }

        for product in all_data:
            sku_id = product.get("singleSKUCatalogEntryID", None)
            if sku_id and sku_id in availability_statuses:
                english_status = availability_statuses[sku_id]
                greek_status = availability_translation.get(english_status, english_status)
                product["Availability Status"] = greek_status
            else:
                product["Availability Status"] = "N/A"

        output_template = IO_CONFIG["output_filename_template"].format(brand_name=SITE_CONFIG["brand_name"])
        file_name = datetime.now().strftime(output_template)
        save_to_excel(all_data, file_name)

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        if all_data:
            save_to_excel(all_data, IO_CONFIG["crash_save_filename"])


if __name__ == "__main__":
    main(limit=None)
