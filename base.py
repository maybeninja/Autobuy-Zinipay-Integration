from fastapi import FastAPI, HTTPException, Request 
from fastapi.responses import RedirectResponse , HTMLResponse
from discord_webhook import DiscordWebhook, DiscordEmbed

import requests 

from config import *
from komerza import *
from rupantor import *
from payments import *

app = FastAPI()

from pyfiglet import Figlet

PROJECT_NAME = "Konmerza x Rupantorpay Integration"

f = Figlet(font="standard")

print("\033[95m")  # Purple
print(f.renderText(PROJECT_NAME))
print("\033[92mStatus   : ONLINE")
print("\033[96mGitHub   : maybeninja")
print("Discord  : ninja.code")
print("\033[0m")


def eur_to_bdt(amount_eur: float) -> float:
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
            detail="Unable to fetch EUR exchange rate.",
        )


def send_discord(
    orderid,
    txid,
    amount,
    payment_method,
):
    webhook = DiscordWebhook(
        url=DiscordWebhookUrl
    )

    embed = DiscordEmbed(
        title="✅ Payment Received",
        color=0x57F287,
    )

    embed.add_embed_field(
        name="Order ID",
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
    embed.set_footer(text="Discord: `ninja.code`",icon_url="https://images-ext-1.discordapp.net/external/96UVSxbqz1NFia_04sK5bhsYgeW9TVqFX9g7bRS0xgU/%3Fsize%3D256/https/cdn.discordapp.com/avatars/1364687618964459570/a_73130e6fca7c9818acfa6a0541ee9844.gif")
    

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
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            background: #0d1117;
            color: #ffffff;
            font-family: Arial, Helvetica, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }}

        .container {{
            text-align: center;
            padding: 20px;
        }}

        h1 {{
            font-size: 3rem;
            margin-bottom: 18px;
            font-weight: 700;
        }}

        .status {{
            display: inline-block;
            background: #238636;
            color: #fff;
            padding: 10px 24px;
            border-radius: 8px;
            font-size: 1.2rem;
            font-weight: bold;
            margin-bottom: 18px;
        }}

        .meta {{
            color: #8b949e;
            font-size: 0.95rem;
        }}

        .meta a {{
            color: #58a6ff;
            text-decoration: none;
        }}

        .meta a:hover {{
            text-decoration: underline;
        }}

        @media (max-width: 768px) {{
            h1 {{
                font-size: 2rem;
            }}

            .status {{
                font-size: 1rem;
            }}

            .meta {{
                font-size: 0.85rem;
            }}
        }}
    </style>
</head>
<body>

<div class="container">
    <h1>{PROJECT_NAME}</h1>

    <div class="status">
        ● STATUS: ONLINE
    </div>

    <div class="meta">
        GitHub:
        <a href="https://github.com/maybeninja" target="_blank">maybeninja</a>
        &nbsp;|&nbsp;
        Discord:
         <a href="https://discord.com/users/1364687618964459570" target="_blank">ninja.code</a>
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
            404,
            result["error"],
        )

    order = result["order"]

    if is_delivered(order):
        raise HTTPException(
            400,
            "Order already delivered.",
        )

    amount_eur = get_amount(order)

    amount_bdt = eur_to_bdt(
        amount_eur
    )

    payment = create_payment(
        orderid=orderid,
        email=get_email(order),
        amount_eur=amount_eur,
        amount_bdt=amount_bdt,
    )

    if not payment["success"]:
        raise HTTPException(
            500,
            payment["error"],
        )

    return RedirectResponse(
        payment["payment_url"],
        status_code=302,
    )
    
@app.post("/webhook/{orderid}/paid")
async def payment_webhook(
    orderid: str,
    request: Request,
):
    form = await request.form()

    transaction_id = form.get("transactionId")
    payment_method = form.get("paymentMethod")
    payment_amount = form.get("paymentAmount")
    payment_fee = form.get("paymentFee")
    webhook_status = form.get("status", "").upper()

    if not transaction_id:
        raise HTTPException(
            status_code=400,
            detail="Missing transaction ID.",
        )

    payment = get_payment(orderid)

    if payment is None:
        raise HTTPException(
            status_code=404,
            detail="Payment session not found.",
        )

    # Ignore duplicate webhooks
    if payment_completed(orderid):
        return {
            "success": True,
            "message": "Already processed."
        }

    verify = verify_payment(transaction_id)

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

    result = get_order(orderid)

    if not result["success"]:
        raise HTTPException(
            status_code=404,
            detail=result["error"],
        )

    order = result["order"]

    # Security checks

    if verify["fullname"] != orderid:
        raise HTTPException(
            status_code=400,
            detail="Order verification failed.",
        )

    if verify["email"].lower() != get_email(order).lower():
        raise HTTPException(
            status_code=400,
            detail="Email verification failed.",
        )

    expected_amount = round(
        payment["amount_bdt"],
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

    update_payment(
        orderid,
        transaction_id=verify["transaction_id"],
        payment_method=verify["payment_method"],
        status="COMPLETED",
        completed_at=int(__import__("time").time()),
    )

    delivered = deliver_order(orderid)

    if not delivered["success"]:
        update_payment(
            orderid,
            status="DELIVERY_FAILED",
        )

        raise HTTPException(
            status_code=500,
            detail=delivered["error"],
        )

    send_discord(
        orderid=orderid,
        txid=verify["transaction_id"],
        amount=verify["amount"],
        payment_method=verify["payment_method"],
    )

    return {
        "success": True,
        "message": "Payment verified and order delivered."
    }