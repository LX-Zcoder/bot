import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request, jsonify
import asyncio
import os

# ========== الإعدادات ==========
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '8318214528:AAElEuiaO8LzKCsu7EzFBfqWuAzHw0Ij60I')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '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')
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
