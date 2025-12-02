from flask import Flask, render_template, request

app = Flask(__name__)

# --- CONSTANTS ---
TAX_RATE_PERCENT = 7.0             # Fixed FL tax
FIXED_SHIPPING_AMOUNT = 900.0      # Fixed shipping, NOT taxed, NOT revenue

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
    """Safely convert a form value to float."""
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return default


@app.route("/", methods=["GET", "POST"])
def index():
    # ---------- Language & theme ----------
    lang = request.values.get("language", "en")
    if lang not in ("en", "es"):
        lang = "en"

    theme = request.values.get("theme", "dark")
    if theme not in ("dark", "light"):
        theme = "dark"

    # ---------- Default form values ----------
    form_values = {
        "total_price": "",
        "include_shipping": True,
        "tax_rate": TAX_RATE_PERCENT,  # shown but NOT editable
        "bike_cost": "",
        "seller_commission": "",       # still in form, even if not used in math now
    }

    # Bank form values (amount + selected rate)
    bank_form = {}
    for key, (_, _, rates) in BANKS.items():
        bank_form[key] = {
            "amount": "",
            "rate": rates[0],  # default rate
        }

    results = None

    # ---------- POST: do the calculation ----------
    if request.method == "POST":
        # Main numeric inputs
        total_price = parse_float(request.form.get("total_price"))
        include_shipping = request.form.get("include_shipping") == "on"
        bike_cost = parse_float(request.form.get("bike_cost"))
        seller_commission = parse_float(request.form.get("seller_commission"))  # kept for display if you want

        # Lock tax at 7%, ignore anything user typed into tax field
        tax_rate_percent = TAX_RATE_PERCENT

        # Keep values for re-fill in form
        form_values["total_price"] = total_price if total_price else ""
        form_values["include_shipping"] = include_shipping
        form_values["bike_cost"] = bike_cost if bike_cost else ""
        form_values["seller_commission"] = seller_commission if seller_commission else ""

        # ---------- Read bank inputs ----------
        bank_results = []
        total_bank_fees = 0.0

        for key, (name_en, name_es, rates) in BANKS.items():
            amount_field = f"{key}_amount"
            rate_field = f"{key}_rate"

            amount = parse_float(request.form.get(amount_field))
            rate = parse_float(request.form.get(rate_field), rates[0])

            bank_form[key]["amount"] = amount if amount else ""
            bank_form[key]["rate"] = rate

            if amount > 0 and rate > 0:
                fee = amount * (rate / 100.0)
            else:
                fee = 0.0

            total_bank_fees += fee

            bank_results.append(
                {
                    "key": key,
                    "name_en": name_en,
                    "name_es": name_es,
                    "amount": amount,
                    "rate": rate,
                    "fee": fee,
                }
            )

        # ---------- Core math ----------
        shipping_amount = FIXED_SHIPPING_AMOUNT if include_shipping else 0.0

        # Portion of total that is bike + tax only (shipping is NOT taxed & NOT revenue)
        bike_plus_tax = max(total_price - shipping_amount, 0.0)

        tax_rate = tax_rate_percent / 100.0
        if bike_plus_tax > 0 and tax_rate >= 0:
            bike_price_before_tax = bike_plus_tax / (1.0 + tax_rate)
        else:
            bike_price_before_tax = 0.0

        tax_amount = bike_plus_tax - bike_price_before_tax

        # This is what actually comes in from the deal (bike + tax, no shipping)
        gross_income_no_shipping = bike_plus_tax

        # ---------- Case A: you do NOT pass bank fees ----------
        net_to_store_no_bank_pass = gross_income_no_shipping - total_bank_fees
        # Profit here = net to store after bank fees - bike cost
        # (NOT subtracting seller_commission, since you want the "deal profit")
        profit_no_bank_pass = net_to_store_no_bank_pass - bike_cost

        # ---------- Case B: you PASS bank fees ----------
        # Customer pays bank fees on top of total
        customer_price_with_fees = total_price + total_bank_fees
        # Store still only keeps bike + tax (no shipping as revenue)
        net_to_store_with_bank_pass = gross_income_no_shipping

        # You told me: when you pass fees, that last line should be 900 in your example.
        # That corresponds to: bike_price_before_tax - bike_cost
        profit_with_bank_pass = bike_price_before_tax - bike_cost

        # ---------- Labels (EN / ES) ----------
        if lang == "es":
            labels = {
                "results_title": "Resultados",
                "bike_before_tax": "Precio de la moto antes de impuestos:",
                "tax_amount": "Monto de impuesto:",
                "subtotal_no_shipping": "Subtotal con impuesto (sin envío):",
                "shipping": "Envío (no ingreso):",
                "gross_income": "Ingreso bruto (solo moto + impuesto):",
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
            "bike_before_tax": bike_price_before_tax,
            "tax_amount": tax_amount,
            "subtotal_no_shipping": bike_plus_tax,
            "shipping": shipping_amount,
            "gross_income": gross_income_no_shipping,
            "total_bank_fees": total_bank_fees,
            "net_no_pass": net_to_store_no_bank_pass,
            "profit_no_pass": profit_no_bank_pass,
            "customer_price_with_fees": customer_price_with_fees,
            "net_with_pass": net_to_store_with_bank_pass,
            "profit_with_pass": profit_with_bank_pass,
            "bank_results": bank_results,
        }

    # ---------- Render ----------
    return render_template(
        "index.html",
        form=form_values,
        banks=BANKS,
        bank_form=bank_form,
        results=results,
        tax_rate_percent=TAX_RATE_PERCENT,
        shipping_amount=FIXED_SHIPPING_AMOUNT,
        language=lang,
        theme=theme,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
