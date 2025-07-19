import os
import traceback
from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP
from dotenv import load_dotenv

load_dotenv()

# === הגדרות קבועות ===
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
LEVERAGE = 10

client = HTTP(
    testnet=False,
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET
)

app = Flask(__name__)

# === פונקציה לחישוב גודל עסקה על בסיס ההון שלך ===
def calculate_position_size(symbol="ETHUSDT", leverage=LEVERAGE):
    try:
        account_info = client.get_wallet_balance(accountType="UNIFIED")
        usdt_balance = float(account_info["result"]["list"][0]["totalAvailableBalance"])

        ticker = client.get_ticker(symbol=symbol)
        mark_price = float(ticker["result"]["list"][0]["lastPrice"])

        qty = (usdt_balance * leverage) / mark_price
        return round(qty, 4)
    except Exception as e:
        print("⚠️ Failed to calculate position size:", e)
        return None

# === Webhook Receiver ===
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        print("\n✅ Payload received:", data)
    except Exception:
        print("\n❌ Failed to parse JSON. Raw body:", request.data)
        return jsonify({'error': 'Invalid or missing JSON'}), 400

    if not data or 'action' not in data or 'symbol' not in data:
        print("⚠️ Missing required fields.")
        return jsonify({'error': 'Missing required fields'}), 400

    action = data['action']
    symbol = data['symbol']
    position_side = data.get('position_side', 'long')
    new_stop = data.get('new_stop')

    try:
        qty = calculate_position_size(symbol)
        if qty is None:
            return jsonify({'error': 'Failed to calculate position size'}), 500

        if action == "buy":
            print("📈 Opening LONG position...")
            client.place_order(
                category="linear",
                symbol=symbol,
                side="Buy",
                order_type="Market",
                qty=qty,
                time_in_force="GoodTillCancel",
                reduce_only=False
            )
            return jsonify({'status': 'Buy order sent'})

        elif action == "sell":
            print("📉 Opening SHORT position...")
            client.place_order(
                category="linear",
                symbol=symbol,
                side="Sell",
                order_type="Market",
                qty=qty,
                time_in_force="GoodTillCancel",
                reduce_only=False
            )
            return jsonify({'status': 'Sell order sent'})

        elif action == "close":
            print("❌ Closing position...")
            client.place_order(
                category="linear",
                symbol=symbol,
                side="Sell" if position_side == "long" else "Buy",
                order_type="Market",
                qty=qty,
                reduce_only=True,
                time_in_force="GoodTillCancel"
            )
            return jsonify({'status': 'Close order sent'})

        elif action == "update_stop" and new_stop is not None:
            print("🔄 Updating stop loss...")
            client.set_trading_stop(
                category="linear",
                symbol=symbol,
                stop_loss=new_stop
            )
            return jsonify({'status': 'Stop loss updated'})

        else:
            print("⚠️ Unknown action.")
            return jsonify({'error': 'Unknown action'}), 400

    except Exception as e:
        print("❌ Error executing action:", e)
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)

