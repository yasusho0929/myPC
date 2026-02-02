"""SUUMO物件ページから必要な情報を抽出する簡易スクレイパー。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

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


def _first_match(patterns: List[str], text: str) -> str:
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""


def _extract_road_info(value: str) -> Dict[str, str]:
    direction = _first_match(
        [r"(北東|北西|南東|南西|北|南|東|西)"],
        value,
    )
    road_type = _first_match(
        [r"(公道|私道|国道|県道|市道|道道|農道|その他)"],
        value,
    )
    width = _first_match(
        [r"幅員\s*([0-9.]+)\s*(?:m|ｍ)", r"道路幅[:：]\s*([0-9.]+)\s*(?:m|ｍ)"],
        value,
    )

    return {
        "direction": direction,
        "type": road_type,
        "width": width,
    }


def _extract_city_planning(table_data: Dict[str, str]) -> str:
    for key, value in table_data.items():
        if "都市計画" in key:
            return value
    return ""


def _extract_coverage_ratio(value: str) -> Dict[str, str]:
    percents = re.findall(r"([0-9.]+\s*％)", value)
    if len(percents) >= 2:
        return {
            "coverage": percents[0].replace(" ", ""),
            "floor_area": percents[1].replace(" ", ""),
        }

    numbers = re.findall(r"([0-9.]+)", value)
    coverage = numbers[0] if len(numbers) >= 1 else ""
    floor_area = numbers[1] if len(numbers) >= 2 else ""
    return {
        "coverage": f"{coverage}%" if coverage else "",
        "floor_area": f"{floor_area}%" if floor_area else "",
    }


def scrape_suumo_property(url: str) -> List[str]:
    """
    SUUMO物件ページから以下の情報を抽出してリストで返す。

    - 前面道路：方位
    - 前面道路：種類
    - 前面道路：幅員（ｍ）
    - 都市計画
    - 建ぺい率（％）
    - 容積率（％）
    """

    html = _load_html(url)
    soup = BeautifulSoup(html, "html.parser")
    table_data = _extract_table_data(soup)

    road_value = ""
    for key, value in table_data.items():
        if "私道負担" in key and "道路" in key:
            road_value = value
            break

    road_info = _extract_road_info(road_value)
    city_planning = _extract_city_planning(table_data)

    ratio_value = ""
    for key, value in table_data.items():
        if "建ぺい率" in key and "容積率" in key:
            ratio_value = value
            break

    ratio_info = _extract_coverage_ratio(ratio_value)

    return [
        road_info["direction"],
        road_info["type"],
        road_info["width"],
        city_planning,
        ratio_info["coverage"],
        ratio_info["floor_area"],
    ]
