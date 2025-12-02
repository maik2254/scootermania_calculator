from flask import Flask, render_template, request

app = Flask(__name__)

# ------------ CONSTANTS ------------
TAX_RATE_PERCENT = 7.0              # Fixed FL tax
FIXED_SHIPPING_AMOUNT = 900.0       # Fixed shipping, not taxed, not revenue

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
    """Safely parse a float from form values."""
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return default


@app.route("/", methods=["GET", "POST"])
def index():
    # ---------- Language & Theme ----------
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
        "tax_rate": TAX_RATE_PERCENT,  # displayed but not editable
        "bike_cost": "",
        "seller_commission": "",
        "theme": theme,
        "language": lang,
    }

    # Bank form values initial state
    bank_form = {}
    for key, (_, _, rates) in BANKS.items():
        bank_form[key] = {
            "amount": "",
            "rate": rates[0],
        }

    results = None

    # ---------- Handle POST / calculations ----------
    if request.method == "POST":
        # Main numeric inputs
        total_price = parse_float(request.form.get("total_price"))
        include_shipping = request.form.get("include_shipping") == "on"
        # Tax rate is fixed at constant
        tax_rate_percent = TAX_RATE_PERCENT
        bike_cost = parse_float(request.form.get("bike_cost"))
        seller_commission_input = parse_float(request.form.get("seller_commission"))

        form_values["total_price"] = total_price if total_price else ""
        form_values["include_shipping"] = include_shipping
        form_values["bike_cost"] = bike_cost if bike_cost else ""
        form_values["seller_commission"] = (
            seller_commission_input if seller_commission_input else ""
        )

        # ----- Bank inputs -----
        bank_results = []
        total_bank_fees = 0.0
        total_financed_principal = 0.0  # sum of amounts only

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

            total_financed_principal += amount
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

        # Bike + tax part of total price (shipping is not taxed, not revenue)
        bike_plus_tax = max(total_price - shipping_amount, 0.0)

        tax_rate = tax_rate_percent / 100.0
        if bike_plus_tax > 0 and tax_rate >= 0:
            bike_price_before_tax = bike_plus_tax / (1.0 + tax_rate)
        else:
            bike_price_before_tax = 0.0

        tax_amount = bike_plus_tax - bike_price_before_tax

        # Income the store gets from the sale (bike + tax only, no shipping)
        gross_income = bike_plus_tax

        # Case A: merchant does NOT pass bank fees to the customer
        net_no_pass = gross_income - total_bank_fees
        # Profit if you eat the bank fees: after bike cost, before commission split
        profit_no_pass = net_no_pass - bike_cost

        # Case B: merchant PASSES bank fees to the customer
        customer_price_with_fees = total_price + total_bank_fees
        net_with_pass = gross_income  # store keeps bike + tax; customer pays fees on top

        # Commission logic: margin on the bike (before tax) vs cost
        commission_total = bike_price_before_tax - bike_cost
        if commission_total < 0:
            commission_total = 0.0
        commission_store = commission_total / 2.0
        commission_seller = commission_total / 2.0

        # For the last line ("profit after cost + commission") the user
        # wants to treat it as total commission amount when fees are passed.
        profit_with_pass = commission_total

        # Total financed INCLUDING fees (for missing amount calculation)
        total_financed_including_fees = 0.0
        for b in bank_results:
            total_financed_including_fees += b["amount"] + b["fee"]

        # Amount missing from total price
        missing_amount = total_price - total_financed_including_fees

        # ---------- Labels ----------
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
                "no_pass_profit": "Si NO Pasas Comisión Del Banco – Ganancia después de costo:",
                "pass_price": "Si PASAS Comisión Del Banco – Precio al cliente (incl. comisiones):",
                "pass_net": "Si PASAS Comisión Del Banco – Neto a la tienda (solo moto + impuesto):",
                "pass_profit": "Si PASAS Comisión Del Banco – Comisión total (tienda + vendedor):",
                "commission_total": "Comisión total (tienda + vendedor):",
                "commission_store": "Comisión de la tienda (50%):",
                "commission_seller": "Comisión del vendedor (50%):",
                "missing_amount": "Monto faltante del precio total:",
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
                "no_pass_profit": "If you DO NOT pass bank fees – Profit after cost:",
                "pass_price": "If you PASS bank fees – Customer price (incl. fees):",
                "pass_net": "If you PASS bank fees – Net to store (bike + tax only):",
                "pass_profit": "If you PASS bank fees – Total commission (store + seller):",
                "commission_total": "Total commission (store + seller):",
                "commission_store": "Store commission (50%):",
                "commission_seller": "Seller commission (50%):",
                "missing_amount": "Missing amount from total price:",
                "bank_breakdown_title": "Bank fee breakdown by company:",
            }

        results = {
            "labels": labels,
            "bike_before_tax": bike_price_before_tax,
            "tax_amount": tax_amount,
            "subtotal_no_shipping": bike_plus_tax,
            "shipping": shipping_amount,
            "gross_income": gross_income,
            "total_bank_fees": total_bank_fees,
            "net_no_pass": net_no_pass,
            "profit_no_pass": profit_no_pass,
            "customer_price_with_fees": customer_price_with_fees,
            "net_with_pass": net_with_pass,
            "profit_with_pass": profit_with_pass,
            "bank_results": bank_results,
            "commission_total": commission_total,
            "commission_store": commission_store,
            "commission_seller": commission_seller,
            "missing_amount": missing_amount,
            "total_financed_principal": total_financed_principal,
            "total_financed_including_fees": total_financed_including_fees,
        }

    # ---------- Render template ----------
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
