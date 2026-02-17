# Retail Catalog Scraper Pipeline

## What This Project Does

This project is a two-stage pipeline for collecting product catalog data from a configurable e-commerce source.

1. `menu_extractor.py`
- Fetches navigation/menu JSON.
- Flattens category hierarchy into structured levels.
- Exports categories to Excel.

2. `product_catalog_scraper.py`
- Reads stage-1 category output.
- Scrapes products page-by-page by category.
- Enriches availability using bounded multithreading.
- Exports a date-stamped final Excel dataset.

## Why It Was Built

It was built to provide a robust, unattended catalog data collection workflow with retries, defensive parsing, pagination handling, and crash-safe export behavior.

## Tech Stack

- Python 3
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

Required sections:
- `site`: brand label, navigation title, menu endpoint, web base URL
- `api`: endpoint templates and request parameters (store/catalog IDs, page settings, locale/currency fields)
- `io`: menu input/output file names, sheet names, output filename template, crash-save filename
- `runtime`: request retries and timeout
