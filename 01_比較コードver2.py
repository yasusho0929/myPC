from common.property_id import generate_property_id
import pandas as pd
import re

# =====================
# 設定
# =====================
MASTER_CSV = "3data_master.csv"
CURR_CSV   = "3data_260117.csv"   # 今回スナップショット
ENCODING = "utf-8-sig"

# =====================
# 年月日取得（今回）
# =====================
def extract_yymmdd(filename):
    m = re.search(r"3data_(\d{6})\.csv", filename)
    if not m:
        raise ValueError("CSVファイル名から年月日を取得できません")
    return m.group(1)

YYMMDD = extract_yymmdd(CURR_CSV)

# =====================
# 読み込み
# =====================
df_master = pd.read_csv(MASTER_CSV, encoding=ENCODING)
df_curr_raw = pd.read_csv(CURR_CSV, encoding=ENCODING)

# =====================
# ① スナップショットに必ず物件IDを付与
# =====================
df_curr_raw["物件ID"] = df_curr_raw.apply(generate_property_id, axis=1)

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
    df_master
    .sort_values("情報取得日")
    .groupby("物件ID", as_index=False)
    .last()
)

# =====================
# ④ 今回スナップショット正規化（ID生成後）
# =====================
df_curr_norm = (
    df_curr_raw
    .sort_values("情報取得日")
    .groupby("物件ID", as_index=False)
    .last()
)

# =====================
# index を物件IDに
# =====================
df_master_norm = df_master_norm.set_index("物件ID", drop=False)
df_curr_norm   = df_curr_norm.set_index("物件ID", drop=False)

master_ids = set(df_master_norm.index)
curr_ids   = set(df_curr_norm.index)

# =====================
# 1️⃣ 新規物件（ID生成後に判定）
# =====================
new_ids = curr_ids - master_ids

df_new = df_curr_norm.loc[list(new_ids)].copy()
df_new["追加年月日"] = df_new["情報取得日"]
df_new["削除年月日"] = ""

# =====================
# 2️⃣ 削除物件（ID生成後に判定）
# =====================
lost_ids = master_ids - curr_ids

for pid in lost_ids:
    val = df_master_norm.at[pid, "削除年月日"]
    if pd.isna(val) or str(val).strip() == "":
        delete_date = f"20{YYMMDD[:2]}/{YYMMDD[2:4]}/{YYMMDD[4:6]}"
        df_master_norm.at[pid, "削除年月日"] = delete_date

# =====================
# 3️⃣ 継続物件（ID一致後に更新）
# =====================
common_ids = master_ids & curr_ids

update_cols = [
    c for c in df_curr_norm.columns
    if c in df_master_norm.columns
    and c not in ["追加年月日", "削除年月日"]
]

for pid in common_ids:
    for col in update_cols:
        df_master_norm.at[pid, col] = df_curr_norm.at[pid, col]

# =====================
# ⑤ マスター統合
# =====================
df_master_updated = pd.concat(
    [df_master_norm, df_new],
    axis=0
).reset_index(drop=True)

# =====================
# 保存
# =====================
df_master_updated.to_csv(
    MASTER_CSV,
    index=False,
    encoding=ENCODING
)

print("✅ ID付与後に一致判定 → マスター更新 完了")
print(f"  新規追加: {len(new_ids)} 件")
print(f"  削除処理: {len(lost_ids)} 件")
print(f"  継続更新: {len(common_ids)} 件")

# =====================
# 価格変動履歴の管理
# =====================
PRICE_DIFF_CSV = "diff_price_change.csv"

price_logs = []

for pid in common_ids:
    old_price = df_master_norm.at[pid, "販売価格"]
    new_price = df_curr_norm.at[pid, "販売価格"]

    if pd.isna(old_price) or pd.isna(new_price):
        continue

    if float(old_price) != float(new_price):
        price_logs.append({
            "物件ID": pid,
            "種別": df_curr_norm.at[pid, "種別"],
            "物件名": df_curr_norm.at[pid, "物件名"],
            "所在地": df_curr_norm.at[pid, "所在地"],
            "沿線": df_curr_norm.at[pid, "沿線"],
            "駅": df_curr_norm.at[pid, "駅"],
            "徒歩": df_curr_norm.at[pid, "徒歩"],
            "旧価格": old_price,
            "新価格": new_price,
            "価格差": float(new_price) - float(old_price),
            "変動年月日": f"20{YYMMDD[:2]}/{YYMMDD[2:4]}/{YYMMDD[4:6]}",
            "情報取得日": df_curr_norm.at[pid, "情報取得日"],
            "URL": df_curr_norm.at[pid, "URL"],
        })

# ---------------------
# CSVへ追記（履歴管理）
# ---------------------
if price_logs:
    df_price_diff_new = pd.DataFrame(price_logs)

    try:
        df_price_diff_old = pd.read_csv(PRICE_DIFF_CSV, encoding=ENCODING)
        df_price_diff = pd.concat(
            [df_price_diff_old, df_price_diff_new],
            ignore_index=True
        )
    except FileNotFoundError:
        df_price_diff = df_price_diff_new

    df_price_diff.to_csv(
        PRICE_DIFF_CSV,
        index=False,
        encoding=ENCODING
    )

    print(f"💰 価格変動履歴 追加: {len(df_price_diff_new)} 件")
else:
    print("💰 価格変動なし")
