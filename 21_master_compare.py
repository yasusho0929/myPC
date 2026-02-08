import hashlib
import math
import re
import unicodedata

import pandas as pd

# =====================
# 設定
# =====================
MASTER_CSV = "90_3data_master.csv"
CURR_CSV = "past/3data_260117.csv"  # 今回スナップショット
PRICE_DIFF_CSV = "91_diff_price_change.csv"
ENCODING = "utf-8-sig"

PROTECTED_UPDATE_COLUMNS = {
    "check",
    "私道負担・道路",
    "建ぺい率・容積率",
    "構造・工法",
    "用途地域",
    "追加年月日",
    "削除年月日",
}


# =====================
# ユーティリティ
# =====================
def normalize_text(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = unicodedata.normalize("NFKC", str(value)).strip()
    text = re.sub(r"\s+", "", text)
    return text


def normalize_minmax(value):
    text = normalize_text(value)
    return text.replace("〜", "-").replace("～", "-")


def trim_address_before_number(text):
    """所在地：半角/全角数字が出た位置以降を削除"""
    if text is None:
        return ""
    text = str(text)
    return re.split(r"[0-9０-９]", text)[0]


def floor_number(value):
    """土地面積/建物面積：小数点以下切り捨て"""
    try:
        return int(math.floor(float(value)))
    except (TypeError, ValueError):
        return ""


def generate_property_id(row):
    base = "_".join(
        [
            normalize_text(trim_address_before_number(row.get("所在地"))),
            normalize_text(row.get("種別")),
            normalize_minmax(row.get("最小最大")),
            str(floor_number(row.get("土地面積（m2）"))),
            str(floor_number(row.get("建物面積（m2）"))),
            # 築年月（年数換算）は使わない
        ]
    )
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:12]


def extract_yymmdd(filename):
    m = re.search(r"3data_(\d{6})\.csv", filename)
    if not m:
        raise ValueError("CSVファイル名から年月日を取得できません")
    return m.group(1)


def url_priority(url):
    text = str(url).lower()
    if "suumo" in text:
        return 0
    if "sumaity" in text:
        return 1
    if "nifty" in text:
        return 2
    return 3


def to_float(value):
    if pd.isna(value):
        return None
    text = str(value).replace(",", "").strip()
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def fallback_date_from_filename(csv_path):
    yymmdd = extract_yymmdd(csv_path)
    return f"20{yymmdd[:2]}/{yymmdd[2:4]}/{yymmdd[4:6]}"


# =====================
# 読み込み
# =====================
df_master = pd.read_csv(MASTER_CSV, encoding=ENCODING)
df_curr_raw = pd.read_csv(CURR_CSV, encoding=ENCODING)

# =====================
# ① スナップショットに物件IDを付与し、重複IDを優先度で解消
# =====================
df_curr_raw["物件ID"] = df_curr_raw.apply(generate_property_id, axis=1)
df_curr_raw["_url_rank"] = df_curr_raw["URL"].apply(url_priority)
df_curr_norm = (
    df_curr_raw.sort_values(["物件ID", "_url_rank", "情報取得日"], ascending=[True, True, False])
    .drop_duplicates(subset=["物件ID"], keep="first")
    .drop(columns=["_url_rank"])
)

# =====================
# ② マスター側の列補正
# =====================
for col in ["追加年月日", "削除年月日"]:
    if col not in df_master.columns:
        df_master[col] = ""

# =====================
# ③ マスター正規化（1ID=1行）
# =====================
df_master_norm = (
    df_master.sort_values("情報取得日").groupby("物件ID", as_index=False).last()
)

# index を物件IDに
df_master_norm = df_master_norm.set_index("物件ID", drop=False)
df_curr_norm = df_curr_norm.set_index("物件ID", drop=False)

master_ids = set(df_master_norm.index)
curr_ids = set(df_curr_norm.index)

snapshot_date_series = df_curr_norm["情報取得日"].dropna()
snapshot_date = (
    str(snapshot_date_series.iloc[0]).strip()
    if not snapshot_date_series.empty and str(snapshot_date_series.iloc[0]).strip()
    else fallback_date_from_filename(CURR_CSV)
)

# =====================
# 1️⃣ 新規物件: マスターへ追加
# =====================
new_ids = curr_ids - master_ids
df_new = df_curr_norm.loc[list(new_ids)].copy() if new_ids else pd.DataFrame(columns=df_master_norm.columns)
if not df_new.empty:
    df_new["追加年月日"] = df_new["情報取得日"]
    df_new["削除年月日"] = ""

# =====================
# 2️⃣ 削除物件: マスターの削除年月日を更新
# =====================
lost_ids = master_ids - curr_ids
for pid in lost_ids:
    val = df_master_norm.at[pid, "削除年月日"]
    if pd.isna(val) or str(val).strip() == "":
        df_master_norm.at[pid, "削除年月日"] = snapshot_date

# =====================
# 3️⃣ 継続物件: 指定列以外を上書き
# =====================
common_ids = master_ids & curr_ids

old_price_map = {}
if "販売価格" in df_master_norm.columns:
    old_price_map = {pid: df_master_norm.at[pid, "販売価格"] for pid in common_ids}

update_cols = [
    c
    for c in df_curr_norm.columns
    if c in df_master_norm.columns and c not in PROTECTED_UPDATE_COLUMNS
]

for pid in common_ids:
    for col in update_cols:
        df_master_norm.at[pid, col] = df_curr_norm.at[pid, col]
    df_master_norm.at[pid, "削除年月日"] = ""

# =====================
# 4️⃣ マスター統合・保存
# =====================
df_master_updated = pd.concat([df_master_norm, df_new], axis=0).reset_index(drop=True)
df_master_updated.to_csv(MASTER_CSV, index=False, encoding=ENCODING)

# =====================
# 5️⃣ 価格変動履歴を追記
# =====================
price_logs = []

for pid in common_ids:
    old_price = to_float(old_price_map.get(pid))
    new_price = to_float(df_curr_norm.at[pid, "販売価格"]) if "販売価格" in df_curr_norm.columns else None

    if old_price is None or new_price is None:
        continue

    if old_price != new_price:
        row = df_curr_norm.loc[pid].to_dict()
        row["価格差"] = new_price - old_price
        row["変化年月日"] = snapshot_date
        price_logs.append(row)

if price_logs:
    df_price_diff_new = pd.DataFrame(price_logs)

    try:
        df_price_diff_old = pd.read_csv(PRICE_DIFF_CSV, encoding=ENCODING)
        df_price_diff = pd.concat([df_price_diff_old, df_price_diff_new], ignore_index=True)
    except FileNotFoundError:
        df_price_diff = df_price_diff_new

    df_price_diff.to_csv(PRICE_DIFF_CSV, index=False, encoding=ENCODING)

print("✅ スナップショットID生成・重複解消・マスター更新 完了")
print(f"  新規追加: {len(new_ids)} 件")
print(f"  削除処理: {len(lost_ids)} 件")
print(f"  継続更新: {len(common_ids)} 件")
print(f"  価格変動履歴: {len(price_logs)} 件")
