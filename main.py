import os
import json
import gspread
from google.oauth2.service_account import Credentials
import requests
import datetime

def main():
    print("--- 処理を開始します ---")

    # 1. 環境変数のチェック
    rakuten_id = os.environ.get('RAKUTEN_APP_ID')
    gcp_key = os.environ.get('GCP_SERVICE_ACCOUNT_KEY')
    
    if not rakuten_id:
        print("❌ 楽天のアプリID(RAKUTEN_APP_ID)が設定されていません")
    if not gcp_key:
        print("❌ Googleの鍵(GCP_SERVICE_ACCOUNT_KEY)が設定されていません")
    
    # 2. スプレッドシート接続
    try:
        # ここにあなたのスプレッドシートIDを貼ってください
        SPREADSHEET_ID = 'あなたのスプレッドシートID' 
        
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(json.loads(gcp_key), scopes=scopes)
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
        print(f"✅ スプレッドシート '{sheet.title}' に接続しました")
    except Exception as e:
        print(f"❌ スプシ接続エラー: {e}")
        return

    # 3. テスト書き込み
    try:
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sheet.update_acell('A1', f"最終更新: {now}")
        print("✅ スプレッドシート A1セルに時刻を書き込みました！")
    except Exception as e:
        print(f"❌ 書き込みエラー: {e}")

    print("--- 処理を終了しました ---")

if __name__ == "__main__":
    main()
