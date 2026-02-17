# Retail Catalog Scraper Pipeline

Config-driven, two-stage scraping pipeline for e-commerce catalog data.

This portfolio project is intentionally retailer-neutral:
- No hardcoded store names
- No hardcoded store IDs or endpoint domains
- All environment-specific values come from `config.yaml`

## What It Does

1. `menu_extractor.py` (Stage 1)
- Downloads navigation/menu JSON from a configured endpoint.
- Recursively flattens category hierarchy (levels + parent relationships).
- Exports categories to Excel with level-based sheets.

2. `product_catalog_scraper.py` (Stage 2)
- Reads the category Excel file from Stage 1.
- Scrapes products page-by-page for each category.
- Fetches availability in parallel using multithreading.
- Preserves retries, logging, pagination, and crash-safe emergency export.
- Exports a date-stamped final Excel dataset.

## Tech Stack

- Python 3.10+
- `requests`
- `pandas`
- `openpyxl`
- `PyYAML`

## Project Structure

```text
.
├── menu_extractor.py
├── product_catalog_scraper.py
├── config.example.yaml
├── config.yaml              # local only (ignored by git)
├── requirements.txt
└── README.md
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
```

Then edit `config.yaml` with your own endpoints, IDs, and output preferences.

## Run

```bash
python menu_extractor.py
python product_catalog_scraper.py
```

## Configuration Notes

- `site.*`: brand label, web base URL, menu source endpoint.
- `api.*`: URL templates + IDs/params for model, search, availability endpoints.
- `io.*`: input/output Excel names and output filename pattern.
- `runtime.*`: retries and request timeout.

## Portfolio Notes

This repo demonstrates:
- Multi-stage data pipeline design
- Externalized configuration for portability/security
- Reliable scraping patterns (retry + timeout + pagination)
- Concurrent enrichment for performance
- Defensive data persistence on failure

## Ethical / Legal Use

Use this code only for websites and APIs you are authorized to access, and always comply with applicable terms of service and laws.

## Publish To GitHub

```bash
cd /Users/chatzigrigorioug.a/Developer/my-projects/retail-catalog-scraper-portfolio
git init
git add .
git commit -m "Initial portfolio version: retail catalog scraper pipeline"

# Option A: using GitHub CLI (if logged in)
gh repo create retail-catalog-scraper-pipeline --public --source . --remote origin --push

# Option B: manual remote URL
# git remote add origin <YOUR_REPO_URL>
# git branch -M main
# git push -u origin main
```
