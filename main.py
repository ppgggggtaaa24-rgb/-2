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
    """
    最新の楽天認証サーバーからアクセストークンを取得する。
    URLを /token 直下に修正しました。
    """
    auth_url = "https://auth.rakuten.co.jp/token"
    
    # 認証に必要な情報をセット
    data = {
        "grant_type": "client_credentials",
        "client_id": app_id,
        "client_secret": access_key,
        "scope": "rakuten_travel_api"
    }
    
    try:
        print(f"📡 認証サーバー({auth_url})に接続中...")
        response = requests.post(auth_url, data=data, timeout=10)
        
        # ステータスコードが200以外ならエラー内容を表示
        if response.status_code != 200:
            print(f"   [DEBUG] 認証エラー: {response.status_code} - {response.text}")
            return None
            
        token_data = response.json()
        return token_data.get("access_token")
    except Exception as e:
        print(f"   [DEBUG] 通信エラーが発生しました: {e}")
        return None

def check_rakuten_vacancy(hotel_no, checkin_date, token):
    """取得したトークンを使って空室を検索する"""
    url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
    
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
            print(f"   [DEBUG] 検索エラー: {data.get('error_description', data.get('error'))}")
            return "Err"
        return "-"
    except Exception as e:
        return "🚫"

def main():
    print("🚀 最新認証（OAuth2）モードでスクリプトを実行します...")

    # GitHub Secrets から環境変数を読み込み
    app_id = os.environ.get('RAKUTEN_APP_ID')
    access_key = os.environ.get('RAKUTEN_ACCESS_KEY')
    gcp_key_raw = os.environ
