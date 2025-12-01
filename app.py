from flask import Flask, render_template, request

app = Flask(__name__)

# ---------- TEXTS (EN / ES) ----------

TEXTS = {
    "en": {
        "title": "ScooterMania - Financing Calculator (Web)",
        "lang_label": "Language",
        "lang_en": "English",
        "lang_es": "Spanish",

        "total_price": "TOTAL price (customer pays):",
        "tax_rate": "Tax rate % (FL):",
        "shipping_toggle": "Include default $900 shipping in total?",
        "bank_fees": "Bank fee % (one or multiple, e.g. 4.5 or 4.5, 3):",
        "cost_price": "Bike cost to you:",
        "seller_commission": "Seller commission ($):",

        "btn_calculate": "Calculate",
        "btn_clear": "Clear",

        "section_breakdown": "Price breakdown",
        "shipping_label": "Shipping (if included):",
        "minus_shipping": "Total minus shipping:",
        "untaxed_amount": "Amount before tax (no shipping):",
        "tax_amount": "Tax amount:",
        "subtotal_with_tax": "Subtotal with tax (no shipping, no bank fee):",

        "section_bank": "Bank fees & results",
        "bank_breakdown": "Bank fee breakdown:",
        "no_pass_fee": "[If you DO NOT pass fees] Bank fees:",
        "no_pass_net": "[If you DO NOT pass fees] Net to store:",
        "no_pass_profit": "[If you DO NOT pass fees] Profit after commission:",

        "pass_price": "[If you PASS fees] Customer price:",
        "pass_net": "[If you PASS fees] Net to store:",
        "pass_profit": "[If you PASS fees] Profit after commission:",

        "error_numbers": "Please enter valid numbers.",
    },
    "es": {
        "title": "ScooterMania - Calculadora de Financiamiento (Web)",
        "lang_label": "Idioma",
        "lang_en": "Inglés",
        "lang_es": "Español",

        "total_price": "Precio TOTAL (cliente paga):",
        "tax_rate": "Impuesto % (FL):",
        "shipping_toggle": "¿Incluir envío por defecto de $900 en el total?",
        "bank_fees": "Comisión bancaria % (una o varias, ej: 4.5 o 4.5, 3):",
        "cost_price": "Costo de la moto para ti:",
        "seller_commission": "Comisión del vendedor ($):",

        "btn_calculate": "Calcular",
        "btn_clear": "Limpiar",

        "section_breakdown": "Desglose del precio",
        "shipping_label": "Envío (si está incluido):",
        "minus_shipping": "Total menos envío:",
        "untaxed_amount": "Monto antes de impuestos (sin envío):",
        "tax_amount": "Monto de impuesto:",
        "subtotal_with_tax": "Subtotal con impuesto (sin envío, sin comisión bancaria):",

        "section_bank": "Comisiones bancarias & resultados",
        "bank_breakdown": "Detalle de comisiones:",
        "no_pass_fee": "[Si NO pasas comisión] Comisiones:",
        "no_pass_net": "[Si NO pasas comisión] Neto para la tienda:",
        "no_pass_profit": "[Si NO pasas comisión] Ganancia después de comisión:",

        "pass_price": "[Si PASAS comisión] Precio al cliente:",
        "pass_net": "[Si PASAS comisión] Neto para la tienda:",
        "pass_profit": "[Si PASAS comisión] Ganancia después de comisión:",

        "error_numbers": "Por favor ingrese números válidos.",
    },
}


def get_texts(lang_code: str):
    return TEXTS.get(lang_code, TEXTS["en"])


# ---------- CALCULATION ROUTE ----------

@app.route("/", methods=["GET", "POST"])
def index():
    lang = request.form.get("lang", "en")
    txt = get_texts(lang)

    context = {
        "lang": lang,
        "txt": txt,
        "form": {
            "total_price": "",
            "tax_rate": "7.0",
            "shipping_included": "on",  # default checked
            "bank_fees": "",
            "cost_price": "",
            "seller_commission": "",
        },
        "results": None,
        "error": None,
    }

    if request.method == "POST":
        try:
            total_price = float(request.form.get("total_price") or 0)
            tax_rate = float(request.form.get("tax_rate") or 0)
            shipping_included = request.form.get("shipping_included") == "on"
            bank_fees_text = request.form.get("bank_fees", "").strip()
            cost_price = float(request.form.get("cost_price") or 0)
            seller_commission = float(
                request.form.get("seller_commission") or 0
            )

            # save form back into context so it persists on page
            context["form"] = {
                "total_price": total_price,
                "tax_rate": tax_rate,
                "shipping_included": "on" if shipping_included else "",
                "bank_fees": bank_fees_text,
                "cost_price": cost_price,
                "seller_commission": seller_commission,
            }

            # ---- SHIPPING & TAX BREAKDOWN ----
            SHIPPING_DEFAULT = 900.0
            shipping_amount = SHIPPING_DEFAULT if shipping_included else 0.0

            total_minus_shipping = total_price - shipping_amount

            # avoid division by zero if tax_rate=0
            if tax_rate > 0:
                tax_multiplier = 1 + (tax_rate / 100.0)
                untaxed_amount = total_minus_shipping / tax_multiplier
            else:
                untaxed_amount = total_minus_shipping

            tax_amount = total_minus_shipping - untaxed_amount

            # this is equivalent to the "subtotal with tax (no bank fee)" used for bank fees
            subtotal_with_tax = total_minus_shipping

            # ---- BANK FEES ----
            total_bank_fee_pct = 0.0
            fee_parts = []
            if bank_fees_text:
                raw_parts = bank_fees_text.replace("%", "").split(",")
                for part in raw_parts:
                    p = part.strip()
                    if not p:
                        continue
                    value = float(p)
                    fee_parts.append(value)
                    total_bank_fee_pct += value

            # Case 1: you DO NOT pass bank fees
            bank_fees_no_pass = subtotal_with_tax * (total_bank_fee_pct / 100.0)
            net_no_pass = subtotal_with_tax - bank_fees_no_pass
            profit_no_pass = net_no_pass - cost_price - seller_commission

            # Case 2: you DO pass bank fees
            if total_bank_fee_pct >= 100:
                customer_price_pass = None
                net_pass = None
                profit_pass = None
            else:
                factor = 1 - (total_bank_fee_pct / 100.0)
                if factor > 0:
                    customer_price_pass = subtotal_with_tax / factor
                    total_fees_pass = customer_price_pass * (
                        total_bank_fee_pct / 100.0
                    )
                    net_pass = customer_price_pass - total_fees_pass
                    profit_pass = net_pass - cost_price - seller_commission
                else:
                    customer_price_pass = None
                    net_pass = None
                    profit_pass = None

            # Format bank fee breakdown
            if fee_parts:
                breakdown_str = " + ".join(f"{p:.2f}%" for p in fee_parts)
                breakdown_str += f" = {total_bank_fee_pct:.2f}%"
            else:
                breakdown_str = "0.00%"

            context["results"] = {
                "shipping_amount": shipping_amount,
                "total_minus_shipping": total_minus_shipping,
                "untaxed_amount": untaxed_amount,
                "tax_amount": tax_amount,
                "subtotal_with_tax": subtotal_with_tax,
                "bank_breakdown": breakdown_str,
                "bank_fees_no_pass": bank_fees_no_pass,
                "net_no_pass": net_no_pass,
                "profit_no_pass": profit_no_pass,
                "customer_price_pass": customer_price_pass,
                "net_pass": net_pass,
                "profit_pass": profit_pass,
            }

        except ValueError:
            context["error"] = txt["error_numbers"]

    return render_template("index.html", **context)


if __name__ == "__main__":
    # For local testing; on Render you'll use gunicorn / waitress, etc.
    app.run(debug=True, host="0.0.0.0", port=5000)
