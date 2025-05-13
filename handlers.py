from telegram import InputMediaPhoto, Update
import telegram
from telegram.ext import ContextTypes
from modules.photo_handler import process_interesting_info_message_product
from modules.question_handler import delete_question, show_questions, answer_questions, view_later
from config import ALLOWED_USER_IDS
from modules.useful_handler import process_interesting_info_message
from modules.storage import get_user_message, save_user_message
from telegram.error import TimedOut
import asyncio
from datetime import datetime


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


async def send_items_sorted(bot, chat_id, items):
    items.sort(key=lambda x: x.get("saved_date") or datetime.min)
    i, n = 0, len(items)
    while i < n:
        it = items[i]
        # Фото с подписей
        if it["type"] == "photo" and "caption" in it:
            await bot.send_photo(chat_id=chat_id, photo=it["media"], caption=it["caption"])
            i += 1
        # Группа фото без подписей
        elif it["type"] == "photo":
            grp = []
            while i < n and items[i]["type"] == "photo" and "caption" not in items[i]:
                grp.append(items[i]["media"])
                i += 1
            await send_media_group(bot, chat_id, grp)
        # Видео
        elif it["type"] == "video":
            if "caption" in it:
                await bot.send_video(chat_id=chat_id, video=it["media"], caption=it["caption"])
            else:
                await bot.send_video(chat_id=chat_id, video=it["media"])
            i += 1
        # Текст
        else:
            await bot.send_message(chat_id=chat_id, text=it["media"])
            i += 1

# Отправка медиа группы


async def send_media_group(bot, chat_id, files, batch_size=10, delay=2):
    for j in range(0, len(files), batch_size):
        group = [InputMediaPhoto(media=f) for f in files[j:j+batch_size]]
        try:
            await bot.send_media_group(chat_id, group)
        except TimedOut:
            await asyncio.sleep(1)
            await bot.send_media_group(chat_id, group)
        if delay:
            await asyncio.sleep(delay)


async def products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except:
        pass
    user_id = update.effective_user.id
    items = get_user_message("product")
    if items:
        await send_items_sorted(context.bot, user_id, items)
    else:
        await context.bot.send_message(chat_id=user_id, text="Нет новых товаров.")

# Хендлер /useful отправляет в ЛС пользователю


async def useful(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except:
        pass
    user_id = update.effective_user.id
    raw = get_user_message("useful")
    items = []
    # Фото
    for p in raw.get("useful_photo", []):
        media = p["photo"] if isinstance(p, dict) else p
        date = p.get("saved_date") if isinstance(p, dict) else None
        entry = {"type": "photo", "media": media, "saved_date": date}
        if isinstance(p, dict) and p.get("caption"):
            entry["caption"] = p.get("caption")
        items.append(entry)
    # Видео
    for v in raw.get("useful_video", []):
        media = v["video"] if isinstance(v, dict) else v
        date = v.get("saved_date") if isinstance(v, dict) else None
        entry = {"type": "video", "media": media, "saved_date": date}
        if isinstance(v, dict) and v.get("caption"):
            entry["caption"] = v.get("caption")
        items.append(entry)
    # Тексты
    for t in raw.get("useful_text", []):
        text = t.get("text") if isinstance(t, dict) else t
        date = t.get("saved_date") if isinstance(t, dict) else None
        cleaned = text.replace("@Интересное", "").strip()
        if cleaned:
            items.append(
                {"type": "text", "media": cleaned, "saved_date": date})
    if not items:
        await context.bot.send_message(chat_id=user_id, text="Нет сохранённых @Интересное.")
        return
    await send_items_sorted(context.bot, user_id, items)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if "@интересное" in update.message.text.lower():
        await process_interesting_info_message(update)
        return
    if "@товары" in update.message.text.lower():
        await process_interesting_info_message_product(update)
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
                original_chat_id = q.get("chat_id", "@tany3201chat")
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
