import os
import telebot
import threading
import json
import time
from flask import Flask
from datetime import datetime

# ============================================
# CONFIGURATION & SECURITY
# ============================================
TOKEN = "8954395264:AAGtLtIHsNN-HDYDCFylEBV_IJ0X7-JvSaU"
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required!")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Admin user IDs (add your admin IDs here for faster checking)
ADMIN_IDS = set()  # You can add IDs like: {123456789, 987654321}

# Spam tracking
last_message_time = {}
SPAM_COOLDOWN = 1  # seconds

# ============================================
# PERSISTENT DATA MANAGEMENT
# ============================================
def load_warnings():
    """Load warnings from JSON file"""
    try:
        with open('data/warnings.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        os.makedirs('data', exist_ok=True)
        return {}
    except Exception as e:
        print(f"Error loading warnings: {e}")
        return {}

def save_warnings():
    """Save warnings to JSON file"""
    try:
        os.makedirs('data', exist_ok=True)
        with open('data/warnings.json', 'w') as f:
            json.dump(warnings, f, indent=2)
    except Exception as e:
        print(f"Error saving warnings: {e}")

# Load warnings on startup
warnings = load_warnings()

# ============================================
# BAD WORDS LIST (Bengali & English)
# ============================================
BAD_WORDS = [
    "শালা", "shala", "শালি", "shali", "কুত্তা", "kutta", 
    "হারামি", "harami", "হারামজাদা", "haramzada", "বালের", "baler", 
    "বাল", "bal", "গাধা", "gadha", "গাধার বাচ্চা", "gadhar baccha", 
    "চুদির", "chudir", "চুদনা", "chudna", "চোদা", "choda", 
    "চোদাচোদি", "chodachodi", "মাগি", "magi", "ফালতু", "faltu", 
    "তোর বাপের", "tor baper", "কুত্তার বাচ্চা", "kuttar baccha", 
    "শুয়োর", "shuyor", "বেয়াদব", "beyadob", "খাইয়া দে", "khaiya de", 
    "তোর মা", "tor ma", "তোর বোন", "tor bon", "লুচ্চা", "luccha", 
    "খানকি", "khanki", "খানকির পো", "khankir po", "পোদ", "pod", 
    "পুদ", "pud", "বালের পো", "baler po"
]

# Link detection patterns
LINK_PATTERNS = ["http://", "https://", "t.me/", "www.", ".com", ".net", ".org", ".io", ".co"]

# Episode-related keywords for auto-reply
EPISODE_KEYWORDS = ["episode", "ep", "এপিসোড", "দিবেন", "কখন", "kokhon", "diben", "den", "পর্ব", "ajker"]

# ============================================
# UTILITY FUNCTIONS
# ============================================
def is_spam(user_id):
    """Check if user is spamming (cooldown check)"""
    current_time = time.time()
    if user_id in last_message_time:
        if current_time - last_message_time[user_id] < SPAM_COOLDOWN:
            return True
    last_message_time[user_id] = current_time
    return False

def is_user_admin(chat_id, user_id):
    """Check if user is an admin or bot creator"""
    try:
        # Quick check against hardcoded admin IDs
        if user_id in ADMIN_IDS:
            return True
        
        # Check if user is the bot itself
        if user_id == bot.get_me().id:
            return True
        
        # Check chat member status
        member = bot.get_chat_member(chat_id, user_id)
        is_admin = member.status in ['administrator', 'creator']
        
        if is_admin and user_id not in ADMIN_IDS:
            ADMIN_IDS.add(user_id)  # Cache the admin ID
        
        return is_admin
    except Exception as e:
        print(f"Error checking admin status for user {user_id} in chat {chat_id}: {e}")
        return False

def contains_links(text):
    """Check if text contains links"""
    text_lower = text.lower()
    return any(link in text_lower for link in LINK_PATTERNS)

def contains_bad_words(text):
    """Check if text contains bad words"""
    text_lower = text.lower()
    return any(word in text_lower for word in BAD_WORDS)

def contains_episode_keywords(text):
    """Check if text mentions episodes"""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in EPISODE_KEYWORDS)

def get_text_content(message):
    """Extract text from message (handles text, caption, etc.)"""
    if message.text:
        return message.text
    elif message.caption:
        return message.caption
    return ""

# ============================================
# COMMAND HANDLERS
# ============================================
@bot.message_handler(commands=['start', 'rules'])
def send_rules(message):
    """Send group rules"""
    rules_text = """📜 **গ্রুপের নিয়মাবলী:**

1️⃣ অশালীন ভাষা ব্যবহার নিষেধ ❌
2️⃣ লিংক শেয়ার করা নিষেধ 🔗
3️⃣ এডমিনদের সম্মান করুন 🎖️
4️⃣ স্প্যাম বা বিজ্ঞাপন নিষেধ 📵

⚠️ নিয়ম ভাঙলে সতর্কতা এবং পরে ব্যান করা হবে।
"""
    bot.reply_to(message, rules_text, parse_mode='Markdown')

@bot.message_handler(commands=['warn'])
def check_warnings(message):
    """Check own warnings"""
    user_id = str(message.from_user.id)
    user_warnings = warnings.get(user_id, 0)
    bot.reply_to(message, f"⚠️ আপনার সতর্কতা: {user_warnings}/3")

@bot.message_handler(commands=['clearwarnings'])
def clear_warnings(message):
    """Admin command to clear user warnings"""
    if not is_user_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ আপনি এডমিন নন।")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ এই কমান্ড ব্যবহার করতে একটি বার্তার উত্তর দিন।")
        return
    
    target_user_id = str(message.reply_to_message.from_user.id)
    if target_user_id in warnings:
        warnings[target_user_id] = 0
        save_warnings()
        bot.reply_to(message, f"✅ সতর্কতা রিসেট করা হয়েছে।")
    else:
        bot.reply_to(message, "ℹ️ এই ব্যবহারকারীর কোনো সতর্কতা নেই।")

# ============================================
# JOIN REQUEST HANDLER
# ============================================
@bot.chat_join_request_handler()
def approve_request(request):
    """Auto-approve join requests"""
    try:
        bot.approve_chat_join_request(request.chat.id, request.from_user.id)
        welcome_msg = f"🌟 স্বাগতম {request.from_user.first_name}! আমাদের গ্রুপে নিয়ম মেনে চলুন। /rules দেখতে টাইপ করুন।"
        bot.send_message(request.chat.id, welcome_msg)
    except Exception as e:
        print(f"Join request error: {e}")

# ============================================
# MAIN MODERATION HANDLER
# ============================================
@bot.message_handler(content_types=['text'])
def auto_moderator(message):
    """Main moderation function for text messages"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "ব্যবহারকারী"
    
    # Skip private messages
    if message.chat.type == "private":
        return
    
    # Skip if message is None
    if not message.text:
        return
    
    # ✅ SKIP ALL MODERATION FOR ADMINS
    if is_user_admin(chat_id, user_id):
        return
    
    # Skip if user is spamming the moderation system
    if is_spam(user_id):
        return
    
    text = message.text
    
    # ============================================
    # 1. LINK DETECTION & DELETION
    # ============================================
    if contains_links(text):
        try:
            bot.delete_message(chat_id, message.message_id)
            bot.send_message(
                chat_id, 
                f"⚠️ {user_name}, গ্রুপে লিংক শেয়ার করা নিষেধ! 🔗"
            )
            print(f"[LINK FILTER] Deleted message from {user_name} ({user_id}) in {chat_id}")
            return
        except Exception as e:
            print(f"Error deleting link message: {e}")
            return
    
    # ============================================
    # 2. BAD WORDS DETECTION & WARNING SYSTEM
    # ============================================
    if contains_bad_words(text):
        try:
            bot.delete_message(chat_id, message.message_id)
            
            user_id_str = str(user_id)
            warnings[user_id_str] = warnings.get(user_id_str, 0) + 1
            current_warnings = warnings[user_id_str]
            
            save_warnings()
            
            if current_warnings >= 3:
                # Ban the user after 3 warnings
                try:
                    bot.ban_chat_member(chat_id, user_id)
                    bot.send_message(
                        chat_id, 
                        f"🚫 {user_name} কে ৩ বার অশালীন ভাষা ব্যবহারের কারণে ব্যান করা হয়েছে।"
                    )
                    print(f"[BAN] User {user_name} ({user_id}) banned in {chat_id}")
                    warnings[user_id_str] = 0
                    save_warnings()
                except Exception as e:
                    print(f"Error banning user: {e}")
            else:
                # Send warning message
                warning_msg = f"⚠️ {user_name}, অশালীন ভাষা ব্যবহার করবেন না!\n\n সতর্কতা: {current_warnings}/3"
                bot.send_message(chat_id, warning_msg)
                print(f"[WARNING] {user_name} ({user_id}) - Warning {current_warnings}/3")
            
            return
        except Exception as e:
            print(f"Error handling bad word: {e}")
            return
    
    # ============================================
    # 3. EPISODE-RELATED AUTO REPLIES
    # ============================================
    if contains_episode_keywords(text):
        try:
            bot.reply_to(
                message,
                "⏳ দয়া করে ধৈর্য ধরুন, শীঘ্রই আজকের এপিসোড আপলোড দেওয়া হবে। 🎬"
            )
            print(f"[AUTO-REPLY] Episode reply sent to {user_name}")
        except Exception as e:
            print(f"Error sending episode reply: {e}")

# ============================================
# CAPTION & MEDIA HANDLER
# ============================================
@bot.message_handler(content_types=['photo', 'video', 'document', 'audio'])
def handle_media(message):
    """Handle media messages with captions"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "ব্যবহারকারী"
    
    # Skip private messages
    if message.chat.type == "private":
        return
    
    # ✅ SKIP ALL MODERATION FOR ADMINS
    if is_user_admin(chat_id, user_id):
        return
    
    # Get caption if exists
    caption = message.caption or ""
    
    if not caption:
        return
    
    # Check for links in caption
    if contains_links(caption):
        try:
            bot.delete_message(chat_id, message.message_id)
            bot.send_message(
                chat_id,
                f"⚠️ {user_name}, ক্যাপশনে লিংক শেয়ার করা নিষেধ! 🔗"
            )
            print(f"[LINK FILTER] Deleted media with link from {user_name}")
            return
        except Exception as e:
            print(f"Error deleting media with link: {e}")
            return
    
    # Check for bad words in caption
    if contains_bad_words(caption):
        try:
            bot.delete_message(chat_id, message.message_id)
            
            user_id_str = str(user_id)
            warnings[user_id_str] = warnings.get(user_id_str, 0) + 1
            current_warnings = warnings[user_id_str]
            
            save_warnings()
            
            if current_warnings >= 3:
                try:
                    bot.ban_chat_member(chat_id, user_id)
                    bot.send_message(
                        chat_id,
                        f"🚫 {user_name} কে ৩ বার অশালীন ভাষা ব্যবহারের কারণে ব্যান করা হয়েছে।"
                    )
                    warnings[user_id_str] = 0
                    save_warnings()
                except Exception as e:
                    print(f"Error banning user: {e}")
            else:
                warning_msg = f"⚠️ {user_name}, ক্যাপশনে অশালীন ভাষা ব্যবহার করবেন না!\n\n সতর্কতা: {current_warnings}/3"
                bot.send_message(chat_id, warning_msg)
            
            return
        except Exception as e:
            print(f"Error handling bad word in caption: {e}")

# ============================================
# FLASK SERVER (for health check & hosting)
# ============================================
@app.route('/')
def home():
    """Health check endpoint"""
    return {
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "bot": "Telegram Moderator Bot"
    }

@app.route('/stats')
def stats():
    """Return bot statistics"""
    return {
        "total_warnings": len(warnings),
        "timestamp": datetime.now().isoformat()
    }

def run_flask():
    """Run Flask server in background"""
    app.run(host="0.0.0.0", port=8080, debug=False)

# ============================================
# MAIN BOT STARTUP
# ============================================
if __name__ == "__main__":
    # Start Flask server in background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("✅ Flask server started on port 8080")
    
    # Start bot with error handling
    print("🤖 Bot is starting...")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    while True:
        try:
            print("🔄 Starting bot polling...")
            bot.infinity_polling(timeout=10, long_polling_timeout=5, non_stop=True)
        except Exception as e:
            print(f"❌ Polling error: {e}")
            print(f"⏳ Retrying in 5 seconds...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user")
            save_warnings()
            break
