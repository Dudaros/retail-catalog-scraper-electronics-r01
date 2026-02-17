import concurrent.futures
import threading

import pandas as pd

import product_catalog_scraper


def test_main_skips_rows_with_missing_or_invalid_aem_url(monkeypatch):
    input_df = pd.DataFrame(
        {
            "AEM_URL": [None, "", "   ", "/cat/phones/smartphones", 123],
        }
    )

    additional_info_calls = []
    search_calls = {"count": 0}
    saved = {}

    def fake_read_excel(*args, **kwargs):
        return input_df

    def fake_fetch_additional_info(aem_url_parts):
        additional_info_calls.append(aem_url_parts)
        return {
            "categoryId": "cat-1",
            "title": "Smartphones",
            "remoteSPAUrl": "/electronics/phones/smartphones",
        }

    def fake_fetch_json_data(url, retries=None, timeout=None):
        search_calls["count"] += 1
        if search_calls["count"] == 1:
            return {
                "catalogEntryView": [
                    {
                        "uniqueID": "u1",
                        "singleSKUCatalogEntryID": "sku-1",
                        "partNumber": "pn-1",
                        "shortDescription": "desc",
                        "name": "Phone",
                        "manufacturer": "Brand",
                        "buyable": "true",
                        "UserData": [{"seo_url": "product/sku-1"}],
                        "price": [{"usage": "Offer", "value": "199.99"}],
                    }
                ]
            }
        return {"catalogEntryView": []}

    def fake_fetch_availability_statuses(sku_ids):
        assert sku_ids == ["sku-1"]
        return {"sku-1": "IMMEDIATELY_AVAILABLE"}

    def fake_save_to_excel(data, filename):
        saved["data"] = data
        saved["filename"] = filename

    monkeypatch.setattr(product_catalog_scraper.pd, "read_excel", fake_read_excel)
    monkeypatch.setattr(product_catalog_scraper, "fetch_additional_info", fake_fetch_additional_info)
    monkeypatch.setattr(product_catalog_scraper, "fetch_json_data", fake_fetch_json_data)
    monkeypatch.setattr(product_catalog_scraper, "fetch_availability_statuses", fake_fetch_availability_statuses)
    monkeypatch.setattr(product_catalog_scraper, "save_to_excel", fake_save_to_excel)

    product_catalog_scraper.main(limit=None)

    assert additional_info_calls == [["cat", "phones", "smartphones"]]
    assert len(saved["data"]) == 1
    assert saved["data"][0]["singleSKUCatalogEntryID"] == "sku-1"
    assert saved["data"][0]["Availability Status"] == "Άμεσα διαθέσιμο"


def test_fetch_availability_statuses_deduplicates_and_uses_bounded_workers(monkeypatch):
    seen_calls = []
    lock = threading.Lock()
    executor_max_workers = {}

    def fake_fetch_single_availability(sku_id):
        with lock:
            seen_calls.append(sku_id)
        return f"STATUS-{sku_id}"

    class CapturingExecutor:
        def __init__(self, max_workers=None):
            executor_max_workers["value"] = max_workers
            self._inner = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

        def __enter__(self):
            self._inner.__enter__()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return self._inner.__exit__(exc_type, exc_val, exc_tb)

        def submit(self, fn, *args, **kwargs):
            return self._inner.submit(fn, *args, **kwargs)

    monkeypatch.setattr(product_catalog_scraper, "fetch_single_availability", fake_fetch_single_availability)
    monkeypatch.setattr(product_catalog_scraper, "ThreadPoolExecutor", CapturingExecutor)

    statuses = product_catalog_scraper.fetch_availability_statuses(
        [None, float("nan"), "sku-1", "sku-1", "sku-2", "sku-3"]
    )

    assert executor_max_workers["value"] == 12
    assert set(seen_calls) == {"sku-1", "sku-2", "sku-3"}
    assert len(seen_calls) == 3
    assert statuses == {
        "sku-1": "STATUS-sku-1",
        "sku-2": "STATUS-sku-2",
        "sku-3": "STATUS-sku-3",
    }
