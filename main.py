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
    # 競合を5つまで増やすとB2Bとしての価値が最大化します
]

def check_rakuten_vacancy(hotel_no, checkin_date, app_id, access_key):
    """楽天APIで空室確認（安定版）"""
    url = "https://openapi.rakuten.co.jp/ichibams/api/Travel/VacantHotelSearch/20170426"
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
        response = requests.get(url, params=params, headers=headers, timeout=15)
        data = response.json()
        if "hotels" in data: return "○"
        if response.status_code == 404 or data.get("error") == "not_found": return "×"
        return "Err"
    except: return "🚫"

def main():
    print("⚡️ 爆速B2Bモード起動...")
    app_id = os.environ.get('RAKUTEN_APP_ID')
    access_key = os.environ.get('RAKUTEN_ACCESS_KEY')
    gcp_key_raw = os.environ.get('GCP_SERVICE_ACCOUNT_KEY')

    # スプシ接続
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(json.loads(gcp_key_raw), scopes=scopes)
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(SPREADSHEET_ID).worksheet("data")

    # 今日の日付
    now_jst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    
    # 全データを溜めるリスト
    all_results = []

    print(f"📡 楽天APIへ問い合わせ開始（合計{90}日間）...")
    for i in range(90):
        target_date_obj = now_jst.date() + datetime.timedelta(days=i)
        target_date_str = target_date_obj.strftime("%Y-%m-%d")
        
        sold_out_count = 0
        for hotel in HOTELS:
            status = check_rakuten_vacancy(hotel["id"], target_date_str, app_id, access_key)
            if status == "×":
                sold_out_count += 1
            # 1秒待機はBAN防止のため必須（ここが時間の大部分）
            time.sleep(0.5) 
        
        all_results.append([target_date_str, sold_out_count])
        if i % 10 == 0: print(f"--- {i}日目まで完了 ---")

    # --- 魔法の一括書き込み ---
    print("📝 スプレッドシートへ一括書き込み中...")
    # dataシートをA1からリセットしてドカッと流し込む
    sheet.update('A1', [['日付', '満室数']] + all_results)

    print(f"✨ 完了！処理時間: 約{int(len(all_results)*len(HOTELS)*0.6)}秒")

if __name__ == "__main__":
    main()
