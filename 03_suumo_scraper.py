"""SUUMO物件ページから必要な情報を抽出する簡易スクレイパー。"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import requests
from bs4 import BeautifulSoup

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}
REQUEST_TIMEOUT = 10


def _load_html(url: str) -> str:
    if url.startswith("file://"):
        return Path(url.replace("file://", "")).read_text(encoding="utf-8")

    path = Path(url)
    if path.exists():
        return path.read_text(encoding="utf-8")

    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return response.text


def _extract_table_data(soup: BeautifulSoup) -> Dict[str, str]:
    table_data: Dict[str, str] = {}

    for row in soup.select("tr"):
        headers = row.find_all("th")
        values = row.find_all("td")

        if not headers or not values:
            continue

        if len(headers) == len(values):
            pairs = zip(headers, values)
        else:
            pairs = zip(headers, values[: len(headers)])

        for header, value in pairs:
            key = header.get_text(" ", strip=True)
            val = value.get_text(" ", strip=True)
            if key:
                table_data[key] = val

    return table_data


def _find_table_value(table_data: Dict[str, str], label: str) -> str:
    if label in table_data:
        return table_data[label]

    for key, value in table_data.items():
        if label in key:
            return value
    return ""


def scrape_suumo_property(url: str) -> Dict[str, str]:
    """
    SUUMO物件ページから以下の情報を抽出してJSON風の辞書で返す。

    - 私道負担・道路
    - 建ぺい率・容積率
    - 構造・工法
    - 用途地域
    """

    html = _load_html(url)
    soup = BeautifulSoup(html, "html.parser")
    table_data = _extract_table_data(soup)

    labels = [
        "私道負担・道路",
        "建ぺい率・容積率",
        "構造・工法",
        "用途地域",
    ]

    return {label: _find_table_value(table_data, label) for label in labels}
