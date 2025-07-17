# ... (הקוד למעלה נשאר זהה)

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
                reduce_only=False,
                position_idx=1  # ← לונג
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
                reduce_only=False,
                position_idx=2  # ← שורט
            )
            return jsonify({"status": "Sell order sent"})
