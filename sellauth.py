import requests

from config import *

BASE_URL = f"https://api.sellauth.com/v1/shops/{SellauthShopID}"

HEADERS = {
    "Authorization": f"Bearer {SellauthAPIKey}"
}


def _request(method, endpoint, **kwargs):
    try:
        response = requests.request(
            method=method,
            url=BASE_URL + endpoint,
            headers=HEADERS,
            timeout=20,
            **kwargs,
        )

    except requests.RequestException as e:
        return {
            "success": False,
            "error": str(e),
        }

    if not response.ok:
        return {
            "success": False,
            "status_code": response.status_code,
            "error": response.text,
        }

    try:
        data = response.json()
    except Exception:
        return {
            "success": False,
            "error": "Invalid JSON response.",
        }

    return {
        "success": True,
        "data": data,
    }


def get_order(orderid):
    response = _request(
        "GET",
        f"/invoices/{orderid}",
    )

    if not response["success"]:
        return response

    return {
        "success": True,
        "order": response["data"],
    }


def deliver_order(orderid):
    response = _request(
        "GET",
        f"/invoices/{orderid}/process",
    )

    if not response["success"]:
        return response

    return {
        "success": True,
        "message": response["data"].get("success", "Invoice processed"),
    }


def order_exists(orderid):
    return get_order(orderid)["success"]


def is_delivered(order):
    return order.get("status", "").lower() == "completed"


def get_email(order):
    return order.get("email", "")


def get_amount(order):
    return float(order.get("price", 0))


def get_currency(order):
    return order.get("currency", "")


def get_status(order):
    return order.get("status", "")


def get_customer(order):
    customer = order.get("customer") or {}

    return {
        "email": order.get("email", ""),
        "id": customer.get("$id"),
    }


def get_order_id(order):
    return str(order.get("id"))


def get_unique_id(order):
    return order.get("unique_id", "")


def get_invoice(order):
    return {
        "invoice_id": get_order_id(order),
        "unique_id": get_unique_id(order),
        "email": get_email(order),
        "amount": get_amount(order),
        "currency": get_currency(order),
        "status": get_status(order),
    }