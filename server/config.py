import os

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8765"))

XAI_API_KEY = os.environ.get("XAI_API_KEY", "sk-f4efa7125675d7e6dc7f1bf069f0d22dac6a8a01590e136295d8762f436b1c7b")
XAI_MODEL = os.environ.get("XAI_MODEL", "grok-4.7")
XAI_BASE_URL = os.environ.get("XAI_BASE_URL", "https://sub.geiliapi.com/v1")

# 数据库配置 ！！！
DB = {
    "host": os.environ.get("MYSQL_HOST", "43.155.239.46"),
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": os.environ.get("MYSQL_USER", "dbeaver"),
    "password": os.environ.get("MYSQL_PASSWORD", "Test@123456"),
    "database": os.environ.get("MYSQL_DATABASE", "async_match"),
    "charset": "utf8mb4",
}
