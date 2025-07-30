import os
import math
import traceback
from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP

# === התחברות ל־Bybit ===
BYBIT_API_KEY = os.environ.get("BYBIT_API_KEY")
BYBIT_API_SECRET = os.environ.get("BYBIT_API_SECRET")

client = HTTP(
    testnet=False,
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET,
    recv_window=5000
)

# === הגדרת שרת Flask ===
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        print("📩 Payload received:", data)
    except Exception as e:
        print("❌ Failed to parse JSON:", e)
        return jsonify({"error": "Invalid JSON"}), 400

    if not data or "action" not in data or "symbol" not in data:
        return jsonify({"error": "Missing 'action' or 'symbol'"}), 400

    action = data["action"]
    symbol = data["symbol"]

    # === חישוב כמות לפי 90% מההון ועיגול לפי step size ===
    try:
        balance_data = client.get_wallet_balance(accountType="UNIFIED")
        total_equity = float(balance_data["result"]["list"][0]["totalEquity"])

        price_data = client.get_tickers(category="linear", symbol=symbol)
        last_price = float(price_data["result"]["list"][0]["lastPrice"]) if price_data else 0

        investment_pct = 0.90
        amount_to_use = total_equity * investment_pct

        # שליפת step size אוטומטית מה-API
        instrument_info = client.get_instruments_info(category="linear", symbol=symbol)
        step_size = float(instrument_info["result"]["list"][0]["lotSizeFilter"]["qtyStep"])

        raw_qty = amount_to_use / last_price
        qty = math.floor(raw_qty / step_size) * step_size
        qty = round(qty, 8)  # שומר על דיוק לפי Bybit

        print("🧪 total_equity:", total_equity)
        print("🧪 last_price:", last_price)
        print("🧪 step_size:", step_size)
        print("🧪 qty:", qty)

        if qty <= 0:
            return jsonify({"error": "Insufficient equity or invalid qty"}), 400

    except Exception as e:
        print("❌ Error calculating qty:", e)
        traceback.print_exc()
        return jsonify({"error": "Failed to calculate position size"}), 500

    # === ביצוע פקודות ===
    try:
        if action == "buy":
            print(f"🟢 BUY {symbol} x {qty}")
            client.place_order(
                category="linear",
                symbol=symbol,
                side="Buy",
                order_type="Market",
                qty=qty,
                time_in_force="GoodTillCancel",
                reduce_only=False
            )
            return jsonify({"status": "Buy order sent"})

        elif action == "sell":
            print(f"🔴 SELL {symbol} x {qty}")
            client.place_order(
                category="linear",
                symbol=symbol,
                side="Sell",
                order_type="Market",
                qty=qty,
                time_in_force="GoodTillCancel",
                reduce_only=False
            )
            return jsonify({"status": "Sell order sent"})

        elif action == "close":
            print(f"❎ Closing position for {symbol}")
            positions = client.get_positions(category="linear", symbol=symbol)
            pos = positions['result']['list'][0]
            size = float(pos['size'])
            side = pos['side']

            if size > 0:
                closing_side = "Sell" if side == "Buy" else "Buy"
                client.place_order(
                    category="linear",
                    symbol=symbol,
                    side=closing_side,
                    order_type="Market",
                    qty=size,
                    time_in_force="GoodTillCancel",
                    reduce_only=True
                )
                return jsonify({"status": f"Position closed with {closing_side}"})
            else:
                return jsonify({"status": "No open position to close"})

        elif action == "update_stop":
            new_stop = float(data.get("new_stop", 0))
            if new_stop <= 0:
                return jsonify({"error": "Invalid stop loss price"}), 400

            print(f"🛑 Updating stop for {symbol} to {new_stop}")
            client.set_trading_stop(
                category="linear",
                symbol=symbol,
                stop_loss=new_stop
            )
            return jsonify({"status": f"Stop loss updated to {new_stop}"})

        else:
            return jsonify({"error": f"Unknown action '{action}'"}), 400

    except Exception as e:
        print("❌ Execution error:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# === מתאים להרצה ב־Render או לוקאלית ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
