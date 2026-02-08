"""3サイト向けスクレイパー実行スクリプト。"""

from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
from typing import Callable, Dict

FieldData = Dict[str, str]
ScraperFunc = Callable[[str], FieldData]

TARGET_FIELDS = ["私道負担・道路", "建ぺい率・容積率", "構造・工法", "用途地域"]
EMPTY_DATA: FieldData = {field: "" for field in TARGET_FIELDS}


def _load_scraper_function(module_path: Path, function_name: str) -> ScraperFunc:
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"モジュールを読み込めません: {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    scraper = getattr(module, function_name, None)
    if scraper is None:
        raise AttributeError(f"{function_name} が見つかりません: {module_path}")

    return scraper


def _build_scraper_router(base_dir: Path) -> list[tuple[str, ScraperFunc]]:
    suumo_scraper = _load_scraper_function(base_dir / "03_suumo_scraper.py", "scrape_suumo_property")
    sumaity_scraper = _load_scraper_function(base_dir / "04_sumaity_scraper.py", "scrape_sumaity_property")
    nifty_scraper = _load_scraper_function(base_dir / "05_nifty_scraper.py", "scrape_nifty_property")

    return [
        ("https://suumo.jp/", suumo_scraper),
        ("https://sumaity.com/", sumaity_scraper),
        ("https://myhome.nifty.com/", nifty_scraper),
    ]


def scrape_by_url(url: str, router: list[tuple[str, ScraperFunc]]) -> FieldData:
    if not url:
        return dict(EMPTY_DATA)

    for prefix, scraper in router:
        if prefix in url:
            try:
                data = scraper(url)
            except Exception:
                return dict(EMPTY_DATA)

            merged = dict(EMPTY_DATA)
            for field in TARGET_FIELDS:
                merged[field] = str(data.get(field, "") or "")
            return merged

    return dict(EMPTY_DATA)


def process_master_csv(csv_path: Path) -> None:
    router = _build_scraper_router(csv_path.parent)

    with csv_path.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            return

        fieldnames = reader.fieldnames
        rows = list(reader)

    for row in rows:
        deleted_at = (row.get("削除年月日") or "").strip()
        check = (row.get("check") or "").strip().lower()

        if deleted_at:
            row["check"] = "cannot"
            continue

        if check in {"cannot", "ok"}:
            continue

        url = (row.get("URL") or "").strip()
        scraped = scrape_by_url(url, router)

        for field in TARGET_FIELDS:
            row[field] = scraped.get(field, "")
        row["check"] = "ok"

    with csv_path.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    process_master_csv(base_dir / "3data_master.csv")


if __name__ == "__main__":
    main()
