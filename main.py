import os
import telebot
import threading
from flask import Flask

# TOKEN এবং বটের কনফিগারেশন
TOKEN = "8954395264:AAGtLtIHsNN-HDYDCFylEBV_IJ0X7-JvSaU"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# গালিগালাজের তালিকা
BAD_WORDS = ["শালা", "shala", "শালি", "shali", "কুত্তা", "kutta", "হারামি", "harami", "হারামজাদা", "haramzada", "বালের", "baler", "বাল", "bal", "গাধা", "gadha", "গাধার বাচ্চা", "gadhar baccha", "চুদির", "chudir", "চুদনা", "chudna", "চোদা", "choda", "চোদাচোদি", "chodachodi", "মাগি", "magi", "ফালতু", "faltu", "তোর বাপের", "tor baper", "কুত্তার বাচ্চা", "kuttar baccha", "শুয়োর", "shuyor", "বেয়াদব", "beyadob", "খাইয়া দে", "khaiya de", "তোর মা", "tor ma", "তোর বোন", "tor bon", "লুচ্চা", "luccha", "খানকি", "khanki", "খানকির পো", "khankir po", "পোদ", "pod", "পুদ", "pud", "বালের পো", "baler po"]
warnings = {}

# --- এডমিন চেক করার ফাংশন ---
def is_user_admin(chat_id, user_id):
    try:
        if user_id == bot.get_me().id:
            return True
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except Exception as e:
        print(f"Error checking admin: {e}")
        return False

# --- কমান্ড হ্যান্ডলার ---
@bot.message_handler(commands=['start', 'rules'])
def send_rules(message):
    bot.reply_to(message, "📜 **গ্রুপের নিয়মাবলী:**\n১. অশালীন ভাষা ব্যবহার নিষেধ।\n২. লিংক শেয়ার করা নিষেধ।\n৩. এডমিনদের সম্মান করুন।")

# --- অটো জয়েন রিকোয়েস্ট এক্সেপ্ট ---
@bot.chat_join_request_handler()
def approve_request(request):
    try:
        bot.approve_chat_join_request(request.chat.id, request.from_user.id)
        bot.send_message(request.chat.id, f"🌟 স্বাগতম {request.from_user.first_name}! আমাদের গ্রুপে নিয়ম মেনে চলুন।")
    except Exception as e:
        print(f"Join error: {e}")

# --- মূল মডারেশন লজিক ---
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'document', 'caption'])
def auto_moderator(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    # ১. গ্রুপ চেক এবং এডমিন চেক
    if message.chat.type == "private":
        return
    
    if is_user_admin(chat_id, user_id):
        return # এডমিন হলে কোনো ফিল্টার কাজ করবে না

    # ২. টেক্সট সংগ্রহ
    text = (message.text or message.caption or "").lower()
    if not text:
        return

    # ৩. এন্টি-লিংক চেক
    links = ["http://", "https://", "t.me/", "www.", ".com", ".net"]
    if any(link in text for link in links):
        try:
            bot.delete_message(chat_id, message.message_id)
            bot.send_message(chat_id, f"⚠️ {user_name}, গ্রুপে লিংক দেওয়া নিষেধ!")
            return
        except: pass

    # ৪. গালিগালাজ চেক
    if any(word in text for word in BAD_WORDS):
        try:
            bot.delete_message(chat_id, message.message_id)
            warnings[user_id] = warnings.get(user_id, 0) + 1
            if warnings[user_id] >= 3:
                bot.ban_chat_member(chat_id, user_id)
                bot.send_message(chat_id, f"🚫 {user_name} কে ৩ বার গালি দেওয়ার কারণে ব্যান করা হয়েছে।")
                warnings[user_id] = 0
            else:
                bot.send_message(chat_id, f"⚠️ {user_name}, অশালীন ভাষা ব্যবহার করবেন না! সতর্কতা: {warnings[user_id]}/3")
            return
        except: pass

    # ৫. এপিসোড রিলেটেড অটো রিপ্লাই
    keywords = ["episode", "ep", "এপিসোড", "দিবেন", "কখন", "kokhon", "diben", "den", "পর্ব", "ajker"]
    if any(key in text for key in keywords):
        bot.reply_to(message, "⏳ দয়া করে ধৈর্য ধরুন, শীঘ্রই আজকের এপিসোড আপলোড দেওয়া হবে।")

# --- FLASK SERVER ---
@app.route('/')
def home():
    return "Bot is running perfectly!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    print("Bot is starting...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
