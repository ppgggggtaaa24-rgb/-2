def check_rakuten_vacancy(hotel_no, checkin_date, rakuten_id):
    """最新IDとAccess Keyの両方を試すモード"""
    url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
    
    # もしGitHub SecretsにACCESS_KEYを登録したならここを有効にします
    # 今回はひとまずIDを直接URLに入れる古い形式に戻しつつ、
    # パラメータ名を「applicationId」に固定して再挑戦します
    params = {
        "applicationId": rakuten_id, # ここにハイフンありIDを入れてみる
        "format": "json",
        "hotelNo": hotel_no,
        "checkinDate": checkin_date,
        "checkoutDate": checkin_date,
        "adultNum": 2,
        "hits": 1
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if "hotels" in data:
            hotel_info = data["hotels"][0]["hotel"][0]["hotelBasicInfo"]
            price = hotel_info.get("hotelMinCharge", "不明")
            return f"○ ({price}円)"
        elif "error" in data:
            # 何がダメなのかログに詳しく出す
            print(f"   [DEBUG] 楽天応答: {data.get('error_description', data.get('error'))}")
            if data["error"] == "not_found":
                return "×"
            return "Err"
        return "-"
    except:
        return "🚫"
