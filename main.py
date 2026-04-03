import os
import json
import gspread
from google.oauth2.service_account import Credentials
import requests
import time
import datetime

# --- 設定 ---
SPREADSHEET_ID = '17_qEw869AU_sPvQybe9Gwq4ZUYrbw_rjdjKJmmI8wA8'
HOTELS = [
    {"id": 10832, "name": "ホテル飛鳥"},
    {"id": 160534, "name": "ホテル日本海"},
]

def check_rakuten_vacancy(hotel_no, checkin_date, access_key):
    """最新のアクセスキー認証 (x-api-key) を使った空室チェック"""
    url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
    
    # Zennの記事に基づいた最新のヘッダー設定
    headers = {
        "x-api-key": access_key
    }

    params = {
        "format": "json",
        "hotelNo": hotel_no,
        "checkinDate": checkin_date,
        "checkoutDate": checkin_date,
        "adultNum": 2,
        "hits": 1
    }
    
    try:
        # 認証情報をヘッダーに入れて送信
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        
        if "hotels" in data:
            hotel_info = data["hotels"][0]["hotel"][0]["hotelBasicInfo"]
            price = hotel_info.get("hotelMinCharge", "不明")
            return f"○ ({price}円)"
        elif "error" in data:
            if data["error"] == "not_found":
                return "×"
            print(f"   [DEBUG] 楽天エラー: {data.get('error_description', data.get('error'))}")
            return "Err"
        return "-"
    except Exception as e:
        print(f"   [DEBUG] 通信エラー: {e}")
        return "🚫"

def main():
    print("🚀 最新アクセスキーモードで開始します...")

    # Secretsからキーを取得
    access_key = os.environ.get('RAKUTEN_ACCESS_KEY')
    gcp_key_raw = os.environ.get('GCP_SERVICE_ACCOUNT_KEY')

    if not access_key:
        print("❌ エラー: RAKUTEN_ACCESS_KEY が設定されていません")
        return

    # スプレッドシート準備
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(json.loads(gcp_key_raw), scopes=scopes)
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
    except Exception as e:
        print(f"❌ スプシ接続エラー: {e}")
        return

    # 日付リスト (今日から7日間)
    now_jst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    today = now_jst.date()
    check_dates = [(today + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    # 見出し
    header = ["日付"] + [h["name"] for h in HOTELS]
    sheet.update(range_name='A1', values=[header])

    results_row = []
    for date in check_dates:
        print(f"🔎 {date} チェック中...")
        row = [date]
        for hotel in HOTELS:
            # アクセスキーを使ってチェック
            status = check_rakuten_vacancy(hotel["id"], date, access_key)
            row.append(status)
            time.sleep(1)
        results_row.append(row)

    # 書き込み
    try:
        sheet.update(range_name='A2', values=results_row)
        print("✨ すべて完了しました！")
    except Exception as e:
        print(f"❌ 書き込みエラー: {e}")

if __name__ == "__main__":
    main()
