import requests
import time
import os  # ← これを追加

# --- 【設定】GitHubのSettingsで登録した名前を読み込む ---
# ローカルでテストする時は、一時的にURLを直接入れてもOKです
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# 監視する宿ID（ユーザーが自由に変えられる部分）
HOTEL_IDS = ["108739", "12345", "67890", "11111", "22222"] 
CHECK_DATE = "2026-05-02" 
THRESHOLD = 3 

def check_status(hid, date):
    url = f"https://hotel.travel.rakuten.co.jp/hotelinfo/plan/{hid}"
    # 日付パラメータ（2026年5月2日）
    params = {"hid_isDated": "1", "f_nen1": "2026", "f_tuki1": "5", "f_hi1": "2"}
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        res = requests.get(url, params=params, headers=headers, timeout=10)
        if "ご指定の条件に合うプランがありません" in res.text or "×" in res.text:
            return "×"
        return "○"
    except:
        return "ERR"

def send_discord(msg):
    if not DISCORD_WEBHOOK_URL:
        print("URLが設定されていません")
        return
    payload = {"content": msg}
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

# --- メイン処理 ---
results = []
full_count = 0

for hid in HOTEL_IDS:
    status = check_status(hid, CHECK_DATE)
    results.append(f"宿ID {hid}: {status}")
    if status == "×":
        full_count += 1
    time.sleep(3)

if full_count >= THRESHOLD:
    alert_msg = f" \n**【自動レベニュー監視】**\nターゲット日: `{CHECK_DATE}`\n"
    alert_msg += f"競合 {full_count} 宿が満室です！価格を確認してください。 :money_with_wings:\n"
    alert_msg += "```\n" + "\n".join(results) + "\n```"
    send_discord(alert_msg)
