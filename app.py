import os
import traceback
from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP
from dotenv import load_dotenv

load_dotenv()

BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
QTY = 0.01  # שנה לפי גודל העסקה שאתה רוצה

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

    try:
        side = "Buy" if action == "buy" else "Sell"
        print(f"\n🚀 Placing order: {side} {symbol}...")

        result = client.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            order_type="Market",
            qty=QTY,
            time_in_force="GoodTillCancel"
        )

        print("\n✅ Order result:", result)
        return jsonify(result)

    except Exception as e:
        print("\n❌ Order failed:", traceback.format_exc())
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
