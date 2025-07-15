import os
import traceback
from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP
from dotenv import load_dotenv

load_dotenv()

BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")

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
        print("\n✅ Payload received:", data)
    except Exception:
        print("\n❌ Failed to parse JSON. Raw body:", request.data)
        return jsonify({'error': 'Invalid or missing JSON'}), 400

    if not data or 'action' not in data or 'symbol' not in data:
        return jsonify({'error': 'Missing required fields'}), 400

    action = data['action']
    symbol = data['symbol']
    side = "Buy" if action == "buy" else "Sell"

    try:
        # שלב 1: בדיקת יתרה
        balance_data = client.get_wallet_balance(accountType="UNIFIED", coin="USDT")
        print("📦 Raw balance data:", balance_data)

        coin_list = balance_data.get('result', {}).get('list', [])
        usdt_balance = None

        for account in coin_list:
            coins = account.get('coin', [])
            for coin in coins:
                if coin['coin'] == 'USDT':
                    usdt_balance = float(coin.get('availableToTrade', 0))

        if usdt_balance is None:
            return jsonify({'error': 'USDT balance not found'}), 500
        if usdt_balance <= 0:
            return jsonify({'error': 'No usable USDT balance in account'}), 500

        print(f"💰 USDT Available: {usdt_balance}")

        # שלב 2: מחיר שוק
        price_data = client.get_ticker(category="linear", symbol=symbol)
        mark_price = float(price_data['result']['lastPrice'])
        print(f"📈 Market price: {mark_price}")

        # שלב 3: חישוב כמות לקנייה
        qty = round(usdt_balance / mark_price, 4)
        print(f"🔢 Qty to trade: {qty}")

        # שלב 4: שליחת פקודה
        result = client.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            order_type="Market",
            qty=qty,
            time_in_force="GoodTillCancel"
        )
        print("✅ Order placed:", result)
        return jsonify(result)

    except Exception as e:
        print("❌ Exception:", traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
