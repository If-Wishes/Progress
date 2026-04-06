import asyncio
import re
import requests
import threading
import time
import sys
import os
from datetime import datetime
from flask import Flask, jsonify, request
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Suppress ALL output
sys.stdout = open(os.devnull, 'w')
sys.stderr = open(os.devnull, 'w')

import logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('telethon').setLevel(logging.ERROR)
logging.getLogger('requests').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)

app = Flask(__name__)

# ===== CONFIGURATION =====
API_ID = int(os.environ.get('API_ID', 28057671))
API_HASH = os.environ.get('API_HASH', '081b1f0d65bc8cc11fb4dc8901f7858e')
PHONE_NUMBER = os.environ.get('PHONE_NUMBER', '+2348037138956')
CHANNEL_ID = int(os.environ.get('CHANNEL_ID', -1003481016140))

# Session from environment variable (Render) or file (local)
SESSION_STRING = os.environ.get('MY_SESSION.SESSION', None)
if not SESSION_STRING:
    SESSION_STRING = os.environ.get('SESSION_STRING', None)

# Supabase
SUPABASE_URL = os.environ.get('SUPABASE_URL', "https://uizrpckqnproauqllono.supabase.co")
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVpenJwY2txbnByb2F1cWxsb25vIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUwNDc0NjQsImV4cCI6MjA5MDYyMzQ2NH0.qKVaCbH2NiksMuh85guJiRySQxykwSx-MkbWNuE-PdE")

# ===== GLOBALS =====
recent_messages = []
last_processed_id = 0
processed_ids = set()

def extract_fields(text):
    """Extract all fields from the message"""
    try:
        # Extract Country
        country_match = re.search(r'[🌍]*\s*Country:\s*(.+?)(?:\n|$)', text)
        # Extract Number
        number_match = re.search(r'[📱]*\s*Number:\s*(.+?)(?:\n|$)', text)
        # Extract Sender
        sender_match = re.search(r'[📌]*\s*Sender:\s*(.+?)(?:\n|$)', text)
        # Extract Date/Time
        time_match = re.search(r'[📅]*\s*Date/Time:\s*(.+?)(?:\n|$)', text)
        # Extract Range
        range_match = re.search(r'[🌐]*\s*Range:\s*(.+?)(?:\n|$)', text)
        # Extract the full message
        message_match = re.search(r'(?:💬\s*)?Message:\s*(.+?)(?:\n━━|$)', text, re.DOTALL)
        
        country = country_match.group(1).strip() if country_match else None
        phone_full = number_match.group(1).strip() if number_match else None
        sender = sender_match.group(1).strip() if sender_match else None
        time_raw = time_match.group(1).strip() if time_match else None
        range_val = range_match.group(1).strip() if range_match else None
        message_clean = message_match.group(1).strip() if message_match else None
        
        # Extract last 3 digits from phone number
        phone_last3 = None
        if phone_full:
            digits = re.sub(r'\D', '', phone_full)
            if len(digits) >= 3:
                phone_last3 = digits[-3:]
        
        return {
            "country": country,
            "phone_full": phone_full,
            "phone_last3": phone_last3,
            "sender": sender,
            "time_raw": time_raw,
            "range": range_val,
            "message": message_clean
        }
    except:
        return None

def save_to_supabase(text, message_id):
    try:
        if "Country:" not in text or "Number:" not in text:
            return False
        
        extracted = extract_fields(text)
        if not extracted:
            return False
        
        payload = {
            "country": extracted["country"],
            "phone_full": extracted["phone_full"],
            "phone_last3": extracted["phone_last3"],
            "sender": extracted["sender"],
            "range": extracted["range"],
            "time_raw": extracted["time_raw"],
            "message": extracted["message"]
        }
        
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/otp_logs",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=5
        )
        return response.status_code == 201
    except:
        return False

async def telegram_listener():
    global last_processed_id, processed_ids
    
    # Create client
    if SESSION_STRING:
        client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    else:
        client = TelegramClient('my_session', API_ID, API_HASH)
    
    # Connect
    await client.start(phone=PHONE_NUMBER)
    
    # Load existing messages to prevent duplicates
    try:
        latest_message = await client.get_messages(CHANNEL_ID, limit=1)
        if latest_message:
            last_processed_id = latest_message[0].id
            async for msg in client.iter_messages(CHANNEL_ID, limit=500):
                processed_ids.add(msg.id)
    except:
        pass
    
    # Handle new messages
    @client.on(events.NewMessage(chats=CHANNEL_ID))
    async def handler(event):
        global last_processed_id, processed_ids
        
        try:
            message = event.message
            message_id = message.id
            
            # Duplicate check
            if message_id in processed_ids or message_id <= last_processed_id:
                return
            
            # Mark as processed
            processed_ids.add(message_id)
            last_processed_id = message_id
            
            # Clean old IDs
            if len(processed_ids) > 2000:
                to_remove = list(processed_ids)[:500]
                for old_id in to_remove:
                    processed_ids.remove(old_id)
            
            # Process message
            text = message.text
            if text and "Country:" in text and "Number:" in text:
                message_age = datetime.now().timestamp() - message.date.timestamp()
                if message_age > 120:
                    return
                
                save_to_supabase(text, message_id)
                
                # Store preview
                extracted = extract_fields(text)
                recent_messages.insert(0, {
                    "id": message_id,
                    "phone": extracted.get("phone_full") if extracted else "Unknown",
                    "time": str(message.date)
                })
                while len(recent_messages) > 100:
                    recent_messages.pop()
        except:
            pass
    
    await client.run_until_disconnected()

def run_telegram():
    asyncio.run(telegram_listener())

# ===== FLASK ROUTES =====
@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "last_processed_id": last_processed_id,
        "processed_count": len(processed_ids)
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "ok",
        "messages_tracked": len(recent_messages),
        "last_processed_id": last_processed_id
    })

@app.route('/latest', methods=['GET'])
def get_latest():
    limit = request.args.get('limit', 10, type=int)
    return jsonify({
        "count": len(recent_messages[:limit]),
        "messages": recent_messages[:limit]
    })

# ===== MAIN =====
if __name__ == "__main__":
    telegram_thread = threading.Thread(target=run_telegram, daemon=True)
    telegram_thread.start()
    time.sleep(5)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False, use_reloader=False)
