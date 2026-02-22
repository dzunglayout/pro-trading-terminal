import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta
import yfinance as yf

# ==============================
# 1. CẤU HÌNH BAN ĐẦU
# ==============================
st.set_page_config(page_title="Pro Trading Terminal", layout="wide")
# st.title("🚀 PRO TRADING TERMINAL – T+ & INTRADAY")

# Đặt nút bên góc phải giao diện
col_title, col_btn = st.columns([4, 1])
with col_title:
    st.title("🚀 PRO TRADING TERMINAL – T+ & INTRADAY")
with col_btn:
    st.write("") # Căn chỉnh cho đẹp
    if st.button("🔄 Làm mới dữ liệu", use_container_width=True):
        st.cache_data.clear() # Xóa bộ nhớ tạm để ép tải lại data mới nhất
        st.rerun() # Lệnh Streamlit tự động tải lại trang

ACCOUNT_SIZE = 100_000_000  # Vốn 100 triệu VNĐ
RISK_PERCENT = 1            # Rủi ro 1%
ATR_MULTIPLIER = 1.5
RR_TARGET = 2

WATCHLIST = ["HPG", "VIX", "SSI", "SHB", "MBB", "VND", "DIG", "NVL", "STB", "MWG"]

# ==============================
# 2. HÀM LẤY DỮ LIỆU "BẤT TỬ TỨ TRỤ" (4 LỚP FALLBACK)
# ==============================
def fetch_vn_data(symbol, interval, days_back):
    res_map = {"1d": "1D", "15m": "15"}
    r = res_map.get(interval, "1D")
    
    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=days_back)).timestamp())
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    # LỚP 1: THỬ VNDIRECT
    try:
        url_vnd = f"https://dchart-api.vndirect.com.vn/dchart/history?symbol={symbol}&resolution={r}&from={start_ts}&to={end_ts}"
        res = requests.get(url_vnd, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get('s') == 'ok' and 't' in data:
                df = pd.DataFrame({
                    'Date': pd.to_datetime(data['t'], unit='s') + pd.Timedelta(hours=7),
                    'Open': data['o'], 'High': data['h'], 'Low': data['l'], 'Close': data['c'], 'Volume': data['v']
                })
                df.set_index('Date', inplace=True)
                if not df.empty and df['Close'].iloc[-1] > 1000:
                    df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']] / 1000
                return df.dropna()
    except: pass

    # LỚP 2: THỬ DNSE
    try:
        url_dnse = f"https://services.entrade.com.vn/chart-api/chart?symbol={symbol}&resolution={r}&from={start_ts}&to={end_ts}"
        res = requests.get(url_dnse, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get('s') == 'ok' and 't' in data:
                df = pd.DataFrame({
                    'Date': pd.to_datetime(data['t'], unit='s') + pd.Timedelta(hours=7),
                    'Open': data['o'], 'High': data['h'], 'Low': data['l'], 'Close': data['c'], 'Volume': data['v']
                })
                df.set_index('Date', inplace=True)
                if not df.empty and df['Close'].iloc[-1] > 1000:
                    df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']] / 1000
                return df.dropna()
    except: pass

    # LỚP 3: THỬ TCBS
    try:
        r_tcbs = "D" if interval == "1d" else "15"
        url_tcbs = f"https://apipubaws.tcbs.com.vn/stock-insight/v1/stock/bars-long-term?ticker={symbol}&type=stock&resolution={r_tcbs}&from={start_ts}&to={end_ts}"
        res = requests.get(url_tcbs, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if 'data' in data and len(data['data']) > 0:
                df = pd.DataFrame(data['data'])
                df['Date'] = pd.to_datetime(df['tradingDate'])
                df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
                df.set_index('Date', inplace=True)
                if not df.empty and df['Close'].iloc[-1] > 1000:
                    df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']] / 1000
                return df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    except: pass

    # LỚP 4: THỬ YAHOO FINANCE (PHAO CỨU SINH CUỐI CÙNG)
    try:
        yf_sym = f"{symbol}.VN"
        yf_interval = "1d" if interval == "1d" else "15m"
        # Yahoo chỉ cho phép lấy max 60 ngày với nến 15m
        yf_period = f"{min(days_back, 60)}d" 
        
        df_yf = yf.download(yf_sym, period=yf_period, interval=yf_interval, progress=False)
        if not df_yf.empty:
            if isinstance(df_yf.columns, pd.MultiIndex):
                df_yf.columns = [col[0] for col in df_yf.columns]
            req_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            if all(c in df_yf.columns for c in req_cols):
                return df_yf[req_cols].dropna()
    except: pass

    return pd.DataFrame()

# ==============================
# 3. BỘ LỌC CỔ PHIẾU NÓNG (INTRADAY SCANNER)
# ==============================
st.markdown("---")
with st.expander("🔥 TÌM KIẾM CỔ PHIẾU NÓNG CHO LƯỚT SÓNG (Mở rộng để xem)", expanded=True):
    st.write("🤖 **Trợ lý:** Đang quét hệ thống đa tầng (VNDirect -> DNSE -> TCBS -> Yahoo)...")
    
    @st.cache_data(ttl=120)
    def scan_hot_stocks():
        results = []
        error_logs = []
        
        for sym in WATCHLIST:
            df_scan = fetch_vn_data(sym, "1d", 15) 
            
            if df_scan.empty: 
                error_logs.append(f"{sym}: Lỗi kết nối toàn bộ 4 máy chủ.")
                continue
                
            try:
                avg_vol = df_scan['Volume'].mean()
                df_scan['Volatility'] = (df_scan['High'] - df_scan['Low']) / df_scan['Low'] * 100
                avg_volatility = df_scan['Volatility'].mean()
                
                last_close = float(df_scan['Close'].iloc[-1])
                last_vol = float(df_scan['Volume'].iloc[-1])
                
                results.append({
                    "Mã CP": sym,
                    "Giá Hiện Tại": round(last_close, 2),
                    "Biên độ dao động (%)": round(float(avg_volatility), 2),
                    "Thanh khoản TB (Cổ)": int(avg_vol),
                    "Đột biến Volume": round(last_vol / avg_vol, 1) if avg_vol > 0 else 0
                })
            except Exception as e:
                error_logs.append(f"{sym}: Lỗi tính toán - {str(e)}")
                continue
                
        df_res = pd.DataFrame(results)
        if not df_res.empty:
            df_res = df_res.sort_values(by=["Biên độ dao động (%)", "Thanh khoản TB (Cổ)"], ascending=[False, False])
            
        return df_res.head(5), error_logs 

    top_stocks, errors = scan_hot_stocks()
    
    if not top_stocks.empty:
        # Đã gỡ bỏ tính năng tô màu (.background_gradient) để không cần cài thêm matplotlib
        st.dataframe(
            top_stocks.style.format({
                "Giá Hiện Tại": "{:,.2f}",
                "Biên độ dao động (%)": "{:.2f}%",
                "Thanh khoản TB (Cổ)": "{:,}",
                "Đột biến Volume": "x{:.1f}"
            }),
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown("### 💡 Khuyến nghị:")
        best_volatility = top_stocks.iloc[0]
        best_volume = top_stocks.sort_values(by="Thanh khoản TB (Cổ)", ascending=False).iloc[0]
        
        st.success(f"⚡ **Mã lướt biên lớn nhất:** **{best_volatility['Mã CP']}** (Biên độ trung bình **{best_volatility['Biên độ dao động (%)']}%**/ngày). Phù hợp mua đỏ bán xanh (T+0).")
        st.info(f"🌊 **Mã thanh khoản cao:** **{best_volume['Mã CP']}** (Khối lượng TB **{best_volume['Thanh khoản TB (Cổ)']:,}** cổ). Thích hợp đi tiền lớn.")
    else:
        st.error("❌ Đang lỗi kết nối dữ liệu ở tất cả các máy chủ.")
        if errors: 
            st.code("\n".join(errors))

st.markdown("---")

# ==============================
# 4. GIAO DIỆN CHỌN MÃ & CHẾ ĐỘ (CÓ THANH TÌM KIẾM THÔNG MINH)
# ==============================
st.subheader("🎯 Phân tích chi tiết Điểm Vào/Ra")

# Danh sách các mã cổ phiếu phổ biến, thanh khoản cao trên 3 sàn (VN30, HNX30, Midcap...)
# Bạn có thể tự do thêm bớt các mã mình thích vào danh sách này
ALL_SYMBOLS = [
    "HPG", "HSG", "NKG", "SMC", "VGS", # Thép
    "SSI", "VND", "VIX", "SHS", "MBS", "HCM", "VCI", "FTS", "CTS", "BSI", # Chứng khoán
    "SHB", "MBB", "STB", "VPB", "TCB", "CTG", "VCB", "BID", "ACB", "TPB", "HDB", "VIB", "EIB", "MSB", "LPB", # Ngân hàng
    "DIG", "NVL", "PDR", "DXG", "CEO", "KBC", "IDC", "VGC", "NLG", "KDH", "VIC", "VHM", "VRE", "TCH", "HDG", # Bất động sản
    "FPT", "MWG", "PNJ", "DGW", "FRT", "PET", # Bán lẻ & Công nghệ
    "DGC", "DCM", "DPM", "CSV", # Hóa chất & Phân bón
    "VHC", "ANV", "IDI", "ASM", # Thủy sản
    "HAH", "GMD", "PVT", "VOS", # Cảng biển & Vận tải
    "GAS", "PVS", "PVD", "BSR", "PLX", "POW", "PC1", "NT2", "GEG", # Dầu khí & Năng lượng
    "LCG", "HHV", "VCG", "C4G", "FCN", "KSB", "HUT", # Đầu tư công
    "VNM", "SAB", "MSN", "MCH", "DBC", "BFB", "HAG", "HGND" # Thực phẩm, Nông nghiệp
]

# Sắp xếp danh sách theo bảng chữ cái A-Z để người dùng dễ nhìn
ALL_SYMBOLS.sort()

col_mode, col_sym = st.columns([1, 1])
with col_mode:
    mode = st.radio("Chọn chế độ giao dịch:", ["T+ Swing", "Intraday"], horizontal=True)
with col_sym:
    # Dùng st.selectbox thay thế cho st.text_input
    # index=ALL_SYMBOLS.index("HPG") giúp ô hiển thị mặc định mã HPG lúc mới mở web
    symbol = st.selectbox("🔍 Chọn hoặc gõ tìm mã cổ phiếu:", ALL_SYMBOLS, index=ALL_SYMBOLS.index("HPG"))

# ==============================
# 5. TẢI DỮ LIỆU CHO CHART
# ==============================
@st.cache_data(ttl=60)
def load_chart_data(symbol, interval):
    days = 60 if interval == "1d" else 15
    return fetch_vn_data(symbol, interval, days)

interval = "1d" if mode == "T+ Swing" else "15m"
df = load_chart_data(symbol, interval)

if df is None or df.empty:
    st.error(f"❌ Không lấy được dữ liệu cho mã {symbol}. Hệ thống đều từ chối kết nối.")
    st.stop()

# ==============================
# 6. TÍNH TOÁN CÁC CHỈ BÁO
# ==============================
df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()

tr = pd.concat([
    df["High"] - df["Low"],
    abs(df["High"] - df["Close"].shift()),
    abs(df["Low"] - df["Close"].shift())
], axis=1).max(axis=1)
df["ATR"] = tr.rolling(14).mean()

delta = df['Close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df['RSI'] = 100 - (100 / (1 + rs))

if mode == "Intraday":
    df['Date_Only'] = df.index.date
    df['VWAP'] = df.groupby('Date_Only').apply(
        lambda x: (x['Volume'] * (x['High'] + x['Low'] + x['Close']) / 3).cumsum() / x['Volume'].cumsum()
    ).reset_index(level=0, drop=True)
else:
    df["VWAP"] = (df["Volume"] * (df["High"]+df["Low"]+df["Close"])/3).cumsum() / df["Volume"].cumsum()

df = df.dropna()

latest = df.iloc[-1]
entry = float(latest["Close"])
atr = float(latest["ATR"])
current_rsi = float(latest["RSI"])

# ==============================
# 7. LOGIC ĐIỂM VÀO/RA
# ==============================
if mode == "T+ Swing":
    stop = entry - ATR_MULTIPLIER * atr
    risk_per_share = entry - stop
    target = entry + (risk_per_share * RR_TARGET)
else:
    stop = float(df["Low"].rolling(10).min().iloc[-1])
    risk_per_share = entry - stop
    target = entry + (risk_per_share * 1.5)

if risk_per_share <= 0: risk_per_share = 0.1 

# ==============================
# 8. QUẢN LÝ VỊ THẾ
# ==============================
risk_amount = ACCOUNT_SIZE * (RISK_PERCENT / 100)
raw_shares = int(risk_amount / (risk_per_share * 1000))
shares = (raw_shares // 100) * 100  

# ==============================
# 9. VẼ BIỂU ĐỒ CHUYÊN NGHIỆP CÓ VOLUME
# ==============================
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.03, subplot_titles=(f'{symbol} - Giá', 'Khối lượng (Volume)'), 
                    row_width=[0.2, 0.7])

fig.add_trace(go.Candlestick(
    x=df.index, open=df["Open"], high=df["High"],
    low=df["Low"], close=df["Close"], name="Price"
), row=1, col=1)

fig.add_trace(go.Scatter(x=df.index, y=df["EMA20"], name="EMA20", line=dict(color='blue', width=1)), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df["EMA50"], name="EMA50", line=dict(color='orange', width=1)), row=1, col=1)

if mode == "Intraday":
    fig.add_trace(go.Scatter(x=df.index, y=df["VWAP"], name="VWAP", line=dict(color='purple', dash='dot')), row=1, col=1)

fig.add_hline(y=entry, line_dash="solid", line_color="gray", annotation_text="Entry", row=1, col=1)
fig.add_hline(y=stop, line_dash="dash", line_color="red", annotation_text="Stoploss", row=1, col=1)
fig.add_hline(y=target, line_dash="dash", line_color="green", annotation_text="Target", row=1, col=1)

colors = ['green' if row['Close'] >= row['Open'] else 'red' for index, row in df.iterrows()]
fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name="Volume"), row=2, col=1)

fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
fig.update_layout(height=650, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20))
st.plotly_chart(fig, use_container_width=True)

# ==============================
# 10. BẢNG THÔNG SỐ VÀ LỜI KHUYÊN
# ==============================
st.subheader("💡 Kế hoạch Giao dịch (Trading Plan)")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Giá Hiện Tại (Entry)", f"{entry:,.2f}")
col2.metric("Chốt Lời (Target)", f"{target:,.2f}", f"+{(target-entry)/entry*100:.1f}%")
col3.metric("Cắt Lỗ (Stop)", f"{stop:,.2f}", f"{(stop-entry)/entry*100:.1f}%")
col4.metric("RSI Hiện tại", f"{current_rsi:.1f}")

st.divider()

st.markdown("### 🤖 Trợ lý phân tích")
if shares == 0:
    st.error("⚠️ **Cảnh báo:** Rủi ro lệnh quá lớn hoặc số vốn không đủ mua 1 lô (100 cổ). Hãy chọn mã khác hoặc tăng % rủi ro.")
else:
    if current_rsi > 70:
        st.warning(f"⚠️ **Cẩn thận:** RSI đang ở mức quá mua ({current_rsi:.1f}). Dễ xảy ra đu đỉnh ngắn hạn, không nên fomo lúc này.")
    elif current_rsi < 30:
        st.success(f"✅ **Tín hiệu:** RSI đang ở mức quá bán ({current_rsi:.1f}). Cân nhắc thăm dò vị thế vì giá đã chiết khấu.")
    elif entry > float(latest["EMA20"]) and float(latest["EMA20"]) > float(latest["EMA50"]):
        st.success("✅ **Xu hướng tốt:** Giá đang nằm trên các đường Trung bình động (EMA20 > EMA50). Phe mua đang kiểm soát.")
    else:
        st.info("ℹ️ **Xu hướng trung lập/giảm:** Giá nằm dưới trung bình động. Tránh bắt dao rơi, chỉ mua nếu test hỗ trợ thành công.")

    st.markdown("### 💼 Lệnh đề xuất thực tế (Thực thi)")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.info(f"**Khối lượng mua:** {shares:,} cổ")
    with col_b:
        st.info(f"**Vốn cần có:** {round(shares * entry * 1000, 0):,} VNĐ")
    with col_c:
        st.info(f"**Rủi ro cắt lỗ:** {round((entry - stop) * shares * 1000, 0):,} VNĐ")