import yaml

SETTINGS_FILE = "settings.yaml"

with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

SellauthAPIKey = config.get("SellauthAPIKey", "")
SellauthShopID = config.get("SellauthShopID", "")

ZiniPayAPIKey = config.get("ZiniPayAPIKey", "")

DiscordWebhookUrl = config.get("DiscordWebhookUrl", "")

BaseURL = config.get("BaseURL", "")

Subdomain = config.get("Subdomain", "")