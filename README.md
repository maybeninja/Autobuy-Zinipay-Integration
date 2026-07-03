AutoBuyX × ZiniPay Integration

A lightweight FastAPI integration that connects SellAuth with ZiniPay, allowing SellAuth invoices to be paid through ZiniPay and automatically processed after successful payment verification.

Requirements

* Python 3.11+
* FastAPI
* Uvicorn
* Requests
* PyYAML
* discord-webhook
* pyfiglet

Install dependencies:

pip install -r requirements.txt

Configuration

Edit settings.yaml and fill in your credentials.

SellauthAPIKey: ""
SellauthShopID: ""
ZiniPayAPIKey: ""
DiscordWebhookUrl: ""
BaseURL: "https://payments.example.com"

Running

Start the API with:

uvicorn base:app --host 0.0.0.0 --port 8000

Payment Link

Open the following URL to create a payment:

https://payments.example.com/store/pay?orderid=SELLAUTH_INVOICE_ID

The API will:

* Fetch the SellAuth invoice
* Create a ZiniPay invoice
* Redirect the customer to the payment page

Redirect URL Example

Your payment gateway should redirect back to something like:

https://payments.example.com/checkout/SELLAUTH_UNIQUE_ID

The integration will then redirect the customer to your storefront or checkout page.

Webhook URL

Configure the webhook in your payment request as:

https://payments.example.com/webhook/SELLAUTH_INVOICE_ID/paid

After payment, the API will:

* Verify the payment with ZiniPay
* Process the SellAuth invoice
* Send a Discord notification

Notes

* Payments are cached locally in payment.json.
* Duplicate webhook requests are ignored.
* Every payment is verified before the SellAuth invoice is processed.
* The payment gateway must use the same domain configured for your brand.

⸻

Developed by maybeninja