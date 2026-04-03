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

def get_access_token(app_id, access_key):
    """最新の楽天認証サーバーからアクセストークンを取得"""
    auth_url = "https://auth.rakuten.co.jp/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": app_id,
        "client_secret": access_key,
        "scope": "rakuten_travel_api"
    }
    try:
        print(f"📡 認証サーバーに接続中...")
        response = requests.post(auth_url, data=data, timeout=15)
        if response.status_code != 200:
            print(f"   [DEBUG] 認証エラー: {response.status_code} - {response.text}")
            return None
        return response.json().get("access_token")
    except Exception as e:
        print(f"   [DEBUG] 通信エラー: {e}")
        return None

def check_rakuten_vacancy(hotel_no, checkin_date, token):
    """トークンを使って空室検索"""
    url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "format": "json",
        "hotelNo": hotel_no,
        "checkinDate": checkin_date,
        "checkoutDate": checkin_date,
        "adultNum": 2,
        "hits": 1
    }
    try:
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        if "hotels" in data:
            price = data["hotels"][0]["hotel"][0]["hotelBasicInfo"].get("hotelMinCharge", "不明")
            return f"○ ({price}円)"
        elif "error" in data:
            return "×" if data["error"] == "not_found" else "Err"
        return "-"
    except:
        return "🚫"

def main():
    print("🚀 実行開始...")
    app_id = os.environ.get('RAKUTEN_APP_ID')
    access_key = os.environ.get('RAKUTEN_ACCESS_KEY')
    gcp_key_raw = os.environ.get('GCP_SERVICE_ACCOUNT_KEY')

    if not app_id or not access_key:
        print("❌ 設定不足: Secretsを確認してください")
        return

    token = get_access_token(app_id, access_key)
    if not token:
        print("❌ トークン取得失敗")
        return
    print("✅ トークン取得成功！")

    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(json.loads(gcp_key_raw), scopes=scopes)
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
        print(f"✅ スプシ '{sheet.title}' 接続成功")
    except Exception as e:
        print(f"❌ スプシ接続エラー: {e}")
        return

    now_jst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    check_dates = [(now_jst.date() + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    header = ["日付"] + [h["name"] for h in HOTELS]
    sheet.update(range_name='A1', values=[header])

    results = []
    for date in check_dates:
        print(f"🔎 {date} チェック中...")
        row = [date]
        for hotel in HOTELS:
            row.append(check_rakuten_vacancy(hotel["id"], date, token))
            time.sleep(1)
        results.append(row)

    sheet.update(range_name='A2', values=results)
    print("✨ スプレッドシート更新完了！")

# ⚠️ これが重要！プログラムを動かすための「スイッチ」です
if __name__ == "__main__":
    main()
