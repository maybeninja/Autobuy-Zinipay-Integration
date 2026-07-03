from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from discord_webhook import DiscordWebhook, DiscordEmbed



import requests
from pyfiglet import Figlet

from config import *
from sellauth import *
from zinipay import *
from payments import *

app = FastAPI()

PROJECT_NAME = "Autobuy x ZiniPay Integration"

f = Figlet(font="standard")

print("\033[95m")
print(f.renderText(PROJECT_NAME))
print("\033[92mStatus   : ONLINE")
print("\033[96mGitHub   : maybeninja")
print("Discord  : ninja.code")
print("\033[0m")


def eur_to_bdt(amount_eur: float):
    try:
        r = requests.get(
            "https://open.er-api.com/v6/latest/EUR",
            timeout=10,
        )

        r.raise_for_status()

        data = r.json()

        if data["result"] != "success":
            raise Exception()

        return round(
            amount_eur * data["rates"]["BDT"],
            2,
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to fetch exchange rate.",
        )


    
def send_discord(
    orderid,
    txid,
    amount,
    payment_method,
):
    webhook = DiscordWebhook(
        url=DiscordWebhookUrl,
    )

    embed = DiscordEmbed(
        title="✅ Payment Received",
        color=0x57F287,
    )

    embed.add_embed_field(
        name="Invoice",
        value=orderid,
        inline=False,
    )

    embed.add_embed_field(
        name="Transaction ID",
        value=txid,
        inline=False,
    )

    embed.add_embed_field(
        name="Payment Method",
        value=payment_method,
        inline=True,
    )

    embed.add_embed_field(
        name="Amount",
        value=f"{amount} BDT",
        inline=True,
    )

    embed.set_footer(
        text="Discord: ninja.code",
        icon_url="https://cdn.discordapp.com/avatars/1364687618964459570/a_73130e6fca7c9818acfa6a0541ee9844.gif",
    )

    webhook.add_embed(embed)
    webhook.execute()
    
@app.get("/", response_class=HTMLResponse)
async def home():
    return f"""
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>{PROJECT_NAME}</title>

<style>

*{{
margin:0;
padding:0;
box-sizing:border-box;
}}

body{{
background:#0d1117;
color:#fff;
font-family:Arial,Helvetica,sans-serif;
display:flex;
justify-content:center;
align-items:center;
height:100vh;
}}

.container{{
text-align:center;
}}

.status{{
margin-top:20px;
display:inline-block;
padding:10px 24px;
border-radius:8px;
background:#238636;
font-weight:bold;
}}

.meta{{
margin-top:20px;
color:#8b949e;
}}

.meta a{{
color:#58a6ff;
text-decoration:none;
}}

</style>

</head>

<body>

<div class="container">

<h1>{PROJECT_NAME}</h1>

<div class="status">
ONLINE
</div>

<div class="meta">

<a href="https://github.com/maybeninja">
GitHub
</a>

|

<a href="https://discord.com/users/1364687618964459570">
Discord
</a>

</div>

</div>

</body>
</html>
"""


@app.get("/store/pay")
async def store_pay(orderid: str):

    result = get_order(orderid)

    if not result["success"]:
        raise HTTPException(
            status_code=404,
            detail=result["error"],
        )

    order = result["order"]

    if is_delivered(order):
        raise HTTPException(
            status_code=400,
            detail="Invoice already completed.",
        )

    invoice_id = get_order_id(order)
    unique_id = get_unique_id(order)

    amount = get_amount(order)
    currency = get_currency(order)
    email = get_email(order)

    if currency.upper() == "EUR":
        amount_bdt = eur_to_bdt(amount)
    else:
        amount_bdt = amount

    payment = create_payment(
        orderid=invoice_id,
        unique_id=unique_id,
        email=email,
        amount_eur=amount,
        amount_bdt=amount_bdt,
    )

    if not payment["success"]:
        raise HTTPException(
            status_code=500,
            detail=payment["error"],
        )

    return RedirectResponse(
        url=payment["payment_url"],
        status_code=302,
    )
    
@app.get("/webhook/{orderid}/paid")
async def payment_webhook(
    orderid: str,
    request: Request,
):
    #
    # ZiniPay sends GET query parameters
    #

    query = request.query_params

    zini_invoice_id = (
        query.get("invoice_id")
        or query.get("invoiceId")
    )

    webhook_status = str(
        query.get("status", "")
    ).upper()

    if not zini_invoice_id:
        raise HTTPException(
            status_code=400,
            detail="Missing ZiniPay invoice ID.",
        )

    if webhook_status != "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail="Payment not completed.",
        )

    #
    # Find local payment using ZiniPay invoice
    #

    payment = get_payment_from_zini_invoice(
        zini_invoice_id
    )

    if payment is None:
        raise HTTPException(
            status_code=404,
            detail="Payment session not found.",
        )

    invoice_id = str(
        payment["invoice_id"]
    )

    #
    # Ignore duplicate webhook
    #

    if payment_completed(invoice_id):
        return {
            "success": True,
            "message": "Already processed."
        }

    #
    # Verify payment directly with ZiniPay
    #

    verify = verify_payment(
        zini_invoice_id
    )

    if not verify["success"]:
        raise HTTPException(
            status_code=400,
            detail=verify["error"],
        )

    if verify["status"] != "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail=f"Payment status is {verify['status']}",
        )

    #
    # Fetch SellAuth invoice
    #

    result = get_order(invoice_id)

    if not result["success"]:
        raise HTTPException(
            status_code=404,
            detail=result["error"],
        )

    order = result["order"]

    #
    # Security checks
    #

    if verify["fullname"] != payment["unique_id"]:
        raise HTTPException(
            status_code=400,
            detail="Unique ID mismatch.",
        )

    if verify["email"].lower() != get_email(order).lower():
        raise HTTPException(
            status_code=400,
            detail="Email mismatch.",
        )

    expected_amount = round(
        float(payment["amount_bdt"]),
        2,
    )

    received_amount = round(
        float(verify["amount"]),
        2,
    )

    if abs(expected_amount - received_amount) > 1:
        raise HTTPException(
            status_code=400,
            detail="Amount mismatch.",
        )

    #
    # Save payment
    #

    update_payment(
        invoice_id,
        transaction_id=verify["transaction_id"],
        payment_method=verify["payment_method"],
        status="COMPLETED",
        completed_at=int(__import__("time").time()),
    )

    #
    # Deliver SellAuth order
    #

    processed = deliver_order(
        invoice_id
    )

    if not processed["success"]:

        update_payment(
            invoice_id,
            status="DELIVERY_FAILED",
        )

        raise HTTPException(
            status_code=500,
            detail=processed["error"],
        )

    #
    # Discord notification
    #

    send_discord(
        orderid=payment["unique_id"],
        txid=verify["transaction_id"],
        amount=verify["amount"],
        payment_method=verify["payment_method"],
    )

    return {
        "success": True,
        "invoice_id": invoice_id,
        "zini_invoice_id": zini_invoice_id,
        "transaction_id": verify["transaction_id"],
        "message": "Payment verified and invoice processed successfully."
    }
    
    
@app.get("/cancel/{orderid}", response_class=HTMLResponse)
async def payment_cancelled(orderid: str):
    return f"""
<!DOCTYPE html>
<html lang="en">

<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Payment Cancelled</title>

<style>

body{{
background:#0d1117;
color:#ffffff;
font-family:Arial,Helvetica,sans-serif;
display:flex;
justify-content:center;
align-items:center;
height:100vh;
margin:0;
}}

.container{{
text-align:center;
padding:30px;
}}

h1{{
font-size:2.5rem;
margin-bottom:15px;
color:#ff4d4d;
}}

p{{
font-size:1.1rem;
color:#b0b0b0;
}}

</style>

</head>

<body>

<div class="container">

<h1>❌ Payment Cancelled</h1>

<p>Your transaction has been cancelled.</p>

<p>Invoice: <strong>{orderid}</strong></p>

</div>

</body>

</html>
"""


@app.get("/checkout/{unique_id}")
async def checkout_redirect(unique_id: str):
    return RedirectResponse(
        url=f"https://alzashop.online/checkout/{unique_id}",
        status_code=302,
    )
    