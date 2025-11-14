import json
import logging
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
import os

ADMIN_ID = 76187973  # ← сюда свой telegram ID
ADMIN_IDS = {76187973, 862394584}

#----

from datetime import datetime

# --- ЛОГИРОВАНИЕ В ФАЙЛ ---
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)

# --- СТАТИСТИКА ---
def load_stats():
    if not os.path.exists("stats.json"):
        return {"completed_tests": 0}
    with open("stats.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_stats(stats):
    with open("stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

def increase_completed():
    stats = load_stats()
    stats["completed_tests"] += 1
    save_stats(stats)

#----



# Загружаем переменные из .env
# Загружаем переменные из .env (если файл есть)
from pathlib import Path
env_path = Path('.') / '.env'
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

# Получаем токен из переменных окружения
BOT_TOKEN = os.environ.get("BOT_TOKEN")

if os.getenv("RAILWAY_ENVIRONMENT"):
    print("Running on Railway environment")
    print("Environment keys:", list(os.environ.keys()))
else:
    print("Running locally")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Проверь .env локально или переменные Railway")

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Загрузка данных ---
def load_json(filename: str):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

QUESTIONS = load_json("questions.json")
RESULTS = load_json("results.json")

# --- Хранилище данных пользователей ---
user_data = {}

# --- Команда /start ---
@dp.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id
    user_data[user_id] = {"current_q": 0, "scores": {}}

    await message.answer("✨ Какой ты гаджет в DNS? ✨ /предели свою техническую личность!/nЗабудь о скучных гороскопах! Наше истинное «я» куда точнее раскрывают привычные гаджеты. Пройди тест и узнай, какую функцию ты выполняешь в компании друзей и в повседневной жизни.")
    await send_question(message.chat.id, user_id)

# --- Отправка вопроса ---
async def send_question(chat_id, user_id):
    data = user_data[user_id]
    q_index = data["current_q"]

    if q_index >= len(QUESTIONS):
        await show_result(chat_id, user_id)
        return

    q = QUESTIONS[q_index]
    text = f"❓ <b>{q['question']}</b>"
    builder = InlineKeyboardBuilder()

    for i, option in enumerate(q["options"]):
        builder.button(text=option["text"], callback_data=f"answer_{i}")

    builder.adjust(1)
    await bot.send_message(chat_id, text, reply_markup=builder.as_markup(), parse_mode="HTML")

# --- Обработка ответа ---
@dp.callback_query(F.data.startswith("answer_"))
async def handle_answer(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = user_data[user_id]
    q_index = data["current_q"]
    answer_index = int(callback.data.split("_")[1])

    question = QUESTIONS[q_index]
    option = question["options"][answer_index]

    # Добавляем баллы по всем персонажам
    for name, score in option["scores"].items():
        data["scores"][name] = data["scores"].get(name, 0) + score

    data["current_q"] += 1
    await callback.message.delete()
    await send_question(callback.message.chat.id, user_id)

# --- Показ результата ---
async def show_result(chat_id, user_id):
    scores = user_data[user_id]["scores"]

    if not scores:
        await bot.send_message(chat_id, "Ты не ответил ни на один вопрос 😅")
        return

    # Определяем победителя
    winner = max(scores, key=scores.get)
    result = RESULTS.get(winner, {"description": "Неизвестный персонаж", "image": None})
    
    logging.info(
        f"User {user_id} finished test. Result: {winner}. Scores: {scores}"
    )
    increase_completed()

    text = f"🏆 <b>Ты — {winner}!</b>\n\n{result['description']}"
    if result.get("image"):
        await bot.send_photo(chat_id, photo=result["image"], caption=text, parse_mode="HTML")
    else:
        await bot.send_message(chat_id, text, parse_mode="HTML")

@dp.message(F.text == "/stats")
async def cmd_stats(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("Нет доступа.")

    stats = load_stats()
    await message.answer(f"👥 Тест прошли: {stats['completed_tests']}")

# --- Запуск бота ---
if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
