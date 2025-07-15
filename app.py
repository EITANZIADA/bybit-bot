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

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        print("📩 Payload received:", data)
    except Exception as e:
        print("❌ Failed to parse JSON:", e)
        return jsonify({'error': 'Invalid or missing JSON'}), 400

    try:
        action = data.get("action")
        symbol = data.get("symbol")
        usdt_amount = float(data.get("usdt_amount", 0))

        if not action or not symbol or usdt_amount <= 0:
            return jsonify({'error': 'Missing or invalid parameters'}), 400

        # Get price using get_tickers (returns a list)
        tickers = client.get_tickers(category="linear", symbol=symbol)
        price = float(tickers['list'][0]['lastPrice'])

        qty = round(usdt_amount / price, 4)

        side = "Buy" if action.lower() == "buy" else "Sell"
        resp = client.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            order_type="Market",
            qty=qty,
            time_in_force="GoodTillCancel"
        )
        print("✅ Order Response:", resp)
        return jsonify({'status': 'order placed', 'details': resp})

    except Exception as e:
        print("❌ ERROR:", traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=10000)
