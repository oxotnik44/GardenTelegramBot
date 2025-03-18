import datetime
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from photo_handler import save_photo, get_fresh_photos  # Импортируем функции из модуля для работы с фото
from question_handler import save_question, get_questions  # Импортируем функции из модуля для работы с вопросами

# Загружаем переменные окружения из .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Список разрешенных пользователей (ID пользователей, которым можно показывать вопросы)
ALLOWED_USER_IDS = [123456789, 932335772]  # Пример: замените на реальные ID пользователей

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    
    # Проверяем, разрешено ли пользователю использовать команду /start
    if user_id not in ALLOWED_USER_IDS:
        await update.message.reply_text("У вас нет доступа к этому боту.")
        return

    # Создаем базовую клавиатуру с кнопкой "Переслать мои свежие картинки"
    keyboard = [
        [InlineKeyboardButton("Переслать мои свежие картинки", callback_data="forward_photos")]
    ]

    # Добавляем дополнительные кнопки для разрешенных пользователей
    if user_id in ALLOWED_USER_IDS:
        keyboard.append([InlineKeyboardButton("Показать вопросы", callback_data="show_questions")])

    # Создаем разметку с кнопками
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)

async def question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    
    # Проверяем, разрешено ли пользователю использовать команду /question
    if user_id not in ALLOWED_USER_IDS:
        await update.message.reply_text("У вас нет доступа к этим вопросам.")
        return

    questions = get_questions(user_id)  # Получаем вопросы через функцию из модуля question_handler
    await update.message.reply_text("\n".join(questions) if questions else "Вопросов нет.")

async def forward_photos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.callback_query.from_user.id
    chat_id = update.callback_query.message.chat.id
    fresh_photos = get_fresh_photos(user_id)  # Получаем свежие фотографии через функцию из модуля photo_handler
    
    if fresh_photos:
        for file_id in fresh_photos:
            await context.bot.send_photo(chat_id=chat_id, photo=file_id)
        await update.callback_query.message.reply_text("Свежие картинки пересланы!")
    else:
        await update.callback_query.message.reply_text("Нет новых картинок.")

async def show_questions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.callback_query.from_user.id
    
    # Проверяем, разрешено ли пользователю видеть вопросы
    if user_id not in ALLOWED_USER_IDS:
        await update.callback_query.message.reply_text("У вас нет доступа к этим вопросам.")
        return
    
    questions = get_questions(user_id)  # Получаем вопросы через функцию из модуля question_handler
    await update.callback_query.message.reply_text("\n".join(questions) if questions else "Вопросов нет.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    
    # Сохраняем вопрос (если он текстовый)
    save_question(user_id, text)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    # Получаем file_id самого высокого качества
    photo_file_id = update.message.photo[-1].file_id
    save_photo(user_id, photo_file_id)  # Сохраняем фото синхронно

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()  # отвечаем на callback запрос

    # Проверяем, на какую кнопку был клик
    if query.data == "forward_photos":
        await forward_photos(update, context)
    elif query.data == "show_questions":
        await show_questions(update, context)

def main() -> None:
    app = Application.builder().token(TOKEN).build()

    # Обработчики команд и сообщений
    app.add_handler(CommandHandler("start", start))  # Только разрешенным пользователям будет доступна эта команда
    app.add_handler(CommandHandler("question", question))  # Только разрешенным пользователям будет доступна эта команда
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))  # Обрабатываем фото
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))  # Обрабатываем текстовые сообщения

    # Обработчик callback-запросов
    app.add_handler(CallbackQueryHandler(button_callback))

    app.run_polling()

if __name__ == '__main__':
    main()
