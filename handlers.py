from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from modules.photo_handler import save_photo, get_fresh_photos
from modules.question_handler import save_question, get_questions, delete_question
from config import ALLOWED_USER_IDS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id not in ALLOWED_USER_IDS:
        return await update.message.reply_text("У вас нет доступа к этому действию.")

    keyboard = [
        [InlineKeyboardButton("Показать вопросы",
                              callback_data="show_questions")]
    ]
    await update.message.reply_text("Выберите действие:", reply_markup=InlineKeyboardMarkup(keyboard))


async def products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    fresh_photos = get_fresh_photos(user_id)
    if fresh_photos:
        for file_id in fresh_photos:
            await context.bot.send_photo(chat_id=chat_id, photo=file_id)
    else:
        await update.message.reply_text("Нет новых картинок.")


async def question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /question — сразу показываем список вопросов"""
    user_id = update.message.from_user.id
    if user_id not in ALLOWED_USER_IDS:
        await update.message.reply_text("У вас нет доступа к этим вопросам.")
        return
    await show_questions(update, context)


async def show_questions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показываем все вопросы, создаём кнопки. 
       Важно: для кнопок используем ID ОРИГИНАЛЬНОГО сообщения пользователя."""
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USER_IDS:
        if update.message:
            await update.message.reply_text("У вас нет доступа к этим вопросам.")
        else:
            await update.callback_query.message.reply_text("У вас нет доступа к этим вопросам.")
        return

    # Удаляем предыдущие сообщения с вопросами (сообщения бота)
    old_messages = context.user_data.get("question_messages", [])
    for msg_id in old_messages:
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
        except Exception:
            pass
    context.user_data["question_messages"] = []

    questions = get_questions(user_id)
    if not questions:
        msg = None
        if update.message:
            msg = await update.message.reply_text("Вопросов нет.")
        else:
            msg = await update.callback_query.message.reply_text("Вопросов нет.")
        if msg:
            context.user_data["question_messages"].append(msg.message_id)
        return

    for question_data in questions:
        question_text = question_data.get("text", "Нет текста вопроса")
        # Это ID оригинального сообщения пользователя
        user_msg_id = question_data.get("message_id")

        # Отправляем сообщение бота с текстом вопроса
        if update.message:
            bot_msg = await update.message.reply_text(f"Вопрос: {question_text}")
        else:
            bot_msg = await update.callback_query.message.reply_text(f"Вопрос: {question_text}")

        # Сохраняем bot_message_id в отдельном поле (для удаления сообщения бота при "Удалить" и т.п.)
        question_data["bot_message_id"] = bot_msg.message_id

        # Делаем кнопки, используя ИМЕННО user_msg_id в callback_data
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

        # Редактируем сообщение бота, добавляя кнопки
        await context.bot.edit_message_reply_markup(
            chat_id=bot_msg.chat.id,
            message_id=bot_msg.message_id,
            reply_markup=reply_markup
        )

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
    questions = get_questions(user_id)

    found_q = None
    for q in questions:
        if q.get("message_id") == user_msg_id:
            found_q = q
            break

    if found_q:
        question_text = found_q.get("text", "Нет текста вопроса")
        delayed = context.user_data.get("delayed_questions", [])
        if user_msg_id not in delayed:
            delayed.append(user_msg_id)
            context.user_data["delayed_questions"] = delayed

        # Пробуем удалить сообщение бота
        bot_msg_id = found_q.get("bot_message_id")
        if bot_msg_id:
            try:
                await update.callback_query.message.delete()
            except Exception:
                pass

        await update.callback_query.message.reply_text(f"Хорошо, вы сможете ответить на «{question_text}» позже.")
    else:
        await update.callback_query.message.reply_text("Ошибка: не найден вопрос по указанному идентификатору.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Пользователь вводит ответ. Ответ будет reply на ОРИГИНАЛЬНОЕ сообщение user_msg_id."""
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    user_data_ctx = context.user_data
    user_msg_id = user_data_ctx.pop(
        "current_question_msg_id", None)  # ID сообщения пользователя
    question_owner_id = user_data_ctx.get("current_question_user_id", user_id)

    if user_msg_id:
        questions = get_questions(question_owner_id)
        for idx, q in enumerate(questions):
            if q.get("message_id") == user_msg_id:
                # Делаем reply именно на оригинальное сообщение пользователя
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=text,
                    reply_to_message_id=user_msg_id
                )

                # Удаляем сообщение бота с вопросом и кнопками
                bot_msg_id = q.get("bot_message_id")
                if bot_msg_id:
                    try:
                        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=bot_msg_id)
                    except Exception:
                        await update.message.reply_text("Ответ отправлен, но не удалось удалить сообщение с вопросом.")

                # Удаляем вопрос из базы
                delete_question(question_owner_id, idx)

                # Удаляем bot_msg_id из question_messages
                if bot_msg_id and "question_messages" in user_data_ctx:
                    if bot_msg_id in user_data_ctx["question_messages"]:
                        user_data_ctx["question_messages"].remove(bot_msg_id)
                return
        await update.message.reply_text("Ошибка: не найдено оригинальное сообщение с вопросом.")
    else:
        # Если пользователь пишет текст без нажатия "Ответить", сохраняем как новый вопрос
        save_question(user_id, text, update.message.message_id)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    photo_file_id = update.message.photo[-1].file_id
    save_photo(user_id, photo_file_id)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Общий обработчик кнопок"""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "show_questions":
        await show_questions(update, context)

    elif data.startswith("answer_"):
        user_msg_id = int(data.split("_")[1])
        await answer_questions(update, context, user_msg_id)

    elif data.startswith("later_"):
        await view_later(update, context)

    elif data.startswith("delete_"):
        user_msg_id = int(data.split("_")[1])
        user_id = query.from_user.id
        questions = get_questions(user_id)
        found_index = None
        found_question = None

        for i, q in enumerate(questions):
            if q.get("message_id") == user_msg_id:
                found_index = i
                found_question = q
                break

        if found_index is not None and delete_question(user_id, found_index):
            # Удаляем сообщение бота из чата
            bot_msg_id = found_question.get("bot_message_id")
            if bot_msg_id:
                try:
                    await query.message.delete()
                except Exception:
                    await query.message.reply_text("Не удалось удалить сообщение, но вопрос удалён.")

            # Удаляем bot_msg_id из question_messages
            if bot_msg_id and "question_messages" in context.user_data:
                if bot_msg_id in context.user_data["question_messages"]:
                    context.user_data["question_messages"].remove(bot_msg_id)
        else:
            await query.message.reply_text("Не удалось удалить вопрос: не найден вопрос с данным идентификатором.")
