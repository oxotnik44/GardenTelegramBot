import datetime
import asyncio
from modules.storage import save_user_message, group_buffer


async def handle_photo(update, context, force_tag: bool = False):
    """
    Обрабатывает входящие фото.
    Если фото отправлено в одиночку – сохраняет сразу;
    если это часть альбома (media_group) – группирует и ждёт завершения группы.
    При групповой отправке, если force_tag равен True или хотя бы у одной картинки
    присутствует тег "@товары", то этот тег присваивается всем фотографиям группы.
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
        # Если force_tag установлен, или если в подписи найден тег
        if force_tag or ("@товары" in caption):
            tags.append("@товары")
        item = {"photo": photo_file_id, "tags": tags}
        save_user_message(user_id, item, "product")
    else:
        key = (user_id, media_group_id)
        if key not in group_buffer:
            group_buffer[key] = {
                "photos": [],
                "has_product": False,
                "task": None,
                "created_at": datetime.datetime.now()
            }
        group_info = group_buffer[key]
        group_info["photos"].append(photo_file_id)
        # Если force_tag установлен, либо в подписи найден тег, помечаем группу как содержащую товар
        if force_tag or ("@товары" in caption):
            group_info["has_product"] = True
        if group_info["task"] is not None:
            group_info["task"].cancel()
        group_info["task"] = context.application.create_task(
            group_flush_delayed(user_id, media_group_id, "product")
        )


async def group_flush_delayed(user_id, media_group_id, tag):
    """
    Завершает группировку и сохраняет фотографии из альбома по завершении сбора.
    """
    # Задержка, чтобы собрать все фотографии альбома
    await asyncio.sleep(2)
    key = (user_id, media_group_id)
    group_info = group_buffer.get(key)
    if group_info:
        if group_info["has_product"]:
            for photo in group_info["photos"]:
                # Формируем объект с фотографией для сохранения в полезное хранилище
                item = {"photo": photo, "tags": ["@товары"]}
                save_user_message(user_id, item, "product")

        # Удаляем группу из буфера после обработки, если ключ существует
        if key in group_buffer:
            del group_buffer[key]
