"""nifty不動産の物件ページから必要情報を抽出するスクレイパー。"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}
REQUEST_TIMEOUT = 10


def _load_html(url: str) -> str:
    """URLまたはローカルパスからHTML文字列を読み込む。"""
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
    """テーブル行（tr）のth/td対応から項目名と値を抽出する。"""
    table_data: Dict[str, str] = {}

    for row in soup.select("tr"):
        headers = row.find_all("th")
        values = row.find_all("td")

        if not headers or not values:
            continue

        pairs = zip(headers, values if len(headers) == len(values) else values[: len(headers)])
        for header, value in pairs:
            key = header.get_text(" ", strip=True)
            val = value.get_text(" ", strip=True)
            if key:
                table_data[key] = val

    return table_data


def _find_table_value(table_data: Dict[str, str], label: str) -> str:
    """完全一致→部分一致の順で項目値を返す。見つからなければ空文字。"""
    if label in table_data:
        return table_data[label]

    for key, value in table_data.items():
        if label in key:
            return value
    return ""


def _collect_values(table_data: Dict[str, str], labels: List[str]) -> List[str]:
    """候補ラベル群の値を重複除去しつつ収集する。"""
    values: List[str] = []
    seen = set()

    for label in labels:
        value = _find_table_value(table_data, label)
        if value and value not in seen:
            values.append(value)
            seen.add(value)

    return values


def _join(values: List[str], sep: str = "、") -> str:
    return sep.join([v for v in values if v])


def scrape_nifty_property(url: str) -> Dict[str, str]:
    """
    nifty不動産の個別物件ページから指定項目を抽出し、JSON風dictで返す。

    返却項目:
    - 私道負担・道路（接道状況 / 道路付け / 私道負担・道路 を結合）
    - 建ぺい率・容積率（建ぺい率 + 容積率 + 建ぺい率・容積率 を結合）
    - 構造・工法（建物構造 + 構造および階数 を結合）
    - 用途地域
    """

    html = _load_html(url)
    soup = BeautifulSoup(html, "html.parser")
    table_data = _extract_table_data(soup)

    road_values = _collect_values(table_data, ["接道状況", "道路付け", "私道負担・道路"])

    ratio_values = []
    building_ratio = _find_table_value(table_data, "建ぺい率")
    volume_ratio = _find_table_value(table_data, "容積率")
    if building_ratio:
        ratio_values.append(building_ratio)
    if volume_ratio and volume_ratio not in ratio_values:
        ratio_values.append(volume_ratio)

    combined_ratio = _find_table_value(table_data, "建ぺい率・容積率")
    if combined_ratio and combined_ratio not in ratio_values:
        ratio_values.append(combined_ratio)

    structure_values = _collect_values(table_data, ["建物構造", "構造および階数"])

    return {
        "私道負担・道路": _join(road_values),
        "建ぺい率・容積率": _join(ratio_values),
        "構造・工法": _join(structure_values),
        "用途地域": _find_table_value(table_data, "用途地域"),
    }
