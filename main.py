from config import settings
from mcp_app.app import mcp_app

if __name__ == "__main__":
    mcp_app.run(transport="http", port=settings.mcp_port)
