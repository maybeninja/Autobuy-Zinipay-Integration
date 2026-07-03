import requests

from config import *
from payments import (
    get_payment,
    save_payment,
    payment_expired,
)

CREATE_URL = "https://api.zinipay.com/v1/payment/create"
VERIFY_URL = "https://api.zinipay.com/v1/payment/verify"

HEADERS = {
    "Content-Type": "application/json",
    "zini-api-key": ZiniPayAPIKey,
}


def create_payment(
    orderid: str,
    unique_id: str,
    email: str,
    amount_eur: float,
    amount_bdt: float,
):
    """
    Creates a ZiniPay invoice.

    If a pending invoice already exists and hasn't expired,
    returns the existing payment URL.
    """

    cached = get_payment(orderid)

    if (
        cached
        and cached["status"] == "PENDING"
        and not payment_expired(orderid)
        and cached.get("payment_url")
    ):
        return {
            "success": True,
            "cached": True,
            "payment_url": cached["payment_url"],
            "invoice_id": cached["zini_invoice_id"],
        }

    payload = {
        "cus_name": unique_id,
        "cus_email": email,
        "amount": amount_bdt,
        "metadata": {
            "invoice_id": orderid,
            "unique_id": unique_id,
        },
        "redirect_url": f"{BaseURL}/checkout/{unique_id}",
        "cancel_url": f"{BaseURL}/cancel/{orderid}",
        "webhook_url": f"{BaseURL}/webhook/{orderid}/paid",
    }

    try:
        response = requests.post(
            CREATE_URL,
            json=payload,
            headers=HEADERS,
            timeout=20,
        )
        print("Zigi---> "+response.text)
    except requests.RequestException as e:
        return {
            "success": False,
            "error": str(e),
        }

    if not response.ok:
        return {
            "success": False,
            "error": response.text,
        }

    try:
        data = response.json()
    except Exception:
        return {
            "success": False,
            "error": f"Invalid JSON response: {response.text}",
        }

    if not data.get("status"):
        return {
            "success": False,
            "error": data.get("message", "Unknown error"),
        }

    payment_url = data.get("payment_url")

    if not payment_url:
        return {
            "success": False,
            "error": "payment_url missing.",
        }

    #
    # https://secure.zinipay.com/payment/INVOICE_ID
    #
    zini_invoice_id = payment_url.rstrip("/").split("/")[-1]

    save_payment(
        orderid=orderid,
        unique_id=unique_id,
        payment_url=payment_url,
        amount_eur=amount_eur,
        amount_bdt=amount_bdt,
        zini_invoice_id=zini_invoice_id,
    )

    return {
        "success": True,
        "cached": False,
        "payment_url": payment_url,
        "invoice_id": zini_invoice_id,
    }


def verify_payment(invoice_id: str):
    payload = {
        "invoice_id": invoice_id,
    }

    try:
        response = requests.post(
            VERIFY_URL,
            json=payload,
            headers=HEADERS,
            timeout=20,
        )
    except requests.RequestException as e:
        return {
            "success": False,
            "error": str(e),
        }

    if not response.ok:
        return {
            "success": False,
            "error": response.text,
        }

    try:
        data = response.json()
    except Exception:
        return {
            "success": False,
            "error": f"Invalid JSON response: {response.text}",
        }

    required = [
        "cus_name",
        "cus_email",
        "amount",
        "invoice_id",
        "payment_method",
        "transaction_id",
        "status",
    ]

    for field in required:
        if field not in data:
            return {
                "success": False,
                "error": f"Missing '{field}' in verify response.",
            }

    return {
        "success": True,
        "invoice_id": data["invoice_id"],
        "transaction_id": data["transaction_id"],
        "fullname": data["cus_name"],
        "email": data["cus_email"],
        "amount": float(data["amount"]),
        "payment_method": data["payment_method"],
        "status": data["status"].upper(),
        "raw": data,
    }