import os
import telebot
import threading
import json
from flask import Flask
from time import sleep

# Load environment variables
load_dotenv()

# Configuration
TOKEN = "8954395264:AAGtLtIHsNN-HDYDCFylEBV_IJ0X7-JvSaU"
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required!")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# গালিগালাজের তালিকা
BAD_WORDS = ["শালা", "shala", "শালি", "shali", "কুত্তা", "kutta", "হারামি", "harami", "হারামজাদা", "haramzada", "বালের", "baler", "বাল", "bal", "গাধা", "gadha", "গাধার বাচ্চা", "gadhar baccha", "চুদির", "chudir", "চুদনা", "chudna", "চোদা", "choda", "চোদাচোদি", "chodachodi", "মাগি", "magi", "ফালতু", "faltu", "তোর বাপের", "tor baper", "কুত্তার বাচ্চা", "kuttar baccha", "শুয়োর", "shuyor", "বেয়াদব", "beyadob", "খাইয়া দে", "khaiya de", "তোর মা", "tor ma", "তোর বোন", "tor bon", "লুচ্চা", "luccha", "খানকি", "khanki", "খানকির পো", "khankir po", "পোদ", "pod", "পুদ", "pud", "বালের পো", "baler po"]

# এডমিন আইডি (অপশনাল - দ্রুত চেক এর জন্য)
ADMIN_IDS = []  # উদাহরণ: [123456789, 987654321]

# সতর্কতা ডাটা লোড এবং সেভ করার ফাংশন
def load_warnings():
    try:
        with open('warnings.json', 'r') as f:
            return json.load(f)
    except:
        return {}

def save_warnings():
    with open('warnings.json', 'w') as f:
        json.dump(warnings, f)

warnings = load_warnings()

# --- এডমিন চেক করার ফাংশন ---
def is_user_admin(chat_id, user_id):
    try:
        # দ্রুত চেক - হার্ডকোডেড এডমিন আইডি
        if user_id in ADMIN_IDS:
            return True
        
        # বট নিজেই?
        if user_id == bot.get_me().id:
            return True
        
        # চ্যাট মেম্বার স্ট্যাটাস চেক
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except Exception as e:
        print(f"Error checking admin: {e}")
        return False

# --- কমান্ড হ্যান্ডলার ---
@bot.message_handler(commands=['start', 'rules'])
def send_rules(message):
    bot.reply_to(message, "📜 **গ্রুপের নিয়মাবলী:**\n1. অশালীন ভাষা ব্যবহার নিষেধ।\n2. লিংক শেয়ার করা নিষেধ।\n3. এডমিনদের সম্মান করুন।")

# --- অটো জয়েন রিকোয়েস্ট এক্সেপ্ট ---
@bot.chat_join_request_handler()
def approve_request(request):
    try:
        bot.approve_chat_join_request(request.chat.id, request.from_user.id)
        bot.send_message(request.chat.id, f"🌟 স্বাগতম {request.from_user.first_name}! আমাদের গ্রুপে নিয়ম মেনে চলুন।")
    except Exception as e:
        print(f"Join error: {e}")

# --- লিংক চেক করার ফাংশন ---
def check_links(text):
    links = ["http://", "https://", "t.me/", "www.", ".com", ".net"]
    return any(link in text for link in links)

# --- খারাপ শব্দ চেক করার ফাংশন ---
def check_bad_words(text):
    return any(word in text for word in BAD_WORDS)

# --- মূল মডারেশন লজিক (শুধু টেক্সট) ---
@bot.message_handler(content_types=['text'])
def auto_moderator(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    # 1. প্রাইভেট মেসেজ স্কিপ করো
    if message.chat.type == "private":
        return
    
    # 2. এডমিন হলে কোনো ফিল্টার কাজ করবে না
    if is_user_admin(chat_id, user_id):
        return

    # 3. টেক্সট সংগ্রহ করো
    text = (message.text or "").lower()
    if not text:
        return

    # 4. লিংক চেক করো
    if check_links(text):
        try:
            bot.delete_message(chat_id, message.message_id)
            bot.send_message(chat_id, f"⚠️ {user_name}, গ্রুপে লিংক দেওয়া নিষেধ!")
        except:
            pass
        return

    # 5. গালিগালাজ চেক করো
    if check_bad_words(text):
        try:
            bot.delete_message(chat_id, message.message_id)
            warnings[user_id] = warnings.get(user_id, 0) + 1
            save_warnings()
            
            if warnings[user_id] >= 3:
                bot.ban_chat_member(chat_id, user_id)
                bot.send_message(chat_id, f"🚫 {user_name} কে 3 বার গালি দেওয়ার কারণে ব্যান করা হয়েছে।")
                warnings[user_id] = 0
                save_warnings()
            else:
                bot.send_message(chat_id, f"⚠️ {user_name}, অশালীন ভাষা ব্যবহার করবেন না! সতর্কতা: {warnings[user_id]}/3")
        except:
            pass
        return

    # 6. এপিসোড রিলেটেড অটো রিপ্লাই
    keywords = ["episode", "ep", "এপিসোড", "দিবেন", "কখন", "kokhon", "diben", "den", "পর্ব", "ajker"]
    if any(key in text for key in keywords):
        bot.reply_to(message, "⏳ দয়া করে ধৈর্য ধরুন, শীঘ্রই আজকের এপিসোড আপলোড দেওয়া হবে।")

# --- ফটো/ভিডিও ক্যাপশন মডারেশন ---
@bot.message_handler(content_types=['photo', 'video', 'document'])
def moderate_media_caption(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    if message.chat.type == "private":
        return
    
    if is_user_admin(chat_id, user_id):
        return

    # ক্যাপশন চেক করো
    caption = (message.caption or "").lower()
    if not caption:
        return

    # লিংক চেক করো
    if check_links(caption):
        try:
            bot.delete_message(chat_id, message.message_id)
            bot.send_message(chat_id, f"⚠️ {user_name}, গ্রুপে লিংক দেওয়া নিষেধ!")
        except:
            pass
        return

    # খারাপ শব্দ চেক করো
    if check_bad_words(caption):
        try:
            bot.delete_message(chat_id, message.message_id)
            warnings[user_id] = warnings.get(user_id, 0) + 1
            save_warnings()
            
            if warnings[user_id] >= 3:
                bot.ban_chat_member(chat_id, user_id)
                bot.send_message(chat_id, f"🚫 {user_name} কে 3 বার গালি দেওয়ার কারণে ব্যান করা হয়েছে।")
                warnings[user_id] = 0
                save_warnings()
            else:
                bot.send_message(chat_id, f"⚠️ {user_name}, অশালীন ভাষা ব্যবহার করবেন না! সতর্কতা: {warnings[user_id]}/3")
        except:
            pass

# --- FLASK SERVER ---
@app.route('/')
def home():
    return "Bot is running perfectly!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    # Flask থ্রেড চালু করো
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    print("Flask server started on port 8080")
    print("Bot is starting...")
    
    # বট পোলিং সাথে এরর হ্যান্ডলিং
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"Polling error: {e}")
            sleep(5)  # 5 সেকেন্ড অপেক্ষা করে পুনরায় চেষ্টা করো
