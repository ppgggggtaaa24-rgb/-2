import os
import json
import gspread
from google.oauth2.service_account import Credentials
import requests
import time
import datetime

# --- 1. 認証設定 ---
# GitHub SecretsからJSON鍵を読み込む
json_key_raw = os.environ.get('GCP_SERVICE_ACCOUNT_KEY')
json_key = json.loads(json_key_raw)

scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_info(json_key, scopes=scope)
gc = gspread.authorize(creds)

# --- 2. スプレッドシートの設定 ---
# 先ほどメモしたシートIDをここに貼り付けてください
SPREADSHEET_ID = '17_qEw869AU_sPvQybe9Gwq4ZUYrbw_rjdjKJmmI8wA8' 
sheet = gc.open_by_key(SPREADSHEET_ID).sheet1

# 楽天APIキー
RAKUTEN_APP_ID = os.environ.get('RAKUTEN_APP_ID')

# --- 3. 監視する宿リスト (ID, 名前) ---
HOTELS = [
    {"id": 10832, "name": "ホテル飛鳥"},
    {"id": 160534, "name": "ホテル日本海"},
]

def main():
    today = datetime.date.today()
    # とりあえずテストで直近7日分
    CHECK_DATES = [(today + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    # スプシの見出し作成（最初だけ実行）
    header = ["日付"] + [h["name"] for h in HOTELS]
    sheet.update('A1', [header])

    results_row = []
    
    # 日付ごとにループ
    for i, date in enumerate(CHECK_DATES):
        row = [date]
        for hotel in HOTELS:
            # 楽天APIで空室チェック（前回の関数と同じロジック）
            status = check_rakuten_vacancy(hotel["id"], date) 
            row.append(status)
            time.sleep(1)
        results_row.append(row)
    
    # まとめてスプレッドシートに書き込み
    sheet.update(f'A2:C{len(CHECK_DATES)+1}', results_row)
    print("スプレッドシートの更新が完了しました！")

def check_rakuten_vacancy(hotel_no, checkin_date):
    """楽天APIを使って特定の宿・日付の空室と価格を調べる関数"""
    url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
    
    # 楽天APIに送るパラメーター
    params = {
        "applicationId": RAKUTEN_APP_ID,
        "format": "json",
        "hotelNo": hotel_no,
        "checkinDate": checkin_date,
        "checkoutDate": checkin_date, # 1泊で計算
        "adultNum": 2,               # 大人2名
        "hits": 1                    # 1件取得
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        # 1. 空室がある場合
        if "hotels" in data:
            # 最安値を抽出して「○(価格)」の形式にする
            hotel_info = data["hotels"][0]["hotel"][0]["hotelBasicInfo"]
            min_price = hotel_info.get("hotelMinCharge", "不明")
            return f"○ ({min_price}円)"
        
        # 2. 満室またはエラーの場合
        elif "error" in data:
            if data["error"] == "not_found":
                return "×" # 満室は「×」でスプシに書く
            else:
                return f"Err:{data.get('error')}"
        
        return "-" # その他不明
            
    except Exception as e:
        return "🚫Err"
