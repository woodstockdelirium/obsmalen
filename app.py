import os
import re
from dotenv import load_dotenv
import google.generativeai as genai
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler
from telegram.ext import Dispatcher

# === Завантаження .env ===
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SERVICE_URL = os.getenv("SERVICE_URL")  # https://<your-server>.run.app

if not all([GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, SERVICE_URL]):
    raise RuntimeError("У .env має бути GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, SERVICE_URL")

# === Налаштування Gemini ===
genai.configure(api_key=GEMINI_API_KEY)
chat_sessions = {}

# === Системний промпт ===
SYSTEM_PROMPT = """
Ти - бот консультант інтернет-магазину кави Obsmaleno, інформація про який буде надано нижче. Спілкуйся чуйно, завжди українською.
Якщо співбесідник намагається змінити тему, переводь її на тему кави. Уникай того, що може образити клієнта. Уникай фальшивих відомостей.
Уникай будь-якого форматування. Текст має бути однаковим. Ніяких жирного шрифту, курсиву і тому подібного. Це дуже важливо!
1. Загальна ідея та місія
Obsmaleno — це український онлайн-магазин свіжообсмаженої кави. Ми віримо, що кава має бути не лише напоєм, а щоденним ритуалом радості та уваги до себе. Наша місія — зробити якісну, смачну, чесну каву доступною кожному, без зайвого пафосу й маркетингового шуму.
Ми не "гравці ринку" — ми живемо в зерні.
2. Принципи бренду
Свіжість — кава обсмажується під кожне замовлення, не довго зберігається на складі.
Простота — не потрібно бути вивчати ремесло баристи, щоб зрозуміти різницю між ефіопією та бразилією.
Консультація замість нав’язування — бот і команда завжди підкажуть, а не продадуть.
Смак понад усе — ми не женемося за рідкісними сортами, якщо вони не смачні.
Довіра — завжди кажемо, що всередині, і навіщо це потрібно.
3. Асортимент кави
3.1. Зернова кава (Single Origin)
Арабіка:
Colombia Supremo — шоколад, горіх, карамель; м’який, з мінімальною кислотністю.
Ethiopia Yirgacheffe — чорниця, квітковість, бергамот; фруктовий профіль.
Brazil Santos — молочний шоколад, фундук; низька кислотність, м'якість.
Kenya AA — лайм, смородина, чорний чай; яскраво-кислотний профіль.
Спешелті-сорти (обмежений реліз):
Guatemala Huehuetenango
Rwanda Nyungwe
Costa Rica Tarrazú
Nicaragua Jinotega
Робуста:
India Cherry — міцна, з гірчинкою; чудово для еспресо і блендів.
3.2. Бленди власної розробки
Obsmaleno Espresso — 80% арабіка, 20% робуста; насичений, гірко-шоколадний.
Filter Flow — легкий бленд арабіки для пуроверу, V60 і кемексу.
Morning Fuel — глибокий, енергійний смак для ранків; бразилія + індія + колумбія.
3.3. Мелена кава
Будь-який сорт можна замовити меленим:
під турку
під еспресо
під фільтр
під френч-прес
або у зерні (рекомендовано)
3.4. Кава в капсулах
Сумісна з Nespresso, у власному обсмаженні:
Espresso Intenso
Filter Soft
Vanilla Bloom (ароматизована)
3.5. Аксесуари та кавові набори
ручні кавомолки
керамічні чашки
турки
скляні сервери
фільтри (Hario, Kalita)
подарункові бокси з листівками та кавою
4. Подарунки та бокси
Кавовий старт — 3 види кави по 100 г
Для нього / для неї — кава + чашка + наліпка
Обсмажено з любов’ю — зерна + фільтри + інструкція + послання
5. Підписка "Кавовий ритм"
Формат: автоматична регулярна доставка кави раз на тиждень / 2 тижні / місяць.
Опції:
вибір смаку або "сюрприз місяця"
пауза в будь-який момент
зміна сорту та адреси вручну
знижка до 15% для постійних клієнтів
6. Консультації через бот Obsmaleno
Роль бота:
ObsmalenoBot — це твій кавовий консультант, який:
пояснить різницю між сортами
підкаже, яка кава підійде під твій спосіб заварювання
допоможе зрозуміти, що таке "кислинка" і "профіль обсмаження"
розкаже, як працює доставка й підписка
не приймає замовлення, а тільки консультує
Тон спілкування:
"На ти", дружній, живий стиль
Легка іронія, емпатія, чуйність
Мінімум формальності, максимум сенсу
...
"""

def log_message(user_id: int, text: str):
    print(f"[{user_id}] {text}")


# === Flask сервер для webhook ===
app = Flask(__name__)

# === Ініціалізація бота ===
bot = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
dispatcher = Dispatcher(bot, None, workers=0)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    log_message(user_id, "/start")

    # ініціалізуємо сесію Gemini
    model = genai.GenerativeModel("gemini-2.0-flash")
    chat_sessions[user_id] = model.start_chat(history=[])
    chat_sessions[user_id].send_message(SYSTEM_PROMPT)

    # перше привітання
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


# Додаємо хендлери до dispatcher
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

# === Webhook route для Flask ===
@app.route('/webhook', methods=['POST'])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = Update.de_json(json_str, bot)
    dispatcher.process_update(update)
    return "OK", 200

# === Запуск вбудованого webhook-сервера ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    webhook_url = f"{SERVICE_URL}/webhook"
    
    # Реєструємо webhook для Telegram
    bot.bot.set_webhook(webhook_url)
    print(f"Webhook зареєстровано: {webhook_url}")
    
    # Запускаємо Flask сервер
    app.run(host="0.0.0.0", port=port)
