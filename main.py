# --- main.py 内のループ部分を修正 ---

    for i in range(90):
        target_date_obj = now_jst.date() + datetime.timedelta(days=i)
        
        # 修正ポイント：スラッシュ区切りに変更
        target_date_str = target_date_obj.strftime("%Y/%m/%d")
        
        sold_out_count = 0
        for h_id in hotel_ids:
            status = check_rakuten_vacancy(h_id, target_date_str, app_id, access_key)
            if status == "×":
                sold_out_count += 1
            time.sleep(0.4)
        
        all_results.append([target_date_str, sold_out_count])
