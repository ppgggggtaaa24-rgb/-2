import os
import json
import gspread
from google.oauth2.service_account import Credentials
import requests
import time
import datetime

# --- 1. 設定エリア ---
SPREADSHEET_ID = '17_qEw869AU_sPvQybe9Gwq4ZUYrbw_rjdjKJmmI8wA8'

HOTELS = [
    {"id": 10832, "name": "ホテル飛鳥"},
    {"id": 160534, "name": "ホテル日本海"},
]

def check_rakuten_vacancy(hotel_no, checkin_date, rakuten_id):
    """最新のRAKUTEN ID (英数字ハイフンあり) に対応した関数"""
    url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
    
    # 最新ID用のヘッダー設定 (ここがポイント！)
    headers = {
        "Authorization": f"Bearer {rakuten_id}"
    }

    params = {
        # "applicationId": rakuten_id,  <-- 古い書き方はコメントアウト
        "format": "json",
        "hotelNo": hotel_no,
        "checkinDate": checkin_date,
        "checkoutDate": checkin_date,
        "adultNum": 2,
        "hits": 1
    }
    
    try:
        # headers=headers を追加して最新の認証を通す
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        
        # デバッグログ：エラーが出た場合だけ詳細を表示
        if "hotels" in data:
            hotel_info = data["hotels"][0]["hotel"][0]["hotelBasicInfo"]
            price = hotel_info.get("hotelMinCharge", "不明")
            return f"○ ({price}円)"
        elif "error" in data:
            err_msg = data.get('error_description', data.get('error'))
            if data["error"] == "not_found":
                return "×"
            print(f"   [DEBUG] 楽天エラー: {err_msg}")
            return f"Err"
        return "-"
    except Exception as e:
        return "🚫"

def main():
    print("🚀 最新IDモードでプログラムを開始します...")

    rakuten_id = os.environ.get('RAKUTEN_APP_ID')
    gcp_key_raw = os.environ.get('GCP_SERVICE_ACCOUNT_KEY')

    if not rakuten_id or not gcp_key_raw:
        print("❌ 設定不足です")
        return

    # スプシ接続
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(json.loads(gcp_key_raw), scopes=scopes)
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
        print(f"✅ スプシ '{sheet.title}' 接続OK")
    except Exception as e:
        print(f"❌ 接続エラー: {e}")
        return

    # 日付設定
    now_jst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    today = now_jst.date()
    check_dates = [(today + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    # 書き込み準備
    header = ["日付"] + [h["name"] for h in HOTELS]
    sheet.update(range_name='A1', values=[header])

    results_row = []
    for date in check_dates:
        print(f"🔎 {date} チェック中...")
        row = [date]
        for hotel in HOTELS:
            status = check_rakuten_vacancy(hotel["id"], date, rakuten_id)
            row.append(status)
            time.sleep(1)
        results_row.append(row)

    # 反映
    try:
        sheet.update(range_name='A2', values=results_row)
        print("✨ 更新完了！")
    except Exception as e:
        print(f"❌ 書込エラー: {e}")

if __name__ == "__main__":
    main()
