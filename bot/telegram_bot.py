
#!/usr/bin/env python3
import re
import json
import os
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler

BOT_TOKEN = "7941038643:AAFFM8jv2RkFyyxzgdzuyqy6UiCHNZhIlWo"

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'otp_logs.json')
DAILY_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'otp_%s.json')
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

OTP_PATTERNS = [r'\b\d{6}\b', r'\b\d{4}\b', r'OTP[:\s]*(\d{4,6})', r'code[:\s]*(\d{4,6})', r'verification[:\s]*(\d{4,6})', r'pin[:\s]*(\d{4,6})']
PHONE_PATTERNS = [r'\+?\d{10,15}', r'from\s*\+?(\d+)', r'sent\s*by\s*\+?(\d+)', r'number[:\s]*\+?(\d+)']

def extract_otp(text):
    if not text: return None
    for p in OTP_PATTERNS:
        m = re.search(p, text, re.IGNORECASE)
        if m: return m.group(1) if m.groups() else m.group(0)
    return None

def extract_phone_last4(text):
    if not text: return None
    for p in PHONE_PATTERNS:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            phone = m.group(1) if m.groups() else m.group(0)
            clean = re.sub(r'\D', '', phone)
            if len(clean) >= 4: return clean[-4:]
    return None

def save_otp(otp_code, phone_last4, raw_message, sender):
    now = datetime.now()
    record = {'id': f"{int(now.timestamp())}_{phone_last4}_{otp_code}", 'otp': otp_code, 'phone_last4': phone_last4, 'raw_message': raw_message[:500], 'sender': sender, 'timestamp': int(now.timestamp()), 'date': now.strftime('%Y-%m-%d'), 'time': now.strftime('%H:%M:%S'), 'datetime': now.strftime('%Y-%m-%d %H:%M:%S')}
    logs = []
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f: logs = json.load(f)
        except: pass
    logs.append(record)
    if len(logs) > 10000: logs = logs[-10000:]
    with open(DATA_FILE, 'w') as f: json.dump(logs, f, indent=2)
    daily = DAILY_FILE % now.strftime('%Y-%m-%d')
    daily_logs = []
    if os.path.exists(daily):
        try:
            with open(daily, 'r') as f: daily_logs = json.load(f)
        except: pass
    daily_logs.append(record)
    with open(daily, 'w') as f: json.dump(daily_logs, f, indent=2)
    logger.info(f"✅ Saved OTP {otp_code} for phone ending {phone_last4}")
    return True

async def handle_message(update: Update, context):
    msg = update.message
    if not msg or not msg.text: return
    text, sender = msg.text, msg.from_user.username or msg.from_user.first_name
    otp = extract_otp(text)
    if not otp: return
    phone = extract_phone_last4(text)
    if not phone and msg.reply_to_message: phone = extract_phone_last4(msg.reply_to_message.text or '')
    if not phone: phone = "????"
    if save_otp(otp, phone, text, sender):
        await msg.reply_text(f"✅ OTP Tracked!\nCode: {otp}\nPhone: ***{phone}\nTime: {datetime.now().strftime('%H:%M:%S')}")

async def start(update: Update, context):
    await update.message.reply_text("🤖 NexusPanel OTP Bot Active!\nI monitor OTP messages.\nRate: $0.005 per OTP")

async def stats(update: Update, context):
    today = datetime.now().strftime('%Y-%m-%d')
    count = 0
    daily = DAILY_FILE % today
    if os.path.exists(daily):
        try:
            with open(daily, 'r') as f: count = len(json.load(f))
        except: pass
    await update.message.reply_text(f"📊 Today's Stats\nOTPs: {count}\nEarnings: ${count * 0.005:.2f}")

def main():
    print("🤖 Starting NexusPanel OTP Bot...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
