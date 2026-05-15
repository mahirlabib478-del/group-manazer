import os
import telebot
import threading
from flask import Flask

# TOKEN এনভায়রনমেন্ট ভেরিয়েবল থেকে নেয়া হচ্ছে
TOKEN = "8954395264:AAGtLtIHsNN-HDYDCFylEBV_IJ0X7-JvSaU"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# গালিগালাজের তালিকা
BAD_WORDS =["শালা", "shala", "শালি", "shali", "কুত্তা", "kutta", "হারামি", "harami", "হারামজাদা", "haramzada", "বালের", "baler", "বাল", "bal", "গাধা", "gadha", "গাধার বাচ্চা", "gadhar baccha", "চুদির", "chudir", "চুদনা", "chudna", "চোদা", "choda", "চোদাচোদি", "chodachodi", "মাগি", "magi", "ফালতু", "faltu", "তোর বাপের", "tor baper", "কুত্তার বাচ্চা", "kuttar baccha", "শুয়োর", "shuyor", "বেয়াদব", "beyadob", "খাইয়া দে", "khaiya de", "তোর মা", "tor ma", "তোর বোন", "tor bon", "লুচ্চা", "luccha", "খানকি", "khanki", "খানকির পো", "khankir po", "পোদ", "pod", "পুদ", "pud", "বালের পো", "baler po"]
warnings = {}

# --- কমান্ড হ্যান্ডলার ---
@bot.message_handler(commands=['start', 'rules'])
def send_rules(message):
    bot.reply_to(message, "📜 **গ্রুপের নিয়মাবলী:**\n১. কোনো অশালীন ভাষা ব্যবহার করবেন না।\n২. কোনো প্রকার লিংক শেয়ার করা নিষেধ।\n৩. এডমিনদের সাথে ভদ্র আচরণ করুন।")

# --- অটো জয়েন রিকোয়েস্ট এক্সেপ্ট ---
@bot.chat_join_request_handler()
def approve_request(request):
    try:
        bot.approve_chat_join_request(request.chat.id, request.from_user.id)
        name = request.from_user.first_name
        bot.send_message(request.chat.id, f"🌟 স্বাগতম {name}! আমাদের গ্রুপে নিয়ম মেনে চলুন।")
    except Exception as e:
        print(f"Error in join request: {e}")

# --- মূল মডারেশন লজিক ---
@bot.message_handler(func=lambda message: True)
def auto_moderator(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    # এডমিন চেক (এখানেই পরিবর্তন করা হয়েছে)
    try:
        member = bot.get_chat_member(chat_id, user_id)
        if member.status in ["administrator", "creator"]:
            return
    except:
        pass

    # স্টিকার বা মিডিয়া মেসেজ চেক করা
    if not message.text and not message.caption:
        return
    
    text = (message.text or message.caption).lower()

    # ১. এন্টি-লিংক সিস্টেম
    if any(x in text for x in ["http", "t.me", "www.", ".com"]):
        bot.delete_message(chat_id, message.message_id)
        bot.send_message(chat_id, f"⚠️ {user_name}, গ্রুপে লিংক দেওয়া নিষেধ!")
        return

    # ২. গালিগালাজ ডিটেকশন
    if any(word in text for word in BAD_WORDS):
        bot.delete_message(chat_id, message.message_id)
        warnings[user_id] = warnings.get(user_id, 0) + 1
        if warnings[user_id] >= 3:
            bot.ban_chat_member(chat_id, user_id)
            bot.send_message(chat_id, f"🚫 {user_name} কে ৩ বার গালি দেওয়ার কারণে ব্যান করা হয়েছে।")
        else:
            bot.send_message(chat_id, f"⚠️ {user_name}, অশালীন ভাষা ব্যবহার করবেন না! সতর্কতা: {warnings[user_id]}/3")
        return

    # ৩. এপিসোড রিলেটেড অটো রিপ্লাই
    keywords =["episode", "ep", "এপিসোড", "দিবেন", "কখন", "kokhon", "diben", "দেন", "দ্রুত", "druto", "pathan", "পাঠান", "পর্ব", "ajker", "den"]
    if any(key in text for key in keywords):
        bot.reply_to(message, "⏳ দয়া করে ধৈর্য ধরুন, শীঘ্রই আজকের এপিসোড আপলোড দেওয়া হবে।")

# --- FLASK ---
@app.route('/')
def home():
    return "Bot is running perfectly!"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))).start()
    bot.polling(none_stop=True)
