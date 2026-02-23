import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta
import yfinance as yf

# ==============================
# 1. CẤU HÌNH BAN ĐẦU & TỪ ĐIỂN
# ==============================
st.set_page_config(page_title="Pro Trading Terminal", layout="wide")
st.title("PRO TRADING TERMINAL – T+ & INTRADAY")

# TẠO 2 CỘT: 1 CỘT HIỂN THỊ CHỮ, 1 CỘT CHỨA NÚT BẬT/TẮT
col_info, col_toggle = st.columns([2, 1])
    
with col_info:
        st.write("**Trợ lý:** Đang quét hệ thống đa tầng...")
        
with col_toggle:
    # ĐÂY CHÍNH LÀ NÚT BẠN CẦN TÌM
    auto_alert = st.checkbox(
        "🔔 Tự động báo siêu phẩm", 
        value=False, 
        key="enable_auto_telegram", # Thêm key để Streamlit không nhầm lẫn
        help="Bật để nhận tin nhắn tự động khi có mã mới biến động mạnh."
    )

ACCOUNT_SIZE = 100_000_000  # Vốn 100 triệu VNĐ
RISK_PERCENT = 1            # Rủi ro 1%
ATR_MULTIPLIER = 1.5
RR_TARGET = 2

# Danh sách quét nhanh 10 mã (để không bị lag máy chủ)
SCAN_WATCHLIST = ["HPG", "VIX", "SSI", "SHB", "MBB", "VND", "DIG", "NVL", "STB", "MWG"]

# Từ điển Tên công ty
COMPANY_INFO = {
    "HPG": "Tập đoàn Hòa Phát", "HSG": "Tập đoàn Hoa Sen", "NKG": "Thép Nam Kim", "SMC": "Đầu tư Thương mại SMC", "VGS": "Ống thép Việt Đức",
    "SSI": "Chứng khoán SSI", "VND": "Chứng khoán VNDirect", "VIX": "Chứng khoán VIX", "SHS": "Chứng khoán Sài Gòn - Hà Nội", "MBS": "Chứng khoán MB", "HCM": "Chứng khoán HSC", "VCI": "Chứng khoán Vietcap", "FTS": "Chứng khoán FPT", "CTS": "Chứng khoán VietinBank", "BSI": "Chứng khoán BIDV",
    "SHB": "Ngân hàng SHB", "MBB": "Ngân hàng Quân Đội", "STB": "Ngân hàng Sacombank", "VPB": "Ngân hàng VPBank", "TCB": "Ngân hàng Techcombank", "CTG": "Ngân hàng VietinBank", "VCB": "Ngân hàng Vietcombank", "BID": "Ngân hàng BIDV", "ACB": "Ngân hàng Á Châu", "TPB": "Ngân hàng TPBank", "HDB": "Ngân hàng HDBank", "VIB": "Ngân hàng Quốc tế VIB", "EIB": "Ngân hàng Eximbank", "MSB": "Ngân hàng Hàng Hải", "LPB": "Ngân hàng LPBank",
    "DIG": "Tổng Công ty DIC (DIC Corp)", "NVL": "Tập đoàn Novaland", "PDR": "Phát triển Bất động sản Phát Đạt", "DXG": "Tập đoàn Đất Xanh", "CEO": "Tập đoàn CEO", "KBC": "Phát triển Đô thị Kinh Bắc", "IDC": "Tổng Công ty IDICO", "VGC": "Tổng Công ty Viglacera", "NLG": "Đầu tư Nam Long", "KDH": "Nhà Khang Điền", "VIC": "Tập đoàn Vingroup", "VHM": "Công ty Cổ phần Vinhomes", "VRE": "Vincom Retail", "TCH": "Tài chính Hoàng Huy", "HDG": "Tập đoàn Hà Đô",
    "FPT": "Tập đoàn FPT", "MWG": "Đầu tư Thế Giới Di Động", "PNJ": "Vàng bạc Đá quý Phú Nhuận", "DGW": "Thế Giới Số (Digiworld)", "FRT": "Bán lẻ Kỹ thuật số FPT", "PET": "Dịch vụ Tổng hợp Dầu khí",
    "DGC": "Hóa chất Đức Giang", "DCM": "Phân bón Dầu khí Cà Mau", "DPM": "Phân bón Dầu khí Phú Mỹ", "CSV": "Hóa chất Cơ bản Miền Nam",
    "VHC": "Thủy sản Vĩnh Hoàn", "ANV": "Thủy sản Nam Việt", "IDI": "Đa Quốc Gia IDI", "ASM": "Tập đoàn Sao Mai",
    "HAH": "Vận tải Hải An", "GMD": "Cổ phần Gemadept", "PVT": "Vận tải Dầu khí", "VOS": "Vận tải Biển Việt Nam",
    "GAS": "Tổng Công ty Khí VN", "PVS": "Dịch vụ Kỹ thuật Dầu khí", "PVD": "Khoan Dầu khí", "BSR": "Lọc Hóa dầu Bình Sơn", "PLX": "Tập đoàn Petrolimex", "POW": "Điện lực Dầu khí VN", "PC1": "Tập đoàn PC1", "NT2": "Điện lực Dầu khí Nhơn Trạch 2", "GEG": "Điện Gia Lai",
    "LCG": "Công ty Cổ phần Lizen", "HHV": "Hạ tầng Giao thông Đèo Cả", "VCG": "Vinaconex", "C4G": "Tập đoàn CIENCO4", "FCN": "Công ty Fecon", "KSB": "Khoáng sản Bình Dương", "HUT": "Công ty Tasco",
    "VNM": "Sữa Việt Nam (Vinamilk)", "SAB": "Bia Sài Gòn (Sabeco)", "MSN": "Tập đoàn Masan", "MCH": "Hàng tiêu dùng Masan", "DBC": "Tập đoàn Dabaco", "BAF": "Nông nghiệp BAF", "HAG": "Hoàng Anh Gia Lai", "HNG": "Nông nghiệp Quốc tế HAGL"
}
ALL_SYMBOLS = list(COMPANY_INFO.keys())
ALL_SYMBOLS.sort()

# ==============================
# 2. HÀM TELEGRAM & LẤY DỮ LIỆU
# ==============================
def send_telegram_alert(message):
    # Lấy thông tin từ "két sắt" của Streamlit
    try:
        bot_token = st.secrets["TELEGRAM_TOKEN"]
        bot_chatID = st.secrets["TELEGRAM_CHAT_ID"]
    except KeyError:
        st.error("⚠️ Lỗi: Chưa cấu hình Token hoặc Chat ID trong file Secrets!")
        return

    send_text = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={bot_chatID}&parse_mode=Markdown&text={message}"
    try: 
        requests.get(send_text, timeout=5)
    except: 
        pass

def fetch_vn_data(symbol, interval, days_back):
    res_map = {"1d": "1D", "15m": "15"}
    r = res_map.get(interval, "1D")
    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=days_back)).timestamp())
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # 1. VNDirect
    try:
        res = requests.get(f"https://dchart-api.vndirect.com.vn/dchart/history?symbol={symbol}&resolution={r}&from={start_ts}&to={end_ts}", headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get('s') == 'ok' and 't' in data:
                df = pd.DataFrame({'Date': pd.to_datetime(data['t'], unit='s') + pd.Timedelta(hours=7), 'Open': data['o'], 'High': data['h'], 'Low': data['l'], 'Close': data['c'], 'Volume': data['v']})
                df.set_index('Date', inplace=True)
                if not df.empty and df['Close'].iloc[-1] > 1000: df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']] / 1000
                return df.dropna()
    except: pass

    # 2. DNSE
    try:
        res = requests.get(f"https://services.entrade.com.vn/chart-api/chart?symbol={symbol}&resolution={r}&from={start_ts}&to={end_ts}", headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get('s') == 'ok' and 't' in data:
                df = pd.DataFrame({'Date': pd.to_datetime(data['t'], unit='s') + pd.Timedelta(hours=7), 'Open': data['o'], 'High': data['h'], 'Low': data['l'], 'Close': data['c'], 'Volume': data['v']})
                df.set_index('Date', inplace=True)
                if not df.empty and df['Close'].iloc[-1] > 1000: df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']] / 1000
                return df.dropna()
    except: pass

    # 3. TCBS
    try:
        r_tcbs = "D" if interval == "1d" else "15"
        res = requests.get(f"https://apipubaws.tcbs.com.vn/stock-insight/v1/stock/bars-long-term?ticker={symbol}&type=stock&resolution={r_tcbs}&from={start_ts}&to={end_ts}", headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if 'data' in data and len(data['data']) > 0:
                df = pd.DataFrame(data['data'])
                df['Date'] = pd.to_datetime(df['tradingDate'])
                df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
                df.set_index('Date', inplace=True)
                if not df.empty and df['Close'].iloc[-1] > 1000: df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']] / 1000
                return df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    except: pass

    # 4. Yahoo
    try:
        df_yf = yf.download(f"{symbol}.VN", period=f"{min(days_back, 60)}d", interval="1d" if interval=="1d" else "15m", progress=False)
        if not df_yf.empty:
            if isinstance(df_yf.columns, pd.MultiIndex): df_yf.columns = [col[0] for col in df_yf.columns]
            req = ['Open', 'High', 'Low', 'Close', 'Volume']
            if all(c in df_yf.columns for c in req): return df_yf[req].dropna()
    except: pass
    return pd.DataFrame()

# ==============================
# 3. BỘ LỌC CỔ PHIẾU NÓNG & QUẢN LÝ TELEGRAM
# ==============================
st.markdown("---")
with st.expander("🔥 TÌM KIẾM CỔ PHIẾU NÓNG & CẤU HÌNH BÁO ĐỘNG", expanded=True):
    
    @st.cache_data(ttl=120)
    def scan_hot_stocks():
        results = []
        for sym in SCAN_WATCHLIST:
            # SỬA LỖI Ở ĐÂY: Lấy 60 ngày để bao trọn cả T7, CN và các dịp Lễ
            df_scan = fetch_vn_data(sym, "1d", 60) 
            
            # Cần tối thiểu 25 phiên giao dịch thực tế để đường EMA20 chạy mượt
            if df_scan.empty or len(df_scan) < 25: 
                continue
            
            try:
                current_price = float(df_scan['Close'].iloc[-1])
                
                # ✅ 1. BỘ LỌC PENNY RÁC: Dưới 10k thì bỏ qua
                if current_price < 10.0:
                    continue

                avg_vol = float(df_scan['Volume'].tail(15).mean())
                vol_today = float(df_scan['Volume'].iloc[-1])
                
                # ✅ 2. ĐÁNH GIÁ THANH KHOẢN (> 3 Triệu cổ)
                is_high_liquidity = avg_vol >= 3000000
                vol_icon = "🔥 " if is_high_liquidity else ""
                
                # ✅ 3. BIẾN ĐỘNG GIÁ 3 NGÀY QUA
                price_3d_ago = float(df_scan['Close'].iloc[-4])
                change_3d = ((current_price - price_3d_ago) / price_3d_ago) * 100
                
                # ✅ 4. TRẠNG THÁI: Tích lũy hay Break?
                ema20 = float(df_scan['Close'].ewm(span=20, adjust=False).mean().iloc[-1])
                
                if change_3d > 10:
                    status = "🔴 Đã chạy xa"
                elif current_price > ema20 and vol_today > (avg_vol * 1.5) and change_3d <= 7:
                    status = "🚀 Vừa Break nền"
                elif abs(current_price - ema20) / ema20 < 0.03 and abs(change_3d) < 4:
                    status = "🟡 Đang tích lũy"
                elif current_price < ema20:
                    status = "🔻 Dưới EMA20"
                else:
                    status = "⚪ Nhịp thường"

                # Tính biên độ phiên nay
                volatility = float((df_scan['High'].iloc[-1] - df_scan['Low'].iloc[-1]) / df_scan['Low'].iloc[-1] * 100)

                results.append({
                    "Mã CP": sym,
                    "Giá Hiện Tại": current_price,
                    "Trạng thái": status,
                    "Tăng 3 Ngày (%)": change_3d,
                    "Thanh khoản TB": avg_vol,
                    "Hiển thị TK": f"{vol_icon}{int(avg_vol):,}",
                    "Volume Đột biến": round(vol_today / avg_vol, 1) if avg_vol > 0 else 0,
                    "Biên độ (%)": volatility
                })
            except Exception as e: 
                continue # Nếu mã nào bị lỗi dữ liệu bất thường thì âm thầm bỏ qua
            
        df_res = pd.DataFrame(results)
        if not df_res.empty:
            df_res['Sort_Priority'] = df_res['Trạng thái'].apply(lambda x: 1 if "Break" in x else (2 if "tích lũy" in x else 3))
            df_res = df_res.sort_values(by=["Sort_Priority", "Thanh khoản TB"], ascending=[True, False])
            
            cols_order = ["Mã CP", "Trạng thái", "Giá Hiện Tại", "Tăng 3 Ngày (%)", "Hiển thị TK", "Volume Đột biến", "Biên độ (%)"]
            df_res = df_res[cols_order]
            
        return df_res

    top_stocks = scan_hot_stocks()
    
    if not top_stocks.empty:
        # Hàm tô màu Xanh/Đỏ cho cột Tăng 3 ngày
        def color_3d_change(val):
            color = 'green' if val > 0 and val <= 10 else ('red' if val > 10 else 'gray')
            return f'color: {color}'

        # Hiển thị bảng đã được Format
        st.dataframe(
            top_stocks.style
            .map(color_3d_change, subset=['Tăng 3 Ngày (%)'])
            .format({
                "Giá Hiện Tại": "{:,.2f}", 
                "Tăng 3 Ngày (%)": "{:.1f}%", 
                "Volume Đột biến": "x{:.1f}",
                "Biên độ (%)": "{:.2f}%"
            }), 
            use_container_width=True, 
            hide_index=True
        )
        
        best = top_stocks.iloc[0]
        st.success(f"⚡ **Mã lướt biên lớn nhất:** **{best['Mã CP']}** (Biên độ TB **{best['Biên độ (%)']}%**/ngày).")
        
        # LOGIC TELEGRAM THÔNG MINH: SĂN ĐIỂM BREAK NỀN
        if auto_alert:
            # Khởi tạo bộ nhớ để ghi nhớ các mã đã báo, tránh spam tin nhắn liên tục
            if "alerted_breakouts" not in st.session_state:
                st.session_state["alerted_breakouts"] = []

            # Lọc ra TẤT CẢ các mã có trạng thái "🚀 Vừa Break nền" trong danh sách
            breakout_stocks = top_stocks[top_stocks['Trạng thái'] == "🚀 Vừa Break nền"]
            
            if not breakout_stocks.empty:
                for _, row in breakout_stocks.iterrows():
                    sym = row['Mã CP']
                    
                    # Nếu mã này CHƯA được báo trong phiên làm việc hiện tại -> Báo ngay!
                    if sym not in st.session_state["alerted_breakouts"]:
                        msg = (
                            f"🚀 [TÍN HIỆU MUA: BREAK NỀN]\n"
                            f"Hệ thống phát hiện *{sym}* vừa bứt phá!\n"
                            f"---------------------------\n"
                            f"- Giá hiện tại: {row['Giá Hiện Tại']:,.2f}\n"
                            f"- Thanh khoản: {row['Hiển thị TK']} cổ\n"
                            f"- Volume đột biến: {row['Volume Đột biến']}x so với TB\n"
                            f"- Biến động 3 ngày: +{row['Tăng 3 Ngày (%)']:.1f}%\n"
                            f"👉 Nền giá đang rất đẹp, sếp vào kiểm tra Chart ngay nhé!"
                        )
                        send_telegram_alert(msg)
                        
                        # Đưa mã vào danh sách "Đã báo" để lần quét sau (5 phút sau) không nhắn lại nữa
                        st.session_state["alerted_breakouts"].append(sym)
                        st.toast(f"Đã báo Telegram tín hiệu Break nền của {sym}!", icon="🔔")
        else:
            st.info("🔕 Chế độ im lặng đang bật. Bot sẽ không tự động nhắn tin.")
    else:
        st.error("❌ Đang lỗi kết nối dữ liệu ở tất cả các máy chủ.")
# st.markdown("---")

from streamlit_gsheets import GSheetsConnection

# ==============================
# 3.5 DANH MỤC TRỰC CHIẾN & TÍNH TOÁN THUẾ PHÍ
# ==============================
from streamlit_gsheets import GSheetsConnection

@st.cache_resource
def get_alert_memory():
    return {}

st.markdown("---")
with st.expander("📊 DANH MỤC TRỰC CHIẾN & TÍNH TOÁN LÃI/LỖ RÒNG", expanded=True):
    # Dán link Google Sheets của bạn vào đây
    SHEET_URL = "https://docs.google.com/spreadsheets/d/1Dc3bHb7xKQkjDQgMNCi4JqD62DlH50EtbkMC0gIa2Yk/edit?usp=sharing"
    
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_sheets = conn.read(spreadsheet=SHEET_URL, ttl=60)
        
        if not df_sheets.empty:
            final_list = []
            portfolio_details = {} # Kho lưu trữ chi tiết để tính Thuế/Phí
            alert_memory = get_alert_memory()
            
            for index, row in df_sheets.iterrows():
                symbol_item = str(row['symbol']).upper().strip()
                # Lấy dữ liệu an toàn, nếu cột volume chưa có thì mặc định là 0
                vol = float(row.get('volume', 0)) 
                
                df_live = fetch_vn_data(symbol_item, "1d", 1)
                current_p = float(df_live['Close'].iloc[-1]) if not df_live.empty else 0.0
                
                buy_p = float(row['buy'])
                pnl_percent = ((current_p - buy_p) / buy_p * 100) if buy_p > 0 else 0
                
                # --- LOGIC CẢNH BÁO CHỐNG SPAM (Giữ nguyên) ---
                if current_p > 0:
                    is_alerting = False
                    alert_msg = ""
                    if current_p <= float(row['stop']) and float(row['stop']) > 0:
                        is_alerting = True
                        alert_msg = f"🚨 [CẮT LỖ] {symbol_item} chạm giá {current_p:,.2f}!"
                    elif current_p >= float(row['target']) and float(row['target']) > 0:
                        is_alerting = True
                        alert_msg = f"💰 [CHỐT LÃI] {symbol_item} chạm giá {current_p:,.2f}!"

                    if is_alerting:
                        last_price = alert_memory.get(symbol_item)
                        if current_p != last_price:
                            send_telegram_alert(alert_msg)
                            alert_memory[symbol_item] = current_p
                    else:
                        if symbol_item in alert_memory:
                            del alert_memory[symbol_item]

                # --- TÍNH TOÁN TIỀN TỆ (Thuế 0.1%, Phí ~0.15%) ---
                # Lưu ý: Giá trên web đang hiển thị theo đơn vị "Nghìn đồng" (Ví dụ: 35.0 = 35,000 VNĐ)
                gia_tri_mua = buy_p * vol * 1000
                phi_mua = gia_tri_mua * 0.0015
                
                gia_tri_ban = current_p * vol * 1000
                phi_ban = gia_tri_ban * 0.0015
                thue_ban = gia_tri_ban * 0.0010
                
                tong_thue_phi = phi_mua + phi_ban + thue_ban
                thuc_nhan = gia_tri_ban - phi_ban - thue_ban
                lai_lo_rong = thuc_nhan - (gia_tri_mua + phi_mua)

                # Lưu vào kho chi tiết
                portfolio_details[symbol_item] = {
                    "vol": vol, "buy_p": buy_p, "current_p": current_p,
                    "tong_thue_phi": tong_thue_phi, "thuc_nhan": thuc_nhan, "lai_lo_rong": lai_lo_rong
                }

                # Dữ liệu cho Bảng tổng quan
                final_list.append({
                    "Mã CP": symbol_item,
                    "Khối lượng": f"{int(vol):,}",
                    "Giá Mua": buy_p,
                    "Hiện tại": current_p,
                    "Lời/Lỗ (%)": f"{pnl_percent:.2f}%",
                    "Stoploss": row['stop'],
                    "Target": row['target']
                })

            st.write("**Bảng theo dõi tổng quan:**")
            st.dataframe(
                pd.DataFrame(final_list).style.map(
                    lambda x: 'color: red' if '-' in str(x) else 'color: green', 
                    subset=['Lời/Lỗ (%)']
                ),
                use_container_width=True, hide_index=True
            )
            
            # ==========================================
            # KHU VỰC BÓC TÁCH THUẾ PHÍ THEO TỪNG MÃ
            # ==========================================
            st.markdown("Phân tích Lãi/Lỗ Thực Nhận (Sau Thuế Phí)")
            list_ma = list(portfolio_details.keys())
            
            if list_ma:
                # Tạo thanh chọn mã CP
                selected_sym = st.selectbox("👉 Chọn mã CP trong danh mục để xem chi tiết:", list_ma)
                
                if selected_sym:
                    dt = portfolio_details[selected_sym]
                    if dt['vol'] == 0:
                        st.warning(f"Vui lòng nhập số lượng (volume) cho mã {selected_sym} vào Google Sheets để tính toán.")
                    else:
                        st.write(f"Đang phân tích: **{selected_sym}** (Đang nắm giữ: {int(dt['vol']):,} cổ phiếu)")
                        
                        # Hiển thị 4 cột Metric (Chỉ số) cực đẹp
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Vốn bỏ ra ban đầu", f"{int(dt['buy_p'] * dt['vol'] * 1000):,} đ")
                        c2.metric("Tổng Thuế & Phí (2 chiều)", f"-{int(dt['tong_thue_phi']):,} đ")
                        
                        # Đổi màu Lãi/Lỗ Ròng
                        if dt['lai_lo_rong'] >= 0:
                            c3.metric("LÃI RÒNG (Bỏ túi)", f"+{int(dt['lai_lo_rong']):,} đ", "Có Lời")
                        else:
                            c3.metric("LỖ RÒNG", f"{int(dt['lai_lo_rong']):,} đ", "-Lỗ")
                            
                        c4.metric("💰 TIỀN THỰC NHẬN", f"{int(dt['thuc_nhan']):,} đ")
                        
            st.info("💡 Lưu ý: Phí giao dịch đang tính trung bình 0.15% (cả chiều mua và bán). Thuế thu nhập 0.1% tính trên chiều bán.")
        else:
            st.warning("File Google Sheets của bạn đang trống dữ liệu.")
            
    except Exception as e:
        st.error(f"Lỗi kết nối Google Sheets: {e}")
        st.info("Vui lòng kiểm tra lại link Google Sheets và quyền chia sẻ.")
 
# ==============================
# 4. GIAO DIỆN CHỌN MÃ & CHẾ ĐỘ
# ==============================
st.subheader("Phân tích chi tiết Điểm Vào/Ra")
col_mode, col_sym = st.columns([1, 1])
with col_mode:
    mode = st.radio("Chọn chế độ giao dịch:", ["T+ Swing", "Intraday"], horizontal=True)
with col_sym:
    # Ô tìm kiếm hiển thị Mã + Tên Công Ty (Có Tooltip)
    symbol = st.selectbox(
        "🔍 Chọn mã cổ phiếu (Gõ chữ cái để lọc nhanh):", 
        ALL_SYMBOLS, 
        index=ALL_SYMBOLS.index("HPG") if "HPG" in ALL_SYMBOLS else 0,
        format_func=lambda x: f"{x} - {COMPANY_INFO.get(x, '')}",
        help="Công cụ tự động vẽ Biểu đồ, tính kháng cự hỗ trợ và vị thế đi tiền cho bạn."
    )
    # Tên công ty bôi đậm phía dưới
    st.caption(f"🏢 **{COMPANY_INFO.get(symbol, '')}**")

# ==============================
# 5. TẢI DỮ LIỆU & TÍNH CHỈ BÁO
# ==============================
@st.cache_data(ttl=60)
def load_chart_data(symbol, interval):
    return fetch_vn_data(symbol, interval, 60 if interval == "1d" else 15)

df = load_chart_data(symbol, "1d" if mode == "T+ Swing" else "15m")
if df is None or df.empty:
    st.error(f"❌ Không lấy được dữ liệu cho mã {symbol}.")
    st.stop()

df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()

tr = pd.concat([df["High"] - df["Low"], abs(df["High"] - df["Close"].shift()), abs(df["Low"] - df["Close"].shift())], axis=1).max(axis=1)
df["ATR"] = tr.rolling(14).mean()

delta = df['Close'].diff()
rs = (delta.where(delta > 0, 0)).rolling(14).mean() / (-delta.where(delta < 0, 0)).rolling(14).mean()
df['RSI'] = 100 - (100 / (1 + rs))

if mode == "Intraday":
    df['Date_Only'] = df.index.date
    df['VWAP'] = df.groupby('Date_Only').apply(lambda x: (x['Volume'] * (x['High'] + x['Low'] + x['Close']) / 3).cumsum() / x['Volume'].cumsum()).reset_index(level=0, drop=True)
else:
    df["VWAP"] = (df["Volume"] * (df["High"]+df["Low"]+df["Close"])/3).cumsum() / df["Volume"].cumsum()

df = df.dropna()
latest = df.iloc[-1]
entry, atr, current_rsi = float(latest["Close"]), float(latest["ATR"]), float(latest["RSI"])

# ==============================
# 6. QUẢN LÝ VỊ THẾ & ĐI TIỀN
# ==============================
if mode == "T+ Swing":
    stop = entry - ATR_MULTIPLIER * atr
    risk_per_share = entry - stop
    target = entry + (risk_per_share * RR_TARGET)
else:
    stop = float(df["Low"].rolling(10).min().iloc[-1])
    risk_per_share = entry - stop
    target = entry + (risk_per_share * 1.5)

risk_per_share = max(risk_per_share, 0.1)
shares = (int((ACCOUNT_SIZE * (RISK_PERCENT / 100)) / (risk_per_share * 1000)) // 100) * 100  

# ==============================
# 7. VẼ CHART & BẢNG KẾ HOẠCH
# ==============================
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, subplot_titles=(f'{symbol} - Giá', 'Khối lượng'), row_width=[0.2, 0.7])
fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Price"), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df["EMA20"], name="EMA20", line=dict(color='blue', width=1)), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df["EMA50"], name="EMA50", line=dict(color='orange', width=1)), row=1, col=1)
if mode == "Intraday": fig.add_trace(go.Scatter(x=df.index, y=df["VWAP"], name="VWAP", line=dict(color='purple', dash='dot')), row=1, col=1)
for y_val, c, txt in zip([entry, stop, target], ["gray", "red", "green"], ["Entry", "Stoploss", "Target"]): fig.add_hline(y=y_val, line_dash="dash", line_color=c, annotation_text=txt, row=1, col=1)
colors = ['green' if row['Close'] >= row['Open'] else 'red' for _, row in df.iterrows()]
fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name="Volume"), row=2, col=1)
fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
fig.update_layout(height=650, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20))
st.plotly_chart(fig, use_container_width=True)

st.subheader("Kế hoạch Giao dịch (Trading Plan)")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Giá Hiện Tại (Entry)", f"{entry:,.2f}")
c2.metric("Chốt Lời (Target)", f"{target:,.2f}", f"+{(target-entry)/entry*100:.1f}%")
c3.metric("Cắt Lỗ (Stop)", f"{stop:,.2f}", f"{(stop-entry)/entry*100:.1f}%")
c4.metric("RSI Hiện tại", f"{current_rsi:.1f}")

st.divider()
st.markdown("### Trợ lý phân tích")
if shares == 0: st.error("⚠️ **Cảnh báo:** Rủi ro quá lớn hoặc vốn không đủ mua 1 lô (100 cổ).")
else:
    if current_rsi > 70: st.warning(f"⚠️ **Cẩn thận:** RSI quá mua ({current_rsi:.1f}). Dễ đu đỉnh ngắn hạn.")
    elif current_rsi < 30: st.success(f"✅ **Tín hiệu:** RSI quá bán ({current_rsi:.1f}). Cân nhắc thăm dò.")
    elif entry > float(latest["EMA20"]) and float(latest["EMA20"]) > float(latest["EMA50"]): st.success("✅ **Xu hướng tốt:** Giá trên các EMA. Phe mua kiểm soát.")
    else: st.info("ℹ️ **Xu hướng trung lập/giảm:** Giá dưới trung bình động. Tránh bắt dao rơi.")

    ca, cb, cc = st.columns(3)
    ca.info(f"**Khối lượng mua:** {shares:,} cổ")
    cb.info(f"**Vốn cần có:** {round(shares * entry * 1000, 0):,} VNĐ")
    cc.info(f"**Rủi ro cắt lỗ:** {round((entry - stop) * shares * 1000, 0):,} VNĐ")
    
    # === NÚT GỬI KẾ HOẠCH THỦ CÔNG QUA TELEGRAM (CÓ THUẾ PHÍ) ===
    st.write("") # Tạo khoảng trống
    
    # 1. TÍNH TOÁN KỊCH BẢN THUẾ PHÍ (Dựa trên Phí 0.15%/chiều và Thuế 0.1% lúc bán)
    von_mua = shares * entry * 1000
    phi_mua = von_mua * 0.0015
    
    # Kịch bản Thắng (Chạm Target)
    von_ban_win = shares * target * 1000
    thue_phi_win = phi_mua + (von_ban_win * 0.0025) # Phí bán 0.15% + Thuế 0.1% = 0.25%
    lai_rong = (von_ban_win - von_mua) - thue_phi_win
    
    # Kịch bản Thua (Chạm Stoploss)
    von_ban_loss = shares * stop * 1000
    thue_phi_loss = phi_mua + (von_ban_loss * 0.0025)
    lo_rong = (von_mua - von_ban_loss) + thue_phi_loss

    # 2. HIỂN THỊ NÚT BẤM VÀ GỬI TELEGRAM
    if st.button(f"📲 Bắn Kế hoạch lệnh {symbol} qua Telegram", use_container_width=True):
        plan_msg = (
            f"🎯 [KẾ HOẠCH GIAO DỊCH: {symbol}]\n"
            f"🏢 {COMPANY_INFO.get(symbol, '')}\n"
            f"---------------------------\n"
            f"🟢 Điểm vào (Entry): {entry:,.2f}\n"
            f"🔴 Cắt lỗ (Stop): {stop:,.2f} ({((stop-entry)/entry)*100:.1f}%)\n"
            f"🍀 Chốt lời (Target): {target:,.2f} ({((target-entry)/entry)*100:.1f}%)\n"
            f"📊 Chỉ số RSI: {current_rsi:.1f}\n"
            f"---------------------------\n"
            f"📦 Đi tiền: Mua {shares:,} cổ (Vốn {von_mua:,.0f} đ)\n"
            f"💸 Ước tính Thuế/Phí: {thue_phi_win:,.0f} đ\n"
            f"💎 LÃI RÒNG (nếu Win): +{lai_rong:,.0f} đ\n"
            f"⚠️ LỖ RÒNG (nếu Fail): -{lo_rong:,.0f} đ"
        )
        send_telegram_alert(plan_msg)
        st.toast(f"✅ Đã gửi kế hoạch {symbol} vào Telegram của bạn!", icon="🚀")





















