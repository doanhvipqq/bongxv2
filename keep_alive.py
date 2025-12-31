from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
    # Chạy trên port 8080 (hoặc port Render cấp qua biến môi trường PORT)
    # Render thường tự động set PORT env var, nhưng default 8080 là an toàn
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
