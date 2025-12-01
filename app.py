from flask import Flask, render_template, request

app = Flask(__name__)

# Constants
FIXED_SHIPPING = 900.0


def to_float(val):
    """Convert a form value to float safely."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace(",", "").strip()
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


@app.route("/", methods=["GET", "POST"])
def index():
    # Defaults
    language = "en"
    theme = "dark"
    include_shipping = True

    # Form values buffer so we can re-render with what user typed
    form_values = {
        "total_price": "",
        "tax_rate": "7.0",
        "manual_bank_fee_pct": "",
        "bike_cost": "",
        "seller_commission": "",
        "aff_amount": "",
        "aff_rate": "5.0",
        "acima_amount": "",
        "acima_rate": "0.0",
        "dignify_amount": "",
        "dignify_rate": "6.5",
        "synchrony_amount": "",
        "synchrony_rate": "5.0",
        "afterpay_amount": "",
        "afterpay_rate": "6.0",
        "usbank_amount": "",
        "usbank_rate": "5.0",
        "snap_amount": "",
        "snap_rate": "2.0",
        "progressive_amount": "",
        "progressive_rate": "2.0",
        "zip_amount": "",
        "zip_rate": "6.0",
        "klarna_amount": "",
        "klarna_rate": "6.0",
    }

    result = None

    if request.method == "POST":
        action = request.form.get("action", "calculate")
        language = request.form.get("language", "en")
        theme = request.form.get("theme", "dark")

        include_shipping = request.form.get("include_shipping") == "on"

        # Update form_values from POST so if there is an error we keep what user typed
        for key in form_values.keys():
            form_values[key] = request.form.get(key, form_values[key])

        if action == "clear":
            # Reset to defaults (we already have form_values defaults defined)
            result = None
        else:
            # ---- CALCULATIONS ----
            total_price = to_float(form_values["total_price"])
            tax_rate = to_float(form_values["tax_rate"])
            manual_bank_fee_pct = to_float(form_values["manual_bank_fee_pct"])
            bike_cost = to_float(form_values["bike_cost"])
            seller_commission = to_float(form_values["seller_commission"])

            # Shipping rule
            shipping_amount = FIXED_SHIPPING if include_shipping else 0.0

            # Tax is applied ONLY on the bike (no shipping)
            taxable_total = max(total_price - shipping_amount, 0.0)

            if tax_rate > 0:
                bike_price_before_tax = taxable_total / (1.0 + tax_rate / 100.0)
                tax_amount = taxable_total - bike_price_before_tax
            else:
                bike_price_before_tax = taxable_total
                tax_amount = 0.0

            # Financing companies: each one is AMOUNT financed with that bank,
            # and a merchant fee RATE % applied to that amount.
            banks = [
                ("aff", "American First Finance", "aff_amount", "aff_rate"),
                ("acima", "Acima", "acima_amount", "acima_rate"),
                ("dignify", "Dignify", "dignify_amount", "dignify_rate"),
                ("synchrony", "Synchrony", "synchrony_amount", "synchrony_rate"),
                ("afterpay", "Afterpay", "afterpay_amount", "afterpay_rate"),
                ("usbank", "US Bank", "usbank_amount", "usbank_rate"),
                ("snap", "Snap Finance", "snap_amount", "snap_rate"),
                ("progressive", "Progressive", "progressive_amount", "progressive_rate"),
                ("zip", "Zip", "zip_amount", "zip_rate"),
                ("klarna", "Klarna", "klarna_amount", "klarna_rate"),
            ]

            bank_details = []
            total_bank_fees_dollars = 0.0

            for code, label, amount_key, rate_key in banks:
                amount = to_float(form_values[amount_key])
                rate = to_float(form_values[rate_key])

                if amount > 0 and rate > 0:
                    fee = amount * rate / 100.0
                    bank_details.append(
                        {
                            "label": label,
                            "amount": amount,
                            "rate": rate,
                            "fee": fee,
                        }
                    )
                    total_bank_fees_dollars += fee

            # Manual bank fee % applies on bike+tax (taxable_total)
            manual_fee_amount = taxable_total * manual_bank_fee_pct / 100.0
            if manual_fee_amount > 0:
                bank_details.append(
                    {
                        "label": "Manual bank fee",
                        "amount": taxable_total,
                        "rate": manual_bank_fee_pct,
                        "fee": manual_fee_amount,
                    }
                )
            total_bank_fees_dollars += manual_fee_amount

            if taxable_total > 0:
                total_bank_fee_pct_vs_bike = (
                    total_bank_fees_dollars / taxable_total * 100.0
                )
            else:
                total_bank_fee_pct_vs_bike = 0.0

            # Case 1: You DO NOT pass any fees to customer
            net_to_store_no_pass_bike_only = taxable_total - total_bank_fees_dollars
            profit_no_pass = (
                net_to_store_no_pass_bike_only - bike_cost - seller_commission
            )

            # Case 2: You PASS all fees to customer.
            # We simply add bank fees on top of the original customer price.
            customer_price_pass = total_price + total_bank_fees_dollars
            net_to_store_pass_bike_only = taxable_total  # you get full bike+tax
            profit_pass = net_to_store_pass_bike_only - bike_cost - seller_commission

            # Build a human-readable breakdown string for banks
            breakdown_parts = []
            for bd in bank_details:
                breakdown_parts.append(
                    f"{bd['label']} ${bd['amount']:,.2f} @ {bd['rate']:.2f}% = ${bd['fee']:,.2f}"
                )
            bank_breakdown_str = " + ".join(breakdown_parts) if breakdown_parts else "-"

            result = {
                "bike_price_before_tax": bike_price_before_tax,
                "tax_amount": tax_amount,
                "subtotal_with_tax_bike_only": taxable_total,
                "shipping_amount": shipping_amount,
                "total_to_customer": taxable_total + shipping_amount,
                "total_bank_fees_dollars": total_bank_fees_dollars,
                "total_bank_fee_pct_vs_bike": total_bank_fee_pct_vs_bike,
                "net_to_store_no_pass_bike_only": net_to_store_no_pass_bike_only,
                "profit_no_pass": profit_no_pass,
                "customer_price_pass": customer_price_pass,
                "net_to_store_pass_bike_only": net_to_store_pass_bike_only,
                "profit_pass": profit_pass,
                "bank_breakdown_str": bank_breakdown_str,
            }

    else:
        # GET: defaults
        language = "en"
        theme = "dark"
        include_shipping = True
        result = None

    return render_template(
        "index.html",
        language=language,
        theme=theme,
        include_shipping=include_shipping,
        form=form_values,
        result=result,
        fixed_shipping=FIXED_SHIPPING,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
