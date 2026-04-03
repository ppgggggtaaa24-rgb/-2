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
    """
    最新の認証方式(OAuth2)でトークンを取得する。
    URL解決エラー対策として、IP直指定に近い挙動や別エンドポイントを試行します。
    """
    # 楽天の最新認証エンドポイント（複数の候補をループで試す）
    auth_urls = [
        "https://auth.rakuten.co.jp/token",
        "https://auth.rakuten.co.jp/v2/oauth2/token"
    ]
    
    data = {
        "grant_type": "client_credentials",
        "client_id": app_id,
        "client_secret": access_key,
        "scope": "rakuten_travel_api"
    }

    for url in auth_urls:
        try:
            print(f"📡 認証試行中: {url}")
            # タイムアウトを長めに設定し、海外からの不安定な接続に対応
            response = requests.post(url, data=data, timeout=30)
            if response.status_code == 200:
                return response.json().get("access_token")
            else:
                print(f"   ⚠️ 応答エラー({response.status_code}): {response.text}")
        except Exception as e:
            print(f"   ⚠️ 接続失敗: {e}")
            continue
    return None

def check_rakuten_vacancy(hotel_no, checkin_date, token):
    url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
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
        return "×" if data.get("error") == "not_found" else "Err"
    except:
        return "🚫"

def main():
    print("🚀 最新ID・OAuth2認証モードで開始...")
    app_id = os.environ.get('RAKUTEN_APP_ID')
    access_key = os.environ.get('RAKUTEN_ACCESS_KEY')
    gcp_key_raw = os.environ.get('GCP_SERVICE_ACCOUNT_KEY')

    # 1. トークン取得
    token = get_access_token(app_id, access_key)
    if not token:
        print("❌ 致命的エラー: 全ての認証エンドポイントで失敗しました。")
        print("💡 ヒント: 楽天デベロッパーの管理画面で『Allowed IPs』を完全に空にするか、'0.0.0.0/0'になっているか再確認してください。")
        return

    # 2. スプレッドシート接続
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(json.loads(gcp_key_raw), scopes=scopes)
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
    except Exception as e:
        print(f"❌ スプシ接続エラー: {e}")
        return

    # 3. 実行
    now_jst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    dates = [(now_jst.date() + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    results = []
    for date in dates:
        print(f"🔎 {date} チェック中...")
        row = [date]
        for h in HOTELS:
            row.append(check_rakuten_vacancy(h["id"], date, token))
            time.sleep(1)
        results.append(row)

    sheet.update(range_name='A1', values=[["日付"] + [h["name"] for h in HOTELS]])
    sheet.update(range_name='A2', values=results)
    print("✨ 最新IDでの更新に成功しました！")

if __name__ == "__main__":
    main()
