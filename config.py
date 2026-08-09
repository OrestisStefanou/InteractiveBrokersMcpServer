from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    interactive_brokers_portal_base_url: str = "https://localhost:5000/v1/api"

    mcp_port: int = 9092

    # If True, the server will not expose any tools that can modify the state of the IB account.
    # Enforced in mcp_app/app.py, which skips registration of placeOrder and confirmOrder.
    read_only: bool = False

    # Read from `.env`
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Config()
