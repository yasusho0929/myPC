"""3data_master.csv を上から順に更新する。"""

from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
from typing import Dict, List

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "3data_master.csv"

TARGET_FIELDS = [
    "私道負担・道路",
    "建ぺい率・容積率",
    "構造・工法",
    "用途地域",
]


def _load_scrape_function():
    module_path = BASE_DIR / "06_3site_scraper.py"
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"{module_path} の読み込みに失敗しました")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    scrape_func = getattr(module, "scrape_3site_property", None)
    if not callable(scrape_func):
        raise AttributeError("scrape_3site_property が見つかりません")
    return scrape_func


def _read_csv(path: Path) -> tuple[List[str], List[Dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSVヘッダーが読み取れません")
        rows = list(reader)
        return reader.fieldnames, rows


def _write_csv(path: Path, fieldnames: List[str], rows: List[Dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _is_blank(value: str | None) -> bool:
    return value is None or str(value).strip() == ""


def main() -> None:
    scrape_3site_property = _load_scrape_function()
    fieldnames, rows = _read_csv(CSV_PATH)

    for index, row in enumerate(rows):
        deleted_at = row.get("削除年月日", "")
        check_value = (row.get("check", "") or "").strip().lower()

        if not _is_blank(deleted_at):
            row["check"] = "cannot"
            _write_csv(CSV_PATH, fieldnames, rows)
            continue

        if check_value in {"cannot", "ok"}:
            continue

        if check_value in {"not", ""}:
            url = (row.get("URL", "") or "").strip()
            if _is_blank(url):
                row["check"] = "not"
                _write_csv(CSV_PATH, fieldnames, rows)
                continue

            try:
                scraped = scrape_3site_property(url)
            except Exception as exc:
                print(f"[{index}] スクレイピング失敗: {url} ({exc})")
                row["check"] = "not"
                _write_csv(CSV_PATH, fieldnames, rows)
                continue

            for field in TARGET_FIELDS:
                row[field] = (scraped or {}).get(field, "")

            row["check"] = "ok"
            _write_csv(CSV_PATH, fieldnames, rows)


if __name__ == "__main__":
    main()
