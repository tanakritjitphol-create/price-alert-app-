from flask import Flask, request, jsonify, send_from_directory
import yfinance as yf
import ccxt
import requests
import threading
import time
import os

app = Flask(__name__, static_folder='static')

# Store alerts in memory
user_alerts = {}

def send_telegram(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})
    except:
        pass

def get_prices():
    prices = {}
    try:
        exchange = ccxt.binance()
        for symbol in ["BTC/USDT", "ETH/USDT", "XRP/USDT", "SOL/USDT"]:
            ticker = exchange.fetch_ticker(symbol)
            prices[symbol] = ticker['last']
    except:
        pass
    try:
        gold = yf.Ticker("GC=F")
        prices["Gold"] = gold.fast_info['last_price']
        thb = yf.Ticker("THBUSD=X")
        rate = thb.fast_info['last_price']
        prices["USD/THB"] = round(1 / rate, 4) if rate else None
    except:
        pass
    return prices

def monitor_loop():
    triggered = {}
    while True:
        try:
            prices = get_prices()
            for user_id, config in list(user_alerts.items()):
                token = config.get("token")
                chat_id = config.get("chat_id")
                alerts = config.get("alerts", [])
                for alert in alerts:
                    asset = alert["asset"]
                    above = alert.get("above")
                    below = alert.get("below")
                    price = prices.get(asset)
                    if price is None:
                        continue
                    key_above = f"{user_id}_{asset}_above"
                    key_below = f"{user_id}_{asset}_below"
                    if above and price >= float(above) and not triggered.get(key_above):
                        send_telegram(token, chat_id, f"<b>{asset}</b> ราคาขึ้นถึง <b>${price:,.2f}</b> แล้วค่ะ!")
                        triggered[key_above] = True
                    elif above and price < float(above):
                        triggered[key_above] = False
                    if below and price <= float(below) and not triggered.get(key_below):
                        send_telegram(token, chat_id, f"<b>{asset}</b> ราคาลงถึง <b>${price:,.2f}</b> แล้วค่ะ!")
                        triggered[key_below] = True
                    elif below and price > float(below):
                        triggered[key_below] = False
        except Exception as e:
            print(f"Monitor error: {e}")
        time.sleep(60)

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/api/prices")
def api_prices():
    return jsonify(get_prices())

@app.route("/api/save", methods=["POST"])
def save_alerts():
    data = request.json
    user_id = data.get("chat_id")
    user_alerts[user_id] = {
        "token": data.get("token"),
        "chat_id": data.get("chat_id"),
        "alerts": data.get("alerts", [])
    }
    send_telegram(data.get("token"), data.get("chat_id"),
        "Price Alert Bot พร้อมแจ้งเตือนแล้วค่ะ!")
    return jsonify({"status": "ok"})

t = threading.Thread(target=monitor_loop, daemon=True)
t.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
