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
        print("✅ Payload received:", data)
    except Exception as e:
        print("❌ Failed to parse JSON:", e)
        return jsonify({'error': 'Invalid or missing JSON'}), 400

    if not data or 'action' not in data or 'symbol' not in data:
        return jsonify({'error': 'Missing required parameters'}), 400

    action = data['action']
    symbol = data['symbol']
    usdt_amount = float(data.get('usdt_amount', 10))  # ברירת מחדל: 10 דולר

    try:
        # שליפת מחיר עדכני
        price_data = client.get_mark_price(category="linear", symbol=symbol)
        mark_price = float(price_data["result"]["markPrice"])
        qty = round(usdt_amount / mark_price, 4)  # כמות מטבעות

        print(f"🔢 Price: {mark_price}, Qty: {qty}, Action: {action}")

        if action == 'buy':
            response = client.place_order(
                category="linear",
                symbol=symbol,
                side="Buy",
                order_type="Market",
                qty=qty,
                time_in_force="GoodTillCancel"
            )
        elif action == 'sell':
            response = client.place_order(
                category="linear",
                symbol=symbol,
                side="Sell",
                order_type="Market",
                qty=qty,
                time_in_force="GoodTillCancel"
            )
        else:
            return jsonify({'error': 'Invalid action'}), 400

        print("📤 Order response:", response)
        return jsonify({'status': 'order sent', 'response': response})

    except Exception as e:
        print("❌ Error placing order:", traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5100)
