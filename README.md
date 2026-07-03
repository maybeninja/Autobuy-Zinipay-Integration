# AutoBuyX × ZiniPay Integration

A lightweight FastAPI integration that connects SellAuth with ZiniPay
for automated payment processing.

## Requirements

Install all required dependencies:

``` bash
pip install -r requirements.txt
```

## Configuration

Edit `settings.yaml` and fill in your credentials.

``` yaml
SellauthAPIKey: ""
SellauthShopID: ""

ZiniPayAPIKey: ""

DiscordWebhookUrl: ""

BaseURL: "https://payments.example.com"
```

## Running

``` bash
uvicorn base:app --host 0.0.0.0 --port 8000
```

## Payment Link

``` text
https://payments.example.com/store/pay?orderid=SELLAUTH_INVOICE_ID
```

## Redirect URL Example

``` text
https://payments.example.com/checkout/SELLAUTH_UNIQUE_ID
```

## Webhook URL Example

``` text
https://payments.example.com/webhook/SELLAUTH_INVOICE_ID/paid
```

## License

MIT License

------------------------------------------------------------------------

Developed by **maybeninja**
