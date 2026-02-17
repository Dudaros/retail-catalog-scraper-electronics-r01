# Retail Catalog Scraper Pipeline

## What This Project Does

This project is a two-stage Python pipeline for collecting product catalog data from an e-commerce source.

1. `menu_extractor.py`
- Fetches the navigation/menu JSON.
- Flattens nested categories into structured levels.
- Exports category data to an Excel file.

2. `product_catalog_scraper.py`
- Reads the category Excel file from stage 1.
- Scrapes products page-by-page for each category.
- Enriches products with availability status using multithreading.
- Exports a date-stamped Excel dataset.

## Why It Was Built

The goal is to provide a reusable, configuration-driven scraping workflow for catalog analysis and data collection. The code emphasizes unattended execution by using retries, defensive parsing, bounded concurrency, logging, and emergency save-on-failure behavior.

## Tech Stack

- Python 3.10+
- requests
- pandas
- openpyxl
- PyYAML
- pytest

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
```

## How To Run

```bash
python menu_extractor.py
python product_catalog_scraper.py
```

## Configuration (`config.yaml`)

The pipeline reads all source-specific settings from `config.yaml`.

### `site`
- `brand_name`: Label used in output filename template.
- `nav_title`: Navigation section title to extract.
- `menu_endpoint`: URL for menu/navigation JSON.
- `web_base_url`: Base web URL used to build product links.

### `api`
- `product_model_template`: URL template for category metadata (`{aem_path}`).
- `availability_template`: URL template for SKU availability (`{sku_id}`, `{store_id}`).
- `category_search_template`: URL template for paginated category products (`{store_id}`, `{category_slug}`, `{page_number}`, `{page_size}`, `{catalog_id}`, `{currency}`, `{lang_id}`, `{order_by}`).
- `store_id`: Store identifier for API requests.
- `catalog_id`: Catalog identifier.
- `currency`: Currency code.
- `lang_id`: Language identifier.
- `order_by`: Sort mode for category API.
- `page_size`: Number of products per page.

### `io`
- `menu_excel_filename`: Output file from stage 1 and input file for stage 2.
- `menu_sheet_name`: Sheet name stage 2 reads (typically `Level_3`).
- `menu_levels_to_export`: Number of category levels to export.
- `output_filename_template`: Final output naming pattern (supports `%Y%m%d` and `{brand_name}`).
- `crash_save_filename`: Emergency output file used on unexpected failure.

### `runtime`
- `request_retries`: Number of retries per API request.
- `request_timeout`: Request timeout in seconds.
