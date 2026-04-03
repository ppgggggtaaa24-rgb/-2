import os
import json
import gspread
from google.oauth2.service_account import Credentials
import requests
import time
import datetime

# --- 設定エリア ---
SPREADSHEET_ID = '17_qEw869AU_sPvQybe9Gwq4ZUYrbw_rjdjKJmmI8wA8'
HOTELS = [
    {"id": 10832, "name": "ホテル飛鳥"},
    {"id": 160534, "name": "ホテル日本海"},
]

def check_rakuten_vacancy_ninja(hotel_no, checkin_date, app_id, access_key):
    """
    2026年最新エンドポイントを使用し、門番を突破します。
    """
    # 🔗 URLを最新の『openapi』ドメインに変更しました！
    url = "https://openapi.rakuten.co.jp/travel/VacantHotelSearch/20170426"
    
    headers = {
        "Referer": "https://www.rakuten.co.jp/",
        "Origin": "https://www.rakuten.co.jp/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
    }

    params = {
        "applicationId": app_id,
        "accessKey": access_key,
        "format": "json",
        "hotelNo": hotel_no,
        "checkinDate": checkin_date,
        "checkoutDate": checkin_date,
        "adultNum": 2,
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=20)
        data = response.json()
        
        # 成功時
        if "hotels" in data:
            price = data["hotels"][0]["hotel"][0]["hotelBasicInfo"].get("hotelMinCharge", "不明")
            return f"○ ({price}円)"
        
        # エラー詳細（デバッグ用）
        error_code = data.get("error") or data.get("errors", {}).get("errorCode")
        if error_code == "not_found":
            return "×"
        
        print(f"   [DEBUG] 楽天エラー: {error_code} - {data}")
        return f"Err({error_code})"
    except Exception as e:
        return "🚫"

def main():
    print("🚀 【2026年最新・完全対応版】実行開始...")
    
    app_id = os.environ.get('RAKUTEN_APP_ID')
    access_key = os.environ.get('RAKUTEN_ACCESS_KEY')
    gcp_key_raw = os.environ.get('GCP_SERVICE_ACCOUNT_KEY')

    if not app_id or not access_key:
        print("❌ Secretsの設定を確認してください")
        return

    # スプシ接続
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(json.loads(gcp_key_raw), scopes=scopes)
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
        print("✅ スプシ接続成功")
    except Exception as e:
        print(f"❌ スプシ接続エラー: {e}")
        return

    # 日付作成
    now_jst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    dates = [(now_jst.date() + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    # 空室チェック
    results = []
    for date in dates:
        print(f"🔎 {date} チェック中...")
        row = [date]
        for hotel in HOTELS:
            row.append(check_rakuten_vacancy_ninja(hotel["id"], date, app_id, access_key))
            time.sleep(1)
        results.append(row)

    # 書き込み
    try:
        header = ["日付"] + [h["name"] for h in HOTELS]
        sheet.update(range_name='A1', values=[header])
        sheet.update(range_name='A2', values=results)
        print("✨ 更新完了！今度こそ勝利です！")
    except Exception as e:
        print(f"❌ 書込エラー: {e}")

if __name__ == "__main__":
    main()
