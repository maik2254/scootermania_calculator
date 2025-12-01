from flask import Flask, render_template, request

app = Flask(__name__)


def parse_bank_fees(text: str):
    text = text.strip()
    if not text:
        return [], 0.0

    parts = text.replace("%", "").split(",")
    fees = []
    total = 0.0
    for part in parts:
        p = part.strip()
        if not p:
            continue
        v = float(p)
        fees.append(v)
        total += v
    return fees, total


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None

    if request.method == "POST":
        try:
            base_price = float(request.form.get("base_price") or 0)
            tax_rate = float(request.form.get("tax_rate") or 0)
            bank_fees_text = request.form.get("bank_fees") or ""
            cost_price = float(request.form.get("cost_price") or 0)
            seller_commission = float(request.form.get("seller_commission") or 0)

            if base_price <= 0:
                raise ValueError("Base price must be greater than 0")

            fee_parts, total_bank_fee_pct = parse_bank_fees(bank_fees_text)

            tax_amount = base_price * (tax_rate / 100)
            subtotal_with_tax = base_price + tax_amount

            # Case 1: you DON'T pass fees
            bank_fee_amount_not_passed = subtotal_with_tax * (
                total_bank_fee_pct / 100
            )
            net_not_passed = subtotal_with_tax - bank_fee_amount_not_passed
            profit_not_passed = net_not_passed - cost_price - seller_commission

            # Case 2: you DO pass fees
            if total_bank_fee_pct >= 100:
                customer_price_passed = None
                net_passed = None
                profit_passed = None
            else:
                factor = 1 - (total_bank_fee_pct / 100)
                customer_price_passed = (
                    subtotal_with_tax / factor if factor > 0 else None
                )
                if customer_price_passed is not None:
                    total_fees_passed = (
                        customer_price_passed * (total_bank_fee_pct / 100)
                    )
                    net_passed = customer_price_passed - total_fees_passed
                    profit_passed = net_passed - cost_price - seller_commission
                else:
                    net_passed = None
                    profit_passed = None

            result = {
                "base_price": base_price,
                "tax_rate": tax_rate,
                "bank_fees_text": bank_fees_text,
                "cost_price": cost_price,
                "seller_commission": seller_commission,
                "fee_parts": fee_parts,
                "total_bank_fee_pct": total_bank_fee_pct,
                "tax_amount": tax_amount,
                "subtotal_with_tax": subtotal_with_tax,
                "bank_fee_amount_not_passed": bank_fee_amount_not_passed,
                "net_not_passed": net_not_passed,
                "profit_not_passed": profit_not_passed,
                "customer_price_passed": customer_price_passed,
                "net_passed": net_passed,
                "profit_passed": profit_passed,
            }

        except ValueError as e:
            error = str(e)
        except Exception:
            error = "Please enter valid numbers."

    return render_template("index.html", result=result, error=error)
    

if __name__ == "__main__":
    # For local testing
    app.run(host="0.0.0.0", port=5000, debug=True)
