"""入力URLに応じて3サイト用スクレイパーを振り分ける。"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Callable, Dict

BASE_DIR = Path(__file__).resolve().parent


def _load_function(file_name: str, function_name: str) -> Callable[[str], Dict[str, str]]:
    module_path = BASE_DIR / file_name
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to load module: {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    func = getattr(module, function_name, None)
    if not callable(func):
        raise AttributeError(f"Function '{function_name}' was not found in {file_name}")
    return func


scrape_suumo_property = _load_function("03_suumo_scraper.py", "scrape_suumo_property")
scrape_sumaity_property = _load_function("04_sumaity_scraper.py", "scrape_sumaity_property")
scrape_nifty_property = _load_function("05_nifty_scraper.py", "scrape_nifty_property")


EMPTY_DATA = {
    "私道負担・道路": "",
    "建ぺい率・容積率": "",
    "構造・工法": "",
    "用途地域": "",
}


def scrape_3site_property(url: str) -> Dict[str, str]:
    """URLに含まれるドメインに応じて各サイトのスクレイパーを呼び分ける。"""
    if "https://suumo.jp/" in url:
        print("[scrape_3site_property] suumoの条件に一致したため、scrape_suumo_propertyを実行します。")
        return scrape_suumo_property(url)

    if "https://sumaity.com/" in url:
        print("[scrape_3site_property] sumaityの条件に一致したため、scrape_sumaity_propertyを実行します。")
        return scrape_sumaity_property(url)

    if "https://myhome.nifty.com/" in url:
        print("[scrape_3site_property] niftyの条件に一致したため、scrape_nifty_propertyを実行します。")
        return scrape_nifty_property(url)

    return EMPTY_DATA.copy()
