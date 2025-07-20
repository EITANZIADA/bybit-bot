import os
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
    qty = 0.02  # גודל העסקה

    # === הדפסת מצב הארנק
    try:
        wallet = client.get_wallet_balance(accountType="UNIFIED")
        print("🔍 Wallet balance response:", wallet)

        # ✅ שימוש ב-get_tickers במקום get_ticker
        price_data = client.get_tickers(category="linear", symbol=symbol)
        print("📈 Price data:", price_data)

    except Exception as e:
        print("⚠️ Failed to fetch wallet balance or price:", e)

    try:
        if action == "buy":
            print("🟢 Executing BUY order")
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
            print("🔴 Executing SELL order")
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
            print("❎ Closing all open orders for", symbol)
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

            # במצב One-Way אי אפשר לשלוט בפוזיציה נפרדת לפי צד
            client.set_trading_stop(
                category="linear",
                symbol=symbol,
                stop_loss=new_stop
            )
            return jsonify({"status": f"Stop loss updated to {new_stop}"})

        else:
            return jsonify({"error": "Unknown action"}), 400

    except Exception as e:
        print("❌ Execution error:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# === שורת הרצה שמתאימה ל-Render ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
