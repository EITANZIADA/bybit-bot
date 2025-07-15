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

        if not data or 'action' not in data or 'symbol' not in data or 'usdt_amount' not in data:
            return jsonify({"error": "Missing fields"}), 400

        action = data['action']
        symbol = data['symbol']
        usdt_amount = float(data['usdt_amount'])

        # ❌ זה היה הקוד הישן שגרם לשגיאה:
        # price = client.get_mark_price(symbol=symbol)['result']['markPrice']

        # תחליף עם קריאה נכונה או הסר בכלל אם אתה בוחר כמות קבועה:
        # לדוגמה:
        qty = round(usdt_amount / 3000, 4)  # מחליף ב־3000 זמנית כ־ETH price

        side = "Buy" if action == "buy" else "Sell"

        order = client.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            order_type="Market",
            qty=qty,
            time_in_force="GoodTillCancel"
        )

        print("✅ Order Placed:", order)
        return jsonify(order)

    except Exception as e:
        print("\n❌ Error:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
