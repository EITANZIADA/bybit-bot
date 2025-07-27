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

    # === חישוב כמות לפי 100% מההון ===
    try:
        # שליפת יתרה
        balance_data = client.get_wallet_balance(accountType="UNIFIED")
        wallets = balance_data["result"]["list"][0]["coin"]
        usdt_balance = next((item for item in wallets if item["coin"] == "USDT"), None)
        available_balance = float(usdt_balance.get("availableBalance", 0)) if usdt_balance else 0

        # שליפת מחיר נוכחי
        price_data = client.get_tickers(category="linear", symbol=symbol)
        last_price = float(price_data["result"]["list"][0]["lastPrice"]) if price_data else 0

        # חישוב כמות
        qty = round(available_balance / last_price, 4) if last_price > 0 else 0

        if qty <= 0:
            return jsonify({"error": "Insufficient balance or invalid price"}), 400

        print(f"🧮 Available balance: {available_balance} USDT, Price: {last_price}, Qty: {qty}")

    except Exception as e:
        print("❌ Error calculating qty:", e)
        traceback.print_exc()
        return jsonify({"error": "Failed to calculate position size"}), 500

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

# === מתאים להרצה ב־Render ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
