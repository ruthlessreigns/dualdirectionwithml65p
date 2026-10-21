import streamlit as st
import pandas as pd
import requests
import datetime
import os

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="XAUUSD Institutional Sniper Dashboard",
    page_icon="🎯",
    layout="wide"
)

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stButton>button { width: 100%; background-color: #ff4b4b; color: white; font-weight: bold; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# SIDEBAR: TELEGRAM & MT5 SETTINGS
# ==========================================
st.sidebar.markdown("### 🔑 Telegram & MT5 Settings")
telegram_token = st.sidebar.text_input("Telegram Bot Token", value="8861143878:AAGo0rx1OIPBXc_z_3xlqP8AF-GM_kml0TA", type="password")
telegram_chat_id = st.sidebar.text_input("Telegram Chat ID", value="6611581565")
mt5_symbol = st.sidebar.selectbox("MT5 Symbol Name", ["XAUUSD", "XAUUSDm", "GOLD"], index=0)

def send_telegram_message(token, chat_id, message):
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        return False

# ==========================================
# STEP 1: FETCH REAL DATA FROM MT5
# ==========================================
st.markdown("## 📊 Step 1: Fetch Real Data from MT5 & Parameter Inputs")

# Session state initialization for data storage
if 'fetched_price' not in st.session_state:
    st.session_state['fetched_price'] = 2720.50
    st.session_state['ob_mid'] = 2718.20
    st.session_state['h1_high'] = 2735.00
    st.session_state['h1_low'] = 2705.00
    st.session_state['m5_high'] = 2722.00
    st.session_state['m5_low'] = 2716.80
    st.session_state['trend'] = "BULLISH"

# MT5 Data Fetching Button
if st.button("🔄 FETCH REAL DATA FROM MT5"):
    mt5_success = False
    try:
        import MetaTrader5 as mt5
        if mt5.initialize():
            rates = mt5.copy_rates_from_pos(mt5_symbol, mt5.TIMEFRAME_M30, 0, 50)
            rates_h1 = mt5.copy_rates_from_pos(mt5_symbol, mt5.TIMEFRAME_H1, 0, 20)
            rates_h4 = mt5.copy_rates_from_pos(mt5_symbol, mt5.TIMEFRAME_H4, 0, 10)
            mt5.shutdown()
            
            if rates is not None and len(rates) > 0:
                df = pd.DataFrame(rates)
                st.session_state['fetched_price'] = float(df.iloc[-1]['close'])
                st.session_state['m5_high'] = float(df.iloc[-1]['high'])
                st.session_state['m5_low'] = float(df.iloc[-1]['low'])
                st.session_state['ob_mid'] = float((df.iloc[-2]['high'] + df.iloc[-2]['low']) / 2)
                
                if rates_h1 is not None and len(rates_h1) > 0:
                    df_h1 = pd.DataFrame(rates_h1)
                    st.session_state['h1_high'] = float(df_h1['high'].max())
                    st.session_state['h1_low'] = float(df_h1['low'].min())
                
                if rates_h4 is not None and len(rates_h4) > 0:
                    df_h4 = pd.DataFrame(rates_h4)
                    st.session_state['trend'] = "BULLISH" if df_h4.iloc[-1]['close'] > df_h4.iloc[-5]['close'] else "BEARISH"
                
                mt5_success = True
    except Exception as e:
        mt5_success = False

    if mt5_success:
        st.success(f"Successfully fetched live market data for {mt5_symbol} from MT5 terminal!")
    else:
        st.warning("⚠️ MT5 Terminal could not be connected (Streamlit Cloud cannot run local MT5). Using fallback/default values. (For true MT5 live data, run this script locally on your PC with MT5 open).")

# Input boxes reflecting fetched data or manual input
col1, col2 = st.columns(2)

with col1:
    current_gold_price = st.number_input("Current Gold Price ($)", value=st.session_state['fetched_price'], format="%.2f")
    h4_macro_trend = st.selectbox("H4 Macro Trend", ["BULLISH", "BEARISH"], index=0 if st.session_state['trend']=="BULLISH" else 1)
    h1_structure_high = st.number_input("H1 Structure High ($)", value=st.session_state['h1_high'], format="%.2f")
    h1_structure_low = st.number_input("H1 Structure Low ($)", value=st.session_state['h1_low'], format="%.2f")

with col2:
    m15_ob_mid = st.number_input("M15 Order Block Mid ($)", value=st.session_state['ob_mid'], format="%.2f")
    m5_candle_high = st.number_input("M5 Trigger Candle High ($)", value=st.session_state['m5_high'], format="%.2f")
    m5_candle_low = st.number_input("M5 Trigger Candle Low ($)", value=st.session_state['m5_low'], format="%.2f")
    volume_spike = st.checkbox("Volume Spike Confirmed (>110%)?", value=True)

st.markdown("---")

# ==========================================
# STEP 2: CALCULATE & DISPATCH SIGNAL
# ==========================================
st.markdown("## 🚀 Step 2: Calculate & Dispatch Telegram Signal")

if st.button("⚙️ CALCULATE & TRIGGER TELEGRAM SIGNAL"):
    is_valid_buy = (h4_macro_trend == "BULLISH") and (current_gold_price <= h1_structure_high) and volume_spike
    
    if is_valid_buy:
        signal_msg = f"""
🎯 <b>XAUUSD SNIPER SIGNAL DISPATCHED!</b>
==================================
<b>Current Price:</b> ${current_gold_price}
<b>Order Block Mid:</b> ${m15_ob_mid}
<b>Trend:</b> {h4_macro_trend}
<b>Status:</b> HIGH PROBABILITY BUY SETUP 🟢
==================================
"""
        st.success(f"HIGH PROBABILITY SETUP CONFIRMED! (Price: ${current_gold_price})")
        success = send_telegram_message(telegram_token, telegram_chat_id, signal_msg)
        if success:
            st.info("📱 'BUY SIGNAL' status update successfully dispatched to your Telegram.")
        else:
            st.error("Failed to send message to Telegram. Check your Token & Chat ID.")
    else:
        warning_msg = f"⚠️ <b>NO TRADE ZONE</b> - High probability confluence rules not fully met. (Price: ${current_gold_price})"
        st.warning(f"NO TRADE ZONE - High probability confluence rules not fully met. (Price: ${current_gold_price})")
        success = send_telegram_message(telegram_token, telegram_chat_id, warning_msg)
        if success:
            st.info("📱 'NO TRADE' status update dispatched to your Telegram.")
