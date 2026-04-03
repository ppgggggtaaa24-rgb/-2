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
    # あと3つ、競合のホテルIDをここに追加してください！
]

def check_rakuten_vacancy(hotel_no, checkin_date, app_id, access_key):
    """楽天APIで空室確認"""
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
        response = requests.get(url, params=params, headers=headers, timeout=20)
        data = response.json()
        if "hotels" in data: return "○"
        if response.status_code == 404 or data.get("error") == "not_found": return "×"
        return "Err"
    except: return "🚫"

def main():
    print("🚀 B2Bレベニューパトロール開始...")
    app_id = os.environ.get('RAKUTEN_APP_ID')
    access_key = os.environ.get('RAKUTEN_ACCESS_KEY')
    gcp_key_raw = os.environ.get('GCP_SERVICE_ACCOUNT_KEY')

    # スプシ接続（"data" という名前のシートを操作します）
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(json.loads(gcp_key_raw), scopes=scopes)
    gc = gspread.authorize(creds)
    
    # "data"シートを開く（名前が違う場合はここを修正）
    sheet = gc.open_by_key(SPREADSHEET_ID).worksheet("data")

    # 今日の日付（日本時間）
    now_jst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    
    # 既存データを一括取得して、どの日付が何行目にあるか把握する
    all_rows = sheet.get_all_values()
    date_to_row = {row[0]: i + 1 for i, row in enumerate(all_rows) if len(row) > 0}

    # 90日分チェック（頻度はGitHub ActionsのCron設定に依存）
    updates = []
    for i in range(90):
        target_date_obj = now_jst.date() + datetime.timedelta(days=i)
        target_date_str = target_date_obj.strftime("%Y-%m-%d")
        
        print(f"🔎 {target_date_str} を調査中...")
        
        sold_out_count = 0
        for hotel in HOTELS:
            status = check_rakuten_vacancy(hotel["id"], target_date_str, app_id, access_key)
            if status == "×":
                sold_out_count += 1
            time.sleep(1) # API負荷軽減
        
        # もし既にスプシにその日付があれば「上書き」、なければ「追加」
        if target_date_str in date_to_row:
            row_num = date_to_row[target_date_str]
            sheet.update_cell(row_num, 2, sold_out_count) # B列に満室数を書く
        else:
            sheet.append_row([target_date_str, sold_out_count])
            # 行番号を更新
            date_to_row[target_date_str] = len(date_to_row) + 2

    print("✨ すべての更新が完了しました！カレンダーを確認してください。")

if __name__ == "__main__":
    main()
