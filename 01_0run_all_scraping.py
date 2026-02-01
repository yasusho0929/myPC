"""
============================================================
スクレイピング一括実行管理スクリプト
============================================================

【概要】
本スクリプトは、複数の不動産スクレイピング処理を
「順番に」「安全に」実行するための実行管理用スクリプトである。

以下のスクレイピングスクリプトを対象とし、
1本ずつ直列で実行する。

  - 01suumo_scrayping.py   （SUUMO）
  - 01_nifty_scraping.py  （ニフティ不動産）
  - 01_sumaity_scraping.py（スマイティ）

各スクリプトは独立したプロセスとして実行され、
途中でエラーが発生した場合でも、
後続のスクレイピング処理は継続して実行される。

------------------------------------------------------------
【設計方針】
- subprocess を用いた別プロセス実行
- 処理は必ず「指定順」で直列実行
- 例外・異常終了が発生しても全体は停止しない
- 実行結果（標準出力・エラー出力）をログに保存
- 日次運用・定期実行（タスクスケジューラ等）を想定

------------------------------------------------------------
【ログ仕様】
- logs/ ディレクトリ配下に日付単位でログを出力
- ファイル名形式：
    scraping_YYYYMMDD.log

- ログ内容：
    - 各スクリプトの開始・終了時刻
    - 標準出力（STDOUT）
    - エラー出力（STDERR）
    - 異常終了時のリターンコード
    - 例外発生時のメッセージ

------------------------------------------------------------
【前提条件】
- 本スクリプトと各スクレイピングスクリプトは
  同一ディレクトリに配置されていること
- Python 実行環境は sys.executable により自動取得される
- 各スクレイピングスクリプトは
  単体実行が可能であること

------------------------------------------------------------
【目的・位置づけ】
- 「生データ取得」フェーズの実行管理を担う
- 各スクレイピング処理の内部仕様には立ち入らない
- 失敗を許容しつつ、継続的なデータ蓄積を最優先とする

============================================================
"""

import subprocess
import datetime
import os
import sys

# =====================
# 設定
# =====================
SCRIPTS = [
    "01suumo_scrayping.py",
    "01_nifty_scraping.py",
    "01_sumaity_scraping.py",
]

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(
    LOG_DIR,
    f"scraping_{datetime.date.today().strftime('%Y%m%d')}.log"
)

PYTHON_EXE = sys.executable  # 今使っているPythonをそのまま使う

# =====================
# ログ出力関数
# =====================
def log(msg):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# =====================
# メイン処理
# =====================
if __name__ == "__main__":
    log("==== スクレイピング一括実行 開始 ====")

    for script in SCRIPTS:
        log(f"--- 実行開始: {script} ---")

        try:
            result = subprocess.run(
                [PYTHON_EXE, script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False  # エラーでも例外にしない
            )

            # 標準出力
            if result.stdout:
                log(f"[STDOUT] {script}\n{result.stdout.strip()}")

            # エラー出力
            if result.stderr:
                log(f"[STDERR] {script}\n{result.stderr.strip()}")

            if result.returncode != 0:
                log(f"⚠ エラー終了（スキップ）: {script} (code={result.returncode})")
            else:
                log(f"✔ 正常終了: {script}")

        except Exception as e:
            log(f"❌ 実行失敗（例外・スキップ）: {script}")
            log(str(e))

    log("==== スクレイピング一括実行 終了 ====")
