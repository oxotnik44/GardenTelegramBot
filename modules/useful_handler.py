import datetime
import asyncio
from telegram import Update
from modules.storage import save_user_message, group_buffer_useful


async def process_interesting_info_message(update: Update):
    """
    Обрабатывает сообщение с тегом @интересное, сохраняет его как полезное текстовое сообщение.
    """
    # Получаем текст сообщения
    message_text = update.message.text.strip()
    # Удаляем тег @интересное из текста
    message_text = message_text.replace('@интересное', '').strip()
    # Создаем объект для сохранения
    item = {
        "text": message_text,  # Сохраняем текст без тега
        "message_id": update.message.message_id,
        "type": "text"  # Тип сообщения - текст
    }
    # Сохраняем сообщение как полезную информацию для пользователя, передавая user_id
    save_user_message(update.message.from_user.id, item, tag="useful")


async def handle_photo_useful(update, context, force_tag: bool = False):
    """
    Обрабатывает входящие фото.
    Если фото отправлено в одиночку – сохраняет сразу;
    если это часть альбома (media_group) – группирует и ждёт завершения группы.

    При групповой отправке, если force_tag равен True или хотя бы у одной картинки
    присутствует тег "@интересное", то этот тег присваивается всем фотографиям группы.
    """
    user_id = update.message.from_user.id
    photo_file_id = update.message.photo[-1].file_id
    caption = update.message.caption or ""
    media_group_id = update.message.media_group_id

    # Приводим caption к нижнему регистру и убираем лишние пробелы
    caption = caption.strip().lower()

    if media_group_id is None:
        # Одиночное фото
        tags = []
        if force_tag or ("@интересное" in caption):
            tags.append("@интересное")
        item = {"photo": photo_file_id, "tags": tags}
        save_user_message(user_id, item, tag="useful")
    else:
        key = (user_id, media_group_id)
        if key not in group_buffer_useful:
            group_buffer_useful[key] = {
                "photos": [],
                "has_interesting_info": False,
                "task": None,
                "created_at": datetime.datetime.now()
            }
        group_info = group_buffer_useful[key]
        group_info["photos"].append(photo_file_id)
        if force_tag or ("@интересное" in caption):
            group_info["has_interesting_info"] = True
        if group_info["task"] is not None:
            group_info["task"].cancel()
        group_info["task"] = context.application.create_task(
            group_flush_delayed(user_id, media_group_id, "useful")
        )


async def group_flush_delayed(user_id, media_group_id, tag):
    """
    Завершает группировку и сохраняет фотографии из альбома по завершении сбора.
    """
    # Задержка, чтобы собрать все фотографии альбома
    await asyncio.sleep(2)
    key = (user_id, media_group_id)
    group_info = group_buffer_useful.get(key)
    if group_info:
        if group_info["has_interesting_info"]:
            for photo in group_info["photos"]:
                # Формируем объект с фотографией для сохранения в полезное хранилище
                item = {"photo": photo, "tags": ["@интересное"]}
                save_user_message(user_id, item, tag="useful")
        # Удаляем группу из буфера после обработки
        del group_buffer_useful[key]
