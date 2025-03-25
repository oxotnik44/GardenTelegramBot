
from telegram import InputMediaPhoto

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from modules.photo_handler import get_tagged_fresh_photos
from modules.question_handler import save_question, get_questions, delete_question, show_questions, answer_questions, view_later
from config import ALLOWED_USER_IDS
from modules.useful_handler import get_useful_items, process_interesting_info_message


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
    # Отправляем только в чат, откуда пришёл запрос (личный чат пользователя)
    chat_id = update.message.chat.id
    tagged_photos = get_tagged_fresh_photos(user_id, tag="@Товары")

    if tagged_photos:
        # Группируем фото по 10 штук (максимум для media_group)
        batch_size = 10
        for i in range(0, len(tagged_photos), batch_size):
            media_group = []
            for file_id in tagged_photos[i:i+batch_size]:
                media_group.append(InputMediaPhoto(media=file_id))
            await context.bot.send_media_group(chat_id=chat_id, media=media_group)
    else:
        await update.message.reply_text("Нет новых картинок с тегом @Товары.")


async def useful(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    items = get_useful_items(user_id)

    if not items:
        await update.message.reply_text("Нет сохранённых сообщений с тегом @Интересная информация.")
        return

    # Отделяем текстовые сообщения и фото
    text_messages = [item["text"] for item in items if item["type"] == "text"]
    photo_ids = [item["file_id"] for item in items if item["type"] == "photo"]

    if text_messages:
        text_response = "\n\n".join(text_messages)
        await context.bot.send_message(chat_id=chat_id, text=text_response)

    if photo_ids:
        batch_size = 10  # максимум для media_group
        for i in range(0, len(photo_ids), batch_size):
            media_group = [InputMediaPhoto(media=file_id)
                           for file_id in photo_ids[i:i+batch_size]]
            await context.bot.send_media_group(chat_id=chat_id, media=media_group)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Пользователь вводит ответ. Ответ будет reply на ОРИГИНАЛЬНОЕ сообщение user_msg_id.
    Если сообщение содержит тег @Интересная информация, обработка происходит в отдельной функции.
    """
# Если в тексте присутствует тег, сохраняем сообщение как полезное и выходим
    if "@интересная информация" in update.message.text.lower():
        await process_interesting_info_message(update)
        return

    # Стандартная логика: обработка ответа на вопрос или сохранение нового вопроса.
    user_data_ctx = context.user_data
    user_msg_id = user_data_ctx.pop(
        "current_question_msg_id", None)  # ID оригинального сообщения
    question_owner_id = user_data_ctx.get(
        "current_question_user_id", update.message.from_user.id)

    if user_msg_id:
        questions = get_questions(question_owner_id)
        for idx, q in enumerate(questions):
            if q.get("message_id") == user_msg_id:
                # Отправляем ответ в виде reply на оригинальное сообщение пользователя
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=update.message.text.strip(),
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
                # Удаляем bot_msg_id из question_messages, если он там присутствует
                if bot_msg_id and "question_messages" in user_data_ctx:
                    if bot_msg_id in user_data_ctx["question_messages"]:
                        user_data_ctx["question_messages"].remove(bot_msg_id)
                return
        await update.message.reply_text("Ошибка: не найдено оригинальное сообщение с вопросом.")
    else:
        # Если пользователь пишет текст без нажатия "Ответить", сохраняем как новый вопрос
        save_question(update.message.from_user.id,
                      update.message.text.strip(), update.message.message_id)


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
