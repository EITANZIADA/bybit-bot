import os
import traceback
from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP

# === הגדרת קלטים מהסביבה ===
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
LEVERAGE = 10  # מינוף קבוע

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
        print("\n📩 Payload received:", data)
    except Exception:
        print("\n❌ Failed to parse JSON. Raw body:", request.data)
        return jsonify({'error': 'Invalid or missing JSON'}), 400

    if not data or 'action' not in data or 'symbol' not in data:
        return jsonify({'error': 'Missing required fields'}), 400

    symbol = data['symbol'].upper()
    action = data['action'].lower()

    try:
        if action == "test":
            print("✅ Test webhook received successfully!")
            return jsonify({'status': 'Test OK'}), 200

        # קביעת מינוף
        client.set_leverage(category="linear", symbol=symbol, buyLeverage=LEVERAGE, sellLeverage=LEVERAGE)

        if action == "buy":
            client.place_order(
                category="linear",
                symbol=symbol,
                side="Buy",
                order_type="Market",
                qty=None,
                time_in_force="GoodTillCancel"
            )
            return jsonify({'status': 'Buy order sent'})

        elif action == "sell":
            side = data.get("position_side", "Sell")
            client.place_order(
                category="linear",
                symbol=symbol,
                side=side,
                order_type="Market",
                qty=None,
                time_in_force="GoodTillCancel"
            )
            return jsonify({'status': 'Sell order sent'})

        elif action == "close":
            client.place_order(
                category="linear",
                symbol=symbol,
                side="Sell",  # הפוך מהפוזיציה הפתוחה
                order_type="Market",
                qty=None,
                reduce_only=True,
                time_in_force="GoodTillCancel"
            )
            return jsonify({'status': 'Close order sent'})

        elif action == "update_stop":
            new_stop = float(data.get("new_stop"))
            side = data.get("side")
            is_long = side == "long"
            stop_loss_side = "Sell" if is_long else "Buy"

            client.place_order(
                category="linear",
                symbol=symbol,
                side=stop_loss_side,
                order_type="StopMarket",
                stop_loss=round(new_stop, 2),
                qty=None,
                time_in_force="GoodTillCancel",
                reduce_only=True
            )
            return jsonify({'status': 'Stop loss updated'})

        else:
            return jsonify({'error': 'Unknown action'}), 400

    except Exception as e:
        print("\n❌ Exception occurred:", traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# הפעלת השרת
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
