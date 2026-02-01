"""
02_suumo_dataframe.py
02_sumaity_dataframe.py
02_nifty_dataframe.py
を順番に実行し、それぞれの 02.csv を結合して

  3data_YYMMDD.csv

を出力する統合スクリプト。

・沿線・駅 / 沿線 の全角英字は最終的に半角へ正規化（NFKC）
・同一URLが複数ある場合、販売価格の最小／最大を判定し
  「最小最大」列にフラグを付与する
"""

import subprocess
import pandas as pd
from datetime import datetime
import sys
import os
import unicodedata

# =====================
# 1. 実行日（ファイル名用）
# =====================
today = datetime.now()
date_str = today.strftime("%y%m%d")  # 例: 260108

# =====================
# 2. 実行するスクリプト（順番厳守）
# =====================
SCRIPTS = [
    "02_suumo_dataframe.py",
    "02_sumaity_dataframe.py",
    "02_nifty_dataframe.py",
]

# =====================
# 3. 各スクリプトの出力CSV
# =====================
CSV_FILES = [
    "suumo02.csv",
    "sumaity02.csv",
    "nifty02.csv",
]

# =====================
# 4. サブスクリプトを順番に実行
# =====================
for script in SCRIPTS:
    print(f"▶ 実行中: {script}")

    result = subprocess.run(
        [sys.executable, script],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("❌ エラー発生")
        print(result.stderr)
        raise RuntimeError(f"{script} の実行に失敗しました")

    if result.stdout:
        print(result.stdout)

# =====================
# 5. CSV読み込み & 結合
# =====================
dfs = []

for csv_file in CSV_FILES:
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"{csv_file} が見つかりません")

    df = pd.read_csv(csv_file, encoding="utf-8-sig")
    dfs.append(df)

df_all = pd.concat(dfs, ignore_index=True)

# =====================
# 6. 全角英字 → 半角 正規化
# =====================
def normalize_ascii(text):
    if pd.isna(text):
        return text
    return unicodedata.normalize("NFKC", str(text))

for col in ["沿線・駅", "沿線"]:
    if col in df_all.columns:
        df_all[col] = df_all[col].apply(normalize_ascii)

# =====================
# 7. 販売価格を数値化（比較用）
# =====================
PRICE_COL = "販売価格"

df_all["_price_num"] = (
    df_all[PRICE_COL]
    .astype(str)
    .str.replace(",", "", regex=False)
    .str.replace("万円", "", regex=False)
)

df_all["_price_num"] = pd.to_numeric(df_all["_price_num"], errors="coerce")

# =====================
# 8. 最小 / 最大 判定（URL単位）
# =====================
df_all["最小最大"] = ""

for url, g in df_all.groupby("URL"):
    if len(g) <= 1:
        continue

    min_price = g["_price_num"].min()
    max_price = g["_price_num"].max()

    # 同額の場合は「最小」を優先
    df_all.loc[
        (df_all["URL"] == url) & (df_all["_price_num"] == min_price),
        "最小最大"
    ] = "最小"

    if max_price != min_price:
        df_all.loc[
            (df_all["URL"] == url) & (df_all["_price_num"] == max_price),
            "最小最大"
        ] = "最大"

# =====================
# 9. 補助列削除 & 念のため重複削除
# =====================
df_all = df_all.drop(columns=["_price_num"])
df_all = df_all.drop_duplicates()

# =====================
# 10. 最終CSV出力
# =====================
output_file = f"3data_{date_str}.csv"
df_all.to_csv(output_file, index=False, encoding="utf-8-sig")

print("===================================")
print(f"✅ 完了: {output_file}")
print(f"件数: {len(df_all)}")
print("===================================")
