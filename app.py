import os
import traceback
from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP
from dotenv import load_dotenv

load_dotenv()

BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
LEVERAGE = 10

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
        print("✅ Payload received:", data)
    except Exception:
        print("❌ Failed to parse JSON. Raw body:", request.data)
        return jsonify({'error': 'Invalid or missing JSON'}), 400

    action = data.get("action")
    symbol = data.get("symbol")
    side = data.get("side", "buy")
    new_stop = data.get("new_stop", None)

    if action == "test":
        return jsonify({"status": "Test OK"})

    if not action or not symbol:
        return jsonify({"error": "Missing 'action' or 'symbol'"}), 400

    try:
        # Step 1: Get balance
        balance_info = client.get_wallet_balance(accountType="UNIFIED")
        usdt_balance = float(balance_info['result']['list'][0]['totalEquity'])

        # Step 2: Get market price
        price_data = client.get_ticker(category="linear", symbol=symbol)
        mark_price = float(price_data['result']['list'][0]['lastPrice'])

        # Step 3: Calculate quantity
        qty = round((usdt_balance * LEVERAGE) / mark_price, 3)

        # Step 4: Place order based on action
        if action == "buy":
            client.place_order(
                category="linear",
                symbol=symbol,
                side="Buy",
                order_type="Market",
                qty=qty,
                time_in_force="GoodTillCancel"
            )
            return jsonify({"status": "Buy order placed", "qty": qty})

        elif action == "sell":
            client.place_order(
                category="linear",
                symbol=symbol,
                side="Sell",
                order_type="Market",
                qty=qty,
                time_in_force="GoodTillCancel"
            )
            return jsonify({"status": "Sell order placed", "qty": qty})

        elif action == "close":
            position = client.get_positions(category="linear", symbol=symbol)
            pos_side = position['result']['list'][0]['side']
            current_qty = float(position['result']['list'][0]['size'])
            if current_qty > 0:
                closing_side = "Sell" if pos_side == "Buy" else "Buy"
                client.place_order(
                    category="linear",
                    symbol=symbol,
                    side=closing_side,
                    order_type="Market",
                    qty=current_qty,
                    reduce_only=True
                )
                return jsonify({"status": "Position closed", "side": closing_side, "qty": current_qty})
            else:
                return jsonify({"status": "No open position to close"})

        elif action == "update_stop" and new_stop:
            client.set_trading_stop(
                category="linear",
                symbol=symbol,
                stopLoss=str(new_stop)
            )
            return jsonify({"status": "Stop loss updated", "new_stop": new_stop})

        else:
            return jsonify({"error": "Unknown action or missing data"}), 400

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

