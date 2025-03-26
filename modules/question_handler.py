# {user_id: {"photos": [(timestamp, file_id)], "questions": [{"text": str, "message_id": int}] }}
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ALLOWED_USER_IDS
from modules.storage import get_user_message, user_data


def delete_question(user_id, idx):
    if user_id in user_data and "questions" in user_data[user_id]:
        user_questions = user_data[user_id]["questions"]
        if 0 <= idx < len(user_questions):
            del user_questions[idx]  # Удаляем напрямую из списка
            print(
                f"✅ Успешно удалён вопрос [{idx}] для пользователя {user_id}")
            return True
        else:
            print(
                f"⚠️ Ошибка: Индекс {idx} вне диапазона (0 - {len(user_questions)-1}) у пользователя {user_id}")
    else:
        print(f"❌ Ошибка: Вопросы отсутствуют у пользователя {user_id}")
    return False


async def show_questions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показываем все вопросы, создаём кнопки"""
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USER_IDS:
        if update.message:
            await update.message.reply_text("У вас нет доступа к этим вопросам.")
        else:
            await update.callback_query.message.reply_text("У вас нет доступа к этим вопросам.")
        return

    # Удаляем предыдущие сообщения с вопросами (сообщения бота) последовательно
    old_messages = context.user_data.get("question_messages", [])
    for msg_id in old_messages:
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
        except Exception as e:
            print(f"Не удалось удалить сообщение {msg_id}: {e}")

    # Очистим список старых сообщений
    context.user_data["question_messages"] = []

    questions = get_user_message(user_id, "question")
    if not questions:
        msg = None
        if update.message:
            msg = await update.message.reply_text("Вопросов нет.")
        else:
            msg = await update.callback_query.message.reply_text("Вопросов нет.")
        if msg:
            context.user_data["question_messages"].append(msg.message_id)
        return

    # Отправляем сообщения с кнопками последовательно
    for question_data in questions:
        question_text = question_data.get("text", "Нет текста вопроса")
        # Это ID оригинального сообщения пользователя
        user_msg_id = question_data.get("message_id")

        # Делаем кнопки, используя именно user_msg_id в callback_data
        keyboard = [
            [
                InlineKeyboardButton(
                    "Ответить", callback_data=f"answer_{user_msg_id}"),
                InlineKeyboardButton(
                    "Позже", callback_data=f"later_{user_msg_id}"),
                InlineKeyboardButton(
                    "Удалить", callback_data=f"delete_{user_msg_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправляем сообщение бота с текстом вопроса и кнопками сразу
        if update.message:
            bot_msg = await update.message.reply_text(f"Вопрос: {question_text}", reply_markup=reply_markup)
        else:
            bot_msg = await update.callback_query.message.reply_text(f"Вопрос: {question_text}", reply_markup=reply_markup)

        # Сохраняем bot_message_id в поле вопроса
        question_data["bot_message_id"] = bot_msg.message_id

        # Запоминаем bot_message_id, чтобы удалить при следующем вызове show_questions
        context.user_data["question_messages"].append(bot_msg.message_id)


async def answer_questions(update: Update, context: ContextTypes.DEFAULT_TYPE, user_msg_id: int) -> None:
    """Нажата кнопка "Ответить". Сохраняем user_msg_id для дальнейшего handle_text"""
    user_id = update.callback_query.from_user.id
    if user_id == 932335772:
        context.user_data["current_question_msg_id"] = user_msg_id
        context.user_data["current_question_user_id"] = user_id
        await update.effective_chat.send_message("Введите ответ на вопрос:")
    else:
        await update.callback_query.message.reply_text("Только определённый пользователь может отвечать.")


async def view_later(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Нажата кнопка "Позже". Ищем вопрос по user_msg_id, скрываем сообщение бота, но не удаляем из базы."""
    user_msg_id = int(update.callback_query.data.split("_")[1])
    user_id = update.callback_query.from_user.id

    # Получаем список вопросов один раз
    questions = get_user_message(user_id, "question")

    # Быстрый поиск вопроса по message_id
    found_q = next((q for q in questions if q.get(
        "message_id") == user_msg_id), None)

    if found_q:
        question_text = found_q.get("text", "Нет текста вопроса")

        # Добавляем в "позже", избегая дублирования
        delayed = context.user_data.setdefault("delayed_questions", [])
        if user_msg_id not in delayed:
            delayed.append(user_msg_id)

        # Удаление сообщения бота (если оно ещё есть)
        bot_msg_id = found_q.get("bot_message_id")
        if bot_msg_id:
            try:
                await update.callback_query.message.delete()
                # Удаляем идентификатор из списка для последующих операций
                question_messages = context.user_data.get(
                    "question_messages", [])
                if bot_msg_id in question_messages:
                    question_messages.remove(bot_msg_id)
            except Exception as e:
                if "message to delete not found" not in str(e).lower():
                    print(f"Не удалось удалить сообщение {bot_msg_id}: {e}")

        await update.callback_query.message.reply_text(f"Хорошо, вы сможете ответить на «{question_text}» позже.")
    else:
        await update.callback_query.message.reply_text("Ошибка: не найден вопрос по указанному идентификатору.")
