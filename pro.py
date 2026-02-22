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
st.title("🚀 PRO TRADING TERMINAL – T+ & INTRADAY")

# TẠO 2 CỘT: 1 CỘT HIỂN THỊ CHỮ, 1 CỘT CHỨA NÚT BẬT/TẮT
col_info, col_toggle = st.columns([2, 1])
    
with col_info:
        st.write("🤖 **Trợ lý:** Đang quét hệ thống đa tầng...")
        
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
    # !!! BẠN HÃY THAY 2 DÒNG DƯỚI ĐÂY BẰNG TOKEN VÀ ID CỦA BẠN !!!
    bot_token = "8563387783:AAEh9DwH_iTHYsF7TihlsgKR4BmnMZfRVYI"
    bot_chatID = "1972517879"
    
    if bot_token == "ĐIỀN_TOKEN_CỦA_BẠN_VÀO_ĐÂY": return # Bỏ qua nếu chưa điền
    
    send_text = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={bot_chatID}&parse_mode=Markdown&text={message}"
    try: requests.get(send_text, timeout=5)
    except: pass

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
            df_scan = fetch_vn_data(sym, "1d", 15) 
            if df_scan.empty: continue
            try:
                avg_vol = df_scan['Volume'].mean()
                df_scan['Volatility'] = (df_scan['High'] - df_scan['Low']) / df_scan['Low'] * 100
                results.append({
                    "Mã CP": sym,
                    "Giá Hiện Tại": round(float(df_scan['Close'].iloc[-1]), 2),
                    "Biên độ (%)": round(float(df_scan['Volatility'].mean()), 2),
                    "Thanh khoản TB": int(avg_vol),
                    "Volume Đột biến": round(float(df_scan['Volume'].iloc[-1] / avg_vol), 1) if avg_vol > 0 else 0
                })
            except: continue
        df_res = pd.DataFrame(results)
        if not df_res.empty: df_res = df_res.sort_values(by=["Biên độ (%)", "Thanh khoản TB"], ascending=[False, False])
        return df_res.head(5)

    top_stocks = scan_hot_stocks()
    
    if not top_stocks.empty:
        st.dataframe(top_stocks.style.format({
            "Giá Hiện Tại": "{:,.2f}", 
            "Biên độ (%)": "{:.2f}%", 
            "Thanh khoản TB": "{:,}", 
            "Volume Đột biến": "x{:.1f}"
        }), use_container_width=True, hide_index=True)
        
        best = top_stocks.iloc[0]
        st.success(f"⚡ **Mã lướt biên lớn nhất:** **{best['Mã CP']}** (Biên độ TB **{best['Biên độ (%)']}%**/ngày).")
        
        # LOGIC TELEGRAM THÔNG MINH
        if auto_alert:
            # Khởi tạo bộ nhớ tạm để tránh trùng mã
            if "last_reported_stock" not in st.session_state:
                st.session_state["last_reported_stock"] = ""

            # Chỉ gửi nếu đạt biên độ và là mã MỚI so với lần báo trước
            if float(best['Biên độ (%)']) >= 3.0:
                if best['Mã CP'] != st.session_state["last_reported_stock"]:
                    msg = (
                        f"🚀 [PRO TERMINAL - PHÁT HIỆN SIÊU PHẨM]\n"
                        f"Mã dẫn đầu danh sách: *{best['Mã CP']}*\n"
                        f"- Biên độ dao động: {best['Biên độ (%)']}%\n"
                        f"- Volume đột biến: {best['Volume Đột biến']}x\n"
                        f"👉 Mời sếp vào kiểm tra biểu đồ chi tiết!"
                    )
                    send_telegram_alert(msg)
                    st.session_state["last_reported_stock"] = best['Mã CP']
                    st.toast(f"Đã báo mã {best['Mã CP']} qua Telegram", icon="🔔")
        else:
            st.info("🔕 Chế độ im lặng đang bật. Bot sẽ không tự động nhắn tin.")
    else:
        st.error("❌ Đang lỗi kết nối dữ liệu ở tất cả các máy chủ.")
st.markdown("---")

# ==============================
# 4. GIAO DIỆN CHỌN MÃ & CHẾ ĐỘ
# ==============================
st.subheader("🎯 Phân tích chi tiết Điểm Vào/Ra")
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

st.subheader("💡 Kế hoạch Giao dịch (Trading Plan)")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Giá Hiện Tại (Entry)", f"{entry:,.2f}")
c2.metric("Chốt Lời (Target)", f"{target:,.2f}", f"+{(target-entry)/entry*100:.1f}%")
c3.metric("Cắt Lỗ (Stop)", f"{stop:,.2f}", f"{(stop-entry)/entry*100:.1f}%")
c4.metric("RSI Hiện tại", f"{current_rsi:.1f}")

st.divider()
st.markdown("### 🤖 Trợ lý phân tích")
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
    # === NÚT GỬI KẾ HOẠCH THỦ CÔNG QUA TELEGRAM ===
    st.write("") # Tạo khoảng trống
    if st.button(f"📲 Bắn Kế hoạch lệnh {symbol} qua Telegram", use_container_width=True):
        plan_msg = (
            f"🎯 [KẾ HOẠCH GIAO DỊCH: {symbol}]\n"
            f"🏢 {COMPANY_INFO.get(symbol, '')}\n"
            f"---------------------------\n"
            f"🟢 Điểm vào (Entry): {entry:,.2f}\n"
            f"🔴 Cắt lỗ (Stop): {stop:,.2f} ({((stop-entry)/entry)*100:.1f}%)\n"
            f"🍀 Chốt lời (Target): {target:,.2f} ({((target-entry)/entry)*100:.1f}%)\n"
            f"📊 Chỉ số RSI: {current_rsi:.1f}\n"
            f"📦 Đi tiền: Mua {shares:,} cổ (Vốn {round(shares * entry * 1000, 0):,} VNĐ)\n"
            f"⚠️ Rủi ro tối đa: {round((entry - stop) * shares * 1000, 0):,} VNĐ"
        )
        send_telegram_alert(plan_msg)

        st.toast(f"✅ Đã gửi kế hoạch {symbol} vào Telegram của bạn!", icon="🚀")


