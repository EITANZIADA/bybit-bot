import os
import traceback
from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP
from dotenv import load_dotenv

load_dotenv()

BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
QTY =0.01

client = HTTP(
    testnet=False,
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET,
    recv_window=5000
)

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ השרת פועל!"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        print("\n✅ Payload received:", data)
    except Exception:
        print("\n❌ Failed to parse JSON. Raw body:", request.data)
        return jsonify({'error': 'Invalid or missing JSON'}), 400

    if not data or 'action' not in data or 'symbol' not in data:
        print("\n⚠️ Invalid payload structure:", data)
        return jsonify({'error': 'Invalid payload'}), 400

    action = data['action']
    symbol = data['symbol']

    try:
        if action == "buy":
            order = client.place_order(category="linear", symbol=symbol, side="Buy", order_type="Market", qty=QTY)
        elif action == "sell":
            order = client.place_order(category="linear", symbol=symbol, side="Sell", order_type="Market", qty=QTY)
        elif action in ["close_long", "close_short"]:
            side = "Sell" if action == "close_long" else "Buy"
            order = client.place_order(category="linear", symbol=symbol, side=side, order_type="Market", qty=QTY)
        elif action == "close":
            positions = client.get_positions(category="linear", symbol=symbol)["result"]["list"]
            position = positions[0] if positions else None
            if position and float(position["size"]) > 0:
                current_side = position["side"]
                opposite_side = "Sell" if current_side == "Buy" else "Buy"
                order = client.place_order(category="linear", symbol=symbol, side=opposite_side, order_type="Market", qty=float(position["size"]))
            else:
                return jsonify({'status': 'no open position to close'}), 200
        elif action == "update_stop":
            if "new_stop" not in data or "side" not in data:
                return jsonify({'error': 'Missing new_stop or side in payload'}), 400
            new_stop = float(data["new_stop"])
            side = data["side"].lower()
            order = client.set_trading_stop(category="linear", symbol=symbol, stop_loss=new_stop)
            return jsonify({'status': 'stop updated', 'response': order})
        else:
            return jsonify({'error': 'Unknown action'}), 400

        return jsonify({'status': f'{action} executed', 'order': order})

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
