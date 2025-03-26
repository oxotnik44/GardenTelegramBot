import datetime
import asyncio
from telegram import Update, InputMediaPhoto
from modules.storage import save_user_message, get_user_message, user_data_useful, group_buffer_useful


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

    save_user_message(user_id, item, "useful")

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
