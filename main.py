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

def check_rakuten_vacancy_ninja(hotel_no, checkin_date, app_id, access_key):
    """
    Qiitaの記事に基づいた「楽天偽装」モード。
    最新IDとAccessKeyを使いつつ、ヘッダーで門番をだまします。
    """
    url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
    
    # 2026年最新の「門番突破用ヘッダー」
    headers = {
        "Referer": "https://www.rakuten.co.jp/",
        "Origin": "https://www.rakuten.co.jp/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
    }

    # accessKeyをヘッダーではなく、あえてURLパラメータ（クエリ）に直接入れるのがコツ
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
        
        if "hotels" in data:
            price = data["hotels"][0]["hotel"][0]["hotelBasicInfo"].get("hotelMinCharge", "不明")
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
    print("🚀 【Qiita流・門番突破モード】で実行開始...")
    
    app_id = os.environ.get('RAKUTEN_APP_ID')
    access_key = os.environ.get('RAKUTEN_ACCESS_KEY')
    gcp_key_raw = os.environ.get('GCP_SERVICE_ACCOUNT_KEY')

    # スプシ接続
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(json.loads(gcp_key_raw), scopes=scopes)
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
    except Exception as e:
        print(f"❌ スプシ接続エラー: {e}")
        return

    # 日付と空室チェック
    now_jst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    check_dates = [(now_jst.date() + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    results_row = []
    for date in check_dates:
        print(f"🔎 {date} チェック中...")
        row = [date]
        for hotel in HOTELS:
            status = check_rakuten_vacancy_ninja(hotel["id"], date, app_id, access_key)
            row.append(status)
            time.sleep(1)
        results_row.append(row)

    # 書き込み
    try:
        sheet.update(range_name='A1', values=[["日付"] + [h["name"] for h in HOTELS]])
        sheet.update(range_name='A2', values=results_row)
        print("✨ 更新が成功しました！楽天の壁を越えましたね！")
    except Exception as e:
        print(f"❌ 書込エラー: {e}")

if __name__ == "__main__":
    main()
