import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request, jsonify
import asyncio
import os

# ========== الإعدادات ==========
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
GROQ_MODEL = 'llama3-70b-8192'

# ========== قاعدة المعرفة ==========
faq = {
    "ما هي أكاديمية الماهرون؟": "هي أكاديمية لتحفيظ وتعليم القرآن الكريم أونلاين، بدأت عام 2022.",
    "هل يوجد تجربة مجانية؟": "نعم، الأكاديمية توفر حصة تجريبية مجانية تمامًا.",
    "هل الحصص فردية أم جماعية؟": "كل الحصص فردية وخاصة بين الطالب والمعلم.",
    "ما هي الأسعار؟": "تختلف حسب عدد الأيام والأوقات. تواصل معنا لتحديد السعر المناسب.",
    "هل توجد شهادات؟": "نعم، يحصل الطالب على شهادة بعد اجتياز المستوى."
}

# ========== إعداد السجلات ==========
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# ========== وظائف الذكاء الاصطناعي ==========
def ask_groq(prompt: str) -> str:
    if not GROQ_API_KEY:
        logging.error("GROQ_API_KEY is not set. Cannot call Groq API.")
        return "عذراً، مفتاح Groq API غير متاح. يرجى إبلاغ الإدارة."

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "أجب كأنك خدمة عملاء لأكاديمية لتحفيظ القرآن."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content'].strip()
    except requests.exceptions.RequestException as e:
        logging.error(f"خطأ في الاتصال بـ Groq API: {e}")
        return f"عذراً، حدث خطأ أثناء التواصل مع Groq AI: {e}"

# ========== وظائف البوت ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحباً بك في بوت أكاديمية الماهرون لتحفيظ القرآن الكريم! 🌙\nاكتب سؤالك وسنقوم بالرد عليك.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text.strip()
    logging.info(f"رسالة جديدة من المستخدم: {user_msg}")

    if user_msg in faq:
        reply = faq[user_msg]
        logging.info("الرد من قاعدة المعرفة المحلية.")
    else:
        logging.info("الرد من Groq AI.")
        reply = ask_groq(user_msg)

    await update.message.reply_text(reply)
    logging.info("تم إرسال الرد.")

# إعداد التطبيق الخاص بـ Flask و Telegram
if not TELEGRAM_TOKEN:
    logging.error("متغير البيئة TELEGRAM_TOKEN غير متاح. لا يمكن بناء التطبيق.")
    app = None
else:
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

flask_app = Flask(__name__)

# مسار أساسي يعطي حالة البوت
@flask_app.route('/')
def home():
    status = {}
    status['message'] = "البوت يعمل بنجاح على Render."
    status['telegram_token_set'] = bool(TELEGRAM_TOKEN)
    status['groq_api_key_set'] = bool(GROQ_API_KEY)
    
    if not status['telegram_token_set']:
        status['error'] = "متغير البيئة TELEGRAM_TOKEN غير متاح."
    if not status['groq_api_key_set']:
        status['error'] = "متغير البيئة GROQ_API_KEY غير متاح."
    
    return jsonify(status)

# مسار الويب هوك الذي يستقبل طلبات تيليجرام
@flask_app.route('/webhook', methods=['POST'])
def webhook_handler():
    if app is None:
        logging.error("تم استلام طلب ويب هوك لكن تطبيق البوت غير مهيأ بسبب عدم توفر TELEGRAM_TOKEN.")
        return jsonify({'status': 'error', 'message': 'Bot not initialized'}), 500

    try:
        logging.info("استلام طلب ويب هوك من تيليجرام.")
        update_data = request.get_json()
        
        update = Update.de_json(update_data, app.bot)
        
        asyncio.run(app.process_update(update))
        
        logging.info("تمت معالجة الويب هوك بنجاح.")
        return jsonify({'status': 'ok'})
    except Exception as e:
        logging.error(f"خطأ في معالجة الويب هوك: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def vercel_handler(event, context):
    with flask_app.app_context():
        pass
    return flask_app(event, context)

if __name__ == "__main__":
    flask_app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    data = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "أجب كأنك خدمة عملاء لأكاديمية لتحفيظ القرآن."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content'].strip()
    except requests.exceptions.RequestException as e:
        logging.error(f"خطأ في الاتصال بـ Groq API: {e}")
        return f"عذراً، حدث خطأ أثناء التواصل مع Groq AI: {e}"

# ========== وظائف البوت ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحباً بك في بوت أكاديمية الماهرون لتحفيظ القرآن الكريم! 🌙\nاكتب سؤالك وسنقوم بالرد عليك.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text.strip()
    logging.info(f"رسالة جديدة من المستخدم: {user_msg}")

    if user_msg in faq:
        reply = faq[user_msg]
        logging.info("الرد من قاعدة المعرفة المحلية.")
    else:
        logging.info("الرد من Groq AI.")
        reply = ask_groq(user_msg)

    await update.message.reply_text(reply)
    logging.info("تم إرسال الرد.")

# إعداد التطبيق الخاص بـ Flask و Telegram
if not TELEGRAM_TOKEN:
    logging.error("متغير البيئة TELEGRAM_TOKEN غير متاح. لا يمكن بناء التطبيق.")
    app = None
else:
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

flask_app = Flask(__name__)

# مسار أساسي يعطي حالة البوت
@flask_app.route('/')
def home():
    status = {}
    status['message'] = "البوت يعمل بنجاح على Render."
    status['telegram_token_set'] = bool(TELEGRAM_TOKEN)
    status['groq_api_key_set'] = bool(GROQ_API_KEY)
    
    if not status['telegram_token_set']:
        status['error'] = "متغير البيئة TELEGRAM_TOKEN غير متاح."
    if not status['groq_api_key_set']:
        status['error'] = "متغير البيئة GROQ_API_KEY غير متاح."
    
    return jsonify(status)

# مسار الويب هوك الذي يستقبل طلبات تيليجرام
@flask_app.route('/webhook', methods=['POST'])
def webhook_handler():
    if app is None:
        logging.error("تم استلام طلب ويب هوك لكن تطبيق البوت غير مهيأ بسبب عدم توفر TELEGRAM_TOKEN.")
        return jsonify({'status': 'error', 'message': 'Bot not initialized'}), 500

    try:
        logging.info("استلام طلب ويب هوك من تيليجرام.")
        update_data = request.get_json()
        
        update = Update.de_json(update_data, app.bot)
        
        asyncio.run(app.process_update(update))
        
        logging.info("تمت معالجة الويب هوك بنجاح.")
        return jsonify({'status': 'ok'})
    except Exception as e:
        logging.error(f"خطأ في معالجة الويب هوك: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def vercel_handler(event, context):
    with flask_app.app_context():
        pass
    return flask_app(event, context)

if __name__ == "__main__":
    flask_app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # يرفع خطأ إذا كانت الحالة غير ناجحة
        result = response.json()
        return result['choices'][0]['message']['content'].strip()
    except requests.exceptions.RequestException as e:
        logging.error(f"خطأ في الاتصال بـ Groq API: {e}")
        return "عذرًا، حدث خطأ أثناء التواصل مع الذكاء الاصطناعي."

# ========== وظائف البوت ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحبًا بك في بوت أكاديمية الماهرون لتحفيظ القرآن الكريم! 🌙\nاكتب سؤالك وسنقوم بالرد عليك.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text.strip()
    logging.info(f"رسالة جديدة من المستخدم: {user_msg}")

    if user_msg in faq:
        reply = faq[user_msg]
    else:
        reply = ask_groq(user_msg)

    await update.message.reply_text(reply)

# إعداد التطبيق الخاص بـ Flask و Telegram
app = Application.builder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

flask_app = Flask(__name__)

# مسار أساسي للتحقق من أن التطبيق يعمل
@flask_app.route('/')
def home():
    return "البوت يعمل بنجاح!"

# مسار الويب هوك الذي يستقبل طلبات تيليجرام
@flask_app.route('/webhook', methods=['POST'])
def webhook_handler():
    try:
        # استخراج البيانات من طلب الويب هوك
        update_data = request.get_json()
        logging.info(f"استقبال تحديث ويب هوك: {update_data}")
        
        # إنشاء كائن Update من بيانات الويب هوك
        update = Update.de_json(update_data, app.bot)
        
        # معالجة التحديث بشكل غير متزامن
        asyncio.run(app.process_update(update))
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        logging.error(f"خطأ في معالجة الويب هوك: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# هذه الدالة ضرورية لكي يتم تشغيل التطبيق بواسطة Vercel
def vercel_handler(event, context):
    with flask_app.app_context():
        # هنا يمكنك استخدام المنطق الخاص بك لمعالجة الأحداث
        pass

    return flask_app(event, context)

if __name__ == "__main__":
    flask_app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
