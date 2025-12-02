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
    "dignifi": ("Dignifi", "Dignifi", [6.0, 8.0, 10.0]),
    "square": ("Square Installments", "Square Installments", [3.0, 5.0, 7.0]),
    "wave": ("Wave Financing", "Wave Financing", [2.0, 4.0, 6.0]),
}


def parse_float(value, default=0.0):
    """Convert form string to float, safely."""
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

    # --- Defaults for form fields ---
    form_values = {
        "total_price": "",
        "include_shipping": True,
        "tax_rate": TAX_RATE_PERCENT,  # Always 7, shown but not editable
        "bike_cost": "",
        "seller_commission": "",
        "theme": theme,
        "language": lang,
    }

    # Bank form values (amount + selected rate)
    bank_form = {}
    for key, (name_en, name_es, rates) in BANKS.items():
        bank_form[key] = {
            "amount": "",
            "rate": rates[0],
            "name_en": name_en,
            "name_es": name_es,
            "rates": rates,
        }

    results = None

    if request.method == "POST":
        # --- Core inputs ---
        total_price = parse_float(request.form.get("total_price"))
        include_shipping = request.form.get("include_shipping") == "on"
        # tax_rate is fixed constant:
        tax_rate_percent = TAX_RATE_PERCENT
        bike_cost = parse_float(request.form.get("bike_cost"))
        seller_commission = parse_float(request.form.get("seller_commission"))

        form_values["total_price"] = total_price if total_price else ""
        form_values["include_shipping"] = include_shipping
        form_values["bike_cost"] = bike_cost if bike_cost else ""
        form_values["seller_commission"] = seller_commission if seller_commission else ""

        # --- Bank inputs ---
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

        # Case A: merchant DOES NOT pass bank fees to customer
        net_to_store_no_bank_pass = gross_income_no_shipping - total_bank_fees
        profit_no_bank_pass = (
            net_to_store_no_bank_pass - bike_cost - seller_commission
        )

        # Case B: merchant PASSES bank fees to customer (customer pays them on top)
        customer_price_with_fees = total_price + total_bank_fees
        net_to_store_with_bank_pass = gross_income_no_shipping

        # Commission when PASSING fees:
        # We treat the last line as commission amount based on bike margin
        commission_pass_total = bike_price_before_tax - bike_cost
        if commission_pass_total < 0:
            commission_pass_total = 0.0
        commission_pass_store = commission_pass_total / 2.0
        commission_pass_seller = commission_pass_total / 2.0

        # For the legacy "profit_with_pass" field we now surface the commission total
        profit_with_bank_pass = commission_pass_total

        # --- Total financed amounts (for "amount missing" field) ---
        total_financed_principal = sum(
            (b["amount"] or 0.0) for b in bank_results
        )
        total_financed_with_fees = sum(
            (b["amount"] or 0.0) + (b["fee"] or 0.0) for b in bank_results
        )
        # This is what you asked for:
        # total price - (all financed amounts + their fees)
        missing_amount = total_price - total_financed_with_fees if total_price else 0.0

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
                "missing_amount": "Monto que falta por financiar (precio total menos monto financiado + comisiones):",
                "no_pass_net": "Si NO Pasas Comisión Del Banco – Neto a la tienda:",
                "no_pass_profit": "Si NO Pasas Comisión Del Banco – Ganancia después de costo + comisión:",
                "pass_price": "Si PASAS Comisión Del Banco – Precio al cliente (incl. comisiones):",
                "pass_net": "Si PASAS Comisión Del Banco – Neto a la tienda (solo moto + impuesto):",
                "pass_profit": "Si PASAS Comisión Del Banco – Comisión total (margen de moto después de costo):",
                "commission_pass_total": "Comisión total (margen de moto con comisiones del banco pasadas):",
                "commission_pass_store": "Comisión para la tienda (50%):",
                "commission_pass_seller": "Comisión para el vendedor (50%):",
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
                "missing_amount": "Amount missing from total price (price minus financed amount + fees):",
                "no_pass_net": "If you DO NOT pass bank fees – Net to store:",
                "no_pass_profit": "If you DO NOT pass bank fees – Profit after cost + commission:",
                "pass_price": "If you PASS bank fees – Customer price (incl. fees):",
                "pass_net": "If you PASS bank fees – Net to store (bike + tax only):",
                "pass_profit": "If you PASS bank fees – Commission total (bike margin after cost):",
                "commission_pass_total": "Commission total (bike margin when passing bank fees):",
                "commission_pass_store": "Commission share – store (50%):",
                "commission_pass_seller": "Commission share – seller (50%):",
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
            "commission_pass_total": commission_pass_total,
            "commission_pass_store": commission_pass_store,
            "commission_pass_seller": commission_pass_seller,
            "missing_amount": missing_amount,
            "bank_results": bank_results,
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
