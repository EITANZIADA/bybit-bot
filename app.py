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
    api_secret=BYBIT_API_SECRET,
    recv_window=5000
)

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        print("\n✅ Payload received:", data)
    except Exception:
        print("\n❌ Failed to parse JSON. Raw body:", request.data)
        return jsonify({'error': 'Invalid or missing JSON'}), 400

    if not data or 'action' not in data or 'symbol' not in data:
        print("\n⚠️ Missing required fields.")
        return jsonify({'error': 'Missing required fields'}), 400

    action = data['action']
    symbol = data['symbol']
    side = "Buy" if action == "buy" else "Sell"

    try:
        # שלב 1: לבדוק יתרת USDT
        balance_data = client.get_wallet_balance(accountType="UNIFIED", coin="USDT")
        print("📦 Raw balance response:", balance_data)

        coin_info = balance_data['result']['list'][0]['coin'][0]

        # ננסה להשתמש ב־availableToTrade ואם לא קיים - נ fallback ל־availableBalance
        usdt_balance = float(
            coin_info.get('availableToTrade') or coin_info.get('availableBalance')
        )

        print(f"💰 USDT Available: {usdt_balance}")

        # שלב 2: לבדוק את מחיר השוק של הסימבול
        price_data = client.get_ticker(category="linear", symbol=symbol)
        mark_price = float(price_data['result']['lastPrice'])

        print(f"📈 Market price of {symbol}: {mark_price}")

        # שלב 3: לחשב כמות נכס לפי USDT
        qty = round(usdt_balance / mark_price, 4)

        print(f"📦 Order Qty: {qty}")

        # שלב 4: שליחת פקודה
        result = client.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            order_type="Market",
            qty=qty,
            time_in_force="GoodTillCancel"
        )

        print("\n✅ Order executed:", result)
        return jsonify(result)

    except Exception as e:
        print("\n❌ Order failed:", traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
