import os
import traceback
from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP

# מגדיר את מפתחות ה-API שלך
api_key = os.environ.get("BYBIT_API_KEY")
api_secret = os.environ.get("BYBIT_API_SECRET")

client = HTTP(
    testnet=False,
    api_key=api_key,
    api_secret=api_secret,
    recv_window=5000
)

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        print("🚀 Webhook Received:", data)

        action = data.get("action")
        symbol = data.get("symbol")

        if not action or not symbol:
            return jsonify({"error": "Missing 'action' or 'symbol'"}), 400

        if action in ["buy", "sell"]:
            # בדיקת יתרת USDT
            wallet = client.get_wallet_balance(accountType="UNIFIED", coin="USDT")
            usdt_balance = float(wallet["result"]["list"][0]["coin"][0]["availableToTrade"])
            if usdt_balance <= 0:
                return jsonify({"error": "No usable USDT balance found in account"}), 400

            # מחיר שוק
            ticker = client.get_ticker(category="linear", symbol=symbol)
            price = float(ticker["result"]["lastPrice"])
            qty = round(usdt_balance / price, 4)

            side = "Buy" if action == "buy" else "Sell"

            order = client.place_order(
                category="linear",
                symbol=symbol,
                side=side,
                order_type="Market",
                qty=qty,
                time_in_force="GoodTillCancel"
            )

            return jsonify({"status": "✅ Order sent", "order": order})

        elif action == "close":
            close_order = client.cancel_all_orders(category="linear", symbol=symbol)
            return jsonify({"status": "✅ Close signal received, orders cancelled", "details": close_order})

        elif action == "update_stop":
            new_stop = float(data.get("new_stop"))
            side = data.get("side", "long")

            positions = client.get_positions(category="linear", symbol=symbol)
            pos_data = positions["result"]["list"][0]
            qty = float(pos_data["size"])

            if qty == 0:
                return jsonify({"error": "No open position to update stop"}), 400

            sl_price = new_stop

            sl_side = "Sell" if side == "long" else "Buy"

            sl_order = client.place_order(
                category="linear",
                symbol=symbol,
                side=sl_side,
                order_type="StopMarket",
                stop_px=sl_price,
                qty=qty,
                time_in_force="GoodTillCancel",
                reduce_only=True
            )

            return jsonify({"status": "✅ Stop updated", "stop_order": sl_order})

        else:
            return jsonify({"error": "Unknown action type"}), 400

    except Exception as e:
        print("❌ Error:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
