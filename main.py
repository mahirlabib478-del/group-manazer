import os
import telebot
import threading
from flask import Flask

TOKEN = "8954395264:AAGtLtIHsNN-HDYDCFylEBV_IJ0X7-JvSaU" # আপনার সঠিক টোকেন দিন
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

BAD_WORDS = ["শালা", "shala", "শালি", "shali", "কুত্তা", "kutta", "হারামি", "harami", "হারামজাদা", "haramzada", "বালের", "baler", "বাল", "bal", "গাধা", "gadha", "গাধার বাচ্চা", "gadhar baccha", "চুদির", "chudir", "চুদনা", "chudna", "চোদা", "choda", "চোদাচোদি", "chodachodi", "মাগি", "magi", "ফালতু", "faltu", "তোর বাপের", "tor baper", "কুত্তার বাচ্চা", "kuttar baccha", "শুয়োর", "shuyor", "বেয়াদব", "beyadob", "খাইয়া দে", "khaiya de", "তোর মা", "tor ma", "তোর বোন", "tor bon", "লুচ্চা", "luccha", "খানকি", "khanki", "খানকির পো", "khankir po", "পোদ", "pod", "পুদ", "pud", "বালের পো", "baler po"] # সংক্ষেপে দিলাম
warnings = {}

# --- এডমিন চেক করার ফাংশন ---
def is_user_admin(chat_id, user_id):
    try:
        # বটের নিজের আইডি চেক (বট যেন নিজেকে ডিলিট না করে)
        if user_id == bot.get_me().id:
            return True
        
        member = bot.get_chat_member(chat_id, user_id)
        # এডমিন বা ক্রিয়েটর হলে True রিটার্ন করবে
        if member.status in ['administrator', 'creator']:
            return True
    except Exception as e:
        print(f"Error checking admin status: {e}")
    return False

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, "বট সচল আছে!")

# --- মডারেশন লজিক ---
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'document', 'caption'])
def auto_moderator(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    # ১. প্রথমেই চেক করুন মেসেজটি গ্রুপে কি না (পার্সোনাল চ্যাটে এডমিন চেক কাজ করে না)
    if message.chat.type == "private":
        return

    # ২. এডমিন কি না চেক করুন
    if is_user_admin(chat_id, user_id):
        print(f"Admin {user_name} sent a message. Skipping moderation.")
        return # এডমিন হলে এখানেই কাজ শেষ, নিচের কোনো কিছু চেক হবে না

    # ৩. টেক্সট বা ক্যাপশন বের করা
    text = ""
    if message.text:
        text = message.text.lower()
    elif message.caption:
        text = message.caption.lower()

    if not text:
        return

    # ৪. এন্টি-লিংক (লিংক চেক)
    links = ["http://", "https://", "t.me/", "www.", ".com", ".net"]
    if any(link in text for link in links):
        try:
            bot.delete_message(chat_id, message.message_id)
            bot.send_message(chat_id, f"⚠️ {user_name}, গ্রুপে লিংক শেয়ার করা নিষেধ!")
            return
        except Exception as e:
            print(f"Delete Error (Link): {e}")

    # ৫. গালিগালাজ চেক
    if any(word in text for word in BAD_WORDS):
        try:
            bot.delete_message(chat_id, message.message_id)
            warnings[user_id] = warnings.get(user_id, 0) + 1
            
            if warnings[user_id] >= 3:
                bot.ban_chat_member(chat_id, user_id)
                bot.send_message(chat_id, f"🚫 {user_name} কে ৩ বার গালি দেওয়ার কারণে ব্যান করা হয়েছে।")
            else:
                bot.send_message(chat_id, f"⚠️ {user_name}, গালি দেবেন না! সতর্কতা: {warnings[user_id]}/3")
            return
        except Exception as e:
# ৩. এপিসোড রিলেটেড অটো রিপ্লাই
    keywords =["episode", "ep", "এপিসোড", "দিবেন", "কখন", "kokhon", "diben", "দেন", "দ্রুত", "druto", "pathan", "পাঠান", "পর্ব", "ajker", "den"]
    if any(key in text for key in keywords):
        bot.reply_to(message, "⏳ দয়া করে ধৈর্য ধরুন, শীঘ্রই আজকের এপিসোড আপলোড দেওয়া হবে।")            print(f"Delete Error (Bad Word): {e}")
            

# --- Flask server for keeping it alive ---
@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    t = threading.Thread(target=run)
    t.start()
    print("Bot is starting...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
