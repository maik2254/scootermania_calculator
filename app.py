from flask import Flask, render_template, request

app = Flask(__name__)

FIXED_SHIPPING = 900.0

# Bank config: key, label, fixed_rates or dropdown options
BANKS = [
    {
        "key": "aff",
        "name": "American First Finance",
        "dropdown": False,
        "default_rate": 5.0,
        "options": [],
    },
    {
        "key": "acima",
        "name": "Acima",
        "dropdown": False,
        "default_rate": 3.0,  # adjust if you want 0 sometimes
        "options": [],
    },
    {
        "key": "dignify",
        "name": "Dignify",
        "dropdown": True,
        "default_rate": 6.5,
        "options": [6.5, 9.0],
    },
    {
        "key": "synchrony",
        "name": "Synchrony",
        "dropdown": True,
        "default_rate": 5.0,
        "options": [5.0, 9.0, 13.5],
    },
    {
        "key": "afterpay",
        "name": "Afterpay",
        "dropdown": False,
        "default_rate": 6.0,
        "options": [],
    },
    {
        "key": "usbank",
        "name": "US Bank",
        "dropdown": True,
        "default_rate": 5.0,
        "options": [5.0, 8.0, 10.0, 12.0, 14.0, 16.0],
    },
    {
        "key": "snap",
        "name": "Snap Finance",
        "dropdown": False,
        "default_rate": 2.0,
        "options": [],
    },
    {
        "key": "progressive",
        "name": "Progressive",
        "dropdown": False,
        "default_rate": 2.0,
        "options": [],
    },
    {
        "key": "zip",
        "name": "Zip",
        "dropdown": False,
        "default_rate": 6.0,
        "options": [],
    },
    {
        "key": "klarna",
        "name": "Klarna",
        "dropdown": False,
        "default_rate": 6.0,
        "options": [],
    },
]

TEXTS = {
    "en": {
        "title": "ScooterMania - Financing Price Calculator (Web)",
        "language": "Language",
        "lang_en": "English",
        "lang_es": "Español",

        "total_price": "Total price to customer (incl. shipping):",
        "include_shipping": "Include fixed shipping $900 (not taxed, not revenue)",
        "tax_rate": "Tax rate % (FL):",
        "manual_bank_fee": "Manual bank fee % (one or multiple, applies on bike+tax):",
        "manual_example": "Ex: 4.5 or 4.5, 3",
        "bike_cost": "Bike cost to you ($):",
        "seller_commission": "Seller commission ($):",

        "financing_title": "Financing companies (enter AMOUNT financed for this deal):",
        "financing_note": "Each amount uses that company's merchant fee rate.",

        "calculate": "Calculate",
        "clear": "Clear",

        "results_title": "Results",
        "bike_before_tax": "Bike price before tax:",
        "tax_amount": "Tax amount:",
        "subtotal_bike_tax": "Subtotal with tax (bike only):",
        "shipping": "Shipping (not taxed, not revenue):",
        "cash_total": "Cash total to customer (bike + tax + shipping):",

        "bank_breakdown": "Bank fee breakdown:",
        "total_bank_fees": "Total bank fees (all companies + manual):",

        "no_pass_title": "If you DO NOT pass bank fees to customer:",
        "no_pass_fees": "Bank fees you pay:",
        "no_pass_net": "Net to store (bike only):",
        "no_pass_profit": "Profit after commission:",

        "pass_title": "If you PASS bank fees to customer:",
        "pass_customer_price": "Customer price (incl. shipping):",
        "pass_net": "Net to store (bike only):",
        "pass_profit": "Profit after commission:",

        "error": "Error",
        "error_price": "Total price must be greater than 0.",
        "error_numbers": "Please enter valid numbers.",
    },
    "es": {
        "title": "ScooterMania - Calculadora de Financiamiento (Web)",
        "language": "Idioma",
        "lang_en": "Inglés",
        "lang_es": "Español",

        "total_price": "Precio total al cliente (incl. envío):",
        "include_shipping": "Incluir envío fijo $900 (sin impuestos, sin ingreso)",
        "tax_rate": "Impuesto % (FL):",
        "manual_bank_fee": "Comisión bancaria manual % (una o varias, sobre moto+impuesto):",
        "manual_example": "Ej: 4.5 o 4.5, 3",
        "bike_cost": "Costo de la moto para ti ($):",
        "seller_commission": "Comisión del vendedor ($):",

        "financing_title": "Financieras (ingrese MONTO financiado para esta venta):",
        "financing_note": "Cada monto usa el % de comisión de la financiera.",

        "calculate": "Calcular",
        "clear": "Limpiar",

        "results_title": "Resultados",
        "bike_before_tax": "Precio de la moto antes de impuestos:",
        "tax_amount": "Monto de impuesto:",
        "subtotal_bike_tax": "Subtotal con impuesto (solo moto):",
        "shipping": "Envío (sin impuestos, sin ingreso):",
        "cash_total": "Total al cliente (moto + imp + envío):",

        "bank_breakdown": "Detalle de comisiones bancarias:",
        "total_bank_fees": "Total comisiones bancarias (todas + manual):",

        "no_pass_title": "Si NO pasas las comisiones al cliente:",
        "no_pass_fees": "Comisiones bancarias que pagas:",
        "no_pass_net": "Neto para la tienda (solo moto):",
        "no_pass_profit": "Ganancia después de comisión:",

        "pass_title": "Si PASAS las comisiones al cliente:",
        "pass_customer_price": "Precio al cliente (incl. envío):",
        "pass_net": "Neto para la tienda (solo moto):",
        "pass_profit": "Ganancia después de comisión:",

        "error": "Error",
        "error_price": "El precio total debe ser mayor que 0.",
        "error_numbers": "Por favor ingrese números válidos.",
    },
}


def parse_float(s):
    try:
        s = (s or "").strip()
        if not s:
            return 0.0
        return float(s)
    except ValueError:
        raise


@app.route("/", methods=["GET", "POST"])
def index():
    lang = request.form.get("lang", "en")
    if lang not in ("en", "es"):
        lang = "en"
    tx = TEXTS[lang]

    inputs = {
        "lang": lang,
        "total_price": request.form.get("total_price", ""),
        "include_shipping": request.form.get("include_shipping", "on"),
        "tax_rate": request.form.get("tax_rate", "7.0"),
        "manual_bank_fee": request.form.get("manual_bank_fee", ""),
        "bike_cost": request.form.get("bike_cost", ""),
        "seller_commission": request.form.get("seller_commission", ""),
        "banks": {},
    }

    for bank in BANKS:
        key = bank["key"]
        amount_field = f"{key}_amount"
        rate_field = f"{key}_rate"
        inputs["banks"][key] = {
            "amount": request.form.get(amount_field, ""),
            "rate": request.form.get(rate_field, str(bank["default_rate"])),
        }

    error = None
    results = None
    bank_breakdown = []

    if request.method == "POST":
        try:
            total_price = parse_float(inputs["total_price"])
            tax_rate = parse_float(inputs["tax_rate"])
            bike_cost = parse_float(inputs["bike_cost"])
            seller_commission = parse_float(inputs["seller_commission"])

            if total_price <= 0:
                error = tx["error_price"]
            else:
                include_shipping = inputs["include_shipping"] == "on"
                shipping = FIXED_SHIPPING if include_shipping else 0.0

                taxable_total = total_price - shipping
                if taxable_total < 0:
                    error = tx["error_price"]
                else:
                    if tax_rate > 0:
                        bike_before_tax = taxable_total / (1 + tax_rate / 100.0)
                    else:
                        bike_before_tax = taxable_total
                    tax_amount = taxable_total - bike_before_tax

                    # Manual bank fee % on bike+tax total
                    manual_fee_str = inputs["manual_bank_fee"].strip()
                    manual_fee_amount = 0.0
                    manual_parts = []
                    if manual_fee_str:
                        for part in manual_fee_str.replace("%", "").split(","):
                            p = part.strip()
                            if not p:
                                continue
                            pct = float(p)
                            manual_fee_amount += taxable_total * (pct / 100.0)
                            manual_parts.append(pct)

                    # Per-bank fees on financed AMOUNTS
                    total_bank_fees_banks = 0.0
                    for bank in BANKS:
                        key = bank["key"]
                        name = bank["name"]
                        amount_str = inputs["banks"][key]["amount"]
                        amount = parse_float(amount_str)
                        if amount <= 0:
                            continue

                        if bank["dropdown"]:
                            rate = parse_float(inputs["banks"][key]["rate"])
                        else:
                            rate = bank["default_rate"]

                        fee = amount * (rate / 100.0)
                        total_bank_fees_banks += fee
                        bank_breakdown.append(
                            f"{name}: ${amount:,.2f} × {rate:.2f}% = ${fee:,.2f}"
                        )

                    if manual_fee_amount > 0 and manual_parts:
                        mpct = " + ".join(f"{p:.2f}%" for p in manual_parts)
                        bank_breakdown.append(
                            f"Manual: {mpct} on ${taxable_total:,.2f} = ${manual_fee_amount:,.2f}"
                        )

                    total_bank_fees = total_bank_fees_banks + manual_fee_amount

                    # Scenario A: DO NOT pass fees
                    net_no_pass = bike_before_tax - total_bank_fees
                    profit_no_pass = net_no_pass - bike_cost - seller_commission

                    # Scenario B: PASS fees
                    customer_price_pass = total_price + total_bank_fees
                    net_pass = bike_before_tax
                    profit_pass = net_pass - bike_cost - seller_commission

                    results = {
                        "bike_before_tax": bike_before_tax,
                        "tax_amount": tax_amount,
                        "taxable_total": taxable_total,
                        "shipping": shipping,
                        "cash_total": total_price,
                        "total_bank_fees": total_bank_fees,
                        "net_no_pass": net_no_pass,
                        "profit_no_pass": profit_no_pass,
                        "customer_price_pass": customer_price_pass,
                        "net_pass": net_pass,
                        "profit_pass": profit_pass,
                    }

        except ValueError:
            error = tx["error_numbers"]

    return render_template(
        "index.html",
        tx=tx,
        banks=BANKS,
        inputs=inputs,
        results=results,
        bank_breakdown=bank_breakdown,
        error=error,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
