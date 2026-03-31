#!/usr/bin/env python3
import re
import json
import os
import base64
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
import requests

BOT_TOKEN = os.environ.get('BOT_TOKEN', "7941038643:AAFFM8jv2RkFyyxzgdzuyqy6UiCHNZhIlWo")

# GitHub Settings
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')  # Add this in Render env vars
GITHUB_REPO = "yourusername/your-repo"  # Your GitHub repo
GITHUB_PATH = "data/otp_logs.json"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

OTP_PATTERNS = [r'\b\d{6}\b', r'\b\d{4}\b', r'OTP[:\s]*(\d{4,6})', r'code[:\s]*(\d{4,6})']
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

def save_to_github(otp_code, phone_last4, raw_message, sender):
    """Save OTP to GitHub repository"""
    try:
        now = datetime.now()
        new_otp = {
            'id': f"{int(now.timestamp())}_{phone_last4}_{otp_code}",
            'otp': otp_code,
            'phone_last4': phone_last4,
            'raw_message': raw_message[:500],
            'sender': sender,
            'timestamp': int(now.timestamp()),
            'date': now.strftime('%Y-%m-%d'),
            'time': now.strftime('%H:%M:%S'),
            'datetime': now.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Get current file from GitHub
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_PATH}"
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            content = json.loads(base64.b64decode(data['content']).decode())
            sha = data['sha']
        else:
            content = []
            sha = None
        
        # Add new OTP
        content.append(new_otp)
        if len(content) > 10000:
            content = content[-10000:]
        
        # Commit back
        new_content = json.dumps(content, indent=2)
        encoded = base64.b64encode(new_content.encode()).decode()
        
        commit_data = {
            'message': f'Add OTP {otp_code} from {sender}',
            'content': encoded,
            'sha': sha
        }
        
        requests.put(url, headers=headers, json=commit_data)
        logger.info(f"✅ Saved OTP {otp_code} to GitHub")
        return True
    except Exception as e:
        logger.error(f"GitHub error: {e}")
        return False

async def handle_message(update: Update, context):
    msg = update.message
    if not msg or not msg.text: return
    
    text, sender = msg.text, msg.from_user.username or msg.from_user.first_name
    otp = extract_otp(text)
    if not otp: return
    
    phone = extract_phone_last4(text)
    if not phone and msg.reply_to_message:
        phone = extract_phone_last4(msg.reply_to_message.text or '')
    if not phone: phone = "????"
    
    if save_to_github(otp, phone, text, sender):
        await msg.reply_text(f"✅ OTP Tracked!\nCode: {otp}\nPhone: ***{phone}")

async def start_command(update: Update, context):
    await update.message.reply_text("🤖 NexusPanel OTP Bot Active!\nMonitors OTP messages.\nRate: $0.005 per OTP")

async def stats_command(update: Update, context):
    # Get stats from GitHub
    url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{GITHUB_PATH}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            logs = response.json()
            today = datetime.now().strftime('%Y-%m-%d')
            count = len([l for l in logs if l.get('date') == today])
            await update.message.reply_text(f"📊 Today: {count} OTPs\n💰 Earnings: ${count * 0.005:.2f}")
        else:
            await update.message.reply_text("Unable to fetch stats")
    except:
        await update.message.reply_text("Error fetching stats")

def main():
    print("🤖 Starting NexusPanel OTP Bot (GitHub Mode)...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
