"""XinChao MCP Server configuration — loads credentials from .env"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

API_URL = os.getenv("XINCHAO_API_URL", "https://api.xinchao.world/api/v1")
ADMIN_EMAIL = os.getenv("XINCHAO_EMAIL", "")
ADMIN_PASSWORD = os.getenv("XINCHAO_PASSWORD", "")
PORT = int(os.getenv("PORT", "3000"))
AUTHOR_ID = os.getenv("AUTHOR_ID", "")
