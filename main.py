from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils import executor
import sqlite3

API_TOKEN = '7332735625:AAE9UbrhZFCrsMRK0GMdLK_n9mNmk7_IBho'
ADMIN_ID = '777322005'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

conn = sqlite3.connect('tasks.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS tasks
                  (id INTEGER PRIMARY KEY, user_id INTEGER, task TEXT, done INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS users
                  (user_id INTEGER PRIMARY KEY, language TEXT, phone_number TEXT)''')
conn.commit()

languages = {
    "uz": "🇺🇿 O'zbekcha",
    "ru": "🇷🇺 Русский"
}

descriptions = {
    "uz": "🇺🇿<b>Salom!</b> Men vazifalarni boshqarish uchun botman.\n\n<b>Buyruqlar:</b>\n/add - Vazifa qo'shish\n/list - Barcha vazifalarni ko'rish\n/done - Vazifani bajarilgan deb belgilash\n/delete - Vazifani o'chirish",
    "ru": "🇷🇺<b>Привет!</b> Я бот для управления задачами.\n\n<b>Команды:</b>\n/add - Добавить задачу\n/list - Показать все задачи\n/done - Отметить задачу как выполненную\n/delete - Удалить задачу"
}

functions = {
    "uz": """
<b>Funksiyalar:</b>
/add - Vazifa qo'shish
/list - Barcha vazifalarni ko'rish
/done - Vazifani bajarilgan deb belgilash
/delete - Vazifani o'chirish
    """,
    "ru": """
<b>Функции:</b>
/add - Добавить задачу
/list - Показать все задачи
/done - Отметить задачу как выполненную
/delete - Удалить задачу
    """
}


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if user is None:
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for lang in languages:
            markup.add(KeyboardButton(languages[lang]))

        await message.answer("Выберите язык / Tilni tanlang:", reply_markup=markup)
    else:
        lang = user[0]
        await message.answer(descriptions[lang], parse_mode=types.ParseMode.HTML)
        await message.answer(functions[lang], parse_mode=types.ParseMode.HTML)


@dp.message_handler(lambda message: message.text in languages.values())
async def set_language(message: types.Message):
    user_id = message.from_user.id
    for lang, lang_name in languages.items():
        if message.text == lang_name:
            cursor.execute("INSERT OR REPLACE INTO users (user_id, language) VALUES (?, ?)", (user_id, lang))
            conn.commit()

            # Запрос номера телефона
            phone_button = KeyboardButton('Отправить номер телефона 📞', request_contact=True)
            phone_markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(phone_button)
            await message.answer("Пожалуйста, отправьте свой номер телефона для завершения регистрации.", reply_markup=phone_markup)
            break


@dp.message_handler(content_types=types.ContentType.CONTACT)
async def get_contact(message: types.Message):
    user_id = message.from_user.id
    phone_number = message.contact.phone_number
    cursor.execute("UPDATE users SET phone_number = ? WHERE user_id = ?", (phone_number, user_id))
    conn.commit()

    # Отправка данных админу
    cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
    lang = cursor.fetchone()[0]
    user_data = f"Новый пользователь:\nID: {user_id}\nТелефон: {phone_number}\nЯзык: {languages[lang]}"
    await bot.send_message(ADMIN_ID, user_data)

    # Удаление клавиатуры
    await message.answer("Регистрация завершена.", reply_markup=ReplyKeyboardRemove())
    await message.answer(descriptions[lang], parse_mode=types.ParseMode.HTML)
    await message.answer(functions[lang], parse_mode=types.ParseMode.HTML)


@dp.message_handler(commands=['add'])
async def add_task(message: types.Message):
    task = message.get_args()
    if task:
        cursor.execute("INSERT INTO tasks (user_id, task, done) VALUES (?, ?, 0)", (message.from_user.id, task))
        conn.commit()
        cursor.execute("SELECT language FROM users WHERE user_id = ?", (message.from_user.id,))
        lang = cursor.fetchone()[0]
        await message.answer("Vazifa qo'shildi." if lang == "uz" else "Задача добавлена.")
    else:
        cursor.execute("SELECT language FROM users WHERE user_id = ?", (message.from_user.id,))
        lang = cursor.fetchone()[0]
        await message.answer("Iltimos, /add buyrug'idan keyin vazifani ko'rsating." if lang == "uz" else "Пожалуйста, укажите задачу после команды /add.")


@dp.message_handler(commands=['list'])
async def list_tasks(message: types.Message):
    cursor.execute("SELECT id, task, done FROM tasks WHERE user_id = ?", (message.from_user.id,))
    tasks = cursor.fetchall()
    if tasks:
        response = "Sizning vazifalaringiz:\n" if get_language(message.from_user.id) == "uz" else "Ваши задачи:\n"
        for task in tasks:
            status = "✅" if task[2] else "❌"
            response += f"{task[0]}. {task[1]} {status}\n"
        await message.answer(response)
    else:
        await message.answer("Sizda vazifalar yo'q." if get_language(message.from_user.id) == "uz" else "У вас нет задач.")


@dp.message_handler(commands=['done'])
async def choose_task_done(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT id, task FROM tasks WHERE user_id = ? AND done = 0", (user_id,))
    tasks = cursor.fetchall()
    if tasks:
        markup = InlineKeyboardMarkup()
        for task in tasks:
            markup.add(InlineKeyboardButton(task[1], callback_data=f'done_{task[0]}'))
        await message.answer("Выберите задачу, которую хотите отметить как выполненную:", reply_markup=markup)
    else:
        await message.answer("У вас нет невыполненных задач.")


@dp.message_handler(commands=['delete'])
async def choose_task_delete(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT id, task FROM tasks WHERE user_id = ?", (user_id,))
    tasks = cursor.fetchall()
    if tasks:
        markup = InlineKeyboardMarkup()
        for task in tasks:
            markup.add(InlineKeyboardButton(task[1], callback_data=f'delete_{task[0]}'))
        await message.answer("Выберите задачу, которую хотите удалить:", reply_markup=markup)
    else:
        await message.answer("У вас нет задач.")


@dp.callback_query_handler(lambda c: c.data and (c.data.startswith('done_') or c.data.startswith('delete_')))
async def process_callback_button(callback_query: types.CallbackQuery):
    action, task_id = callback_query.data.split('_')
    user_id = callback_query.from_user.id
    task_id = int(task_id)

    if action == 'done':
        cursor.execute("UPDATE tasks SET done = 1 WHERE id = ? AND user_id = ?", (task_id, user_id))
        conn.commit()
        await bot.answer_callback_query(callback_query.id, "Задача отмечена как выполненная.")
    elif action == 'delete':
        cursor.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
        conn.commit()
        await bot.answer_callback_query(callback_query.id, "Задача удалена.")

    # Удаление клавиатуры
    await bot.edit_message_reply_markup(callback_query.message.chat.id, callback_query.message.message_id, reply_markup=None)


def get_language(user_id):
    cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()[0]


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
