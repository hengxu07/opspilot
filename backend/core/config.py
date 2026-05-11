from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Shopify
    shopify_shop_domain: str = ""
    shopify_access_token: str = ""
    shopify_webhook_secret: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # LangSmith
    langchain_api_key: str = ""
    langchain_tracing_v2: str = "true"
    langchain_project: str = "opspilot"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Slack
    slack_bot_token: str = ""
    slack_ops_channel: str = "#ops-alerts"

    # Google Sheets
    google_sheets_id: str = ""
    google_service_account_json: str = ""

    # Linear (optional)
    linear_api_key: str = ""
    linear_team_id: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
