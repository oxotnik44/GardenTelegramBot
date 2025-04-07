# {user_id: {"photos": [(timestamp, file_id)], "questions": [{"text": str, "message_id": int}] }}
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import telegram
from telegram.ext import ContextTypes
from config import ALLOWED_USER_IDS
from modules.storage import get_user_message, load_storage_data, save_storage_data, user_data, delete_record_by_storage


async def delete_question(context, uuid_to_delete):
    """
    Удаляет вопрос из глобального хранилища по uuid.
    Также удаляет сообщение из чата, если оно существует.
    """
    from modules import storage

    # Загружаем данные из хранилища
    storage.load_storage_data()

    # Удаляем вопрос из хранилища
    storage.delete_record_by_storage("question", uuid_to_delete)

    # Сохраняем обновленные данные
    storage.save_storage_data()
    storage.load_storage_data()

    return True


async def show_questions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показываем все вопросы, создаём кнопки только для разрешённых пользователей"""
    user_id = update.message.from_user.id

    # Проверяем, что пользователь есть в списке разрешённых
    if user_id not in ALLOWED_USER_IDS:
        return  # Если пользователь не в списке ALLOWED_USER_IDS, ничего не делаем

    # Удаляем предыдущие сообщения с вопросами (сообщения бота) последовательно
    old_messages = context.user_data.get("question_messages", [])
    for msg_id in old_messages:
        try:
            # Отправляем в личный чат
            await context.bot.delete_message(chat_id=user_id, message_id=msg_id)
        except Exception as e:
            print(f"Не удалось удалить сообщение {msg_id}: {e}")

    # Очистим список старых сообщений
    context.user_data["question_messages"] = []

    questions = get_user_message("question")
    if not questions:
        msg = None
        # Проверяем, где пришел запрос (от message или callback)
        if update.message:
            # Ответ в личку
            msg = await context.bot.send_message(user_id, "Вопросов нет.")
        else:
            # Ответ в личку
            msg = await context.bot.send_message(user_id, "Вопросов нет.")
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
                    "Ответить", callback_data=f"answer_{question_data['uuid']}|{question_data['message_id']}"),
                InlineKeyboardButton(
                    "Позже", callback_data=f"later_{question_data['uuid']}|{question_data['message_id']}"),
                InlineKeyboardButton(
                    "Удалить", callback_data=f"delete_{question_data['uuid']}|{question_data['message_id']}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        bot_msg = await context.bot.send_message(user_id, f"Вопрос: {question_text}", reply_markup=reply_markup)

        # Сохраняем bot_message_id в поле вопроса
        question_data["bot_message_id"] = bot_msg.message_id

        # Запоминаем bot_message_id, чтобы удалить при следующем вызове show_questions
        context.user_data["question_messages"].append(bot_msg.message_id)


async def answer_questions(update: Update, context: ContextTypes.DEFAULT_TYPE, user_msg_id: int) -> None:
    """Нажата кнопка "Ответить". Сохраняем user_msg_id для дальнейшего handle_text"""
    user_id = update.callback_query.from_user.id

    if user_id not in ALLOWED_USER_IDS:
        return  # Если пользователя нет в списке ALLOWED_USER_IDS, ничего не отправляем

    context.user_data["current_question_msg_id"] = user_msg_id
    context.user_data["current_question_user_id"] = user_id

    # Отправляем сообщение с просьбой ввести ответ и сохраняем его message_id
    prompt_message = await update.effective_chat.send_message("Введите ответ на вопрос:")
    # ✅ Сохраняем ID сообщения
    context.user_data["prompt_message_id"] = prompt_message.message_id

    # Сохраняем bot_msg_id (предположительно, это id сообщения, связанного с вопросом)
    # Если у вас есть bot_msg_id из предыдущих данных
    bot_msg_id = context.user_data.get("current_question_msg_id")
    if bot_msg_id:
        # Сохраняем bot_msg_id в context.user_data
        context.user_data["current_bot_msg_id"] = bot_msg_id
        print(f"Сохранён bot_msg_id: {bot_msg_id}")


async def view_later(update: Update, context: ContextTypes.DEFAULT_TYPE, uuid_to_find: str, user_msg_id: int) -> None:
    """Нажата кнопка "Позже". Ищем вопрос по UUID, скрываем сообщение бота, но не удаляем из базы."""
    user_id = update.callback_query.from_user.id

    # Проверка, что пользователь в списке разрешённых
    if user_id not in ALLOWED_USER_IDS:
        return  # Если пользователя нет в списке ALLOWED_USER_IDS, ничего не отправляем

    # Для отладки
    print(f"Ищем вопрос с uuid: {uuid_to_find} и message_id: {user_msg_id}")

    # Получаем список вопросов
    questions = get_user_message("question")

    # Быстрый поиск вопроса по UUID
    found_q = next(
        (q for q in questions if q.get("uuid") == uuid_to_find), None)

    if found_q:
        question_text = found_q.get("text", "Нет текста вопроса")
        user_msg_id_from_storage = found_q.get("message_id")
        print(found_q)
        # Проверяем, что message_id совпадает
        if user_msg_id_from_storage != user_msg_id:
            print(
                f"Ошибка: message_id не совпадает. Ожидалось {user_msg_id_from_storage}, но получено {user_msg_id}")
            await update.effective_chat.send_message("Ошибка: message_id не совпадает.")
            return

        # Добавляем в "позже", избегая дублирования
        delayed = context.user_data.setdefault("delayed_questions", [])
        if user_msg_id not in delayed:
            delayed.append(user_msg_id)

        # Удаление сообщения бота (если оно ещё есть)
        bot_msg_id = found_q.get("message_id")
        print(bot_msg_id)
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

        await update.effective_chat.send_message(f"Хорошо, вы сможете ответить на «{question_text}» позже.")
    else:
        await update.effective_chat.send_message("Ошибка: не найден вопрос по указанному идентификатору.")
