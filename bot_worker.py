import requests
import pandas as pd
from datetime import datetime, timedelta

# 1. CẤU HÌNH THÔNG TIN
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Dc3bHb7xKQkjDQgMNCi4JqD62DlH50EtbkMC0gIa2Yk/export?format=csv"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdaqt1OPFuSZ0daTneYrRMNn9V7x58kvb7GYhe5vi5e3JOPsw/formResponse"

TELEGRAM_TOKEN = "AAEh9DwH_iTHYsF7TihlsgKR4BmnMZfRVYI"
TELEGRAM_CHAT_ID = "1972517879"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Lỗi gửi Telegram: {e}")

def get_current_price(symbol):
    # Sử dụng API nguồn dữ liệu bạn đang dùng trong fetch_vn_data
    # Ví dụ với vnstock / SSI / tcbs api
    try:
        url = f"https://apipubaws.tcbs.com.vn/stock-insight/v1/stock/bars-long-term?ticker={symbol}&type=stock&resolution=D"
        res = requests.get(url, timeout=10).json()
        if 'data' in res and len(res['data']) > 0:
            return float(res['data'][-1]['close']) / 1000.0  # Quy về nghìn đồng
    except:
        pass
    return 0.0

def run_scanner():
    try:
        df = pd.read_csv(SHEET_URL)
        if df.empty:
            return
        
        for _, row in df.iterrows():
            symbol = str(row['symbol']).upper().strip()
            buy_p = float(row.get('buy', 0))
            stop_p = float(row.get('stop', 0))
            target_p = float(row.get('target', 0))
            
            curr_p = get_current_price(symbol)
            if curr_p == 0:
                continue

            pnl = ((curr_p - buy_p) / buy_p * 100) if buy_p > 0 else 0
            pnl_str = f"LÃI +{pnl:.2f}%" if pnl >= 0 else f"LỖ {pnl:.2f}%"

            is_alert = False
            action = ""

            if stop_p > 0 and curr_p <= stop_p:
                is_alert = True
                action = "🚨 CẮT LỖ"
            elif target_p > 0 and curr_p >= target_p:
                is_alert = True
                action = "💰 CHỐT LÃI"

            if is_alert:
                msg = f"{action} {symbol} tại mức giá {curr_p:,.2f} ({pnl_str})!"
                send_telegram(msg)
                
                # Ghi Log vào Google Form
                now_vn = (datetime.utcnow() + timedelta(hours=7)).strftime("%d/%m/%Y %H:%M:%S")
                form_data = {
                    "entry.MÃ_1": now_vn,
                    "entry.MÃ_2": symbol,
                    "entry.MÃ_3": curr_p,
                    "entry.MÃ_4": pnl_str,
                    "entry.MÃ_5": f"{action} - Quét tự động"
                }
                try:
                    requests.post(FORM_URL, data=form_data, timeout=10)
                except:
                    pass
    except Exception as e:
        print(f"Lỗi thực thi: {e}")

if __name__ == "__main__":
    run_scanner()
