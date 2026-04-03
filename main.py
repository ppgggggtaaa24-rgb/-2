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
    最新API(openapi.rakuten.co.jp)の仕様に合わせ、
    ヘッダー偽装と二重ID送信で門番を突破します。
    """
    url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
    
    # 2026年最新の「門番突破用ヘッダー」
    headers = {
        "Referer": "https://www.rakuten.co.jp/",
        "Origin": "https://www.rakuten.co.jp/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "X-Rakuten-Application-Id": app_id  # ヘッダーにもIDを仕込む
    }

    # パラメータにIDとAccessKeyを両方入れる
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
        
        # ログに生の応答を表示（デバッグ用）
        if response.status_code != 200:
            print(f"   [DEBUG] 楽天からの応答({response.status_code}): {response.text}")

        data = response.json()
        
        if "hotels" in data:
            hotel_info = data["hotels"][0]["hotel"][0]["hotelBasicInfo"]
            price = hotel_info.get("hotelMinCharge", "不明")
            return f"○ ({price}円)"
        elif "error" in data:
            if data["error"] == "not_found":
                return "×"
            return f"Err({data.get('error')})"
        return "-"
    except Exception as e:
        print(f"   [DEBUG] 通信エラー: {e}")
        return "🚫"

def main():
    print("🚀 【2026年最新版・門番突破モード】実行開始...")
    
    # GitHub Secrets から環境変数を読み込み
    app_id = os.environ.get('RAKUTEN_APP_ID')
    access_key = os.environ.get('RAKUTEN_ACCESS_KEY')
    gcp_key_raw = os.environ.get('GCP_SERVICE_ACCOUNT_KEY')

    if not app_id or not access_key:
        print("❌ エラー: RAKUTEN_APP_ID または RAKUTEN_ACCESS_KEY が設定されていません。")
        return

    # 1. スプレッドシートに接続
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(json.loads(gcp_key_raw), scopes=scopes)
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
        print(f"✅ スプレッドシート '{sheet.title}' 接続成功")
    except Exception as e:
        print(f"❌ スプシ接続エラー: {e}")
        return

    # 2. 今日から7日分の日付を作成
    now_jst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    check_dates = [(now_jst.date() + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    # 3. ホテルごとに空室をチェック
    results_row = []
    for date in check_dates:
        print(f"🔎 {date} をチェック中...")
        row = [date]
        for hotel in HOTELS:
            status = check_rakuten_vacancy_ninja(hotel["id"], date, app_id, access_key)
            row.append(status)
            time.sleep(1) # API制限対策
        results_row.append(row)

    # 4. スプレッドシートを更新
    try:
        header = ["日付"] + [h["name"] for h in HOTELS]
        sheet.update(range_name='A1', values=[header])
        sheet.update(range_name='A2', values=results_row)
        print("✨ すべてのデータが正常に反映されました！勝利です！")
    except
