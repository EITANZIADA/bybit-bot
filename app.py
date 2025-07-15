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
        print("\n✅ Payload received:", data)
    except Exception:
        print("\n❌ Failed to parse JSON. Raw body:", request.data)
        return jsonify({'error': 'Invalid or missing JSON'}), 400

    if not data or 'action' not in data or 'symbol' not in data:
        return jsonify({'error': 'Missing required parameters'}), 400

    action = data['action'].lower()
    symbol = data['symbol'].upper()
    qty = data.get("qty", None)
    usdt_amount = data.get("usdt_amount", None)

    try:
        # חישוב כמות לפי USDT אם לא נשלח qty
        if qty is None and usdt_amount is not None:
            price_data = client.get_ticker(symbol=symbol)
            mark_price = float(price_data['result']['list'][0]['lastPrice'])
            qty = round(usdt_amount / mark_price, 3)  # עיגול לשלוש ספרות אחרי הנקודה

        if qty is None:
            return jsonify({'error': 'Missing qty or usdt_amount'}), 400

        side = "Buy" if action == "buy" else "Sell"

        print(f"📦 Sending order: {side} {qty} {symbol}")

        order = client.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            order_type="Market",
            qty=qty,
            time_in_force="GoodTillCancel"
        )
        return jsonify(order)

    except Exception as e:
        print("\n❌ Error placing order:")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5100)
