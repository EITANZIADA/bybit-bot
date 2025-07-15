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
    except Exception as e:
        print("\n❌ Failed to parse JSON:", e)
        return jsonify({'error': 'Invalid or missing JSON'}), 400

    if not data or 'action' not in data or 'symbol' not in data:
        return jsonify({'error': 'Missing required fields'}), 400

    action = data['action']
    symbol = data['symbol']
    usdt_amount = float(data.get('usdt_amount', 10))  # ברירת מחדל 10 אם לא נשלח

    try:
        # שליפת מחיר עדכני
        tickers = client.get_tickers(category="linear", symbol=symbol)
        mark_price = float(tickers['list'][0]['lastPrice'])
        print(f"📈 Current price of {symbol}: {mark_price}")

        # חישוב כמות לפי המחיר
        quantity = round(usdt_amount / mark_price, 5)  # עיגול ל־5 ספרות
        print(f"📦 Order quantity for ${usdt_amount}: {quantity}")

        if action == "buy":
            order = client.place_order(
                category="linear",
                symbol=symbol,
                side="Buy",
                order_type="Market",
                qty=quantity,
                time_in_force="GoodTillCancel"
            )
            print("✅ Buy order placed:", order)
            return jsonify({'status': 'Buy order sent', 'details': order})

        elif action == "sell":
            order = client.place_order(
                category="linear",
                symbol=symbol,
                side="Sell",
                order_type="Market",
                qty=quantity,
                time_in_force="GoodTillCancel"
            )
            print("✅ Sell order placed:", order)
            return jsonify({'status': 'Sell order sent', 'details': order})

        else:
            return jsonify({'error': 'Invalid action'}), 400

    except Exception as e:
        print("\n❌ Error placing order:", traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# 🟢 התחלת השרת עם PORT מ־Render
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5100))
    app.run(host='0.0.0.0', port=port)
