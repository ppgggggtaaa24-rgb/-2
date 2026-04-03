import os
import json
import gspread
from google.oauth2.service_account import Credentials
import requests
import time
import datetime

# --- 1. 設定エリア ---
# あなたのスプレッドシートID
SPREADSHEET_ID = '17_qEw869AU_sPvQybe9Gwq4ZUYrbw_rjdjKJmmI8wA8'

# 監視する宿リスト (ID, 名前)
HOTELS = [
    {"id": 10832, "name": "ホテル飛鳥"},
    {"id": 160534, "name": "ホテル日本海"},
]

def check_rakuten_vacancy(hotel_no, checkin_date, rakuten_id):
    """楽天APIを使って空室チェックを行う関数"""
    url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
    params = {
        "applicationId": rakuten_id,
        "format": "json",
        "hotelNo": hotel_no,
        "checkinDate": checkin_date,
        "checkoutDate": checkin_date,
        "adultNum": 2,
        "hits": 1
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if "hotels" in data:
            hotel_info = data["hotels"][0]["hotel"][0]["hotelBasicInfo"]
            price = hotel_info.get("hotelMinCharge", "不明")
            return f"○ ({price}円)"
        elif "error" in data:
            if data["error"] == "not_found":
                return "×"
            return f"Err:{data.get('error')}"
        return "-"
    except:
        return "🚫Err"

def main():
    print("🚀 プログラムを開始します...")

    # 環境変数の取得
    rakuten_id = os.environ.get('RAKUTEN_APP_ID')
    gcp_key_raw = os.environ.get('GCP_SERVICE_ACCOUNT_KEY')

    if not rakuten_id or not gcp_key_raw:
        print("❌ エラー: GitHubのSecrets設定（RAKUTEN_APP_ID または GCP_SERVICE_ACCOUNT_KEY）が足りません")
        return

    # スプレッドシート認証
    try:
        print("🔑 Google認証を実行中...")
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(json.loads(gcp_key_raw), scopes=scopes)
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
        print(f"✅ スプレッドシート '{sheet.title}' に接続成功！")
    except Exception as e:
        print(f"❌ スプシ接続エラー: {e}")
        return

    # 日付リスト作成 (今日から7日間)
    today = datetime.date.today()
    check_dates = [(today + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    # 見出しの書き込み
    header = ["日付"] + [h["name"] for h in HOTELS]
    sheet.update('A1', [header])

    # 楽天APIでチェック
    results_row = []
    for date in check_dates:
        print(f"🔎 {date} の空室をチェック中...")
        row = [date]
        for hotel in HOTELS:
            status = check_rakuten_vacancy(hotel["id"], date, rakuten_id)
            row.append(status)
            time.sleep(1) # API負荷軽減
        results_row.append(row)

    # まとめて書き込み
    try:
        # A2セルから結果を流し込む
        sheet.update(f'A2', results_row)
        print("✨ スプレッドシートの更新がすべて完了しました！")
    except Exception as e:
        print(f"❌ 書き込みエラー: {e}")

# これが重要！プログラムを動かすスイッチです
if __name__ == "__main__":
    main()
