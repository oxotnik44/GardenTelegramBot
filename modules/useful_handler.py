import datetime
import asyncio
from telegram import Update, InputMediaPhoto
from telegram.ext import ContextTypes

# Единое хранилище полезной информации для пользователей
user_data_useful = {}

# Буфер для групповых фото (медиа-альбомы)
group_buffer_useful = {}


def save_useful_item(user_id, item):
    """Сохраняет полезный элемент (текст/фото/видео) для пользователя."""
    if user_id not in user_data_useful:
        user_data_useful[user_id] = {"items": []}
    user_data_useful[user_id]["items"].append(item)


def get_useful_items(user_id):
    """Возвращает список всех полезных элементов только для запрашивающего пользователя."""
    return user_data_useful.get(user_id, {}).get("items", [])


async def useful(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выводит сохранённые полезные сообщения только для запрашивающего пользователя."""
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    items = get_useful_items(user_id)

    if not items:
        await update.message.reply_text("Нет сохранённых сообщений с тегом @Интересная информация.")
        return

    # Разделяем текстовые сообщения и фото
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


async def process_interesting_info_message(update: Update) -> bool:
    """
    Обрабатывает входящее сообщение с тегом @Интересная информация.
    Удаляет этот тег, но сохраняет остальной текст, если он есть.
    Если после удаления тега текст пуст, сообщение не сохраняется.
    """
    user_id = update.message.from_user.id
    text = update.message.caption if update.message.caption else update.message.text
    if not text:
        return False

    # Удаляем тег "@Интересная информация"
    clean_text = text.replace("@Интересная информация", "", 1).strip()

    # Если после удаления тега ничего не осталось, не сохраняем
    if not clean_text:
        return False

    item = {
        "message_id": update.message.message_id,
        "date": update.message.date,
        "text": clean_text,
        "type": "text"
    }

    if update.message.photo:
        item["type"] = "photo"
        item["file_id"] = update.message.photo[-1].file_id
    elif update.message.video:
        item["type"] = "video"
        item["file_id"] = update.message.video.file_id

    save_useful_item(user_id, item)

    if item["type"] == "photo":
        await update.message.reply_photo(
            photo=item["file_id"],
            caption="Сообщение сохранено как полезная информация."
        )
    elif item["type"] == "video":
        await update.message.reply_video(
            video=item["file_id"],
            caption="Сообщение сохранено как полезная информация."
        )
    else:
        await update.message.reply_text("Сообщение сохранено как полезная информация.")

    return True

# Функции для групповой обработки фото (альбомы)


async def flush_group_useful(user_id: int, media_group_id: str):
    """
    Переносит данные из group_buffer_useful в основное хранилище user_data_useful для группы фото.
    Если хотя бы у одного фото в группе присутствует тег, общий текст берётся из caption группы.
    """
    key = (user_id, media_group_id)
    group_info = group_buffer_useful.get(key)
    if not group_info:
        return

    photos = group_info["photos"]
    # Если в группе присутствует полезный тег, очищаем caption от него
    clean_caption = group_info.get("caption", "").replace(
        "@интересная информация", "").strip()

    for file_id in photos:
        item = {
            "message_id": None,  # Можно добавить идентификатор группы, если требуется
            "date": datetime.datetime.now(),
            "text": clean_caption,
            "type": "photo",
            "file_id": file_id
        }
        save_useful_item(user_id, item)

    del group_buffer_useful[key]


async def group_flush_delayed_useful(user_id, media_group_id, delay=2):
    """
    Ждет заданное время и вызывает flush_group_useful для обработки группы фото.
    """
    try:
        await asyncio.sleep(delay)
        await flush_group_useful(user_id, media_group_id)
    except asyncio.CancelledError:
        pass


async def handle_photo_useful(update: Update, context):
    """
    Обрабатывает входящие фото, содержащие тег @Интересная информация.
    Если фото отправлено одиночным сообщением, оно сохраняется сразу.
    Если фото входит в альбом (media_group), они группируются с задержкой.
    """
    user_id = update.message.from_user.id
    photo_file_id = update.message.photo[-1].file_id
    caption = update.message.caption or ""
    media_group_id = update.message.media_group_id
    caption_lower = caption.strip().lower()

    # Если одиночное фото
    if media_group_id is None:
        clean_caption = caption.replace("@интересная информация", "").strip()
        item = {
            "message_id": update.message.message_id,
            "date": update.message.date,
            "text": clean_caption,
            "type": "photo",
            "file_id": photo_file_id
        }
        save_useful_item(user_id, item)
    else:
        # Если фото отправлено в группе (альбоме)
        key = (user_id, media_group_id)
        if key not in group_buffer_useful:
            group_buffer_useful[key] = {
                "photos": [],
                "has_useful": False,
                "task": None,
                "created_at": datetime.datetime.now(),
                "caption": caption  # сохраняем общий текст альбома
            }
        group_info = group_buffer_useful[key]
        group_info["photos"].append(photo_file_id)
        if "@интересная информация" in caption_lower:
            group_info["has_useful"] = True
            group_info["caption"] = caption  # сохраняем исходную подпись
        if group_info["task"] is not None:
            group_info["task"].cancel()
        group_info["task"] = context.application.create_task(
            group_flush_delayed_useful(user_id, media_group_id)
        )
