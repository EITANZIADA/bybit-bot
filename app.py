import os
import traceback
from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP

# === הגדרות קבועות ===
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
LEVERAGE = 10  # תוכל לשנות לפי הצורך

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
        print("📩 Payload received:", data)

        action = data.get("action")
        symbol = data.get("symbol")

        if action == "test":
            print("✅ Test webhook received.")
            return jsonify({"status": "Test OK"})

        if not action or not symbol:
            raise ValueError("Missing required field: 'action' or 'symbol'")

        # מביא מידע על הנכס כדי לחשב את ה־quantity לפי כל ההון
        balance = client.get_wallet_balance(accountType="UNIFIED")["result"]["list"][0]["totalEquity"]
        price_data = client.get_ticker(category="linear", symbol=symbol)
        mark_price = float(price_data["result"]["list"][0]["markPrice"])
        quantity = round((float(balance) * LEVERAGE) / mark_price, 3)

        print(f"🔢 Calculated quantity: {quantity} (Balance: {balance}, Price: {mark_price})")

        if action == "buy":
            client.place_order(
                category="linear",
                symbol=symbol,
                side="Buy",
                order_type="Market",
                qty=quantity,
                time_in_force="GoodTillCancel"
            )
            print("✅ BUY order sent.")

        elif action == "sell":
            client.place_order(
                category="linear",
                symbol=symbol,
                side="Sell",
                order_type="Market",
                qty=quantity,
                time_in_force="GoodTillCancel"
            )
            print("✅ SELL order sent.")

        elif action == "close":
            client.place_order(
                category="linear",
                symbol=symbol,
                side="Sell",  # סוגר פוזיציה לונג
                order_type="Market",
                qty=quantity,
                reduce_only=True,
                time_in_force="GoodTillCancel"
            )
            print("✅ CLOSE position (Reduce Only).")

        elif action == "update_stop":
            position_side = data.get("side")
            new_stop = data.get("new_stop")
            if not position_side or not new_stop:
                raise ValueError("Missing 'side' or 'new_stop' for update_stop")

            client.set_trading_stop(
                category="linear",
                symbol=symbol,
                side=position_side.capitalize(),
                stop_loss=round(float(new_stop), 2)
            )
            print("✅ Stop-loss updated.")

        else:
            raise ValueError("Invalid action received.")

        return jsonify({"status": "ok"})

    except Exception as e:
        print("❌ ERROR:", str(e))
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=10000)
