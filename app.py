import os
import traceback
from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP

# הגדר את פרטי החיבור שלך
BYBIT_API_KEY = os.environ.get("BYBIT_API_KEY")
BYBIT_API_SECRET = os.environ.get("BYBIT_API_SECRET")

# התחברות ל־Bybit Unified Trading
client = HTTP(
    testnet=False,
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET,
    recv_window=5000
)

# הגדרת Flask
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        print("📩 קיבלנו נתונים מה־Webhook:", data)
    except Exception as e:
        print("❌ שגיאה בפיענוח JSON:", e)
        return jsonify({"error": "Invalid JSON"}), 400

    # בדיקות נתונים
    if not data or "action" not in data or "symbol" not in data:
        return jsonify({"error": "Missing required fields"}), 400

    action = data["action"]
    symbol = data["symbol"]
    qty = 0.01  # כמות קבועה של ETH

    try:
        if action == "buy":
            print("🟢 מבצע עסקת BUY")
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
            print("🔴 מבצע עסקת SELL")
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
            print("❎ סוגר עסקה")
            client.cancel_all_orders(
                category="linear",
                symbol=symbol
            )
            return jsonify({"status": "All positions closed"})

        elif action == "update_stop":
            side = data.get("side", "")
            new_stop = float(data.get("new_stop", 0))
            if side not in ["long", "short"]:
                return jsonify({"error": "Invalid side"}), 400

            is_long = side == "long"

            client.set_trading_stop(
                category="linear",
                symbol=symbol,
                stop_loss=new_stop,
                position_idx=1 if is_long else 2
            )
            return jsonify({"status": f"Stop loss updated to {new_stop}"})

        else:
            return jsonify({"error": "Unknown action"}), 400

    except Exception as e:
        print("❌ שגיאה בביצוע הפקודה:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=10000)
