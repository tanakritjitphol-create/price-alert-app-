from flask import Flask, request, jsonify, send_from_directory
from apscheduler.schedulers.background import BackgroundScheduler
import yfinance as yf
import ccxt
import requests
import os

app = Flask(__name__, static_folder='static')

user_alerts = {}
triggered = {}

def send_telegram(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def get_prices():
    prices = {}
    try:
        exchange = ccxt.binance()
        for symbol in ["BTC/USDT", "ETH/USDT", "XRP/USDT", "SOL/USDT"]:
            ticker = exchange.fetch_ticker(symbol)
            prices[symbol] = ticker['last']
    except Exception as e:
        print(f"Crypto error: {e}")
    try:
        gold = yf.Ticker("GC=F")
        prices["Gold"] = gold.fast_info['last_price']
        thb = yf.Ticker("THBUSD=X")
        rate = thb.fast_info['last_price']
        prices["USD/THB"] = round(1 / rate, 4) if rate else None
    except Exception as e:
        print(f"Forex error: {e}")
    return prices

def check_alerts():
    print(f"Checking alerts... {len(user_alerts)} users")
    try:
        prices = get_prices()
        print(f"Prices: {prices}")
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
                if above and price >= float(above):
                    if not triggered.get(key_above):
                        send_telegram(token, chat_id, f"<b>{asset}</b> ราคาขึ้นถึง <b>${price:,.2f}</b> แล้วค่ะ!")
                        triggered[key_above] = True
                        print(f"Alert sent: {asset} above {above}")
                elif above and price < float(above):
                    triggered[key_above] = False

                if below and price <= float(below):
                    if not triggered.get(key_below):
                        send_telegram(token, chat_id, f"<b>{asset}</b> ราคาลงถึง <b>${price:,.2f}</b> แล้วค่ะ!")
                        triggered[key_below] = True
                        print(f"Alert sent: {asset} below {below}")
                elif below and price > float(below):
                    triggered[key_below] = False
    except Exception as e:
        print(f"Check alerts error: {e}")

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
    print(f"Saved alerts for {user_id}: {data.get('alerts')}")
    send_telegram(data.get("token"), data.get("chat_id"), "Price Alert Bot พร้อมแจ้งเตือนแล้วค่ะ!")
    return jsonify({"status": "ok"})

scheduler = BackgroundScheduler()
scheduler.add_job(check_alerts, 'interval', seconds=60)
scheduler.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
