import os
from dotenv import load_dotenv
import google.generativeai as genai
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler, ContextTypes

# === Завантаження .env ===
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SERVICE_URL = os.getenv("SERVICE_URL")  # https://<your-server>.onrender.com

if not all([GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, SERVICE_URL]):
    raise RuntimeError("У .env має бути GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, SERVICE_URL")

# === Налаштування Gemini ===
genai.configure(api_key=GEMINI_API_KEY)
chat_sessions = {}

# === Системний промпт ===
SYSTEM_PROMPT = """
Ти - бот консультант інтернет-магазину кави Obsmaleno, інформація про який буде надано нижче. Спілкуйся чуйно, завжди українською.
...
"""

def log_message(user_id: int, text: str):
    print(f"[{user_id}] {text}")

# === Flask сервер для webhook ===
app = Flask(__name__)

# === Ініціалізація бота ===
bot = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    log_message(user_id, "/start")
    model = genai.GenerativeModel("gemini-2.0-flash")
    chat_sessions[user_id] = model.start_chat(history=[])
    chat_sessions[user_id].send_message(SYSTEM_PROMPT)

    response = chat_sessions[user_id].send_message("Привіт!")
    await update.message.reply_text(response.text)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    log_message(user_id, text)

    if user_id not in chat_sessions:
        await start(update, context)
        return
    try:
        response = chat_sessions[user_id].send_message(text)
        await update.message.reply_text(response.text)
    except Exception as e:
        print("Помилка Gemini:", e)
        await update.message.reply_text("Сталася помилка. Спробуй ще раз пізніше.")

# Додаємо хендлери до бота
bot.add_handler(CommandHandler("start", start))
bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

# === Обробник для кореневого шляху ===
@app.route('/')
def home():
    return "ObsmalenoBot is running! Use /webhook for updates.", 200

# === Webhook route для Flask ===
@app.route('/webhook', methods=['POST'])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = Update.de_json(json_str, bot)
    bot.process_update(update)
    return "OK", 200

# === Запуск Flask серверу ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Використовуємо порт з середовища
    webhook_url = f"{SERVICE_URL}/webhook"
    
    # Реєструємо webhook для Telegram
    bot.bot.set_webhook(webhook_url)
    print(f"Webhook зареєстровано: {webhook_url}")
    
    # Запускаємо Flask сервер
    app.run(host="0.0.0.0", port=port)
