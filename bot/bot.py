#!/usr/bin/env python3
import re
import os
import requests
import time
import threading
import logging
from flask import Flask

# 🔐 CONFIG (YOUR REAL API)
BOT_TOKEN = "7783590119:AAGScPFVEreH-fvwSQNTuamGlFOGI-VDK7w"
SUPABASE_URL = "https://uizrpckqnproauqllono.supabase.co"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVpenJwY2txbnByb2F1cWxsb25vIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUwNDc0NjQsImV4cCI6MjA5MDYyMzQ2NH0.qKVaCbH2NiksMuh85guJiRySQxykwSx-MkbWNuE-PdE"

# 🔕 DISABLE LOGS
logging.getLogger().setLevel(logging.CRITICAL)
logging.getLogger("werkzeug").setLevel(logging.CRITICAL)

app = Flask(__name__)

last_id = 0

# 🌐 KEEP ALIVE
@app.route('/')
def home():
    return ""


# 🔄 SAFE REQUESTS
def safe_get(url, **kwargs):
    try:
        return requests.get(url, **kwargs)
    except:
        return None

def safe_post(url, **kwargs):
    try:
        return requests.post(url, **kwargs)
    except:
        return None


# ⏱️ FIX TIME FORMAT (IMPORTANT)
def clean_time(t):
    try:
        return str(t).strip()
    except:
        return None


# 🤖 TELEGRAM BOT
def poll():
    global last_id

    while True:
        try:
            res = safe_get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
                params={"offset": last_id + 1, "timeout": 10},
                timeout=15
            )

            if not res:
                time.sleep(3)
                continue

            try:
                data = res.json()
            except:
                time.sleep(2)
                continue

            for update in data.get("result", []):
                try:
                    last_id = update.get("update_id", last_id)

                    text = update.get("message", {}).get("text", "")
                    if not text:
                        continue

                    # 📥 Extract Data
                    country = re.search(r'Country:\s*(.+)', text)
                    phone = re.search(r'Number:\s*(.+)', text)
                    sender = re.search(r'Sender:\s*(.+)', text)
                    time_raw = re.search(r'Date/Time:\s*(.+)', text)
                    range_val = re.search(r'Range:\s*(.+)', text)
                    msg = re.search(r'Message:\s*(.+)', text, re.DOTALL)

                    phone_full = phone.group(1).strip() if phone else None
                    phone_last3 = re.sub(r'\D', '', phone_full)[-3:] if phone_full else None

                    payload = {
                        "country": country.group(1).strip() if country else None,
                        "phone_full": phone_full,
                        "phone_last3": phone_last3,
                        "sender": sender.group(1).strip() if sender else None,
                        "range_name": range_val.group(1).strip() if range_val else None,
                        "message_time": clean_time(time_raw.group(1)) if time_raw else None,
                        "message": msg.group(1).strip() if msg else None
                    }

                    # 🚀 SEND TO SUPABASE
                    safe_post(
                        f"{SUPABASE_URL}/rest/v1/otp_logs",
                        headers={
                            "apikey": API_KEY,
                            "Authorization": f"Bearer {API_KEY}",
                            "Content-Type": "application/json",
                            "Prefer": "return=minimal"
                        },
                        json=payload,
                        timeout=8
                    )

                except:
                    continue

        except:
            pass

        time.sleep(2)


# 🚀 START THREAD AFTER SERVER READY
def start_bot():
    t = threading.Thread(target=poll, daemon=True)
    t.start()


# ▶️ RUN SERVER
if __name__ == "__main__":
    start_bot()  # start bot here (important fix)

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
