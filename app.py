import os
import traceback
from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP
from dotenv import load_dotenv

load_dotenv()

BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")

client = HTTP(
    testnet=False,
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET
)

app = Flask(__name__)

# פונקציה שמביאה את כל היתרה שלך ומחשבת את הכמות לפי מחיר נוכחי
def get_max_position_size(symbol):
    try:
        balance_data = client.get_wallet_balance(accountType="UNIFIED")
        print("📦 Raw balance_data:", balance_data)  # הדפסה למעקב

        available_usdt = float(balance_data["result"]["list"][0]["totalEquity"])
        print("💰 Available USDT:", available_usdt)

        price_data = client.get_ticker(category="linear", symbol=symbol)
        print("📈 Price data:", price_data)

        last_price = float(price_data["result"]["lastPrice"])
        print("💵 Last price:", last_price)

        qty = available_usdt / last_price
        return round(qty, 0.01)
    except Exception as e:
        print("❌ Error calculating max position size:", e)
        return 0



@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        print("✅ Webhook received:", data)

        action = data.get("action")
        symbol = data.get("symbol")

        qty = get_max_position_size(symbol)
        print(f"🔢 Calculated qty: {qty}")

        if qty < 0.01:
            return jsonify({"error": "Not enough balance to place order"}), 400

        if action == "buy":
            side = "Buy"
        elif action == "sell":
            side = "Sell"
        else:
            return jsonify({"error": "Invalid action"}), 400

        order = client.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            order_type="Market",
            qty=qty
        )

        print("✅ Order placed:", order)
        return jsonify(order)

    except Exception as e:
        print("❌ Error in /webhook:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5100)
