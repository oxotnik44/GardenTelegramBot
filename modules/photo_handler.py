# modules/photo_handler.py

import datetime
import asyncio

# Хранение данных пользователей: { user_id: {"photos": [(time, file_id, [tags])], ...} }
user_data = {}

# Буфер для групп фото:
# group_buffer: {
#   (user_id, media_group_id): {
#       "photos": [file_id1, file_id2, ...],
#       "has_tovar": bool,
#       "task": ссылка на asyncio.Task,
#       "created_at": datetime
#   },
#   ...
# }
group_buffer = {}


def save_photo(user_id, file_id, tags=None):
    """Сохраняет фото пользователя с дополнительными тэгами."""
    if tags is None:
        tags = []
    user_data.setdefault(user_id, {"photos": [], "questions": []})["photos"].append(
        (datetime.datetime.now(), file_id, tags)
    )


def get_tagged_fresh_photos(user_id, tag="@Товары"):
    """Возвращает фото, загруженные за последние 45 дней и содержащие указанный тэг."""
    now = datetime.datetime.now()
    photos = user_data.get(user_id, {}).get("photos", [])
    return [
        file_id
        for (time, file_id, tags) in photos
        if (now - time) <= datetime.timedelta(days=45) and tag in tags
    ]


async def flush_group(user_id: int, media_group_id: str):
    """
    Переносит данные из group_buffer в user_data для группы фото.
    Если хотя бы у одного фото был тег @Товары, то всем присваивается этот тег.
    """
    key = (user_id, media_group_id)
    group_info = group_buffer.get(key)
    if not group_info:
        return

    photos = group_info["photos"]
    has_tovar = group_info["has_tovar"]
    tags = ["@Товары"] if has_tovar else []

    for file_id in photos:
        save_photo(user_id, file_id, tags=tags)

    del group_buffer[key]


async def group_flush_delayed(user_id, media_group_id, delay=2):
    """
    Ждёт заданное время, затем вызывает flush_group для обработки группы фото.
    """
    try:
        await asyncio.sleep(delay)
        await flush_group(user_id, media_group_id)
    except asyncio.CancelledError:
        # Если задача отменена, значит поступило новое сообщение из этой же группы.
        pass


async def handle_photo(update, context):
    """
    Обрабатывает входящие фото.
    Если фото отправлено в одиночку – сохраняет сразу;
    если это часть альбома (media_group) – группирует и ждёт завершения группы.
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
        if "@товары" in caption:  # проверяем, если тег есть в caption
            tags.append("@Товары")
        save_photo(user_id, photo_file_id, tags=tags)
    else:
        key = (user_id, media_group_id)
        if key not in group_buffer:
            group_buffer[key] = {
                "photos": [],
                "has_tovar": False,
                "task": None,
                "created_at": datetime.datetime.now()
            }
        group_info = group_buffer[key]
        group_info["photos"].append(photo_file_id)
        if "@товары" in caption:  # проверяем, если тег есть в caption
            group_info["has_tovar"] = True
        if group_info["task"] is not None:
            group_info["task"].cancel()
        group_info["task"] = context.application.create_task(
            group_flush_delayed(user_id, media_group_id)
        )
