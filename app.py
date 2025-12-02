from flask import Flask, render_template, request

app = Flask(__name__)

# Fixed tax & shipping rules
TAX_RATE = 7.0
SHIPPING_FIXED = 900.0

# Text in both languages
LANG = {
    "en": {
        "title": "ScooterMania – Financing Price Calculator (Web)",
        "language_label": "Language",
        "theme_label": "Theme",
        "total_price_label": "Total price to customer (incl. shipping):",
        "shipping_toggle": "Include fixed shipping $900 (not taxed, not revenue)",
        "tax_rate_label": "Tax rate % (FL):",
        "bike_cost_label": "Bike cost to you ($):",
        "seller_commission_label": "Seller commission ($):",
        "financing_section_title": "Financing companies (enter AMOUNT financed for this deal):",
        "financing_section_hint": "Each amount uses that company's merchant fee rate.",
        "results_title": "Results",
        "bike_before_tax": "Bike price before tax:",
        "tax_amount": "Tax amount:",
        "subtotal_with_tax": "Subtotal with tax (bike only):",
        "shipping_not_revenue": "Shipping (not revenue):",
        "total_customer_price": "Cash total to customer (bike + tax + shipping):",
        "bank_fees_total": "Bank fees (if you do NOT pass fees):",
        "bank_fee_breakdown": "Bank fee breakdown (total %):",
        "gross_income_bike_tax": "Gross income (bike + tax only):",
        "no_pass_net_store": "If you DO NOT pass bank fees – Net to store (bike only):",
        "no_pass_profit": "If you DO NOT pass bank fees – Profit after cost + commission:",
        "pass_customer_price": "If you PASS bank fees – Customer price (incl. commissions):",
        "pass_net_store": "If you PASS bank fees – Net to store (bike only):",
        "pass_profit": "If you PASS bank fees – Profit after cost + commission:",
        "calculate": "Calculate",
        "clear": "Clear",
    },
    "es": {
        "title": "ScooterMania – Calculadora de Precio con Financiamiento (Web)",
        "language_label": "Idioma",
        "theme_label": "Tema",
        "total_price_label": "Precio total al cliente (incl. envío):",
        "shipping_toggle": "Incluir envío fijo de $900 (no tributado, no ingreso)",
        "tax_rate_label": "Impuesto % (FL):",
        "bike_cost_label": "Costo de la moto para ti ($):",
        "seller_commission_label": "Comisión del vendedor ($):",
        "financing_section_title": "Financieras (ingresa el MONTO financiado en este negocio):",
        "financing_section_hint": "Cada monto usa la comisión de comerciante de esa financiera.",
        "results_title": "Resultados",
        "bike_before_tax": "Precio de la moto antes de impuestos:",
        "tax_amount": "Monto de impuesto:",
        "subtotal_with_tax": "Subtotal con impuesto (solo moto):",
        "shipping_not_revenue": "Envío (no ingreso):",
        "total_customer_price": "Total al cliente en efectivo (moto + impuesto + envío):",
        "bank_fees_total": "Comisiones bancarias (si NO PASAS comisión del banco):",
        "bank_fee_breakdown": "Comisiones bancarias totales:",
        "gross_income_bike_tax": "Ingreso bruto (solo moto + impuesto):",
        "no_pass_net_store": "Si NO PASAS comisión del banco – Neto a la tienda (solo moto):",
        "no_pass_profit": "Si NO PASAS comisión del banco – Ganancia después de costo + comisión:",
        "pass_customer_price": "Si PASAS comisión del banco – Precio al cliente (incl. comisiones):",
        "pass_net_store": "Si PASAS comisión del banco – Neto a la tienda (solo moto):",
        "pass_profit": "Si PASAS comisión del banco – Ganancia después de costo + comisión:",
        "calculate": "Calcular",
        "clear": "Limpiar",
    },
}

# Bank config: default rates + allowed options for dropdowns
BANKS = [
    {
        "key": "aff",
        "name_en": "American First Finance",
        "name_es": "American First Finance",
        "rate_default": 5.0,
        "rate_choices": None,          # free text
    },
    {
        "key": "acima",
        "name_en": "Acima",
        "name_es": "Acima",
        "rate_default": 0.0,
        "rate_choices": [0.0, 3.0],    # 0% or 3%
    },
    {
        "key": "dignify",
        "name_en": "Dignify",
        "name_es": "Dignify",
        "rate_default": 6.5,
        "rate_choices": [6.5, 9.0],    # 6.5% or 9%
    },
    {
        "key": "synchrony",
        "name_en": "Synchrony",
        "name_es": "Synchrony",
        "rate_default": 5.0,
        "rate_choices": [5.0, 9.0, 13.5],  # dropdown
    },
    {
        "key": "afterpay",
        "name_en": "Afterpay",
        "name_es": "Afterpay",
        "rate_default": 6.0,
        "rate_choices": None,
    },
    {
        "key": "us_bank",
        "name_en": "US Bank",
        "name_es": "US Bank",
        "rate_default": 5.0,
        "rate_choices": [5.0, 8.0, 10.0, 12.0, 14.0, 16.0],
    },
    {
        "key": "snap",
        "name_en": "Snap Finance",
        "name_es": "Snap Finance",
        "rate_default": 2.0,
        "rate_choices": None,
    },
    {
        "key": "progressive",
        "name_en": "Progressive",
        "name_es": "Progressive",
        "rate_default": 2.0,
        "rate_choices": None,
    },
    {
        "key": "zip",
        "name_en": "Zip",
        "name_es": "Zip",
        "rate_default": 6.0,
        "rate_choices": None,
    },
    {
        "key": "klarna",
        "name_en": "Klarna",
        "name_es": "Klarna",
        "rate_default": 6.0,
        "rate_choices": None,
    },
]


def fmt_money(value):
    """Format numbers as $X,XXX.XX or N/A."""
    if value is None:
        return "N/A"
    return f"${value:,.2f}"


@app.route("/", methods=["GET", "POST"])
def index():
    # language & theme
    lang = request.form.get("language", "en")
    if lang not in LANG:
        lang = "en"
    strings = LANG[lang]

    theme = request.form.get("theme", "dark")
    if theme not in ("dark", "light"):
        theme = "dark"

    results = None

    # default form values
    form_data = {
        "total_price": "",
        "include_shipping": True,
        "bike_cost": "",
        "seller_commission": "",
    }

    # financing form values
    bank_form = {f"{b['key']}_amount": "" for b in BANKS}
    bank_rate_values = {f"{b['key']}_rate": str(b["rate_default"]) for b in BANKS}

    if request.method == "POST":
        action = request.form.get("action", "calculate")

        if action == "clear":
            # Just reset to defaults (no calculation)
            pass
        else:
            # ---- read inputs ----
            total_price = float(request.form.get("total_price", "0") or 0)
            include_shipping = request.form.get("include_shipping") == "on"
            bike_cost = float(request.form.get("bike_cost", "0") or 0)
            seller_commission = float(request.form.get("seller_commission", "0") or 0)

            form_data["total_price"] = total_price if total_price != 0 else ""
            form_data["include_shipping"] = include_shipping
            form_data["bike_cost"] = bike_cost if bike_cost != 0 else ""
            form_data["seller_commission"] = (
                seller_commission if seller_commission != 0 else ""
            )

            # ---- shipping and tax breakdown ----
            shipping = SHIPPING_FIXED if include_shipping else 0.0
            bike_plus_tax = max(total_price - shipping, 0.0)

            if bike_plus_tax > 0:
                base_price = bike_plus_tax / (1 + TAX_RATE / 100)
                tax_amount = bike_plus_tax - base_price
            else:
                base_price = 0.0
                tax_amount = 0.0

            gross_to_customer = bike_plus_tax + shipping

            # ---- bank fees ----
            total_bank_fee_amount = 0.0
            total_bank_fee_pct = 0.0
            breakdown_parts = []

            for bank in BANKS:
                amount_key = f"{bank['key']}_amount"
                rate_key = f"{bank['key']}_rate"

                amount_str = request.form.get(amount_key, "").strip()
                rate_str = request.form.get(rate_key, "").strip()

                # amount financed with that bank
                try:
                    amount = float(amount_str) if amount_str else 0.0
                except ValueError:
                    amount = 0.0

                # rate (respect dropdown limits if defined)
                if bank["rate_choices"]:
                    try:
                        rate = float(rate_str)
                    except ValueError:
                        rate = bank["rate_default"]
                    if rate not in bank["rate_choices"]:
                        rate = bank["rate_default"]
                else:
                    try:
                        rate = float(rate_str) if rate_str else bank["rate_default"]
                    except ValueError:
                        rate = bank["rate_default"]

                bank_form[amount_key] = amount_str
                bank_rate_values[rate_key] = str(rate)

                if amount > 0 and rate > 0:
                    fee_amount = amount * rate / 100.0
                    total_bank_fee_amount += fee_amount
                    total_bank_fee_pct += rate
                    breakdown_parts.append(f"{rate:.2f}%")

            if breakdown_parts:
                breakdown_text = (
                    " + ".join(breakdown_parts)
                    + f" = {total_bank_fee_pct:.2f}%"
                )
            else:
                breakdown_text = "0.00%"

            gross_income_bike_tax = bike_plus_tax

            # ---- Scenario A: you do NOT pass bank fees ----
            net_store_no_pass = bike_plus_tax - total_bank_fee_amount
            profit_no_pass = net_store_no_pass - bike_cost - seller_commission

            # ---- Scenario B: you PASS bank fees (customer pays them) ----
            if 0 < total_bank_fee_pct < 100 and bike_plus_tax > 0:
                factor = 1 - total_bank_fee_pct / 100.0
                adjusted_bike_plus_tax = bike_plus_tax / factor
                customer_price_pass = adjusted_bike_plus_tax + shipping
                net_store_pass = bike_plus_tax
                profit_pass = net_store_pass - bike_cost - seller_commission
            else:
                customer_price_pass = None
                net_store_pass = None
                profit_pass = None

            results = [
                (strings["bike_before_tax"], fmt_money(base_price)),
                (strings["tax_amount"], fmt_money(tax_amount)),
                (strings["subtotal_with_tax"], fmt_money(bike_plus_tax)),
                (strings["shipping_not_revenue"], fmt_money(shipping)),
                (strings["total_customer_price"], fmt_money(gross_to_customer)),
                (strings["bank_fee_breakdown"], breakdown_text),
                (strings["bank_fees_total"], fmt_money(total_bank_fee_amount)),
                (strings["gross_income_bike_tax"], fmt_money(gross_income_bike_tax)),
                (strings["no_pass_net_store"], fmt_money(net_store_no_pass)),
                (strings["no_pass_profit"], fmt_money(profit_no_pass)),
                (strings["pass_customer_price"], fmt_money(customer_price_pass)),
                (strings["pass_net_store"], fmt_money(net_store_pass)),
                (strings["pass_profit"], fmt_money(profit_pass)),
            ]

    return render_template(
        "index.html",
        lang=lang,
        strings=strings,
        theme=theme,
        tax_rate=TAX_RATE,
        banks=BANKS,
        form_data=form_data,
        bank_form=bank_form,
        bank_rate_values=bank_rate_values,
        results=results,
    )


if __name__ == "__main__":
    app.run(debug=True)
