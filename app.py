from flask import Flask, render_template, request, jsonify

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.post("/calculate")
def calculate():
    """
    Receives JSON with all inputs and returns a JSON with all calculated values.
    """
    data = request.get_json() or {}

    try:
        total_price = float(data.get("total_price") or 0.0)
        include_shipping = bool(data.get("include_shipping"))
        tax_rate = float(data.get("tax_rate") or 0.0)
        manual_bank_fee_pct = float(data.get("manual_bank_fee_pct") or 0.0)
        bike_cost = float(data.get("bike_cost") or 0.0)
        seller_commission = float(data.get("seller_commission") or 0.0)

        # Fixed shipping logic (not taxed, not revenue)
        SHIPPING_FIXED = 900.0 if include_shipping else 0.0

        # Amount that is actually taxed (bike price + tax, without shipping)
        taxable_total = max(total_price - SHIPPING_FIXED, 0.0)

        # Separate tax and bike price before tax
        if tax_rate != 0:
            bike_price_before_tax = taxable_total / (1.0 + tax_rate / 100.0)
        else:
            bike_price_before_tax = taxable_total

        tax_amount = taxable_total - bike_price_before_tax

        # Manual bank fee that applies on bike+tax (not shipping)
        manual_bank_fee_amount = taxable_total * (manual_bank_fee_pct / 100.0)

        # Financing companies (each one has amount financed and a rate %)
        financing = data.get("financing") or {}
        financing_breakdown = []
        financing_fees_total = 0.0

        for code, info in financing.items():
            amount = float(info.get("amount") or 0.0)
            rate = float(info.get("rate") or 0.0)
            label = info.get("label", code)

            # Ignore empty rows
            if amount <= 0 or rate <= 0:
                continue

            fee = amount * (rate / 100.0)
            financing_fees_total += fee

            financing_breakdown.append(
                {
                    "code": code,
                    "name": label,
                    "amount_financed": round(amount, 2),
                    "rate_pct": round(rate, 2),
                    "fee": round(fee, 2),
                }
            )

        total_bank_fees = manual_bank_fee_amount + financing_fees_total

        # Revenue here is ONLY bike + tax (shipping is pass-through, not revenue)
        revenue_gross = taxable_total

        # Scenario 1: Store eats the bank fees (no pass)
        net_no_pass = revenue_gross - total_bank_fees
        profit_no_pass = net_no_pass - bike_cost - seller_commission

        # Scenario 2: Store passes all bank fees to the customer on top of price
        customer_price_with_fees = total_price + total_bank_fees
        net_with_pass = revenue_gross  # store keeps same revenue, customer pays fees
        profit_with_pass = net_with_pass - bike_cost - seller_commission

        results = {
            "bike_price_before_tax": round(bike_price_before_tax, 2),
            "tax_amount": round(tax_amount, 2),
            "subtotal_with_tax": round(taxable_total, 2),
            "shipping_amount": round(SHIPPING_FIXED, 2),
            "manual_bank_fee_amount": round(manual_bank_fee_amount, 2),
            "total_bank_fees": round(total_bank_fees, 2),
            "financing_breakdown": financing_breakdown,
            "revenue_gross": round(revenue_gross, 2),
            "net_to_store_no_pass": round(net_no_pass, 2),
            "profit_no_pass": round(profit_no_pass, 2),
            "customer_price_with_fees": round(customer_price_with_fees, 2),
            "net_to_store_with_pass": round(net_with_pass, 2),
            "profit_with_pass": round(profit_with_pass, 2),
        }

        return jsonify(success=True, results=results)

    except Exception as e:
        # If something goes wrong, return an error with message
        return jsonify(success=False, error=str(e)), 400


if __name__ == "__main__":
    # For local testing
    app.run(debug=True, host="0.0.0.0", port=5000)
