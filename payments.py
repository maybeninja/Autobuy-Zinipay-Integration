import json
import os
import time

PAYMENTS_FILE = "payment.json"


def _ensure():
    if not os.path.exists(PAYMENTS_FILE):
        with open(PAYMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "orders": {},
                    "transactions": {},
                    "zinipay": {}
                },
                f,
                indent=4,
            )


def load():
    _ensure()

    try:
        with open(PAYMENTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        data.setdefault("orders", {})
        data.setdefault("transactions", {})
        data.setdefault("zinipay", {})

        return data

    except Exception:
        return {
            "orders": {},
            "transactions": {},
            "zinipay": {}
        }


def save(data):
    with open(PAYMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def get_payment(orderid):
    data = load()
    return data["orders"].get(str(orderid))


def get_payment_from_transaction(transaction_id):
    data = load()

    orderid = data["transactions"].get(transaction_id)

    if not orderid:
        return None

    return data["orders"].get(orderid)


def get_payment_from_unique_id(unique_id):
    data = load()

    for payment in data["orders"].values():
        if payment.get("unique_id") == unique_id:
            return payment

    return None


def get_payment_from_zini_invoice(invoice_id):
    data = load()

    orderid = data["zinipay"].get(invoice_id)

    if not orderid:
        return None

    return data["orders"].get(orderid)


def save_payment(
    orderid,
    unique_id,
    payment_url,
    amount_eur,
    amount_bdt,
    zini_invoice_id,
):
    data = load()

    orderid = str(orderid)

    data["orders"][orderid] = {
        "invoice_id": orderid,
        "unique_id": unique_id,
        "zini_invoice_id": zini_invoice_id,
        "payment_url": payment_url,
        "transaction_id": None,
        "payment_method": None,
        "status": "PENDING",
        "amount_eur": amount_eur,
        "amount_bdt": amount_bdt,
        "created_at": int(time.time()),
        "completed_at": None,
    }

    data["zinipay"][zini_invoice_id] = orderid

    save(data)


def update_payment(orderid, **kwargs):
    data = load()

    orderid = str(orderid)

    if orderid not in data["orders"]:
        return False

    data["orders"][orderid].update(kwargs)

    transaction_id = kwargs.get("transaction_id")

    if transaction_id:
        data["transactions"][transaction_id] = orderid

    zini_invoice_id = kwargs.get("zini_invoice_id")

    if zini_invoice_id:
        data["zinipay"][zini_invoice_id] = orderid

    save(data)
    return True


def delete_payment(orderid):
    data = load()

    orderid = str(orderid)

    payment = data["orders"].get(orderid)

    if not payment:
        return

    transaction_id = payment.get("transaction_id")

    if transaction_id:
        data["transactions"].pop(transaction_id, None)

    zini_invoice_id = payment.get("zini_invoice_id")

    if zini_invoice_id:
        data["zinipay"].pop(zini_invoice_id, None)

    data["orders"].pop(orderid, None)

    save(data)


def payment_exists(orderid):
    return get_payment(orderid) is not None


def payment_completed(orderid):
    payment = get_payment(orderid)

    if not payment:
        return False

    return payment["status"] == "COMPLETED"


def payment_expired(orderid, expiry=900):
    payment = get_payment(orderid)

    if not payment:
        return True

    if payment["status"] != "PENDING":
        return True

    return (time.time() - payment["created_at"]) > expiry