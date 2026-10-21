import streamlit as st
import pandas as pd
import requests
import datetime
import os
import json

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="XAUUSD Institutional Sniper Dashboard",
    page_icon="🎯",
    layout="wide"
)

# Custom Styling to match the professional layout
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stButton>button { width: 100%; background-color: #ff4b4b; color: white; font-weight: bold; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# SIDEBAR: TELEGRAM SETTINGS
# ==========================================
st.sidebar.markdown("### 🔑 Your Telegram Settings")
st.sidebar.markdown("Provide your Telegram Bot parameters below:")

telegram_token = st.sidebar.text_input("Telegram Bot Token", value="8861143878:AAGo0rx1OIPBXc_z_3xlqP8AF-GM_kml0TA", type="password")
telegram_chat_id = st.sidebar.text_input("Telegram Chat ID", value="6611581565")

# Telegram Sender Function
def send_telegram_message(token, chat_id, message):
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram Error: {e}")
        return False

# ==========================================
# MAIN DASHBOARD CONTENT
# ==========================================
st.markdown("## 📊 Step 1: Input Chart Parameters from MT5")

# Two-column layout for parameters matching the image
col1, col2 = st.columns(2)

with col1:
    current_gold_price = st.number_input("Current Gold Price ($)", value=2720.50, format="%.2f")
    h4_macro_trend = st.selectbox("H4 Macro Trend", ["BULLISH", "BEARISH"], index=0)
    h1_structure_high = st.number_input("H1 Structure High ($)", value=2735.00, format="%.2f")
    h1_structure_low = st.number_input("H1 Structure Low ($)", value=2705.00, format="%.2f")

with col2:
    m15_ob_mid = st.number_input("M15 Order Block Mid ($)", value=2718.20, format="%.2f")
    m5_candle_high = st.number_input("M5 Trigger Candle High ($)", value=2722.00, format="%.2f")
    m5_candle_low = st.number_input("M5 Trigger Candle Low ($)", value=2716.80, format="%.2f")
    volume_spike = st.checkbox("Volume Spike Confirmed (>110%)?", value=True)

st.markdown("---")

st.markdown("## 🚀 Step 2: Calculate & Dispatch Telegram Signal")

# Trigger Button
if st.button("⚙️ CALCULATE & TRIGGER TELEGRAM SIGNAL"):
    # Confluence / Strategy Logic
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
        
        # Send to Telegram
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
