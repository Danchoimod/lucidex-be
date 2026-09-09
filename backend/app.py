import os
import uvicorn

if __name__ == "__main__":
    # Ưu tiên lấy Port từ môi trường Pterodactyl (SERVER_PORT / PORT), mặc định về 25693 nếu không có
    port = int(os.environ.get("SERVER_PORT", os.environ.get("PORT", 25693)))
    uvicorn.run("src.main:app", host="0.0.0.0", port=port)
