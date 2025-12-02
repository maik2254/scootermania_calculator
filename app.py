from flask import Flask, render_template, request

app = Flask(__name__)

# --- CONSTANTS ---
TAX_RATE_PERCENT = 7.0
FIXED_SHIPPING_AMOUNT = 900.0

# Bank definitions: key -> (name_en, name_es, list_of_possible_rates)
BANKS = {
    "aff": ("American First Finance", "American First Finance", [5.0]),
    "acima": ("Acima", "Acima", [0.0, 3.0]),
    "dignify": ("Dignify", "Dignify", [6.5, 9.0]),
    "synchrony": ("Synchrony", "Synchrony", [5.0, 9.0, 13.5]),
    "afterpay": ("Afterpay", "Afterpay", [6.0]),
    "usbank": ("US Bank", "US Bank", [5.0, 8.0, 10.0, 12.0, 14.0, 16.0]),
    "snap": ("Snap Finance", "Snap Finance", [2.0]),
    "progressive": ("Progressive", "Progressive", [2.0]),
    "zip": ("Zip", "Zip", [6.0]),
    "klarna": ("Klarna", "Klarna", [6.0]),
}


def parse_float(value, default=0.0):
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return default


@app.route("/", methods=["GET", "POST"])
def index():
    # Language & theme handling
    lang = request.values.get("language", "en")
    if lang not in ("en", "es"):
        lang = "en"

    theme = request.values.get("theme", "dark")
    if theme not in ("dark", "light"):
        theme = "dark"

    # Base form values
    total_price = 0.0
    include_shipping = True
    tax_rate_percent = TAX_RATE_PERCENT
    bike_cost = 0.0
    seller_commission = 0.0
    manual_bank_fee_percent = 0.0

    # Bank amounts + chosen rates
    bank_form = {}
    for key, (name_en, name_es, allowed_rates) in BANKS.items():
        amount_str = request.values.get(f"bank_amount_{key}", "")
        chosen_rate_str = request.values.get(f"bank_rate_{key}", "")

        amount = parse_float(amount_str, 0.0)
        chosen_rate = parse_float(chosen_rate_str, allowed_rates[0] if allowed_rates else 0.0)

        bank_form[key] = {
            "amount": amount,
            "rate": chosen_rate,
        }

    results = None

    if request.method == "POST":
        # Read main numeric inputs
        total_price = parse_float(request.values.get("total_price", 0.0))
        include_shipping = bool(request.values.get("include_shipping"))
        # Tax is fixed 7%, but we still read field to display; do not trust user changes
        _ignored_user_tax = parse_float(request.values.get("tax_rate_percent", TAX_RATE_PERCENT))
        tax_rate_percent = TAX_RATE_PERCENT

        bike_cost = parse_float(request.values.get("bike_cost", 0.0))
        seller_commission = parse_float(request.values.get("seller_commission", 0.0))
        manual_bank_fee_percent = parse_float(request.values.get("manual_bank_fee_percent", 0.0))

        # --- Core math ---
        shipping_amount = FIXED_SHIPPING_AMOUNT if include_shipping else 0.0

        # Bike+tax is total minus shipping (shipping is NOT taxed and NOT revenue)
        bike_plus_tax = max(total_price - shipping_amount, 0.0)

        tax_rate = tax_rate_percent / 100.0
        if bike_plus_tax > 0 and tax_rate >= 0:
            bike_price_before_tax = bike_plus_tax / (1.0 + tax_rate)
        else:
            bike_price_before_tax = 0.0

        tax_amount = bike_plus_tax - bike_price_before_tax

        gross_income_no_shipping = bike_plus_tax  # bike + tax only

        # Manual bank fee (if any) applies to bike_plus_tax
        manual_bank_fee_amount = bike_plus_tax * (manual_bank_fee_percent / 100.0)

        # Bank fees by company
        bank_breakdown = []
        total_bank_fees = manual_bank_fee_amount

        for key, info in bank_form.items():
            amount = info["amount"]
            rate = info["rate"]  # already numeric %
            if amount > 0 and rate > 0:
                fee_amount = amount * (rate / 100.0)
                total_bank_fees += fee_amount
                bank_breakdown.append(
                    {
                        "key": key,
                        "name_en": BANKS[key][0],
                        "name_es": BANKS[key][1],
                        "amount": amount,
                        "rate": rate,
                        "fee_amount": fee_amount,
                    }
                )

        # --- Profit / net calculations ---

        # Case A: merchant DOES NOT pass bank fees to customer
        net_to_store_no_bank_pass = gross_income_no_shipping - total_bank_fees
        # Profit when you do NOT pass fees: you pay the bank fees yourself
        # Profit is what remains after bike cost (before paying seller commission)
        profit_no_bank_pass = net_to_store_no_bank_pass - bike_cost

        # Case B: merchant PASSES bank fees to customer (customer pays them on top)
        customer_price_with_fees = total_price + total_bank_fees
        net_to_store_with_bank_pass = gross_income_no_shipping
        # Profit when you PASS fees: customer pays the bank fees, so
        # profit after bike cost (before seller commission) is based on
        # bike price before tax.
        profit_with_bank_pass = bike_price_before_tax - bike_cost

        # Build labels depending on language
        if lang == "es":
            labels = {
                "results_title": "Resultados",
                "bike_before_tax": "Precio de la moto antes de impuestos:",
                "tax_amount": "Monto de impuesto:",
                "subtotal_no_shipping": "Subtotal con impuesto (sin envío):",
                "shipping": "Envío (no ingreso):",
                "gross_income": "Ingreso bruto (solo moto + impuesto):",
                "manual_bank": "Comisión manual de banco:",
                "total_bank": "Comisiones bancarias totales:",
                "no_pass_net": "Si NO Pasas Comisión Del Banco – Neto a la tienda:",
                "no_pass_profit": "Si NO Pasas Comisión Del Banco – Ganancia después de costo + comisión:",
                "pass_price": "Si PASAS Comisión Del Banco – Precio al cliente (incl. comisiones):",
                "pass_net": "Si PASAS Comisión Del Banco – Neto a la tienda (solo moto + impuesto):",
                "pass_profit": "Si PASAS Comisión Del Banco – Ganancia después de costo + comisión:",
                "bank_breakdown_title": "Detalle de comisiones por banco:",
            }
        else:
            labels = {
                "results_title": "Results",
                "bike_before_tax": "Bike price before tax:",
                "tax_amount": "Tax amount:",
                "subtotal_no_shipping": "Subtotal with tax (bike only, no shipping):",
                "shipping": "Shipping (not taxed, not revenue):",
                "gross_income": "Gross income (bike + tax only):",
                "manual_bank": "Manual bank fee:",
                "total_bank": "Total bank fees:",
                "no_pass_net": "If you DO NOT pass bank fees – Net to store:",
                "no_pass_profit": "If you DO NOT pass bank fees – Profit after cost + commission:",
                "pass_price": "If you PASS bank fees – Customer price (incl. fees):",
                "pass_net": "If you PASS bank fees – Net to store (bike + tax only):",
                "pass_profit": "If you PASS bank fees – Profit after cost + commission:",
                "bank_breakdown_title": "Bank fee breakdown by company:",
            }

        results = {
            "labels": labels,
            "bike_price_before_tax": bike_price_before_tax,
            "tax_amount": tax_amount,
            "subtotal_no_shipping": bike_plus_tax,
            "shipping_amount": shipping_amount,
            "gross_income_no_shipping": gross_income_no_shipping,
            "manual_bank_fee_amount": manual_bank_fee_amount,
            "total_bank_fees": total_bank_fees,
            "net_to_store_no_bank_pass": net_to_store_no_bank_pass,
            "profit_no_bank_pass": profit_no_bank_pass,
            "customer_price_with_fees": customer_price_with_fees,
            "net_to_store_with_bank_pass": net_to_store_with_bank_pass,
            "profit_with_bank_pass": profit_with_bank_pass,
            "bank_breakdown": bank_breakdown,
        }

    # Values to keep in the form
    form_values = {
        "language": lang,
        "theme": theme,
        "total_price": total_price,
        "include_shipping": include_shipping,
        "tax_rate_percent": TAX_RATE_PERCENT,
        "bike_cost": bike_cost,
        "seller_commission": seller_commission,
        "manual_bank_fee_percent": manual_bank_fee_percent,
    }

    return render_template(
        "index.html",
        form=form_values,
        banks=BANKS,
        bank_form=bank_form,
        results=results,
        tax_rate_percent=TAX_RATE_PERCENT,
        shipping_amount=FIXED_SHIPPING_AMOUNT,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
