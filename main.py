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

def get_access_token(app_id, access_key):
    """Access Keyを使って、一時的な『引換券(トークン)』を発行する"""
    auth_url = "https://auth.rakuten.co.jp/v2/oauth2/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": app_id,
        "client_secret": access_key,
        "scope": "rakuten_travel_api"
    }
    try:
        # 楽天の認証サーバーに問い合わせ
        res = requests.post(auth_url, data=data)
        token_data = res.json()
        return token_data.get("access_token")
    except Exception as e:
        print(f"   [DEBUG] トークン発行失敗: {e}")
        return None

def check_rakuten_vacancy(hotel_no, checkin_date, token):
    """発行されたトークンを使って空室をチェックする"""
    url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
    
    # 楽天が求めている『Bearer』形式でトークンを送る
    headers = {
        "Authorization": f"Bearer {token}"
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
        return "🚫"

def main():
    print("🚀 最強のOAuth2認証モードで開始します...")

    # GitHub Secrets から取得
    # ※RAKUTEN_APP_ID には「ハイフン入りの ID」
    # ※RAKUTEN_ACCESS_KEY には「Access Key」を入れておいてください
    app_id = os.environ.get('RAKUTEN_APP_ID')
    access_key = os.environ.get('RAKUTEN_ACCESS_KEY')
    gcp_key_raw = os.environ.get('GCP_SERVICE_ACCOUNT_KEY')

    # 1. 引換券（トークン）をゲットする
    print("🔑 トークンを発行中...")
    token = get_access_token(app_id, access_key)
    if not token:
        print("❌ トークンの発行に失敗しました。IDかAccess Keyが間違っている可能性があります。")
        return
    print("✅ トークン発行成功！")

    # 2. スプシ接続
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(json.loads(gcp_key_raw), scopes=scopes)
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
    except Exception as e:
        print(f"❌ スプシ接続エラー: {e}")
        return

    # 3. 日付と空室チェック
    now_jst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    today = now_jst.date()
    check_dates = [(today + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    results_row = []
    for date in check_dates:
        print(f"🔎 {date} チェック中...")
        row = [date]
        for hotel in HOTELS:
            status = check_rakuten_vacancy(hotel["id"], date, token)
            row.append(status)
            time.sleep(1)
        results_row.append(row)

    # 4. スプシに書き込み
    try:
        sheet.update(range_name='A2', values=results_row)
        print("✨ 更新が完了しました！")
    except Exception as e:
        print(f"❌ 書込エラー: {e}")

if __name__ == "__main__":
    main()
