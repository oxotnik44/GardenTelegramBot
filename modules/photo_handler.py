import datetime
import asyncio
from modules.storage import get_user_message, user_data, save_user_message, group_buffer, group_buffer_useful


async def flush_group(user_id: int, media_group_id: str, content_type: str):
    """
    Переносит данные из group_buffer в user_data для группы фото.
    Если хотя бы у одного фото был тег @Товары, то всем присваивается этот тег.
    """
    if content_type == "useful":
        key = (user_id, media_group_id)
        group_info = group_buffer_useful.get(key)
        if not group_info:
            return
        photos = group_info["photos"]
        clean_caption = group_info.get("caption", "").replace(
            "@интересная информация", "").strip()
        for file_id in photos:
            item = {
                "message_id": None,
                "date": datetime.datetime.now(),
                "text": clean_caption,
                "type": "photo",
                "file_id": file_id
            }
            save_user_message(user_id, item, "useful")
        del group_buffer_useful[key]

    elif content_type == "product":
        key = (user_id, media_group_id)
        group_info = group_buffer.get(key)
        if not group_info:
            return
        tags = ["@Товары"] if group_info.get("has_tovar") else []
        for file_id in group_info["photos"]:
            save_user_message(user_id, file_id, "product", tags)
        del group_buffer[key]

    else:
        print(f"Неизвестный тип контента: {content_type}")


async def group_flush_delayed(user_id, media_group_id, content_type, delay=2):
    """
    Ждёт заданное время, затем вызывает функцию для обработки группы фото, в зависимости от типа контента.
    Параметр content_type определяет, какую функцию вызывать:
    """
    try:
        await asyncio.sleep(delay)
        await flush_group(user_id, media_group_id, content_type)
    except asyncio.CancelledError:
        # Если задача отменена, значит поступило новое сообщение из этой же группы.
        pass


async def handle_photo(update, context):
    user_id = update.message.from_user.id
    photo_file_id = update.message.photo[-1].file_id
    caption = update.message.caption or ""
    media_group_id = update.message.media_group_id
    caption_lower = caption.strip().lower()

    # Определяем тег по caption
    tag = None
    tag_name = None

    if "@товары" in caption_lower:
        tag = "product"
        tag_name = "@Товары"
    elif "@интересная информация" in caption_lower:
        tag = "useful"
        tag_name = "@Интересная информация"

    print(f"Определённый тег: {tag}")

    # Если тег не определён, прекращаем обработку
    if tag is None:
        print(f"⚠️ Неизвестный тег для пользователя {user_id}: {caption}")
        return

    # Обработка одиночного фото
    if media_group_id is None:
        if tag == "product":
            save_user_message(user_id, photo_file_id, "product", [tag_name])
        elif tag == "useful":
            clean_caption = caption.replace(tag_name, "").strip()
            item = {
                "message_id": update.message.message_id,
                "date": update.message.date,
                "text": clean_caption,
                "type": "photo",
                "file_id": photo_file_id
            }
            save_user_message(user_id, item, "useful")
    else:
        # Обработка альбома
        # Выбираем соответствующий буфер по типу тега
        group_buffer_reference = group_buffer if tag == "product" else group_buffer_useful
        key = (user_id, media_group_id)

        if key not in group_buffer_reference:
            # Если это первое фото альбома, требуем, чтобы тег был определён
            group_buffer_reference[key] = {
                "photos": [],
                "tag": tag,
                "tag_name": tag_name,
                "created_at": datetime.datetime.now(),
                "caption": caption,  # сохраняем оригинальный caption
                "has_tovar": tag == "product",
                "has_useful": tag == "useful",
                "task": None
            }

        group_info = group_buffer_reference[key]
        group_info["photos"].append(photo_file_id)

        # Гарантируем, что для группы установлен тег с первого фото
        tag = group_info["tag"]
        tag_name = group_info["tag_name"]

        if tag == "product":
            save_user_message(user_id, photo_file_id, "product", [tag_name])
        elif tag == "useful":
            clean_caption = group_info["caption"].replace(tag_name, "").strip()
            item = {
                "message_id": update.message.message_id,
                "date": update.message.date,
                "text": clean_caption,
                "type": "photo",
                "file_id": photo_file_id
            }
            save_user_message(user_id, item, "useful")
        else:
            print(
                f"⚠️ Ошибка! Неизвестный тип контента в группе {media_group_id}")

        # Отменяем предыдущую задачу для группы и создаём новую
        if group_info["task"] is not None:
            group_info["task"].cancel()

        group_info["task"] = context.application.create_task(
            group_flush_delayed(user_id, media_group_id, tag)
        )
        print(f"Фото добавлено в группу {media_group_id}, тег: {tag}")
