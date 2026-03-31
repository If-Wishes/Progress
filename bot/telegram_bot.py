#!/usr/bin/env python3
"""
NexusPanel Telegram Bot - Auto-pushes OTPs to GitHub
"""

import re
import json
import os
import subprocess
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler

# ============ CONFIGURATION ============
BOT_TOKEN = "7941038643:AAFFM8jv2RkFyyxzgdzuyqy6UiCHNZhIlWo"
GITHUB_TOKEN = "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"
GITHUB_REPO = "If-Wishes/Progress"
REPO_PATH = os.path.dirname(os.path.dirname(__file__))  # Path to your Progress folder

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ OTP PATTERNS ============
OTP_PATTERNS = [
    r'\b\d{6}\b', r'\b\d{4}\b',
    r'OTP[:\s]*(\d{4,6})', r'code[:\s]*(\d{4,6})',
    r'verification[:\s]*(\d{4,6})', r'pin[:\s]*(\d{4,6})',
]

PHONE_PATTERNS = [
    r'\+?\d{10,15}', r'from\s*\+?(\d+)',
    r'sent\s*by\s*\+?(\d+)', r'number[:\s]*\+?(\d+)',
]

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

def save_otp_to_file(otp_code, phone_last4, raw_message, sender):
    """Save OTP to local file and commit to GitHub"""
    try:
        now = datetime.now()
        DATA_FILE = os.path.join(REPO_PATH, 'data', 'otp_logs.json')
        
        # Create data directory if needed
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        
        # Load existing logs
        logs = []
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except:
                logs = []
        
        # Add new OTP
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
        logs.append(new_otp)
        
        # Keep only last 5000
        if len(logs) > 5000:
            logs = logs[-5000:]
        
        # Save to file
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Saved OTP {otp_code} for phone ending {phone_last4}")
        
        # Push to GitHub
        git_push_to_github()
        
        return True
    except Exception as e:
        logger.error(f"Error saving OTP: {e}")
        return False

def git_push_to_github():
    """Commit and push changes to GitHub"""
    try:
        # Configure git
        subprocess.run(['git', '-C', REPO_PATH, 'config', 'user.email', 'bot@nexuspanel.com'], capture_output=True)
        subprocess.run(['git', '-C', REPO_PATH, 'config', 'user.name', 'NexusPanel Bot'], capture_output=True)
        
        # Add the changed file
        subprocess.run(['git', '-C', REPO_PATH, 'add', 'data/otp_logs.json'], capture_output=True)
        
        # Check if there are changes to commit
        status = subprocess.run(['git', '-C', REPO_PATH, 'status', '--porcelain'], capture_output=True, text=True)
        if not status.stdout.strip():
            logger.info("No changes to commit")
            return True
        
        # Commit
        commit_msg = f"Add OTP - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(['git', '-C', REPO_PATH, 'commit', '-m', commit_msg], capture_output=True)
        
        # Push with token
        remote_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
        result = subprocess.run(['git', '-C', REPO_PATH, 'push', remote_url], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("✅ Pushed to GitHub successfully")
            return True
        else:
            logger.error(f"Push failed: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Git error: {e}")
        return False

async def handle_message(update: Update, context):
    message = update.message
    if not message or not message.text:
        return
    
    text = message.text
    sender = message.from_user.username or message.from_user.first_name
    
    logger.info(f"📨 Message from {sender}: {text[:100]}...")
    
    otp = extract_otp(text)
    if not otp:
        return
    
    logger.info(f"🔑 Found OTP: {otp}")
    
    phone = extract_phone_last4(text)
    if not phone and message.reply_to_message:
        phone = extract_phone_last4(message.reply_to_message.text or '')
    
    if not phone:
        phone = "????"
    
    if save_otp_to_file(otp, phone, text, sender):
        await message.reply_text(
            f"✅ OTP Tracked!\n"
            f"Code: {otp}\n"
            f"Phone: ***{phone}\n"
            f"Time: {datetime.now().strftime('%H:%M:%S')}\n"
            f"Synced to GitHub Pages"
        )
    else:
        await message.reply_text("❌ Failed to save OTP")

async def start_command(update: Update, context):
    await update.message.reply_text(
        "🤖 *NexusPanel OTP Bot*\n\n"
        "I monitor OTP messages in this group.\n"
        "When I detect an OTP code with a phone number,\n"
        "I'll save it and sync to GitHub.\n\n"
        "*Commands:*\n"
        "/start - Show this message\n"
        "/stats - Show today's OTP count\n\n"
        f"💰 Rate: $0.005 per OTP",
        parse_mode='Markdown'
    )

async def stats_command(update: Update, context):
    DATA_FILE = os.path.join(REPO_PATH, 'data', 'otp_logs.json')
    today = datetime.now().strftime('%Y-%m-%d')
    count = 0
    
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                logs = json.load(f)
                count = len([l for l in logs if l.get('date') == today])
        except:
            pass
    
    await update.message.reply_text(
        f"📊 *Today's Stats*\n"
        f"OTPs: {count}\n"
        f"Earnings: ${count * 0.005:.2f}",
        parse_mode='Markdown'
    )

def main():
    print("=" * 50)
    print("🤖 Starting NexusPanel OTP Bot...")
    print(f"📁 Repo path: {REPO_PATH}")
    print(f"🔑 GitHub Token: {GITHUB_TOKEN[:10]}... (hidden)")
    print("=" * 50)
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Bot is running! Press Ctrl+C to stop")
    app.run_polling()

if __name__ == "__main__":
    main()            phone = m.group(1) if m.groups() else m.group(0)
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
