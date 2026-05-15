import os
import telebot
import threading
import re
from flask import Flask

# ================== কনফিগারেশন ==================
TOKEN = "8954395264:AAGtLtIHsNN-HDYDCFylEBV_IJ0X7-JvSaU"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# গালিগালাজের তালিকা
BAD_WORDS = ["শালা", "shala", "শালি", "shali", "কুত্তা", "kutta", "হারামি", "harami", 
             "হারামজাদা", "haramzada", "বালের", "baler", "বাল", "bal", "গাধা", "gadha", 
             "গাধার বাচ্চা", "gadhar baccha", "চুদির", "chudir", "চুদনা", "chudna", 
             "চোদা", "choda", "চোদাচোদি", "chodachodi", "মাগি", "magi", "ফালতু", "faltu", 
             "তোর বাপের", "tor baper", "কুত্তার বাচ্চা", "kuttar baccha", "শুয়োর", "shuyor", 
             "বেয়াদব", "beyadob", "খাইয়া দে", "khaiya de", "তোর মা", "tor ma", 
             "তোর বোন", "tor bon", "লুচ্চা", "luccha", "খানকি", "khanki", 
             "খানকির পো", "khankir po", "পোদ", "pod", "পুদ", "pud", "বালের পো", "baler po"]

warnings = {}
admin_cache = {}  # ক্যাশিং যাতে বারবার এডমিন চেক না হয়

# ================== এডমিন চেক ফাংশন ==================
def is_user_admin(chat_id, user_id):
    if user_id == bot.get_me().id:
        return True

    cache_key = f"{chat_id}_{user_id}"
    if cache_key in admin_cache:
        return admin_cache[cache_key]

    try:
        member = bot.get_chat_member(chat_id, user_id)
        is_admin = member.status in ['administrator', 'creator']
        admin_cache[cache_key] = is_admin
        return is_admin
    except Exception as e:
        print(f"Admin check error: {e}")
        return False

# ================== কমান্ড হ্যান্ডলার ==================
@bot.message_handler(commands=['start', 'rules'])
def send_rules(message):
    bot.reply_to(message, "📜 **গ্রুপের নিয়মাবলী:**\n"
                          "১. অশালীন ভাষা ব্যবহার নিষেধ।\n"
                          "২. লিংক শেয়ার করা নিষেধ।\n"
                          "৩. এডমিনদের সম্মান করুন।")

# ================== জয়েন রিকোয়েস্ট ==================
@bot.chat_join_request_handler()
def approve_request(request):
    try:
        bot.approve_chat_join_request(request.chat.id, request.from_user.id)
        bot.send_message(request.chat.id, 
                        f"🌟 স্বাগতম {request.from_user.first_name}! আমাদের গ্রুপে নিয়ম মেনে চলুন।")
    except Exception as e:
        print(f"Join error: {e}")

# ================== মূল মডারেশন ==================
@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video', 'document', 'caption'])
def auto_moderator(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "User"

    if message.chat.type == "private":
        return

    # এডমিন হলে কোনো ফিল্টার চলবে না
    if is_user_admin(chat_id, user_id):
        return

    # টেক্সট সংগ্রহ
    text = (message.text or message.caption or "").lower()
    if not text:
        return

    # ================== এন্টি-লিংক (উন্নত) ==================
    link_pattern = re.compile(r'(https?://|t\.me/|www\.|\.com|\.net|\.org|\.info)', re.IGNORECASE)
    if link_pattern.search(text):
        try:
            bot.delete_message(chat_id, message.message_id)
            bot.send_message(chat_id, f"⚠️ {user_name}, গ্রুপে লিংক দেওয়া নিষেধ!")
            return
        except:
            pass

    # ================== গালি ফিল্টার ==================
    if any(word in text for word in BAD_WORDS):
        try:
            bot.delete_message(chat_id, message.message_id)
            warnings[user_id] = warnings.get(user_id, 0) + 1

            if warnings[user_id] >= 3:
                bot.ban_chat_member(chat_id, user_id)
                bot.send_message(chat_id, f"🚫 {user_name} কে ৩ বার গালি দেওয়ার কারণে ব্যান করা হয়েছে।")
                warnings[user_id] = 0
            else:
                bot.send_message(chat_id, 
                    f"⚠️ {user_name}, অশালীন ভাষা ব্যবহার করবেন না! সতর্কতা: {warnings[user_id]}/3")
            return
        except:
            pass

    # ================== এপিসোড রিলেটেড অটো রিপ্লাই ==================
    keywords = ["episode", "ep", "এপিসোড", "দিবেন", "কখন", "kokhon", "diben", "den", 
                "পর্ব", "ajker", "আজকের", "কবে"]
    if any(key in text for key in keywords):
        bot.reply_to(message, "⏳ দয়া করে ধৈর্য ধরুন, শীঘ্রই আজকের এপিসোড আপলোড দেওয়া হবে।")

# ================== FLASK SERVER ==================
@app.route('/')
def home():
    return "✅ Bot is running perfectly!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# ================== বট চালু ==================
if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    print("🤖 Bot is starting...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
