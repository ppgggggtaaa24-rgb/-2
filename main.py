import os
import json
import gspread
from google.oauth2.service_account import Credentials
import requests
import time
import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- 設定 ---
SPREADSHEET_ID = '17_qEw869AU_sPvQybe9Gwq4ZUYrbw_rjdjKJmmI8wA8'
HOTELS = [
    {"id": 10832, "name": "ホテル飛鳥"},
    {"id": 160534, "name": "ホテル日本海"},
]

def get_access_token(app_id, access_key):
    """
    最新の認証方式(OAuth2)でトークンを取得。
    海外サーバーからの不安定な接続に備え、リトライと長いタイムアウトを設定。
    """
    # 候補となるURLを複数用意
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

    # セッションを作成し、リトライ戦略を設定
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))

    for url in auth_urls:
        try:
            print(f"📡 認証サーバーへ接続試行中: {url}")
            # 接続待ち(connect)と応答待ち(read)にたっぷり時間を取る
            response = session.post(url, data=data, timeout=(15, 30))
            
            if response.status_code == 200:
                print("✅ 認証成功！")
                return response.json().get("access_token")
            else:
                print(f"   ⚠️ サーバー応答あり(拒否): {response.status_code} - {response.text}")
        except Exception as e:
            print(f"   ⚠️ 接続失敗(詳細): {e}")
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
    print("🚀 【最新規格】OAuth2認証プロセスを開始します...")
    
    app_id = os.environ.get('RAKUTEN_APP_ID')
    access_key = os.environ.get('RAKUTEN_ACCESS_KEY')
    gcp_key_raw = os.environ.get('GCP_SERVICE_ACCOUNT_KEY')

    # 1. トークン取得
    token = get_access_token(app_id, access_key)
    if not token:
        print("❌ 致命的エラー: 認証サーバーに到達できませんでした。")
        return

    # 2. スプレッドシート接続
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(json.loads(gcp_key_raw), scopes=scopes)
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
        print(f"✅ スプレッドシート '{sheet.title}' に接続完了")
    except Exception as e:
        print(f"❌ スプシ接続エラー: {e}")
        return

    # 3. 空室チェックと書き込み
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

    try:
        sheet.update(range_name='A1', values=[["日付"] + [h["name"] for h in HOTELS]])
        sheet.update(range_name='A2', values=results)
        print("✨ すべての処理が成功しました！")
    except Exception as e:
        print(f"❌ 書き込みエラー: {e}")

if __name__ == "__main__":
    main()
