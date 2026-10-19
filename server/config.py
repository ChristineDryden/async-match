import os

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8765"))

DB = {
    "host": os.environ.get("MYSQL_HOST", "43.155.239.46"),
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": os.environ.get("MYSQL_USER", "dbeaver"),
    "password": os.environ.get("MYSQL_PASSWORD", "Test@123456"),
    "database": os.environ.get("MYSQL_DATABASE", "async_match"),
    "charset": "utf8mb4",
}
