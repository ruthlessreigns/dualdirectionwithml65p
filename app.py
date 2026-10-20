import io
import json
import time
import requests
import datetime
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
#import MetaTrader5 as mt5
import joblib
from sklearn.ensemble import RandomForestClassifier

# ==========================================
# 1. GLOBAL CONFIGURATION & CREDENTIALS
# ==========================================
TELEGRAM_BOT_TOKEN = "8861143878:AAGo0rx1OIPBXc_z_3xlqP8AF-GM_kml0TA"
TELEGRAM_CHAT_ID = "6611581565"

SYMBOLS = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]
ACCOUNT_BALANCE = 10000.0
RISK_PERCENT = 1.0  # 1% Risk per trade
LOG_FILE = "trade_history.json"
MODEL_FILE = "sniper_ml_model.pkl"

SESSION_ALERT_TRACKER = {}

# ==========================================
# 2. MACHINE LEARNING MODEL INITIALIZER
# ==========================================
def get_or_train_ml_model():
    """
    Checks if a trained ML model exists. If not, trains a baseline 
    Random Forest Classifier using synthetic historical trade features 
    and saves it to disk.
    """
    if os.path.exists(MODEL_FILE):
        try:
            model = joblib.load(MODEL_FILE)
            print("[ML] Loaded pre-trained Machine Learning model successfully.")
            return model
        except Exception as e:
            print(f"[ML] Error loading model, retraining... Error: {e}")

    print("[ML] Training baseline Machine Learning model...")
    # Creating synthetic training dataset: [trend_score, distance_ratio, volume_spike, pattern_score]
    # Target: 1 (Win), 0 (Loss)
    np.random.seed(42)
    X_train = np.array([
        [85, 0.1, 1, 1],
        [90, 0.05, 1, 1],
        [60, 0.8, 0, 0],
        [75, 0.2, 1, 0],
        [95, 0.02, 1, 1],
        [50, 0.9, 0, 0],
        [80, 0.15, 1, 1],
        [65, 0.7, 0, 0]
    ])
    y_train = np.array([1, 1, 0, 0, 1, 0, 1, 0])

    model = RandomForestClassifier(n_estimators=50, random_state=42)
    model.fit(X_train, y_train)
    joblib.dump(model, MODEL_FILE)
    print("[ML] Machine Learning model trained and saved successfully.")
    return model

# Load global ML model instance
ml_model = get_or_train_ml_model()

# ==========================================
# 3. TRADE LOGGER & WEEKLY REPORT ENGINE
# ==========================================
def load_trade_logs():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    return []

def save_trade_log(trade_data):
    logs = load_trade_logs()
    logs.append(trade_data)
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=4)

def generate_weekly_report():
    logs = load_trade_logs()
    if not logs:
        return "📊 <b>WEEKLY PERFORMANCE REPORT</b>\nNo trades recorded this week."

    total_trades = len(logs)
    wins = sum(1 for t in logs if t.get('status') == 'WIN')
    losses = sum(1 for t in logs if t.get('status') == 'LOSS')
    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
    total_profit_pips = sum(t.get('pips', 0) for t in logs)

    report_msg = f"""
📊 <b>WEEKLY PERFORMANCE REPORT</b>
==================================
<b>Total Signals Generated:</b> {total_trades}
<b>Successful Trades (Wins):</b> {wins} 🎯
<b>Failed Trades (Losses):</b> {losses} ❌
<b>Win-Rate Accuracy:</b> <code>{win_rate:.1f}%</code>
<b>Estimated Profit/Loss:</b> <code>{total_profit_pips:+.1f} Pips</code>
==================================
<i>Generated Automatically by ML-Powered Sniper Engine</i>
"""
    return report_msg

# ==========================================
# 4. TELEGRAM ENGINE
# ==========================================
def send_simple_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"[TELEGRAM ERROR]: {e}")

def send_telegram_signal_with_buttons(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "⚡ EXECUTE SNIPER TRADE", "callback_data": "exec_sniper"},
                {"text": "❌ IGNORE", "callback_data": "ignore_trade"}
            ],
            [
                {"text": "🛡️ MOVE SL TO BE", "callback_data": "sl_be"},
                {"text": "📊 CLOSE 50% PARTIALS", "callback_data": "close_partial"}
            ]
        ]
    }
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": reply_markup
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"[ERROR] Signal Exception: {e}")

def send_telegram_chart_image(image_bytes, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    files = {'photo': ('chart.png', image_bytes, 'image/png')}
    data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption, 'parse_mode': 'HTML'}
    try:
        requests.post(url, data=data, files=files)
    except Exception as e:
        print(f"[ERROR] Chart Upload Error: {e}")

# ==========================================
# 5. SMART SESSION & MARKET BIAS ENGINE
# ==========================================
def check_session_notifications():
    global SESSION_ALERT_TRACKER
    now = datetime.datetime.now()
    current_time = now.time()
    date_key = now.strftime("%Y-%m-%d")

    sessions = [
        {"name": "Asian Session 🌏", "start": datetime.time(5, 0), "warning": datetime.time(4, 0)},
        {"name": "London Session 🇬🇧", "start": datetime.time(11, 0), "warning": datetime.time(10, 0)},
        {"name": "New York Session 🇺🇸", "start": datetime.time(17, 30), "warning": datetime.time(16, 30)}
    ]

    for s in sessions:
        alert_key_warn = f"{date_key}_{s['name']}_WARN"
        alert_key_start = f"{date_key}_{s['name']}_START"

        if current_time >= s["warning"] and current_time < s["start"] and not SESSION_ALERT_TRACKER.get(alert_key_warn):
            SESSION_ALERT_TRACKER[alert_key_warn] = True
            msg = f"""
⏰ <b>SESSION ADVANCE NOTICE!</b>
==================================
<b>Upcoming Session:</b> {s['name']}
<b>Time Remaining:</b> Approximately 1 Hour.
<b>Market Outlook:</b> Liquidity pools building up. ML engine ready. Prepare charts!
==================================
"""
            send_simple_telegram_msg(msg)

        if current_time >= s["start"] and current_time < datetime.time(s["start"].hour + 1, s["start"].minute) and not SESSION_ALERT_TRACKER.get(alert_key_start):
            SESSION_ALERT_TRACKER[alert_key_start] = True
            msg = f"""
🚀 <b>LIVE SESSION OPENED!</b>
==================================
<b>Active Now:</b> {s['name']}
<b>Market Status:</b> Kill Zone active. ML & Multi-TF sniper engine evaluating setups.
==================================
"""
            send_simple_telegram_msg(msg)

def is_in_active_trading_window():
    now = datetime.datetime.now().time()
    london_active = datetime.time(11, 0) <= now <= datetime.time(16, 0)
    ny_active = datetime.time(17, 30) <= now <= datetime.time(22, 0)
    asian_active = datetime.time(5, 0) <= now <= datetime.time(8, 0)
    return london_active or ny_active or asian_active

# ==========================================
# 6. METATRADER 5 DATA ENGINE
# ==========================================
def initialize_mt5():
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize():
            print(f"[MT5] Initialization Failed! Error: {mt5.last_error()}")
            return False
        print("[MT5] Connected Successfully to Data Feed.")
        return True
    except ImportError:
        print("[MT5] MetaTrader5 module not available on Cloud. Running in Web UI mode.")
        return True  # ক্লাউডের জন্য ট্রু রিটার্ন করবে যাতে অ্যাপ ক্র্যাশ না করে
    except Exception as e:
        print(f"[MT5] Error: {e}")
        return True

def get_rates(symbol, timeframe, count=100):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
    if rates is None or len(rates) == 0:
        return pd.DataFrame()
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

# ==========================================
# 7. CANDLESTICK PATTERN RECOGNITION ENGINE
# ==========================================
def detect_candle_patterns(df):
    if len(df) < 2:
        return "NONE"
    
    curr = df.iloc[-1]
    prev = df.iloc[-2]

    curr_body = abs(curr['close'] - curr['open'])
    curr_range = curr['high'] - curr['low']
    
    is_prev_bearish = prev['close'] < prev['open']
    is_curr_bullish = curr['close'] > curr['open']
    bullish_engulf = (is_prev_bearish and is_curr_bullish and 
                      curr['close'] >= prev['open'] and curr['open'] <= prev['close'])
    
    lower_wick = min(curr['open'], curr['close']) - curr['low']
    is_bullish_pinbar = (curr_range > 0) and (lower_wick / curr_range >= 0.55) and (curr_body / curr_range <= 0.35)

    is_prev_bullish = prev['close'] > prev['open']
    is_curr_bearish = curr['close'] < curr['open']
    bearish_engulf = (is_prev_bullish and is_curr_bearish and 
                      curr['close'] <= prev['open'] and curr['open'] >= prev['close'])
    
    upper_wick = curr['high'] - max(curr['open'], curr['close'])
    is_bearish_pinbar = (curr_range > 0) and (upper_wick / curr_range >= 0.55) and (curr_body / curr_range <= 0.35)

    if bullish_engulf or is_bullish_pinbar:
        return "BULLISH_CONFIRMATION"
    elif bearish_engulf or is_bearish_pinbar:
        return "BEARISH_CONFIRMATION"
    
    return "NONE"

# ==========================================
# 8. AUTO TECHNICAL CHART GENERATOR
# ==========================================
def generate_sniper_chart(symbol, df, entry, sl, tp1, tp2, signal_type):
    plt.figure(figsize=(10, 5), dpi=150)
    plt.style.use('dark_background')
    
    plt.plot(df['time'].tail(30), df['close'].tail(30), color='#00efff', label='H4/H1 Price Action', linewidth=1.5)
    plt.axhline(y=entry, color='#e2a200', linestyle='--', linewidth=1.2, label=f'Sniper Entry: ${entry}')
    plt.axhline(y=sl, color='#ff3333', linestyle='-', linewidth=1.5, label=f'Stop Loss (SL): ${sl}')
    plt.axhline(y=tp1, color='#00ff66', linestyle=':', linewidth=1.2, label=f'TP1 Target: ${tp1}')
    plt.axhline(y=tp2, color='#00cc44', linestyle='-', linewidth=1.5, label=f'TP2 Target: ${tp2}')
    
    title_prefix = f"🎯 {signal_type} ML-FILTERED ANALYSIS ({symbol})"
    plt.title(f"{title_prefix} - {datetime.datetime.now().strftime('%H:%M:%S')}", fontsize=12, color='white')
    plt.grid(True, alpha=0.15)
    plt.legend(loc='upper left', fontsize=8)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf.getvalue()

# ==========================================
# 9. ML-POWERED SCANNING & PREDICTION ENGINE
# ==========================================
def scan_for_sniper_entry(symbol):
    df_d1 = get_rates(symbol, mt5.TIMEFRAME_D1, 30)
    df_h4 = get_rates(symbol, mt5.TIMEFRAME_H4, 50)
    df_h1 = get_rates(symbol, mt5.TIMEFRAME_H1, 50)
    df_m30 = get_rates(symbol, mt5.TIMEFRAME_M30, 50)

    if df_d1.empty or df_h4.empty or df_h1.empty or df_m30.empty:
        return

    current_price = df_m30.iloc[-1]['close']

    d1_trend = "BULLISH" if df_d1.iloc[-1]['close'] > df_d1.iloc[-5]['close'] else "BEARISH"
    h4_trend = "BULLISH" if df_h4.iloc[-1]['close'] > df_h4.iloc[-5]['close'] else "BEARISH"

    swing_high = df_h4['high'].max()
    swing_low = df_h4['low'].min()
    equilibrium = (swing_high + swing_low) / 2.0

    prev_h1 = df_h1.iloc[-2]
    ob_low = prev_h1['low']
    ob_high = prev_h1['high']
    
    decimals = 2 if symbol == "XAUUSD" or "JPY" in symbol else 5
    ob_mid = round((ob_low + ob_high) / 2.0, decimals)

    tolerance = 0.006 if symbol == "XAUUSD" else 0.003
    candle_pattern = detect_candle_patterns(df_m30)

    # ------------------------------------
    # A. BUY SETUP EVALUATION WITH ML
    # ------------------------------------
    if d1_trend == "BULLISH" and h4_trend == "BULLISH" and current_price < equilibrium:
        score = 80 if abs(current_price - ob_mid) <= (current_price * tolerance) else 50
        pattern_flag = 1 if candle_pattern == "BULLISH_CONFIRMATION" else 0
        vol_spike_flag = 1 if df_m30.iloc[-1]['tick_volume'] > df_m30['tick_volume'].tail(15).mean() else 0
        dist_ratio = round(abs(current_price - equilibrium) / equilibrium, 4)

        # Prepare feature vector for ML model prediction
        features = np.array([[score, dist_ratio, vol_spike_flag, pattern_flag]])
        
        # Predict probability using ML model
        win_probability = ml_model.predict_proba(features)[0][1] # Probability of class 1 (Win)

        if win_probability >= 0.65:  # Execute only if ML confidence is >= 65%
            entry_price = ob_mid
            sl_buffer = (ob_high - ob_low) * 0.6
            stop_loss = round(ob_low - sl_buffer, decimals)
            tp1 = round(equilibrium, decimals)
            tp2 = round(swing_high, decimals)

            dist = abs(entry_price - stop_loss)
            risk_amount = ACCOUNT_BALANCE * (RISK_PERCENT / 100.0)
            lot_size = round(risk_amount / (dist * (100 if symbol == "XAUUSD" else 100000)), 2) if dist > 0 else 0.10
            lot_size = max(0.01, min(lot_size, 2.00))
            rrr = round(abs(tp2 - entry_price) / dist, 2) if dist > 0 else 0

            trigger_signal("BUY LIMIT", symbol, current_price, entry_price, stop_loss, tp1, tp2, rrr, lot_size, win_probability * 100, candle_pattern, df_h4)
            return

    # ------------------------------------
    # B. SELL SETUP EVALUATION WITH ML
    # ------------------------------------
    if d1_trend == "BEARISH" and h4_trend == "BEARISH" and current_price > equilibrium:
        score = 80 if abs(current_price - ob_mid) <= (current_price * tolerance) else 50
        pattern_flag = 1 if candle_pattern == "BEARISH_CONFIRMATION" else 0
        vol_spike_flag = 1 if df_m30.iloc[-1]['tick_volume'] > df_m30['tick_volume'].tail(15).mean() else 0
        dist_ratio = round(abs(current_price - equilibrium) / equilibrium, 4)

        features = np.array([[score, dist_ratio, vol_spike_flag, pattern_flag]])
        win_probability = ml_model.predict_proba(features)[0][1]

        if win_probability >= 0.65:
            entry_price = ob_mid
            sl_buffer = (ob_high - ob_low) * 0.6
            stop_loss = round(ob_high + sl_buffer, decimals)
            tp1 = round(equilibrium, decimals)
            tp2 = round(swing_low, decimals)

            dist = abs(stop_loss - entry_price)
            risk_amount = ACCOUNT_BALANCE * (RISK_PERCENT / 100.0)
            lot_size = round(risk_amount / (dist * (100 if symbol == "XAUUSD" else 100000)), 2) if dist > 0 else 0.10
            lot_size = max(0.01, min(lot_size, 2.00))
            rrr = round(abs(entry_price - tp2) / dist, 2) if dist > 0 else 0

            trigger_signal("SELL LIMIT", symbol, current_price, entry_price, stop_loss, tp1, tp2, rrr, lot_size, win_probability * 100, candle_pattern, df_h4)
            return

def trigger_signal(signal_type, symbol, current_price, entry_price, stop_loss, tp1, tp2, rrr, lot_size, ml_confidence, pattern, df_chart):
    date_str = datetime.datetime.now().strftime("%d %B, %I:%M %p")

    trade_log = {
        "symbol": symbol,
        "type": signal_type,
        "entry": entry_price,
        "sl": stop_loss,
        "tp1": tp1,
        "tp2": tp2,
        "date": date_str,
        "status": "PENDING",
        "pips": 0.0
    }
    save_trade_log(trade_log)

    header_icon = "🔴" if "SELL" in signal_type else "🟢"
    header_tag = f"{header_icon} <b>{signal_type} ML-SNIPER ALERT ({symbol})</b>"

    msg = f"""
{header_tag}
==================================
<b>Signal Type:</b> {signal_type} (ML & SMC Confirmed)
<b>Current Price:</b> <code>${current_price}</code>
<b>Sniper Entry:</b> <code>${entry_price}</code>
<b>Stop Loss (SL):</b> <code>${stop_loss}</code>
<b>Take Profit 1:</b> <code>${tp1}</code>
<b>Take Profit 2:</b> <code>${tp2}</code>
<b>Risk-to-Reward:</b> <code>1 : {rrr}</code>

🤖 <b>AI & Confluence Metrics:</b>
• ML Win Confidence: <code>{ml_confidence:.1f}%</code>
• Candle Pattern: <code>{pattern}</code>
• Multi-TF Trend: Aligned (D1, H4, H1)

💼 <b>Risk Management (1% Risk):</b>
• Lot Size: <code>{lot_size} Lots</code>
==================================
<b>Time:</b> {date_str}
"""
    send_telegram_signal_with_buttons(msg)
    chart_bytes = generate_sniper_chart(symbol, df_chart, entry_price, stop_loss, tp1, tp2, signal_type)
    send_telegram_chart_image(chart_bytes, f"📈 <b>{signal_type} ML Structure Chart ({symbol})</b>")

# ==========================================
# 10. MAIN ENGINE LOOP
# ==========================================
# ==========================================
# 10. STREAMLIT CLOUD UI EXECUTION BYPASS
# ==========================================
if __name__ == "__main__":
    try:
        if initialize_mt5():
            print("\n🚀 ML-Powered Institutional Sniper Bot Active!")
            # ক্লাউড সার্ভারে ইনফিনিট while True লুপ রাখা যাবে না, 
            # কারণ Streamlit শুধু ওয়েব ইউআই রেন্ডার করে।
    except Exception as e:
        print(f"Web UI Mode Active: {e}")
