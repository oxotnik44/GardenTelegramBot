from telegram import InputMediaPhoto, Update
import telegram
from telegram.ext import ContextTypes
from modules.question_handler import delete_question, show_questions, answer_questions, view_later
from config import ALLOWED_USER_IDS
from modules.useful_handler import process_interesting_info_message
from modules.storage import get_user_message, save_user_message
from telegram.error import TimedOut
import asyncio


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        user_id = update.message.from_user.id

        try:
            await update.message.delete()
        except Exception:
            pass

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="Добро пожаловать!"
            )
        except telegram.error.Forbidden:
            print(
                f"Ошибка: бот не может начать чат с пользователем {user_id}.")
        except Exception as e:
            print(f"Ошибка при отправке сообщения: {e}")


async def question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /question — сразу показываем список вопросов"""
    try:
        await update.message.delete()
    except Exception:
        pass

    user_id = update.message.from_user.id
    if user_id not in ALLOWED_USER_IDS:
        # Отправляем сообщение в личный чат с ботом
        await context.bot.send_message(chat_id=user_id, text="У вас нет доступа к этим вопросам.")
        return

    # Получаем глобальные вопросы (без привязки к user_id)
    await show_questions(update, context)


async def send_media_group(bot, chat_id, file_ids, batch_size=10, delay=2):
    """
    Отправляет фото группами (альбомами) по batch_size элементов.
    После отправки каждой группы ждёт delay секунд.
    """
    for i in range(0, len(file_ids), batch_size):
        # Формируем группу из batch_size фото
        media_group = [InputMediaPhoto(media=file_id)
                       for file_id in file_ids[i:i+batch_size]]
        try:
            await bot.send_media_group(chat_id=chat_id, media=media_group)
        except TimedOut:
            print("Запрос превысил время ожидания. Повторная попытка отправки группы.")
            # Небольшая задержка перед повторной попыткой
            await asyncio.sleep(1)
            await bot.send_media_group(chat_id=chat_id, media=media_group)

        # После отправки каждой группы ждем указанное время
        await asyncio.sleep(delay)


async def products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id  # Личный чат с ботом
    try:
        await update.message.delete()
    except Exception:
        pass

    # Получаем фото с тегом @товары. Если записи отсутствуют, возвращаем пустой список.
    tagged_photos = get_user_message("product")
    if tagged_photos:
        # Извлекаем только идентификаторы фото
        file_ids = [p["photo"] for p in tagged_photos]
        # Отправляем фото группами по 10 изображений (альбомами)
        await send_media_group(context.bot, user_id, file_ids)
    else:
        await context.bot.send_message(
            chat_id=user_id,
            text="Нет новых картинок с тегом @товары."
        )


async def useful(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду /useful для вывода сохранённых сообщений с тегом @Интересное.
    Данные берутся из хранилища с ключами "useful_photo" и "useful_text".
    """
    user_id = update.message.from_user.id  # Личный чат с ботом

    # Удаляем сообщение с командой, если у бота есть соответствующие права
    try:
        await update.message.delete()
    except Exception:
        pass

    useful_data = get_user_message("useful")

    if not useful_data or (not useful_data.get("useful_text") and not useful_data.get("useful_photo")):
        # Отправляем сообщение в личку
        await context.bot.send_message(chat_id=user_id, text="Нет сохранённых сообщений с тегом @Интересное.")
        return

    # Обработка текстовых сообщений
    text_messages = useful_data.get("useful_text", [])
    if text_messages:
        for item in text_messages:
            text = item.get("text", "") if isinstance(item, dict) else item
            cleaned_text = text.replace("@Интересное", "").strip()
            if cleaned_text:
                await context.bot.send_message(chat_id=user_id, text=cleaned_text)

    # Обработка фото с разбиением на альбомы
    photo_items = useful_data.get("useful_photo", [])
    photo_ids = []

    for item in photo_items:
        if isinstance(item, dict) and "photo" in item:
            photo_ids.append(item["photo"])
        elif isinstance(item, str):
            photo_ids.append(item)

    if photo_ids:
        await send_media_group(context.bot, user_id, photo_ids)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if "@интересное" in update.message.text.lower():
        await process_interesting_info_message(update)
        return

    user_data_ctx = context.user_data
    user_msg_id = user_data_ctx.pop("current_question_msg_id", None)
    prompt_msg_id = user_data_ctx.pop("prompt_message_id", None)
    message_to_delete = user_data_ctx.pop("message_to_delete", None)

    if user_msg_id:
        questions = get_user_message("question")
        for idx, q in enumerate(questions):
            if q.get("message_id") == user_msg_id:
                # Получаем данные о текущем вопросе
                original_chat_id = q.get("chat_id", -1002581494586)
                question_text = q.get("text", "Нет текста вопроса")
                question_uuid = q.get("uuid")
                try:
                    # Отправляем ответ на вопрос
                    await context.bot.send_message(
                        chat_id=original_chat_id,
                        text=update.message.text.strip(),
                        reply_to_message_id=q.get("message_id")
                    )
                except Exception:
                    # Если возникла ошибка, отправляем ответ как текст
                    answer_text = update.message.text.strip()
                    message_text = f"Вопрос: {question_text}\n\nОтвет: {answer_text}"
                    await context.bot.send_message(
                        chat_id=original_chat_id,
                        text=message_text
                    )

                try:
                    # Удаляем сообщение с ответом
                    await update.message.delete()
                except Exception:
                    pass

                # Удаляем сообщение с prompt_message_id

                if prompt_msg_id:
                    try:
                        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=prompt_msg_id)
                        print(
                            f"Удалено сообщение с prompt_message_id: {prompt_msg_id}")
                    except Exception:
                        await update.message.reply_text("Ответ отправлен, но не удалось удалить сообщение с вопросом.")
                # Удаляем вопрос из хранилища
                await message_to_delete.delete()

                if question_uuid:
                    await delete_question(context, question_uuid)
                else:
                    print("❌ Ошибка: у вопроса отсутствует uuid")

                return

        await update.message.reply_text("Ошибка: не найдено оригинальное сообщение с вопросом.")
    else:
        # Сохраняем новый вопрос в хранилище
        save_user_message(
            update.message.from_user.id,
            {
                "text": update.message.text.strip(),
                "message_id": update.message.message_id,
                "chat_id": update.message.chat.id
            },
            tag="question"
        )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Общий обработчик кнопок."""
    query = update.callback_query
    await query.answer()
    data = query.data
    message_to_delete = query.message
    if data == "show_questions":
        await show_questions(update, context)
    elif data.startswith("answer_"):
        # Разделяем uuid и message_id
        uuid_to_find, user_msg_id = data.split("_", 1)[1].split("|")
        user_msg_id = int(user_msg_id)  # Преобразуем user_msg_id в int
        # Для отладки
        await answer_questions(update, context, user_msg_id, message_to_delete)

    elif data.startswith("later_"):
        # Разделяем uuid и message_id
        uuid_to_find, user_msg_id = data.split("_", 1)[1].split("|")
        user_msg_id = int(user_msg_id)  # Преобразуем user_msg_id в int
        await view_later(update, context, uuid_to_find, user_msg_id)
    elif data.startswith("delete_"):
        # Разделяем uuid и message_id
        uuid_to_find, user_msg_id = data.split("_", 1)[1].split("|")
        user_msg_id = int(user_msg_id)  # Преобразуем user_msg_id в int
        # Для отладки
        await delete_question(context, uuid_to_find)
        await query.message.delete()
