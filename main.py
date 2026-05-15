import os
import telebot
from flask import Flask
import threading

TOKEN = "8954395264:AAGtLtIHsNN-HDYDCFylEBV_IJ0X7-JvSaU"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# গালিগালাজের লিস্ট (আপনার প্রয়োজন মতো আরও যোগ করতে পারেন)
BAD_WORDS =["শালা", "shala",
  "শালি", "shali",
  "কুত্তা", "kutta",
  "হারামি", "harami",
  "হারামজাদা", "haramzada",
  "বালের", "baler",
  "বাল", "bal",
  "গাধা", "gadha",
  "গাধার বাচ্চা", "gadhar baccha",
  "চুদির", "chudir",
  "চুদনা", "chudna",
  "চোদা", "choda",
  "চোদাচোদি", "chodachodi",
  "মাগি", "magi",
  "ফালতু", "faltu",
  "তোর বাপের", "tor baper",
  "কুত্তার বাচ্চা", "kuttar baccha",
  "শুয়োর", "shuyor",
  "বেয়াদব", "beyadob",
  "খাইয়া দে", "khaiya de",
  "তোর মা", "tor ma",
  "তোর বোন", "tor bon",
  "লুচ্চা", "luccha",
  "খানকি", "khanki",
  "খানকির পো", "khankir po",
  "পোদ", "pod",
  "পুদ", "pud",
  "বালের পো", "baler po"]
# --- অটো জয়েন রিকোয়েস্ট এক্সেপ্ট ---
@bot.chat_join_request_handler()
def approve_request(request):
    bot.approve_chat_join_request(request.chat.id, request.from_user.id)
    bot.send_message(request.chat.id, f"🌟 স্বাগতম @{request.from_user.username}! আমাদের গ্রুপে আসার জন্য ধন্যবাদ। নিয়ম মেনে চলুন।")

# --- স্মার্ট রিপ্লাই ও অটো মডারেশন ---
@bot.message_handler(func=lambda message: True)
def auto_moderator(message):

    text = message.text.lower() if message.text else ""

    # ১. এপিসোড রিলেটেড অটো রিপ্লাই
    keywords = [
        "episode",
        "ep",
        "এপিসোড",
        "দিবেন",
        "কখন",
        "পর্ব",
        "ajker",
        "porbo",
        "den",
        "diben",
        "taratari",
        "তাড়াতাড়ি",
        "কখন দিবেন",
        "দেন"
    ]

    if any(key in text for key in keywords):

        bot.reply_to(
            message,
            "⏳ দয়া করে ধৈর্য ধরুন, "
            "শীঘ্রই আজকের এপিসোড আপলোড দেওয়া হবে।"
        )

        return

    # ২. গালিগালাজ চেক
    if any(word in text for word in BAD_WORDS):

        bot.delete_message(
            message.chat.id,
            message.message_id
        )

        bot.send_message(
            message.chat.id,
            f"⚠️ {message.from_user.first_name}, "
            f"বাজে ভাষা ব্যবহার করবেন না!"
        )

        return

    # ৩. এন্টি-লিংক
    if (
        "http" in text
        or "t.me" in text
        or "www." in text
        or ".com" in text
    ):

        member = bot.get_chat_member(
            message.chat.id,
            message.from_user.id
        )

        # Admin হলে delete করবে না
        if member.status not in [
            "administrator",
            "creator"
        ]:

            # Bot নিজের message delete করবে না
            if (
                message.from_user.id
                != bot.get_me().id
            ):

                bot.delete_message(
                    message.chat.id,
                    message.message_id
                )

                bot.send_message(
                    message.chat.id,
                    f"⚠️ {message.from_user.first_name}, "
                    f"গ্রুপে লিংক দেওয়া নিষেধ!"
                )

                
# --- FLASK (Render) ---
@app.route('/')
def home(): return "Manager Bot is active!"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))).start()
    bot.polling(none_stop=True)
