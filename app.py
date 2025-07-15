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
    recv_window=5100
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
        return jsonify({'error': 'Missing required fields'}), 400

    action = data['action']
    symbol = data['symbol']
    usdt_amount = data.get('usdt_amount')

    try:
        # Get latest price for the symbol
        ticker = client.get_tickers(category='linear', symbol=symbol)
        price = float(ticker['result']['list'][0]['lastPrice'])

        print(f"📈 Current price for {symbol}: {price}")

        qty = round(usdt_amount / price, 3) if usdt_amount else 0.01

        print(f"💰 Calculated quantity: {qty}")

        if action == "buy":
            order = client.place_order(
                category="linear",
                symbol=symbol,
                side="Buy",
                order_type="Market",
                qty=qty,
                time_in_force="GoodTillCancel"
            )
        elif action == "sell":
            order = client.place_order(
                category="linear",
                symbol=symbol,
                side="Sell",
                order_type="Market",
                qty=qty,
                time_in_force="GoodTillCancel"
            )
        else:
            return jsonify({'error': 'Invalid action'}), 400

        return jsonify(order)

    except Exception as e:
        print("\n❌ Exception occurred:", traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run()
